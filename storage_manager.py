"""
Storage Manager module for managing temporary video files.
Handles file creation, deletion, and cleanup of old files.
"""
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List
from logger import setup_logger

logger = setup_logger(__name__)


class StorageManager:
    """Manager for temporary video file storage."""
    
    def __init__(self, temp_dir: str):
        """
        Initialize Storage Manager.
        
        Args:
            temp_dir: Directory path for temporary files
        """
        self.temp_dir = Path(temp_dir)
        self._ensure_temp_dir_exists()
    
    def _ensure_temp_dir_exists(self) -> None:
        """Create temporary directory if it doesn't exist."""
        try:
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Temporary directory ready: {self.temp_dir}")
        except Exception as e:
            logger.error(f"Failed to create temporary directory: {e}")
            raise
    
    def get_temp_path(self, video_id: str, extension: str = "mp4") -> str:
        """
        Generate unique temporary file path for a video.
        
        Args:
            video_id: Video identifier
            extension: File extension (default: mp4)
            
        Returns:
            Absolute path to temporary file
        """
        # Create unique filename using video_id and UUID to avoid collisions
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{video_id}_{unique_id}.{extension}"
        file_path = self.temp_dir / filename
        
        logger.debug(f"Generated temp path: {file_path}")
        return str(file_path.absolute())
    
    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            file_path: Path to file to delete
            
        Returns:
            True if file was deleted, False otherwise
        """
        try:
            path = Path(file_path)
            if path.exists() and path.is_file():
                path.unlink()
                logger.info(f"Deleted file: {file_path}")
                return True
            else:
                logger.warning(f"File not found or not a file: {file_path}")
                return False
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            return False
    
    def get_file_age(self, file_path: str) -> timedelta:
        """
        Get the age of a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            timedelta representing file age
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"File does not exist: {file_path}")
                return timedelta(days=999)  # Return large value for non-existent files
            
            # Get file modification time
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            age = datetime.now() - mtime
            
            logger.debug(f"File {file_path} age: {age}")
            return age
        except Exception as e:
            logger.error(f"Failed to get file age for {file_path}: {e}")
            return timedelta(days=999)
    
    def cleanup_old_files(self, max_age_hours: int) -> int:
        """
        Clean up files older than specified age.
        
        Args:
            max_age_hours: Maximum age in hours before file is deleted
            
        Returns:
            Number of files deleted
        """
        deleted_count = 0
        max_age = timedelta(hours=max_age_hours)
        
        try:
            # Iterate through all files in temp directory
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file():
                    file_age = self.get_file_age(str(file_path))
                    
                    if file_age > max_age:
                        if self.delete_file(str(file_path)):
                            deleted_count += 1
            
            logger.info(f"Cleanup completed: {deleted_count} files deleted (max age: {max_age_hours}h)")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        return deleted_count
    
    def get_all_files(self) -> List[str]:
        """
        Get list of all files in temporary directory.
        
        Returns:
            List of file paths
        """
        try:
            files = [str(f.absolute()) for f in self.temp_dir.iterdir() if f.is_file()]
            return files
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return []
    
    def get_storage_size(self) -> int:
        """
        Get total size of all files in temporary directory.
        
        Returns:
            Total size in bytes
        """
        total_size = 0
        try:
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as e:
            logger.error(f"Failed to calculate storage size: {e}")
        
        return total_size
