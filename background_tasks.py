"""
Background Tasks module for periodic cleanup operations.
Handles automatic cleanup of old files and completed tasks.
"""
import asyncio
from typing import Optional
from storage_manager import StorageManager
from task_manager import DownloadTaskManager
from logger import setup_logger

logger = setup_logger(__name__)


class BackgroundTaskScheduler:
    """Scheduler for background cleanup tasks."""
    
    def __init__(
        self,
        storage_manager: StorageManager,
        task_manager: DownloadTaskManager,
        file_cleanup_interval_hours: int = 1,
        task_cleanup_interval_minutes: int = 30,
        max_file_age_hours: int = 1,
        max_task_age_minutes: int = 60
    ):
        """
        Initialize Background Task Scheduler.
        
        Args:
            storage_manager: Storage manager instance
            task_manager: Task manager instance
            file_cleanup_interval_hours: How often to run file cleanup (hours)
            task_cleanup_interval_minutes: How often to run task cleanup (minutes)
            max_file_age_hours: Maximum age of files before deletion (hours)
            max_task_age_minutes: Maximum age of completed tasks before deletion (minutes)
        """
        self.storage_manager = storage_manager
        self.task_manager = task_manager
        self.file_cleanup_interval_hours = file_cleanup_interval_hours
        self.task_cleanup_interval_minutes = task_cleanup_interval_minutes
        self.max_file_age_hours = max_file_age_hours
        self.max_task_age_minutes = max_task_age_minutes
        
        # Task handles for cancellation
        self._file_cleanup_task: Optional[asyncio.Task] = None
        self._task_cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(
            f"Background Task Scheduler initialized "
            f"(file cleanup: every {file_cleanup_interval_hours}h, "
            f"task cleanup: every {task_cleanup_interval_minutes}m)"
        )
    
    async def start(self) -> None:
        """Start all background tasks."""
        if self._running:
            logger.warning("Background tasks already running")
            return
        
        self._running = True
        
        # Start file cleanup task
        self._file_cleanup_task = asyncio.create_task(
            self._file_cleanup_loop()
        )
        
        # Start task cleanup task
        self._task_cleanup_task = asyncio.create_task(
            self._task_cleanup_loop()
        )
        
        logger.info("Background tasks started")
    
    async def stop(self) -> None:
        """Stop all background tasks."""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel tasks
        if self._file_cleanup_task:
            self._file_cleanup_task.cancel()
            try:
                await self._file_cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self._task_cleanup_task:
            self._task_cleanup_task.cancel()
            try:
                await self._task_cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Background tasks stopped")
    
    async def _file_cleanup_loop(self) -> None:
        """Periodic file cleanup loop."""
        logger.info("File cleanup loop started")
        
        while self._running:
            try:
                # Run cleanup
                deleted_count = self.storage_manager.cleanup_old_files(
                    max_age_hours=self.max_file_age_hours
                )
                
                if deleted_count > 0:
                    logger.info(f"File cleanup: deleted {deleted_count} old files")
                
                # Wait for next interval
                await asyncio.sleep(self.file_cleanup_interval_hours * 3600)
            
            except asyncio.CancelledError:
                logger.info("File cleanup loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in file cleanup loop: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(60)
    
    async def _task_cleanup_loop(self) -> None:
        """Periodic task cleanup loop."""
        logger.info("Task cleanup loop started")
        
        while self._running:
            try:
                # Run cleanup
                deleted_count = self.task_manager.cleanup_completed_tasks(
                    max_age_minutes=self.max_task_age_minutes
                )
                
                if deleted_count > 0:
                    logger.info(f"Task cleanup: removed {deleted_count} old tasks")
                
                # Wait for next interval
                await asyncio.sleep(self.task_cleanup_interval_minutes * 60)
            
            except asyncio.CancelledError:
                logger.info("Task cleanup loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in task cleanup loop: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(60)
    
    async def run_file_cleanup_now(self) -> int:
        """
        Run file cleanup immediately (manual trigger).
        
        Returns:
            Number of files deleted
        """
        logger.info("Running manual file cleanup")
        deleted_count = self.storage_manager.cleanup_old_files(
            max_age_hours=self.max_file_age_hours
        )
        logger.info(f"Manual file cleanup: deleted {deleted_count} files")
        return deleted_count
    
    async def run_task_cleanup_now(self) -> int:
        """
        Run task cleanup immediately (manual trigger).
        
        Returns:
            Number of tasks removed
        """
        logger.info("Running manual task cleanup")
        deleted_count = self.task_manager.cleanup_completed_tasks(
            max_age_minutes=self.max_task_age_minutes
        )
        logger.info(f"Manual task cleanup: removed {deleted_count} tasks")
        return deleted_count
    
    def is_running(self) -> bool:
        """Check if background tasks are running."""
        return self._running
