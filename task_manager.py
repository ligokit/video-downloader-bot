"""
Task Manager module for managing download tasks.
Tracks status, progress, and results of video downloads.
"""
import uuid
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional
from url_validator import Platform
from logger import setup_logger

logger = setup_logger(__name__)


class TaskStatus(Enum):
    """Status of a download task."""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DownloadTask:
    """Represents a video download task."""
    task_id: str
    url: str
    user_id: int
    platform: Platform
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    progress: float = 0.0  # 0.0 to 1.0


class DownloadTaskManager:
    """Manager for download tasks."""
    
    # Valid status transitions
    VALID_TRANSITIONS = {
        TaskStatus.PENDING: [TaskStatus.DOWNLOADING, TaskStatus.FAILED],
        TaskStatus.DOWNLOADING: [TaskStatus.COMPLETED, TaskStatus.FAILED],
        TaskStatus.COMPLETED: [],  # Terminal state
        TaskStatus.FAILED: [],  # Terminal state
    }
    
    def __init__(self):
        """Initialize Task Manager with in-memory storage."""
        self.tasks: Dict[str, DownloadTask] = {}
        logger.info("Task Manager initialized")
    
    async def create_task(self, url: str, user_id: int, platform: Platform) -> str:
        """
        Create a new download task.
        
        Args:
            url: Video URL
            user_id: Telegram user ID
            platform: Video platform
            
        Returns:
            Task ID
        """
        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        # Create task
        task = DownloadTask(
            task_id=task_id,
            url=url,
            user_id=user_id,
            platform=platform,
            status=TaskStatus.PENDING
        )
        
        # Store task
        self.tasks[task_id] = task
        
        logger.info(f"Created task {task_id} for user {user_id}, platform: {platform.value}")
        return task_id
    
    async def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        Get status of a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            TaskStatus or None if task not found
        """
        task = self.tasks.get(task_id)
        if task:
            return task.status
        
        logger.warning(f"Task {task_id} not found")
        return None
    
    async def get_task_result(self, task_id: str) -> Optional[DownloadTask]:
        """
        Get complete task information.
        
        Args:
            task_id: Task identifier
            
        Returns:
            DownloadTask or None if not found
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.warning(f"Task {task_id} not found")
        return task
    
    async def update_task_status(
        self,
        task_id: str,
        new_status: TaskStatus,
        file_path: Optional[str] = None,
        error_message: Optional[str] = None,
        progress: Optional[float] = None
    ) -> bool:
        """
        Update task status with validation of state transitions.
        
        Args:
            task_id: Task identifier
            new_status: New status to set
            file_path: Optional file path (for COMPLETED status)
            error_message: Optional error message (for FAILED status)
            progress: Optional progress value (0.0 to 1.0)
            
        Returns:
            True if update successful, False otherwise
        """
        task = self.tasks.get(task_id)
        if not task:
            logger.error(f"Cannot update task {task_id}: task not found")
            return False
        
        # Validate status transition
        current_status = task.status
        if not self._is_valid_transition(current_status, new_status):
            logger.error(
                f"Invalid status transition for task {task_id}: "
                f"{current_status.value} -> {new_status.value}"
            )
            return False
        
        # Update status
        task.status = new_status
        
        # Update additional fields
        if file_path:
            task.file_path = file_path
        
        if error_message:
            task.error_message = error_message
        
        if progress is not None:
            task.progress = max(0.0, min(1.0, progress))  # Clamp to [0.0, 1.0]
        
        # Set completion time for terminal states
        if new_status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            task.completed_at = datetime.now()
        
        logger.info(
            f"Updated task {task_id}: {current_status.value} -> {new_status.value}"
        )
        return True
    
    def _is_valid_transition(
        self,
        current_status: TaskStatus,
        new_status: TaskStatus
    ) -> bool:
        """
        Check if status transition is valid.
        
        Args:
            current_status: Current task status
            new_status: Desired new status
            
        Returns:
            True if transition is valid
        """
        valid_next_states = self.VALID_TRANSITIONS.get(current_status, [])
        return new_status in valid_next_states
    
    def cleanup_completed_tasks(self, max_age_minutes: int) -> int:
        """
        Remove completed/failed tasks older than specified age.
        
        Args:
            max_age_minutes: Maximum age in minutes
            
        Returns:
            Number of tasks removed
        """
        removed_count = 0
        max_age = timedelta(minutes=max_age_minutes)
        current_time = datetime.now()
        
        # Find tasks to remove
        tasks_to_remove = []
        for task_id, task in self.tasks.items():
            # Only cleanup terminal states
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                if task.completed_at:
                    age = current_time - task.completed_at
                    if age > max_age:
                        tasks_to_remove.append(task_id)
        
        # Remove tasks
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
            removed_count += 1
        
        if removed_count > 0:
            logger.info(
                f"Cleaned up {removed_count} completed tasks "
                f"(max age: {max_age_minutes} minutes)"
            )
        
        return removed_count
    
    def get_active_tasks(self) -> Dict[str, DownloadTask]:
        """
        Get all active (non-terminal) tasks.
        
        Returns:
            Dictionary of active tasks
        """
        active = {
            task_id: task
            for task_id, task in self.tasks.items()
            if task.status in [TaskStatus.PENDING, TaskStatus.DOWNLOADING]
        }
        return active
    
    def get_user_tasks(self, user_id: int) -> Dict[str, DownloadTask]:
        """
        Get all tasks for a specific user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dictionary of user's tasks
        """
        user_tasks = {
            task_id: task
            for task_id, task in self.tasks.items()
            if task.user_id == user_id
        }
        return user_tasks
