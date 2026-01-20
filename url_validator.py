"""
URL Validator module for detecting and validating video platform URLs.
Supports YouTube Shorts and TikTok.
"""
import re
from enum import Enum
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse, parse_qs


class Platform(Enum):
    """Supported video platforms."""
    YOUTUBE_SHORTS = "youtube_shorts"
    TIKTOK = "tiktok"
    UNSUPPORTED = "unsupported"


@dataclass
class ValidationResult:
    """Result of URL validation."""
    is_valid: bool
    platform: Platform
    video_id: Optional[str] = None
    error_message: Optional[str] = None


class URLValidator:
    """Validator for video platform URLs."""
    
    # YouTube Shorts URL patterns
    YOUTUBE_SHORTS_PATTERNS = [
        r'youtube\.com/shorts/([a-zA-Z0-9_-]+)',
        r'youtu\.be/([a-zA-Z0-9_-]+)',
    ]
    
    # TikTok URL patterns
    TIKTOK_PATTERNS = [
        r'tiktok\.com/@[\w.-]+/video/(\d+)',
        r'tiktok\.com/.*\?.*v=(\d+)',
        r'vm\.tiktok\.com/([a-zA-Z0-9]+)',
        r'vt\.tiktok\.com/([a-zA-Z0-9]+)',
    ]
    
    def validate_url(self, url: str) -> ValidationResult:
        """
        Validate URL and determine if it's a supported video platform.
        
        Args:
            url: URL string to validate
            
        Returns:
            ValidationResult with validation status and platform info
        """
        if not url or not isinstance(url, str):
            return ValidationResult(
                is_valid=False,
                platform=Platform.UNSUPPORTED,
                error_message="URL must be a non-empty string"
            )
        
        # Basic URL validation
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return ValidationResult(
                    is_valid=False,
                    platform=Platform.UNSUPPORTED,
                    error_message="Invalid URL format"
                )
        except Exception:
            return ValidationResult(
                is_valid=False,
                platform=Platform.UNSUPPORTED,
                error_message="Invalid URL format"
            )
        
        # Detect platform
        platform = self.get_platform(url)
        
        if platform == Platform.UNSUPPORTED:
            return ValidationResult(
                is_valid=False,
                platform=Platform.UNSUPPORTED,
                error_message="Unsupported platform. Only YouTube Shorts and TikTok are supported"
            )
        
        # Extract video ID
        video_id = self.extract_video_id(url)
        
        if not video_id:
            return ValidationResult(
                is_valid=False,
                platform=platform,
                error_message=f"Could not extract video ID from {platform.value} URL"
            )
        
        return ValidationResult(
            is_valid=True,
            platform=platform,
            video_id=video_id
        )
    
    def get_platform(self, url: str) -> Platform:
        """
        Determine the platform from URL.
        
        Args:
            url: URL string
            
        Returns:
            Platform enum value
        """
        url_lower = url.lower()
        
        # Check for YouTube Shorts
        if 'youtube.com/shorts' in url_lower or 'youtu.be' in url_lower:
            # Additional check: youtu.be should be shorts (short URLs)
            if 'youtu.be' in url_lower:
                # youtu.be links are typically short links that could be shorts
                return Platform.YOUTUBE_SHORTS
            return Platform.YOUTUBE_SHORTS
        
        # Check for TikTok
        if 'tiktok.com' in url_lower or 'vm.tiktok.com' in url_lower or 'vt.tiktok.com' in url_lower:
            return Platform.TIKTOK
        
        return Platform.UNSUPPORTED
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """
        Extract video ID from URL based on platform.
        
        Args:
            url: URL string
            
        Returns:
            Video ID string or None if not found
        """
        platform = self.get_platform(url)
        
        if platform == Platform.YOUTUBE_SHORTS:
            return self._extract_youtube_id(url)
        elif platform == Platform.TIKTOK:
            return self._extract_tiktok_id(url)
        
        return None
    
    def _extract_youtube_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube Shorts URL."""
        for pattern in self.YOUTUBE_SHORTS_PATTERNS:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # Try to extract from query parameters (e.g., ?v=VIDEO_ID)
        try:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            if 'v' in query_params:
                return query_params['v'][0]
        except Exception:
            pass
        
        return None
    
    def _extract_tiktok_id(self, url: str) -> Optional[str]:
        """Extract video ID from TikTok URL."""
        for pattern in self.TIKTOK_PATTERNS:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # Fallback: try to extract numeric ID from URL path
        try:
            parsed = urlparse(url)
            path_parts = parsed.path.split('/')
            for part in path_parts:
                if part.isdigit() and len(part) > 10:  # TikTok IDs are long numbers
                    return part
        except Exception:
            pass
        
        return None
