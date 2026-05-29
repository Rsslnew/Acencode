"""
Cleanup utilities - hapus file temp, ensure dirs exist.
Tahan banting: try/except di setiap operasi file.
"""
import shutil
import logging
from pathlib import Path
from bot.config import Config

logger = logging.getLogger(__name__)


def ensure_dirs():
    """Pastikan semua direktori penting ada."""
    for path in [Config.DOWNLOAD_PATH, Config.OUTPUT_PATH, Config.TEMP_PATH, Config.LOG_PATH]:
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create dir {path}: {e}")


def cleanup_files(*paths: Path):
    """Hapus file/directory dengan aman."""
    for p in paths:
        if not p.exists():
            continue
        try:
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
            logger.info(f"Cleaned up: {p}")
        except Exception as e:
            logger.warning(f"Cleanup failed for {p}: {e}")


def cleanup_old_temp(max_age_hours: int = 24):
    """Hapus file temp yang lebih dari X jam."""
    import time
    now = time.time()
    cutoff = now - (max_age_hours * 3600)
    
    for folder in [Config.TEMP_PATH, Config.DOWNLOAD_PATH, Config.OUTPUT_PATH]:
        if not folder.exists():
            continue
        for item in folder.iterdir():
            try:
                if item.stat().st_mtime < cutoff:
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                    logger.info(f"Auto-cleaned old item: {item}")
            except Exception as e:
                logger.warning(f"Auto-cleanup error for {item}: {e}")
                