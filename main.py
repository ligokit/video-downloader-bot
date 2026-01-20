"""
Main entry point for Video Downloader Bot.
Initializes all components and starts the bot.
"""
import asyncio
import signal
import sys
from aiogram import Bot
from config import BotConfig
from url_validator import URLValidator
from video_downloader import VideoDownloader
from storage_manager import StorageManager
from task_manager import DownloadTaskManager
from bot_handler import BotHandler
from background_tasks import BackgroundTaskScheduler
from logger import setup_logger

logger = setup_logger(__name__)


class Application:
    """Main application class."""
    
    def __init__(self):
        """Initialize application."""
        self.config: BotConfig = None
        self.bot: Bot = None
        self.bot_handler: BotHandler = None
        self.background_scheduler: BackgroundTaskScheduler = None
        self.shutdown_event = asyncio.Event()
    
    async def initialize(self) -> None:
        """Initialize all components."""
        try:
            logger.info("Initializing Video Downloader Bot...")
            
            # Load configuration
            logger.info("Loading configuration...")
            self.config = BotConfig.from_env()
            logger.info(f"Bot username: {self.config.bot_username}")
            logger.info(f"Temp directory: {self.config.temp_dir}")
            logger.info(f"Max file size: {self.config.max_file_size_mb}MB")
            
            # Initialize components
            logger.info("Initializing components...")
            
            # Create Bot instance
            self.bot = Bot(token=self.config.telegram_token)
            
            # Create URL Validator
            url_validator = URLValidator()
            
            # Create Storage Manager
            storage_manager = StorageManager(temp_dir=self.config.temp_dir)
            
            # Create Task Manager
            task_manager = DownloadTaskManager()
            
            # Create Video Downloader
            video_downloader = VideoDownloader(
                yt_dlp_options=self.config.yt_dlp_options,
                max_file_size_mb=self.config.max_file_size_mb
            )
            
            # Create Bot Handler
            self.bot_handler = BotHandler(
                bot=self.bot,
                url_validator=url_validator,
                video_downloader=video_downloader,
                storage_manager=storage_manager,
                task_manager=task_manager
            )
            
            # Create Background Task Scheduler
            self.background_scheduler = BackgroundTaskScheduler(
                storage_manager=storage_manager,
                task_manager=task_manager,
                file_cleanup_interval_hours=self.config.cleanup_interval_hours,
                task_cleanup_interval_minutes=30,  # 30 minutes for tasks
                max_file_age_hours=self.config.max_file_age_hours,
                max_task_age_minutes=60  # 1 hour for tasks
            )
            
            logger.info("All components initialized successfully")
        
        except Exception as e:
            logger.error(f"Failed to initialize application: {e}")
            raise
    
    async def start(self) -> None:
        """Start the application."""
        try:
            logger.info("Starting application...")
            
            # Start background tasks
            logger.info("Starting background cleanup tasks...")
            await self.background_scheduler.start()
            
            # Start bot polling
            logger.info("Starting bot polling...")
            logger.info("Bot is ready! Press Ctrl+C to stop.")
            
            # Run bot polling
            await self.bot_handler.start_polling()
        
        except Exception as e:
            logger.error(f"Error during application startup: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Graceful shutdown of the application."""
        logger.info("Shutting down application...")
        
        try:
            # Stop background tasks
            if self.background_scheduler:
                logger.info("Stopping background tasks...")
                await self.background_scheduler.stop()
            
            # Stop bot
            if self.bot_handler:
                logger.info("Stopping bot...")
                await self.bot_handler.stop()
            
            logger.info("Application shutdown complete")
        
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, initiating shutdown...")
            self.shutdown_event.set()
        
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main() -> None:
    """Main entry point."""
    app = Application()
    
    try:
        # Initialize application
        await app.initialize()
        
        # Setup signal handlers for graceful shutdown
        app.setup_signal_handlers()
        
        # Start application
        start_task = asyncio.create_task(app.start())
        
        # Wait for shutdown signal
        await app.shutdown_event.wait()
        
        # Cancel start task if still running
        if not start_task.done():
            start_task.cancel()
            try:
                await start_task
            except asyncio.CancelledError:
                pass
        
        # Perform graceful shutdown
        await app.shutdown()
    
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
        await app.shutdown()
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        await app.shutdown()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.error(f"Application crashed: {e}")
        sys.exit(1)
