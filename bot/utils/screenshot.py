"""
Screenshot module - generates multiple frame captures from video.
"""
import asyncio
import logging
from pathlib import Path
from typing import List, Optional
from bot.config import Config

logger = logging.getLogger(__name__)

# Screenshot storage
SCREENSHOT_DIR = Config.BASE_DIR / "data" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def get_user_screenshot_dir(user_id: int) -> Path:
    """Get screenshot directory for a specific user."""
    user_dir = SCREENSHOT_DIR / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


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
        return float(stdout.decode().strip())
    except Exception as e:
        logger.error(f"Failed to get duration: {e}")
        return 0.0


def seconds_to_timestamp(seconds: float) -> str:
    """Convert seconds to HH:MM:SS.mmm format."""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hrs:02d}:{mins:02d}:{secs:06.3f}"


async def extract_screenshot(video_path: Path, output_path: Path,
                              timestamp: str, width: int = 1280) -> bool:
    """
    Extract a single screenshot frame from video.

    Args:
        video_path: Input video file
        output_path: Output image path
        timestamp: Time position (HH:MM:SS.mmm)
        width: Output image width

    Returns:
        True if successful
    """
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-ss", timestamp,
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "2",
            "-vf", f"scale={width}:-1",
            str(output_path)
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            logger.error(f"Screenshot extraction failed: {stderr.decode()[-200:]}")
            return False

        if not output_path.exists() or output_path.stat().st_size == 0:
            logger.error("Screenshot file not created")
            return False

        return True

    except Exception as e:
        logger.error(f"Screenshot error: {e}")
        return False


async def generate_screenshots(video_path: Path, user_id: int,
                                video_name: str,
                                count: int = 3) -> List[Path]:
    """
    Generate multiple screenshots from video at evenly spaced intervals.

    Args:
        video_path: Input video file
        user_id: User ID
        video_name: Video name for filename
        count: Number of screenshots (1-10)

    Returns:
        List of paths to generated screenshots
    """
    count = max(1, min(10, count))

    duration = await get_video_duration(video_path)
    if duration <= 0:
        logger.error("Could not get video duration")
        return []

    user_dir = get_user_screenshot_dir(user_id)
    safe_name = "".join(c for c in video_name if c.isalnum() or c in ("-", "_", ".")).rstrip()

    screenshots = []

    # Calculate positions (avoid very start and end)
    # For count=3: positions at 25%, 50%, 75%
    # For count=5: positions at 16%, 33%, 50%, 66%, 83%
    step = 100.0 / (count + 1)

    for i in range(1, count + 1):
        percent = step * i
        position_seconds = (percent / 100.0) * duration
        timestamp = seconds_to_timestamp(position_seconds)

        output_path = user_dir / f"{safe_name}_ss{i:02d}.jpg"

        success = await extract_screenshot(video_path, output_path, timestamp)

        if success:
            screenshots.append(output_path)
            logger.info(f"Screenshot {i}/{count} generated: {output_path}")
        else:
            logger.warning(f"Failed to generate screenshot {i}/{count}")

    return screenshots


async def send_screenshots_as_album(client, chat_id: int,
                                     screenshot_paths: List[Path],
                                     caption: str = None) -> bool:
    """
    Send screenshots as a photo album.

    Args:
        client: Pyrogram Client
        chat_id: Target chat ID
        screenshot_paths: List of screenshot file paths
        caption: Optional caption for the album

    Returns:
        True if sent successfully
    """
    if not screenshot_paths:
        return False

    try:
        from pyrogram.types import InputMediaPhoto

        # Build media group
        media_group = []
        for i, path in enumerate(screenshot_paths):
            cap = caption if i == 0 else ""
            media_group.append(InputMediaPhoto(media=str(path), caption=cap))

        # Telegram limit: max 10 photos per album
        chunk_size = 10
        for i in range(0, len(media_group), chunk_size):
            chunk = media_group[i:i + chunk_size]
            await client.send_media_group(chat_id=chat_id, media=chunk)

        return True

    except Exception as e:
        logger.error(f"Failed to send screenshot album: {e}")
        return False


def cleanup_screenshots(user_id: int, video_name: str = None):
    """
    Delete screenshot files for a user.

    Args:
        user_id: User ID
        video_name: If provided, only delete screenshots for this video
    """
    user_dir = get_user_screenshot_dir(user_id)
    if not user_dir.exists():
        return

    try:
        if video_name:
            safe_name = "".join(c for c in video_name if c.isalnum() or c in ("-", "_", ".")).rstrip()
            for f in user_dir.glob(f"{safe_name}_ss*.jpg"):
                f.unlink()
        else:
            # Delete all user screenshots
            for f in user_dir.iterdir():
                if f.is_file():
                    f.unlink()
    except Exception as e:
        logger.error(f"Failed to cleanup screenshots: {e}")
        