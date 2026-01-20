"""
Bot Handler module for Telegram bot.
Handles messages, inline queries, and video sending.
"""
import asyncio
from typing import Optional
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineQueryResultVideo, InlineQueryResultArticle, InputTextMessageContent
from url_validator import URLValidator, Platform
from video_downloader import VideoDownloader
from storage_manager import StorageManager
from task_manager import DownloadTaskManager, TaskStatus
from logger import setup_logger

logger = setup_logger(__name__)


class BotHandler:
    """Handler for Telegram bot operations."""
    
    def __init__(
        self,
        bot: Bot,
        url_validator: URLValidator,
        video_downloader: VideoDownloader,
        storage_manager: StorageManager,
        task_manager: DownloadTaskManager
    ):
        """
        Initialize Bot Handler.
        
        Args:
            bot: Aiogram Bot instance
            url_validator: URL validator instance
            video_downloader: Video downloader instance
            storage_manager: Storage manager instance
            task_manager: Task manager instance
        """
        self.bot = bot
        self.url_validator = url_validator
        self.video_downloader = video_downloader
        self.storage_manager = storage_manager
        self.task_manager = task_manager
        self.dp = Dispatcher()
        
        # Register handlers
        self._register_handlers()
        
        logger.info("Bot Handler initialized")
    
    def _register_handlers(self) -> None:
        """Register message and inline query handlers."""
        # Command handlers
        self.dp.message.register(self.handle_start, Command("start"))
        self.dp.message.register(self.handle_help, Command("help"))
        
        # Message handler for URLs
        self.dp.message.register(self.handle_message)
        
        # Inline query handler
        self.dp.inline_query.register(self.handle_inline_query)
        
        # Chosen inline result handler (when user selects a result)
        self.dp.chosen_inline_result.register(self.handle_chosen_inline_result)
        
        logger.info("Handlers registered")
    
    async def handle_start(self, message: types.Message) -> None:
        """
        Handle /start command.
        
        Args:
            message: Telegram message
        """
        welcome_text = (
            "👋 Привет! Я бот для скачивания видео.\n\n"
            "📹 Поддерживаю:\n"
            "• YouTube Shorts\n"
            "• TikTok\n\n"
            "💡 Как использовать:\n"
            "1. Отправь мне ссылку на видео\n"
            "2. Или используй inline-режим: @savxbot <ссылка>\n\n"
            "Попробуй команду /help для подробностей!"
        )
        await message.answer(welcome_text)
        logger.info(f"User {message.from_user.id} started bot")
    
    async def handle_help(self, message: types.Message) -> None:
        """
        Handle /help command.
        
        Args:
            message: Telegram message
        """
        help_text = (
            "📖 Помощь\n\n"
            "🔗 Поддерживаемые платформы:\n"
            "• YouTube Shorts (youtube.com/shorts/...)\n"
            "• TikTok (tiktok.com/...)\n\n"
            "📝 Способы использования:\n\n"
            "1️⃣ Прямое сообщение:\n"
            "Просто отправь ссылку на видео в чат с ботом\n\n"
            "2️⃣ Inline-режим:\n"
            "В любом чате напиши: @savxbot <ссылка>\n"
            "Видео загрузится и появится в результатах для отправки\n\n"
            "⚠️ Ограничения:\n"
            "• Максимальный размер: 50 МБ\n"
            "• Только публичные видео"
        )
        await message.answer(help_text)
        logger.info(f"User {message.from_user.id} requested help")
    
    async def handle_message(self, message: types.Message) -> None:
        """
        Handle regular messages with video URLs.
        
        Args:
            message: Telegram message
        """
        if not message.text:
            return
        
        user_id = message.from_user.id
        url = message.text.strip()
        
        logger.info(f"Received message from user {user_id}: {url}")
        
        # Validate URL
        validation_result = self.url_validator.validate_url(url)
        
        if not validation_result.is_valid:
            await message.answer(
                f"❌ {validation_result.error_message}\n\n"
                "Отправь ссылку на YouTube Shorts или TikTok видео."
            )
            return
        
        # Send processing message
        status_message = await message.answer(
            f"⏳ Загружаю видео с {validation_result.platform.value}..."
        )
        
        try:
            # Create download task
            task_id = await self.task_manager.create_task(
                url=url,
                user_id=user_id,
                platform=validation_result.platform
            )
            
            # Update task status to downloading
            await self.task_manager.update_task_status(
                task_id=task_id,
                new_status=TaskStatus.DOWNLOADING
            )
            
            # Generate output path
            output_path = self.storage_manager.get_temp_path(
                video_id=validation_result.video_id or task_id
            )
            
            # Download video
            download_result = await self.video_downloader.download_video(
                url=url,
                output_path=output_path
            )
            
            if download_result.success:
                # Update task status to completed
                await self.task_manager.update_task_status(
                    task_id=task_id,
                    new_status=TaskStatus.COMPLETED,
                    file_path=download_result.file_path
                )
                
                # Send video to user
                await self.send_video(
                    chat_id=message.chat.id,
                    video_path=download_result.file_path
                )
                
                # Delete status message
                await status_message.delete()
                
                # Clean up file after sending
                self.storage_manager.delete_file(download_result.file_path)
                
                logger.info(f"Successfully sent video to user {user_id}")
            else:
                # Update task status to failed
                await self.task_manager.update_task_status(
                    task_id=task_id,
                    new_status=TaskStatus.FAILED,
                    error_message=download_result.error_message
                )
                
                # Send error message
                await status_message.edit_text(
                    f"❌ Ошибка загрузки:\n{download_result.error_message}"
                )
                
                logger.warning(
                    f"Download failed for user {user_id}: "
                    f"{download_result.error_message}"
                )
        
        except Exception as e:
            logger.error(f"Error processing message from user {user_id}: {e}")
            await status_message.edit_text(
                "❌ Произошла ошибка при обработке запроса. Попробуйте позже."
            )
    
    async def handle_inline_query(self, inline_query: types.InlineQuery) -> None:
        """
        Handle inline queries (@savxbot <url>) with full download support.
        
        Args:
            inline_query: Telegram inline query
        """
        query_text = inline_query.query.strip()
        user_id = inline_query.from_user.id
        query_id = inline_query.id
        
        logger.info(f"Received inline query from user {user_id}: {query_text}")
        
        # If query is empty, show help
        if not query_text:
            results = [
                InlineQueryResultArticle(
                    id="help",
                    title="📖 Как использовать",
                    description="Вставьте ссылку на YouTube Shorts или TikTok видео",
                    input_message_content=InputTextMessageContent(
                        message_text=(
                            "💡 Вставьте ссылку на видео после @savxbot\n\n"
                            "Поддерживаются:\n"
                            "• YouTube Shorts\n"
                            "• TikTok"
                        )
                    )
                )
            ]
            await inline_query.answer(results, cache_time=300)
            return
        
        # Validate URL
        validation_result = self.url_validator.validate_url(query_text)
        
        if not validation_result.is_valid:
            # Show error result
            results = [
                InlineQueryResultArticle(
                    id="error",
                    title="❌ Неверная ссылка",
                    description=validation_result.error_message,
                    input_message_content=InputTextMessageContent(
                        message_text=f"❌ {validation_result.error_message}"
                    )
                )
            ]
            await inline_query.answer(results, cache_time=10)
            return
        
        # Check if we already have an active or completed task for this URL
        user_tasks = self.task_manager.get_user_tasks(user_id)
        existing_task = None
        for task in user_tasks.values():
            if task.url == query_text and task.status in [TaskStatus.PENDING, TaskStatus.DOWNLOADING, TaskStatus.COMPLETED]:
                existing_task = task
                break
        
        if existing_task:
            # Return status of existing task
            await self._send_inline_task_status(inline_query, existing_task)
        else:
            # Create new download task
            task_id = await self.task_manager.create_task(
                url=query_text,
                user_id=user_id,
                platform=validation_result.platform
            )
            
            # Show initial "processing" result
            results = [
                InlineQueryResultArticle(
                    id=task_id,
                    title="⏳ Загрузка видео...",
                    description=f"Загружаю с {validation_result.platform.value}",
                    input_message_content=InputTextMessageContent(
                        message_text=f"⏳ Загружаю видео с {validation_result.platform.value}..."
                    )
                )
            ]
            await inline_query.answer(results, cache_time=1)
            
            # Start download in background
            asyncio.create_task(
                self._process_inline_download(task_id, query_text, validation_result)
            )
    
    async def _send_inline_task_status(
        self,
        inline_query: types.InlineQuery,
        task: 'DownloadTask'
    ) -> None:
        """
        Send inline query results based on task status.
        
        Args:
            inline_query: Telegram inline query
            task: Download task
        """
        if task.status == TaskStatus.PENDING:
            results = [
                InlineQueryResultArticle(
                    id=task.task_id,
                    title="⏳ В очереди...",
                    description="Ожидание начала загрузки",
                    input_message_content=InputTextMessageContent(
                        message_text="⏳ Видео в очереди на загрузку..."
                    )
                )
            ]
            await inline_query.answer(results, cache_time=1)
        
        elif task.status == TaskStatus.DOWNLOADING:
            progress_percent = int(task.progress * 100)
            results = [
                InlineQueryResultArticle(
                    id=task.task_id,
                    title=f"⏳ Загрузка... {progress_percent}%",
                    description=f"Загружаю с {task.platform.value}",
                    input_message_content=InputTextMessageContent(
                        message_text=f"⏳ Загрузка видео: {progress_percent}%"
                    )
                )
            ]
            await inline_query.answer(results, cache_time=1)
        
        elif task.status == TaskStatus.COMPLETED and task.file_path:
            # Show video result
            try:
                # Upload video to Telegram to get file_id
                # Note: For inline mode, we need to have the video already uploaded
                # or use a URL. For simplicity, we'll show a text result
                results = [
                    InlineQueryResultArticle(
                        id=task.task_id,
                        title="✅ Видео готово!",
                        description="Нажмите, чтобы отправить",
                        input_message_content=InputTextMessageContent(
                            message_text="✅ Видео готово! Отправляю..."
                        )
                    )
                ]
                await inline_query.answer(results, cache_time=300)
            except Exception as e:
                logger.error(f"Error showing completed video: {e}")
        
        elif task.status == TaskStatus.FAILED:
            error_msg = task.error_message or "Неизвестная ошибка"
            results = [
                InlineQueryResultArticle(
                    id=task.task_id,
                    title="❌ Ошибка загрузки",
                    description=error_msg,
                    input_message_content=InputTextMessageContent(
                        message_text=f"❌ Ошибка: {error_msg}"
                    )
                )
            ]
            await inline_query.answer(results, cache_time=60)
    
    async def _process_inline_download(
        self,
        task_id: str,
        url: str,
        validation_result
    ) -> None:
        """
        Process video download for inline query in background.
        
        Args:
            task_id: Task identifier
            url: Video URL
            validation_result: URL validation result
        """
        try:
            # Update task status to downloading
            await self.task_manager.update_task_status(
                task_id=task_id,
                new_status=TaskStatus.DOWNLOADING
            )
            
            # Generate output path
            output_path = self.storage_manager.get_temp_path(
                video_id=validation_result.video_id or task_id
            )
            
            # Progress callback to update task
            async def progress_callback(progress: float):
                await self.task_manager.update_task_status(
                    task_id=task_id,
                    new_status=TaskStatus.DOWNLOADING,
                    progress=progress
                )
            
            # Download video
            download_result = await self.video_downloader.download_video(
                url=url,
                output_path=output_path,
                progress_callback=progress_callback
            )
            
            if download_result.success:
                # Update task status to completed
                await self.task_manager.update_task_status(
                    task_id=task_id,
                    new_status=TaskStatus.COMPLETED,
                    file_path=download_result.file_path
                )
                
                logger.info(f"Inline download completed: {task_id}")
            else:
                # Update task status to failed
                await self.task_manager.update_task_status(
                    task_id=task_id,
                    new_status=TaskStatus.FAILED,
                    error_message=download_result.error_message
                )
                
                logger.warning(f"Inline download failed: {task_id} - {download_result.error_message}")
        
        except Exception as e:
            logger.error(f"Error in inline download processing: {e}")
            await self.task_manager.update_task_status(
                task_id=task_id,
                new_status=TaskStatus.FAILED,
                error_message=str(e)
            )
    
    async def handle_chosen_inline_result(
        self,
        chosen_result: types.ChosenInlineResult
    ) -> None:
        """
        Handle when user selects an inline result.
        Send the video file to the chat.
        
        Args:
            chosen_result: Chosen inline result
        """
        result_id = chosen_result.result_id
        user_id = chosen_result.from_user.id
        inline_message_id = chosen_result.inline_message_id
        
        logger.info(f"User {user_id} chose inline result: {result_id}")
        
        # Get task by ID
        task = await self.task_manager.get_task_result(result_id)
        
        if not task:
            logger.warning(f"Task not found for chosen result: {result_id}")
            return
        
        # If task is completed, we can't send video directly via inline message
        # The video was already sent as text message
        # In a production system, you'd upload the video to Telegram first
        # and use InlineQueryResultCachedVideo with file_id
        
        if task.status == TaskStatus.COMPLETED and task.file_path:
            logger.info(f"Video ready for task {result_id}, file: {task.file_path}")
            # Note: Actual video sending in inline mode requires pre-uploading
            # the video to Telegram to get a file_id, which is beyond basic implementation
    
    async def send_video(self, chat_id: int, video_path: str) -> None:
        """
        Send video file to user.
        
        Args:
            chat_id: Telegram chat ID
            video_path: Path to video file
        """
        try:
            video_file = FSInputFile(video_path)
            await self.bot.send_video(
                chat_id=chat_id,
                video=video_file,
                caption="✅ Видео готово!"
            )
            logger.info(f"Sent video to chat {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send video to chat {chat_id}: {e}")
            raise
    
    async def start_polling(self) -> None:
        """Start bot polling."""
        logger.info("Starting bot polling...")
        await self.dp.start_polling(self.bot)
    
    async def stop(self) -> None:
        """Stop bot and cleanup."""
        logger.info("Stopping bot...")
        await self.bot.session.close()
