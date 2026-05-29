"""
Config module - loads environment variables with defaults.
Tahan banting: kalau .env tidak ada, pakai default yang aman.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env dari root project
ENV_PATH = Path(__file__).parent.parent / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)

class Config:
    # Telegram
    API_ID = int(os.getenv("API_ID", 0))
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    OWNER_ID = int(os.getenv("OWNER_ID", 0))

    # Encode Settings
    MAX_CONCURRENT_ENCODE = int(os.getenv("MAX_CONCURRENT_ENCODE", 2))
    MAX_QUEUE_PER_USER = int(os.getenv("MAX_QUEUE_PER_USER", 2))
    FFMPEG_CRF = int(os.getenv("FFMPEG_CRF", 28))
    FFMPEG_PRESET = os.getenv("FFMPEG_PRESET", "fast")
    VIDEO_CODEC = os.getenv("VIDEO_CODEC", "libx264")
    AUDIO_CODEC = os.getenv("AUDIO_CODEC", "aac")
    AUDIO_BITRATE = os.getenv("AUDIO_BITRATE", "128k")

    # Paths
    BASE_DIR = Path(__file__).parent.parent
    DOWNLOAD_PATH = BASE_DIR / os.getenv("DOWNLOAD_PATH", "downloads")
    OUTPUT_PATH = BASE_DIR / os.getenv("OUTPUT_PATH", "outputs")
    TEMP_PATH = BASE_DIR / os.getenv("TEMP_PATH", "temp")
    LOG_PATH = BASE_DIR / os.getenv("LOG_PATH", "logs")

    # Timeouts
    FFMPEG_TIMEOUT = int(os.getenv("FFMPEG_TIMEOUT", 600))
    DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", 300))

    @classmethod
    def validate(cls):
        missing = []
        if cls.API_ID == 0:
            missing.append("API_ID")
        if not cls.API_HASH:
            missing.append("API_HASH")
        if not cls.BOT_TOKEN:
            missing.append("BOT_TOKEN")
        if missing:
            raise ValueError(f"Missing required env vars: {', '.join(missing)}")
        return True
        