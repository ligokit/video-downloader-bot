"""
Configuration module for Video Downloader Bot.
Loads settings from environment variables.
"""
import os
from dataclasses import dataclass
from typing import Dict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class BotConfig:
    """Bot configuration loaded from environment variables."""
    telegram_token: str
    bot_username: str
    temp_dir: str
    max_file_size_mb: int
    cleanup_interval_hours: int
    max_file_age_hours: int
    yt_dlp_options: Dict

    @classmethod
    def from_env(cls) -> 'BotConfig':
        """Create configuration from environment variables."""
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not telegram_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")
        
        bot_username = os.getenv('BOT_USERNAME', 'savxbot')
        temp_dir = os.getenv('TEMP_DIR', './temp')
        max_file_size_mb = int(os.getenv('MAX_FILE_SIZE_MB', '50'))
        cleanup_interval_hours = int(os.getenv('CLEANUP_INTERVAL_HOURS', '1'))
        max_file_age_hours = int(os.getenv('MAX_FILE_AGE_HOURS', '1'))
        
        # yt-dlp configuration
        yt_dlp_options = {
            'format': 'best[ext=mp4]',
            'outtmpl': '%(id)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'max_filesize': max_file_size_mb * 1024 * 1024,  # Convert to bytes
        }
        
        return cls(
            telegram_token=telegram_token,
            bot_username=bot_username,
            temp_dir=temp_dir,
            max_file_size_mb=max_file_size_mb,
            cleanup_interval_hours=cleanup_interval_hours,
            max_file_age_hours=max_file_age_hours,
            yt_dlp_options=yt_dlp_options
        )
