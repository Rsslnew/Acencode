"""
Helper utilities - formatting, progress bar, etc.
"""
import time
from pathlib import Path


def get_file_size(path: Path) -> str:
    """Return human-readable file size."""
    size = path.stat().st_size
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.2f} {unit}"
        size /= 1024
    return f"{size:.2f} PB"


def format_duration(seconds: float) -> str:
    """Format seconds to mm:ss or hh:mm:ss."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def generate_progress_bar(current: int, total: int, length: int = 20) -> str:
    """Generate ASCII progress bar."""
    if total == 0:
        return "[" + "░" * length + "] 0%"
    progress = min(current / total, 1.0)
    filled = int(length * progress)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}] {int(progress * 100)}%"


def safe_filename(name: str) -> str:
    """Sanitize filename untuk cross-platform."""
    invalid = '<>:"/\\|?*'
    for char in invalid:
        name = name.replace(char, "_")
    return name.strip(".")
    