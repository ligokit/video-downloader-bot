"""
Webhook handler for Vercel serverless deployment.
Handles incoming Telegram updates via webhook.
"""
import os
import json
import asyncio
from http.server import BaseHTTPRequestHandler
from aiogram import Bot, Dispatcher, types
from aiogram.types import Update

# Import bot components
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from url_validator import URLValidator
from video_downloader import VideoDownloader
from storage_manager import StorageManager
from task_manager import DownloadTaskManager
from bot_handler import BotHandler
from config import BotConfig


# Initialize components globally (reused across invocations)
config = None
bot = None
bot_handler = None


def initialize_bot():
    """Initialize bot components if not already initialized."""
    global config, bot, bot_handler
    
    if bot_handler is not None:
        return bot_handler
    
    # Load configuration
    config = BotConfig.from_env()
    
    # Create Bot instance
    bot = Bot(token=config.telegram_token)
    
    # Create components
    url_validator = URLValidator()
    storage_manager = StorageManager(temp_dir="/tmp")  # Vercel uses /tmp
    task_manager = DownloadTaskManager()
    video_downloader = VideoDownloader(
        yt_dlp_options=config.yt_dlp_options,
        max_file_size_mb=config.max_file_size_mb
    )
    
    # Create Bot Handler
    bot_handler = BotHandler(
        bot=bot,
        url_validator=url_validator,
        video_downloader=video_downloader,
        storage_manager=storage_manager,
        task_manager=task_manager
    )
    
    return bot_handler


class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler."""
    
    def do_POST(self):
        """Handle POST requests from Telegram webhook."""
        try:
            # Read request body
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            
            # Parse JSON
            update_data = json.loads(body.decode('utf-8'))
            
            # Initialize bot
            bot_handler = initialize_bot()
            
            # Process update
            asyncio.run(self.process_update(update_data, bot_handler))
            
            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode())
        
        except Exception as e:
            print(f"Error processing webhook: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())
    
    def do_GET(self):
        """Handle GET requests (health check)."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "ok",
            "message": "Video Downloader Bot webhook is running"
        }).encode())
    
    async def process_update(self, update_data: dict, bot_handler: BotHandler):
        """Process Telegram update."""
        try:
            # Create Update object
            update = Update(**update_data)
            
            # Feed update to dispatcher
            await bot_handler.dp.feed_update(bot_handler.bot, update)
        
        except Exception as e:
            print(f"Error processing update: {e}")
            raise
