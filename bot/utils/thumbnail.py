"""
Thumbnail module for video compressor bot.
Handles auto-extraction from video and custom thumbnail uploads.
"""
import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from bot.config import Config

logger = logging.getLogger(__name__)

# Thumbnail storage directory
THUMB_DIR = Config.BASE_DIR / "data" / "thumbnails"
THUMB_DIR.mkdir(parents=True, exist_ok=True)

# Default thumbnail dimensions
DEFAULT_WIDTH = 320
DEFAULT_HEIGHT = -1  # Auto maintain aspect ratio


def get_user_thumb_dir(user_id: int) -> Path:
    """Get thumbnail directory for a specific user."""
    user_dir = THUMB_DIR / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def get_custom_thumbnail_path(user_id: int) -> Path:
    """Get path for user's custom thumbnail."""
    return get_user_thumb_dir(user_id) / "custom_thumb.jpg"


def get_auto_thumbnail_path(user_id: int, video_name: str) -> Path:
    """Get path for auto-generated thumbnail."""
    safe_name = "".join(c for c in video_name if c.isalnum() or c in ("-", "_", ".")).rstrip()
    return get_user_thumb_dir(user_id) / f"auto_{safe_name}.jpg"


async def extract_thumbnail(video_path: Path, output_path: Path,
                            timestamp: str = "00:00:05",
                            width: int = DEFAULT_WIDTH,
                            height: int = DEFAULT_HEIGHT) -> bool:
    """
    Extract a thumbnail frame from video using FFmpeg.

    Args:
        video_path: Input video file path
        output_path: Output thumbnail path
        timestamp: Time position (HH:MM:SS or seconds)
        width: Thumbnail width
        height: Thumbnail height (-1 for auto)

    Returns:
        True if successful
    """
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(video_path),
            "-ss", timestamp,
            "-vframes", "1",
            "-q:v", "2",
            "-vf", f"scale={width}:{height}",
            str(output_path)
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            logger.error(f"Thumbnail extraction failed: {stderr.decode()[-200:]}")
            return False

        if not output_path.exists() or output_path.stat().st_size == 0:
            logger.error("Thumbnail file not created or empty")
            return False

        logger.info(f"Thumbnail extracted: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Thumbnail extraction error: {e}")
        return False


async def extract_thumbnail_at_percentage(video_path: Path, output_path: Path,
                                          percent: float = 50.0,
                                          width: int = DEFAULT_WIDTH) -> bool:
    """
    Extract thumbnail at a percentage of video duration.

    Args:
        video_path: Input video file
        output_path: Output thumbnail path
        percent: 0-100, position in video
        width: Thumbnail width
    """
    # Get video duration first
    duration = await get_video_duration(video_path)
    if duration <= 0:
        return await extract_thumbnail(video_path, output_path, "00:00:05", width)

    target_seconds = (percent / 100.0) * duration
    timestamp = seconds_to_timestamp(target_seconds)

    return await extract_thumbnail(video_path, output_path, timestamp, width)


async def get_video_duration(video_path: Path) -> float:
    """Get video duration in seconds using ffprobe."""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, _ = await proc.communicate()
        duration = float(stdout.decode().strip())
        return duration

    except Exception as e:
        logger.error(f"Failed to get video duration: {e}")
        return 0.0


def seconds_to_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS format."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hrs:02d}:{mins:02d}:{secs:02d}"


def has_custom_thumbnail(user_id: int) -> bool:
    """Check if user has uploaded a custom thumbnail."""
    thumb_path = get_custom_thumbnail_path(user_id)
    return thumb_path.exists() and thumb_path.stat().st_size > 0


def get_thumbnail_for_upload(user_id: int, video_path: Path, video_name: str,
                              layout: str = "default") -> Optional[str]:
    """
    Get thumbnail path for video upload.
    Priority: custom thumbnail > auto-extracted > None

    Args:
        user_id: User ID
        video_path: Video file path
        video_name: Original video name
        layout: Thumbnail layout mode

    Returns:
        Thumbnail file path or None
    """
    # Check custom thumbnail first
    custom = get_custom_thumbnail_path(user_id)
    if custom.exists() and custom.stat().st_size > 0:
        return str(custom)

    # Check auto thumbnail
    auto = get_auto_thumbnail_path(user_id, video_name)
    if auto.exists() and auto.stat().st_size > 0:
        return str(auto)

    return None


async def generate_and_save_thumbnail(video_path: Path, user_id: int,
                                       video_name: str,
                                       position_percent: float = 50.0) -> Optional[Path]:
    """
    Auto-generate thumbnail from video and save to user's thumb directory.

    Args:
        video_path: Video file path
        user_id: User ID
        video_name: Video name for filename
        position_percent: Frame position in video

    Returns:
        Path to generated thumbnail or None
    """
    output_path = get_auto_thumbnail_path(user_id, video_name)

    success = await extract_thumbnail_at_percentage(
        video_path, output_path, position_percent
    )

    if success:
        return output_path
    return None


def delete_custom_thumbnail(user_id: int) -> bool:
    """Delete user's custom thumbnail."""
    thumb_path = get_custom_thumbnail_path(user_id)
    if thumb_path.exists():
        try:
            thumb_path.unlink()
            return True
        except Exception as e:
            logger.error(f"Failed to delete thumbnail: {e}")
    return False


def delete_all_user_thumbnails(user_id: int) -> bool:
    """Delete all thumbnails for a user."""
    user_dir = get_user_thumb_dir(user_id)
    if not user_dir.exists():
        return True

    try:
        for f in user_dir.iterdir():
            if f.is_file():
                f.unlink()
        return True
    except Exception as e:
        logger.error(f"Failed to delete user thumbnails: {e}")
        return False
        