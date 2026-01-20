"""
Video Downloader module using yt-dlp.
Handles video downloads from YouTube Shorts and TikTok with progress tracking.
"""
import asyncio
import os
from dataclasses import dataclass
from typing import Optional, Dict, Callable
from pathlib import Path
import yt_dlp
from logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class DownloadResult:
    """Result of a video download operation."""
    success: bool
    file_path: Optional[str] = None
    error_message: Optional[str] = None
    file_size: int = 0


class VideoDownloader:
    """Video downloader using yt-dlp."""
    
    def __init__(self, yt_dlp_options: Dict, max_file_size_mb: int = 50):
        """
        Initialize Video Downloader.
        
        Args:
            yt_dlp_options: Configuration options for yt-dlp
            max_file_size_mb: Maximum file size in MB (default: 50)
        """
        self.yt_dlp_options = yt_dlp_options.copy()
        self.max_file_size_mb = max_file_size_mb
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        
        # Track active downloads
        self.active_downloads: Dict[str, float] = {}
        
        logger.info(f"Video Downloader initialized (max size: {max_file_size_mb}MB)")
    
    async def download_video(
        self,
        url: str,
        output_path: str,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> DownloadResult:
        """
        Download video from URL.
        
        Args:
            url: Video URL
            output_path: Path where video should be saved
            progress_callback: Optional callback for progress updates (0.0 to 1.0)
            
        Returns:
            DownloadResult with success status and file info
        """
        download_id = url
        self.active_downloads[download_id] = 0.0
        
        try:
            # Prepare output directory
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Configure yt-dlp options for this download
            ydl_opts = self.yt_dlp_options.copy()
            ydl_opts['outtmpl'] = output_path
            
            # Add progress hook
            def progress_hook(d):
                if d['status'] == 'downloading':
                    if 'total_bytes' in d:
                        progress = d['downloaded_bytes'] / d['total_bytes']
                    elif 'total_bytes_estimate' in d:
                        progress = d['downloaded_bytes'] / d['total_bytes_estimate']
                    else:
                        progress = 0.0
                    
                    self.active_downloads[download_id] = progress
                    
                    if progress_callback:
                        progress_callback(progress)
                
                elif d['status'] == 'finished':
                    self.active_downloads[download_id] = 1.0
                    if progress_callback:
                        progress_callback(1.0)
            
            ydl_opts['progress_hooks'] = [progress_hook]
            
            # Run download in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._download_sync,
                url,
                ydl_opts
            )
            
            # Clean up active downloads tracking
            if download_id in self.active_downloads:
                del self.active_downloads[download_id]
            
            return result
            
        except Exception as e:
            logger.error(f"Download failed for {url}: {e}")
            
            # Clean up active downloads tracking
            if download_id in self.active_downloads:
                del self.active_downloads[download_id]
            
            return DownloadResult(
                success=False,
                error_message=f"Download error: {str(e)}"
            )
    
    def _download_sync(self, url: str, ydl_opts: Dict) -> DownloadResult:
        """
        Synchronous download function (runs in executor).
        
        Args:
            url: Video URL
            ydl_opts: yt-dlp options
            
        Returns:
            DownloadResult
        """
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info first to check file size
                logger.info(f"Extracting video info: {url}")
                info = ydl.extract_info(url, download=False)
                
                # Check file size if available
                filesize = info.get('filesize') or info.get('filesize_approx')
                if filesize and filesize > self.max_file_size_bytes:
                    size_mb = filesize / (1024 * 1024)
                    error_msg = (
                        f"Video too large: {size_mb:.1f}MB "
                        f"(max: {self.max_file_size_mb}MB)"
                    )
                    logger.warning(error_msg)
                    return DownloadResult(
                        success=False,
                        error_message=error_msg
                    )
                
                # Download video
                logger.info(f"Downloading video: {url}")
                ydl.download([url])
                
                # Get output file path
                output_path = ydl_opts['outtmpl']
                
                # Verify file exists
                if not os.path.exists(output_path):
                    # Try to find the file (yt-dlp might add extension)
                    base_path = Path(output_path)
                    possible_files = list(base_path.parent.glob(f"{base_path.stem}.*"))
                    
                    if possible_files:
                        output_path = str(possible_files[0])
                    else:
                        return DownloadResult(
                            success=False,
                            error_message="Downloaded file not found"
                        )
                
                # Get file size
                file_size = os.path.getsize(output_path)
                
                # Final size check
                if file_size > self.max_file_size_bytes:
                    os.remove(output_path)
                    size_mb = file_size / (1024 * 1024)
                    error_msg = (
                        f"Downloaded file too large: {size_mb:.1f}MB "
                        f"(max: {self.max_file_size_mb}MB)"
                    )
                    logger.warning(error_msg)
                    return DownloadResult(
                        success=False,
                        error_message=error_msg
                    )
                
                logger.info(
                    f"Download successful: {output_path} "
                    f"({file_size / (1024 * 1024):.1f}MB)"
                )
                
                return DownloadResult(
                    success=True,
                    file_path=output_path,
                    file_size=file_size
                )
                
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            logger.error(f"yt-dlp download error: {error_msg}")
            
            # Provide user-friendly error messages
            if "unavailable" in error_msg.lower():
                return DownloadResult(
                    success=False,
                    error_message="Video is unavailable or private"
                )
            elif "not found" in error_msg.lower():
                return DownloadResult(
                    success=False,
                    error_message="Video not found"
                )
            else:
                return DownloadResult(
                    success=False,
                    error_message=f"Download failed: {error_msg}"
                )
        
        except Exception as e:
            logger.error(f"Unexpected error during download: {e}")
            return DownloadResult(
                success=False,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    async def get_download_progress(self, download_id: str) -> float:
        """
        Get progress of an active download.
        
        Args:
            download_id: Download identifier (typically the URL)
            
        Returns:
            Progress value (0.0 to 1.0) or 0.0 if not found
        """
        return self.active_downloads.get(download_id, 0.0)
    
    def cancel_download(self, download_id: str) -> None:
        """
        Cancel an active download.
        
        Note: yt-dlp doesn't support cancellation easily,
        so this just removes tracking. The download will complete
        but the file can be deleted afterwards.
        
        Args:
            download_id: Download identifier
        """
        if download_id in self.active_downloads:
            del self.active_downloads[download_id]
            logger.info(f"Cancelled download tracking: {download_id}")
