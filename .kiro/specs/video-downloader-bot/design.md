# Design Document: Video Downloader Bot

## Overview

Telegram бот для скачивания видео с YouTube Shorts и TikTok, работающий через inline-режим. Бот использует библиотеку yt-dlp для загрузки видео и Telegram Bot API для взаимодействия с пользователями. Архитектура построена на асинхронной обработке запросов с временным хранением файлов.

## Architecture

Система состоит из следующих основных слоев:

1. **Telegram Interface Layer** - обработка входящих сообщений и inline-запросов
2. **URL Processing Layer** - валидация и парсинг ссылок
3. **Download Layer** - загрузка видео через yt-dlp
4. **Storage Layer** - временное хранение загруженных файлов
5. **Cleanup Layer** - автоматическая очистка старых файлов

```
┌─────────────────────────────────────────┐
│         Telegram Bot API                │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      Bot Handler (aiogram/python-telegram-bot)
│  - Inline Query Handler                 │
│  - Message Handler                      │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│       URL Validator & Parser            │
│  - YouTube Shorts detection             │
│  - TikTok URL detection                 │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      Video Downloader (yt-dlp)          │
│  - Download manager                     │
│  - Progress tracking                    │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      Temporary Storage                  │
│  - File management                      │
│  - Cleanup scheduler                    │
└─────────────────────────────────────────┘
```

## Components and Interfaces

### 1. Bot Handler

**Responsibilities:**
- Обработка inline-запросов от пользователей
- Обработка прямых сообщений с ссылками
- Отправка видео пользователям
- Обновление статуса загрузки в inline-результатах

**Interface:**
```python
class BotHandler:
    async def handle_inline_query(query: InlineQuery) -> None
    async def handle_message(message: Message) -> None
    async def send_video(chat_id: int, video_path: str) -> None
    async def update_inline_result(query_id: str, status: str) -> None
```

### 2. URL Validator

**Responsibilities:**
- Определение типа платформы по URL
- Валидация корректности ссылок
- Извлечение идентификаторов видео

**Interface:**
```python
class URLValidator:
    def validate_url(url: str) -> ValidationResult
    def get_platform(url: str) -> Platform
    def extract_video_id(url: str) -> str
```

**Platform Enum:**
```python
class Platform(Enum):
    YOUTUBE_SHORTS = "youtube_shorts"
    TIKTOK = "tiktok"
    UNSUPPORTED = "unsupported"
```

### 3. Video Downloader

**Responsibilities:**
- Загрузка видео через yt-dlp
- Отслеживание прогресса загрузки
- Обработка ошибок загрузки

**Interface:**
```python
class VideoDownloader:
    async def download_video(url: str, output_path: str) -> DownloadResult
    async def get_download_progress(download_id: str) -> float
    def cancel_download(download_id: str) -> None
```

**DownloadResult:**
```python
@dataclass
class DownloadResult:
    success: bool
    file_path: Optional[str]
    error_message: Optional[str]
    file_size: int
```

### 4. Storage Manager

**Responsibilities:**
- Управление временными файлами
- Генерация уникальных путей для файлов
- Очистка устаревших файлов

**Interface:**
```python
class StorageManager:
    def get_temp_path(video_id: str) -> str
    def cleanup_old_files(max_age_hours: int) -> int
    def delete_file(file_path: str) -> bool
    def get_file_age(file_path: str) -> timedelta
```

### 5. Download Task Manager

**Responsibilities:**
- Управление активными задачами загрузки
- Кэширование результатов для inline-запросов
- Отслеживание статуса задач

**Interface:**
```python
class DownloadTaskManager:
    async def create_task(url: str, user_id: int) -> str  # returns task_id
    async def get_task_status(task_id: str) -> TaskStatus
    async def get_task_result(task_id: str) -> Optional[DownloadResult]
    def cleanup_completed_tasks(max_age_minutes: int) -> None
```

**TaskStatus:**
```python
class TaskStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
```

## Data Models

### Download Task

```python
@dataclass
class DownloadTask:
    task_id: str
    url: str
    user_id: int
    platform: Platform
    status: TaskStatus
    created_at: datetime
    completed_at: Optional[datetime]
    file_path: Optional[str]
    error_message: Optional[str]
    progress: float  # 0.0 to 1.0
```

### Configuration

```python
@dataclass
class BotConfig:
    telegram_token: str
    bot_username: str
    temp_dir: str
    max_file_size_mb: int
    cleanup_interval_hours: int
    max_file_age_hours: int
    yt_dlp_options: dict
```

## Correctness Properties

*Свойство корректности - это характеристика или поведение, которое должно выполняться во всех валидных выполнениях системы. Свойства служат мостом между человекочитаемыми спецификациями и машинно-проверяемыми гарантиями корректности.*

### Property 1: URL Validation Idempotence

*For any* URL string, повторная валидация одного и того же URL должна возвращать идентичный результат (платформа, валидность, video_id).

**Validates: Requirements 1.1, 2.1, 5.1**

### Property 2: Platform Detection Completeness

*For any* валидная ссылка YouTube Shorts или TikTok, функция get_platform должна корректно определить соответствующую платформу (YOUTUBE_SHORTS или TIKTOK) и не возвращать UNSUPPORTED.

**Validates: Requirements 1.1, 2.1**

### Property 3: Unsupported Platform Rejection

*For any* URL, который не является YouTube Shorts или TikTok ссылкой, валидатор должен вернуть Platform.UNSUPPORTED и предоставить сообщение о неподдерживаемой платформе.

**Validates: Requirements 5.2**

### Property 4: Invalid URL Rejection

*For any* строка, которая не является валидным URL, валидатор должен отклонить её и предоставить понятное сообщение об ошибке.

**Validates: Requirements 5.1**

### Property 5: File Path Consistency

*For any* download task со статусом COMPLETED, поле file_path должно содержать путь к существующему файлу в файловой системе.

**Validates: Requirements 1.3, 2.3**

### Property 6: Status Transition Validity

*For any* download task, переходы статусов должны следовать валидной последовательности: PENDING → DOWNLOADING → (COMPLETED | FAILED). Обратные переходы и пропуски промежуточных состояний невозможны.

**Validates: Requirements 4.1, 4.2, 4.3**

### Property 7: Error Message Presence

*For any* download task со статусом FAILED, поле error_message должно содержать непустую строку с описанием причины ошибки.

**Validates: Requirements 4.4, 7.1**

### Property 8: File Cleanup Preservation

*For any* файл в временном хранилище, если время его создания меньше max_age_hours, то операция cleanup не должна удалять этот файл.

**Validates: Requirements 6.2**

### Property 9: Post-Send Cleanup

*For any* download task, после успешной отправки видео пользователю, соответствующий временный файл должен быть удален из файловой системы.

**Validates: Requirements 6.1**

### Property 10: Link Processing Initiation

*For any* валидная ссылка, отправленная через inline-режим (@savxbot), должна быть создана соответствующая download task со статусом PENDING или DOWNLOADING.

**Validates: Requirements 3.2**

### Property 11: Status Display in Inline Results

*For any* активная download task (статус PENDING или DOWNLOADING), inline-результаты должны содержать информацию о текущем статусе загрузки.

**Validates: Requirements 3.3, 4.2**

### Property 12: Completed Video Display

*For any* download task со статусом COMPLETED, inline-результаты должны содержать превью видео и возможность его отправки.

**Validates: Requirements 3.4**

## Error Handling

### Download Errors

1. **Network Errors**: Повторная попытка с экспоненциальной задержкой (max 3 попытки)
2. **Invalid URL**: Немедленный возврат ошибки пользователю
3. **Video Unavailable**: Сообщение о недоступности контента
4. **File Too Large**: Проверка размера перед загрузкой, отклонение если > max_file_size_mb

### Telegram API Errors

1. **Rate Limiting**: Очередь запросов с задержками
2. **File Upload Errors**: Повторная попытка отправки
3. **Invalid Bot Token**: Критическая ошибка, остановка бота

### Storage Errors

1. **Disk Full**: Принудительная очистка старых файлов, сообщение об ошибке
2. **Permission Denied**: Логирование ошибки, сообщение пользователю
3. **File Not Found**: Повторная загрузка видео

## Testing Strategy

### Unit Tests

Тестирование отдельных компонентов:

1. **URL Validator Tests**
   - Валидные YouTube Shorts URLs
   - Валидные TikTok URLs
   - Невалидные URLs
   - Edge cases (короткие ссылки, параметры запроса)

2. **Storage Manager Tests**
   - Создание временных путей
   - Удаление файлов
   - Cleanup старых файлов
   - Проверка возраста файлов

3. **Task Manager Tests**
   - Создание задач
   - Получение статуса
   - Обновление статуса
   - Cleanup завершенных задач

### Property-Based Tests

Тестирование универсальных свойств с использованием библиотеки **Hypothesis** (Python):

**Configuration**: Минимум 100 итераций на тест

**Dual Testing Approach**: Unit tests и property tests дополняют друг друга. Unit tests проверяют конкретные примеры и edge cases, property tests проверяют универсальные свойства на большом количестве сгенерированных входных данных.

1. **Property Test 1: URL Validation Idempotence**
   - **Feature: video-downloader-bot, Property 1**: URL validation idempotence
   - Генерация случайных URL строк
   - Проверка, что повторная валидация возвращает идентичный результат

2. **Property Test 2: Platform Detection Completeness**
   - **Feature: video-downloader-bot, Property 2**: Platform detection completeness
   - Генерация валидных YouTube Shorts и TikTok URLs различных форматов
   - Проверка корректного определения платформы (не UNSUPPORTED)

3. **Property Test 3: Unsupported Platform Rejection**
   - **Feature: video-downloader-bot, Property 3**: Unsupported platform rejection
   - Генерация URLs других платформ (Instagram, Facebook, обычный YouTube)
   - Проверка возврата UNSUPPORTED с сообщением

4. **Property Test 4: Invalid URL Rejection**
   - **Feature: video-downloader-bot, Property 4**: Invalid URL rejection
   - Генерация невалидных строк (не URLs)
   - Проверка отклонения с понятным сообщением

5. **Property Test 5: File Path Consistency**
   - **Feature: video-downloader-bot, Property 5**: File path consistency
   - Генерация завершенных download tasks
   - Проверка существования файлов по указанным путям

6. **Property Test 6: Status Transition Validity**
   - **Feature: video-downloader-bot, Property 6**: Status transition validity
   - Генерация последовательностей обновлений статуса
   - Проверка валидности всех переходов (PENDING → DOWNLOADING → COMPLETED/FAILED)

7. **Property Test 7: Error Message Presence**
   - **Feature: video-downloader-bot, Property 7**: Error message presence
   - Генерация failed download tasks
   - Проверка наличия непустых error_message

8. **Property Test 8: File Cleanup Preservation**
   - **Feature: video-downloader-bot, Property 8**: File cleanup preservation
   - Генерация файлов с различными временными метками
   - Проверка, что файлы моложе max_age_hours не удаляются

9. **Property Test 9: Post-Send Cleanup**
   - **Feature: video-downloader-bot, Property 9**: Post-send cleanup
   - Генерация сценариев успешной отправки видео
   - Проверка удаления временных файлов

10. **Property Test 10: Link Processing Initiation**
    - **Feature: video-downloader-bot, Property 10**: Link processing initiation
    - Генерация валидных ссылок через inline-режим
    - Проверка создания download task

11. **Property Test 11: Status Display in Inline Results**
    - **Feature: video-downloader-bot, Property 11**: Status display in inline results
    - Генерация активных download tasks
    - Проверка наличия статуса в inline-результатах

12. **Property Test 12: Completed Video Display**
    - **Feature: video-downloader-bot, Property 12**: Completed video display
    - Генерация завершенных download tasks
    - Проверка наличия превью в inline-результатах

### Integration Tests

1. **End-to-End Download Flow**
   - Отправка ссылки → загрузка → отправка видео
   - Проверка всей цепочки обработки

2. **Inline Mode Flow**
   - Inline query → создание задачи → обновление статуса → отправка результата

3. **Cleanup Flow**
   - Создание файлов → ожидание → cleanup → проверка удаления

### Test Environment

- **Mock Telegram API**: Использование aiogram testing utilities или python-telegram-bot test framework
- **Mock yt-dlp**: Для быстрых тестов без реальных загрузок
- **Temporary Test Directory**: Изолированная директория для тестовых файлов
- **Test Configuration**: Отдельный конфиг с уменьшенными таймаутами и лимитами

## Implementation Notes

### Technology Stack

- **Python 3.10+**: Основной язык
- **aiogram 3.x** или **python-telegram-bot 20.x**: Telegram Bot framework
- **yt-dlp**: Загрузка видео
- **asyncio**: Асинхронная обработка
- **aiofiles**: Асинхронная работа с файлами
- **Hypothesis**: Property-based testing

### yt-dlp Configuration

```python
YT_DLP_OPTIONS = {
    'format': 'best[ext=mp4]',
    'outtmpl': '%(id)s.%(ext)s',
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'max_filesize': 50 * 1024 * 1024,  # 50 MB (Telegram limit)
}
```

### Deployment Considerations

- **Environment Variables**: TELEGRAM_BOT_TOKEN, BOT_USERNAME
- **Persistent Storage**: Не требуется (только временные файлы)
- **Background Tasks**: Cleanup scheduler должен работать периодически
- **Logging**: Структурированное логирование всех операций
- **Monitoring**: Метрики загрузок, ошибок, времени обработки
