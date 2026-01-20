# Implementation Plan: Video Downloader Bot

## Overview

Реализация Telegram бота для скачивания видео с YouTube Shorts и TikTok через inline-режим. Бот использует aiogram 3.x для работы с Telegram API и yt-dlp для загрузки видео. Реализация включает асинхронную обработку запросов, управление временными файлами и comprehensive тестирование с property-based tests.

## Tasks

- [x] 1. Настройка проекта и базовой структуры
  - Создать структуру директорий проекта
  - Настроить requirements.txt с зависимостями (aiogram, yt-dlp, hypothesis, aiofiles, pytest, pytest-asyncio)
  - Создать конфигурационный файл для переменных окружения
  - Настроить базовое логирование
  - _Requirements: 8.1, 8.2, 8.3_

- [ ] 2. Реализация URL Validator
  - [x] 2.1 Создать модуль url_validator.py с классами Platform, ValidationResult, URLValidator
    - Реализовать метод validate_url для проверки корректности URL
    - Реализовать метод get_platform для определения платформы (YouTube Shorts, TikTok, Unsupported)
    - Реализовать метод extract_video_id для извлечения ID видео
    - Поддержать различные форматы URLs (короткие ссылки, с параметрами)
    - _Requirements: 1.1, 2.1, 5.1, 5.2_

  - [ ]* 2.2 Написать property test для URL validation idempotence
    - **Property 1: URL Validation Idempotence**
    - **Validates: Requirements 1.1, 2.1, 5.1**

  - [ ]* 2.3 Написать property test для platform detection completeness
    - **Property 2: Platform Detection Completeness**
    - **Validates: Requirements 1.1, 2.1**

  - [ ]* 2.4 Написать property test для unsupported platform rejection
    - **Property 3: Unsupported Platform Rejection**
    - **Validates: Requirements 5.2**

  - [ ]* 2.5 Написать property test для invalid URL rejection
    - **Property 4: Invalid URL Rejection**
    - **Validates: Requirements 5.1**

  - [ ]* 2.6 Написать unit tests для URL validator
    - Тестировать конкретные примеры YouTube Shorts URLs
    - Тестировать конкретные примеры TikTok URLs
    - Тестировать edge cases (короткие ссылки, параметры запроса)
    - _Requirements: 1.1, 2.1, 5.1, 5.2_

- [ ] 3. Реализация Storage Manager
  - [x] 3.1 Создать модуль storage_manager.py с классом StorageManager
    - Реализовать метод get_temp_path для генерации уникальных путей
    - Реализовать метод delete_file для удаления файлов
    - Реализовать метод get_file_age для проверки возраста файлов
    - Реализовать метод cleanup_old_files для автоматической очистки
    - _Requirements: 6.1, 6.2, 6.3_

  - [ ]* 3.2 Написать property test для file cleanup preservation
    - **Property 8: File Cleanup Preservation**
    - **Validates: Requirements 6.2**

  - [ ]* 3.3 Написать property test для post-send cleanup
    - **Property 9: Post-Send Cleanup**
    - **Validates: Requirements 6.1**

  - [ ]* 3.4 Написать unit tests для storage manager
    - Тестировать создание временных путей
    - Тестировать удаление файлов
    - Тестировать cleanup с различными временными метками
    - _Requirements: 6.1, 6.2_

- [ ] 4. Реализация Download Task Manager
  - [x] 4.1 Создать модуль task_manager.py с классами TaskStatus, DownloadTask, DownloadTaskManager
    - Реализовать метод create_task для создания новых задач загрузки
    - Реализовать метод get_task_status для получения статуса задачи
    - Реализовать метод get_task_result для получения результата
    - Реализовать метод update_task_status для обновления статуса
    - Реализовать метод cleanup_completed_tasks для очистки старых задач
    - Использовать in-memory хранилище (dict) для задач
    - _Requirements: 3.2, 4.1, 4.2, 4.3, 4.4_

  - [ ]* 4.2 Написать property test для status transition validity
    - **Property 6: Status Transition Validity**
    - **Validates: Requirements 4.1, 4.2, 4.3**

  - [ ]* 4.3 Написать property test для error message presence
    - **Property 7: Error Message Presence**
    - **Validates: Requirements 4.4, 7.1**

  - [ ]* 4.4 Написать unit tests для task manager
    - Тестировать создание задач
    - Тестировать обновление статусов
    - Тестировать получение результатов
    - Тестировать cleanup завершенных задач
    - _Requirements: 4.1, 4.2, 4.3_

- [ ] 5. Checkpoint - Проверка базовых компонентов
  - Убедиться, что все тесты проходят
  - Проверить, что базовые компоненты работают корректно
  - Спросить пользователя, если возникли вопросы

- [ ] 6. Реализация Video Downloader
  - [x] 6.1 Создать модуль video_downloader.py с классами DownloadResult, VideoDownloader
    - Реализовать метод download_video с использованием yt-dlp
    - Настроить yt-dlp options (формат, размер файла, quiet mode)
    - Реализовать отслеживание прогресса загрузки
    - Реализовать обработку ошибок (network errors, invalid URL, file too large)
    - Использовать asyncio для асинхронной загрузки
    - _Requirements: 1.2, 2.2, 7.1, 7.2, 7.3_

  - [ ]* 6.2 Написать property test для file path consistency
    - **Property 5: File Path Consistency**
    - **Validates: Requirements 1.3, 2.3**

  - [ ]* 6.3 Написать unit tests для video downloader
    - Тестировать успешную загрузку (с mock yt-dlp)
    - Тестировать обработку ошибок
    - Тестировать проверку размера файла
    - _Requirements: 1.2, 2.2, 7.1, 7.2, 7.3_

- [ ] 7. Реализация Bot Handler - базовая структура
  - [x] 7.1 Создать модуль bot_handler.py с классом BotHandler
    - Настроить aiogram Bot и Dispatcher
    - Создать обработчик для inline queries
    - Создать обработчик для прямых сообщений
    - Реализовать метод send_video для отправки видео пользователям
    - Интегрировать URLValidator, VideoDownloader, StorageManager, DownloadTaskManager
    - _Requirements: 3.1, 3.5, 1.4, 2.4_

  - [ ]* 7.2 Написать unit tests для bot handler
    - Тестировать обработку inline queries (с mock Telegram API)
    - Тестировать обработку сообщений
    - Тестировать отправку видео
    - _Requirements: 3.1, 3.5_

- [ ] 8. Реализация inline-режима с обновлением статуса
  - [x] 8.1 Расширить BotHandler для поддержки inline-режима
    - Реализовать метод handle_inline_query для обработки @savxbot запросов
    - Реализовать метод update_inline_result для обновления статуса в реальном времени
    - Создать InlineQueryResultVideo для отображения готовых видео
    - Создать InlineQueryResultArticle для отображения статуса загрузки
    - Реализовать периодическое обновление inline-результатов во время загрузки
    - _Requirements: 3.2, 3.3, 3.4, 4.1, 4.2, 4.3_

  - [ ]* 8.2 Написать property test для link processing initiation
    - **Property 10: Link Processing Initiation**
    - **Validates: Requirements 3.2**

  - [ ]* 8.3 Написать property test для status display in inline results
    - **Property 11: Status Display in Inline Results**
    - **Validates: Requirements 3.3, 4.2**

  - [ ]* 8.4 Написать property test для completed video display
    - **Property 12: Completed Video Display**
    - **Validates: Requirements 3.4**

  - [ ]* 8.5 Написать unit tests для inline-режима
    - Тестировать обработку inline queries с валидными ссылками
    - Тестировать отображение статуса загрузки
    - Тестировать отображение готовых видео
    - _Requirements: 3.2, 3.3, 3.4_

- [ ] 9. Checkpoint - Проверка интеграции компонентов
  - Убедиться, что все компоненты интегрированы корректно
  - Проверить, что inline-режим работает с реальными (или mock) Telegram API вызовами
  - Убедиться, что все тесты проходят
  - Спросить пользователя, если возникли вопросы

- [ ] 10. Реализация фоновых задач и cleanup
  - [x] 10.1 Создать модуль background_tasks.py для периодических задач
    - Реализовать scheduler для автоматической очистки старых файлов
    - Реализовать scheduler для очистки завершенных задач
    - Использовать asyncio для фоновых задач
    - Настроить интервалы очистки из конфигурации
    - _Requirements: 6.1, 6.2_

  - [ ]* 10.2 Написать unit tests для background tasks
    - Тестировать периодическую очистку файлов
    - Тестировать очистку завершенных задач
    - _Requirements: 6.1, 6.2_

- [ ] 11. Создание главного файла приложения
  - [x] 11.1 Создать main.py для запуска бота
    - Загрузить конфигурацию из переменных окружения
    - Инициализировать все компоненты (BotHandler, StorageManager, etc.)
    - Запустить фоновые задачи (cleanup schedulers)
    - Запустить бота с polling или webhook
    - Добавить graceful shutdown
    - _Requirements: 8.1, 8.2, 8.3_

  - [ ]* 11.2 Написать integration tests для end-to-end flow
    - Тестировать полный цикл: получение ссылки → загрузка → отправка
    - Тестировать inline-режим end-to-end
    - Тестировать cleanup после отправки
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 3.2, 3.3, 3.4, 3.5_

- [ ] 12. Документация и финальная проверка
  - [x] 12.1 Создать README.md с инструкциями
    - Описать установку зависимостей
    - Описать настройку переменных окружения (TELEGRAM_BOT_TOKEN, BOT_USERNAME)
    - Описать запуск бота
    - Описать использование бота (inline-режим, прямые сообщения)
    - Добавить примеры использования

  - [x] 12.2 Создать .env.example с примерами конфигурации
    - TELEGRAM_BOT_TOKEN=your_token_here
    - BOT_USERNAME=savxbot
    - TEMP_DIR=./temp
    - MAX_FILE_SIZE_MB=50
    - CLEANUP_INTERVAL_HOURS=1
    - MAX_FILE_AGE_HOURS=1

  - [x] 12.3 Финальная проверка
    - Убедиться, что все тесты проходят
    - Проверить, что бот работает с реальным Telegram API (если возможно)
    - Проверить, что все требования выполнены

## Notes

- Задачи, помеченные `*`, являются опциональными и могут быть пропущены для более быстрого MVP
- Каждая задача ссылается на конкретные требования для отслеживаемости
- Checkpoints обеспечивают инкрементальную валидацию
- Property tests валидируют универсальные свойства корректности
- Unit tests валидируют конкретные примеры и edge cases
- Используется Python 3.10+ с aiogram 3.x и Hypothesis для property-based testing
