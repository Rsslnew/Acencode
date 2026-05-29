"""
Bot Configuration - loaded from environment variables.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    # Telegram
    API_ID = int(os.getenv("API_ID", 0))
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    OWNER_ID = int(os.getenv("OWNER_ID", 0))

    # Bot Settings
    MAX_QUEUE_PER_USER = int(os.getenv("MAX_QUEUE_PER_USER", 3))
    MAX_CONCURRENT_ENCODES = int(os.getenv("MAX_CONCURRENT_ENCODES", 2))

    # FFmpeg
    FFMPEG_CRF = int(os.getenv("FFMPEG_CRF", 28))
    FFMPEG_PRESET = os.getenv("FFMPEG_PRESET", "veryfast")
    VIDEO_CODEC = os.getenv("VIDEO_CODEC", "libx264")
    AUDIO_CODEC = os.getenv("AUDIO_CODEC", "copy")
    AUDIO_BITRATE = os.getenv("AUDIO_BITRATE", "128k")
    FFMPEG_TIMEOUT = int(os.getenv("FFMPEG_TIMEOUT", 3600))

    # SafeLinkU (API Token = Bearer, API Key = Legacy)
    SAFELINKU_API_TOKEN = os.getenv("SAFELINKU_API_TOKEN", "")
    SAFELINKU_API_KEY = os.getenv("SAFELINKU_API_KEY", "")
    BYPASS_TARGET_URL = os.getenv("BYPASS_TARGET_URL", "https://t.me/your_channel")
    TOKEN_EXPIRE_SECONDS = int(os.getenv("TOKEN_EXPIRE_SECONDS", 86400))

    # Paths
    DOWNLOAD_PATH = Path(os.getenv("DOWNLOAD_PATH", BASE_DIR / "downloads"))
    OUTPUT_PATH = Path(os.getenv("OUTPUT_PATH", BASE_DIR / "outputs"))
    LOG_PATH = Path(os.getenv("LOG_PATH", BASE_DIR / "logs"))

    @classmethod
    def validate(cls):
        required = ["API_ID", "API_HASH", "BOT_TOKEN"]
        missing = [r for r in required if not getattr(cls, r)]
        if missing:
            raise ValueError(f"Missing required config: {', '.join(missing)}")

        # Ensure directories exist
        cls.DOWNLOAD_PATH.mkdir(parents=True, exist_ok=True)
        cls.OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
        cls.LOG_PATH.mkdir(parents=True, exist_ok=True)
