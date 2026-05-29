"""
User Settings System - per-user preferences database.
JSON-based, auto-save, default fallback.
"""
import json
import logging
from pathlib import Path
from bot.config import Config

logger = logging.getLogger(__name__)

SETTINGS_DIR = Config.BASE_DIR / "data" / "user_settings"
SETTINGS_DIR.mkdir(parents=True, exist_ok=True)

# Default settings template (mirrors VideoCompressor4Bot)
DEFAULT_SETTINGS = {
    # Upload Destination
    "upload_destination": "telegram",  # telegram, gdrive, rclone, gofile

    # Screenshot Settings
    "screenshot_count": 3,       # 0=disabled, 1-10 screenshots

    # Encode Settings
    "video_codec": "libx264",        # libx264, libx265
    "preset": "veryfast",            # ultrafast, superfast, veryfast, faster, fast, medium
    "crf": 23,
    "video_bitrate": None,           # None = CRF mode, else "1000k" etc
    "resolution": 480,               # 1080, 720, 480, 360, 240
    "audio_codec": "copy",           # copy, aac, mp3, flac, opus, ac3, wav
    "audio_bitrate": "copy",         # copy, 128k, 192k, 256k, 320k

    # Watermark Settings
    "text_watermark": None,
    "image_watermark": None,
    "watermark_position": "bottom-right",  # top-left, top-right, bottom-left, bottom-right, center

    # TG Upload Settings
    "upload_type": "MEDIA",          # MEDIA, DOCUMENT
    "split_size": "1.95GB",
    "split_duration": None,
    "equal_splits": False,
    "spoiler_effect": False,
    "caption_above_media": False,
    "upload_chat": None,
    "thumbnail_layout": None,
    "disable_thumbnail": False,
    "caption": None,

    # Gdrive Settings
    "gdrive_token": None,
    "gdrive_id": None,
    "index_url": None,
    "stop_duplicate": False,

    # Extra Settings
    "remove_replace_words": {"regex": None, "simple": None},
    "prefix": None,
    "suffix": None,
    "metadata": {
        "video_title": None,
        "video_author": None,
        "audio_title": None,
        "subtitle_title": None,
    },
    "attachment_photo": None,
    "attachment_url": None,
    "autorename_template": None,
    "autorename_mode": "other",      # regex, other, ai
    "excluded_extensions": None,
}


class UserSettings:
    """Per-user settings manager."""

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.file_path = SETTINGS_DIR / f"{user_id}.json"
        self._data = self._load()

    def _load(self) -> dict:
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Merge with defaults (in case new fields added)
                merged = DEFAULT_SETTINGS.copy()
                merged.update(data)
                return merged
            except Exception as e:
                logger.error(f"Failed to load settings for {self.user_id}: {e}")
        return DEFAULT_SETTINGS.copy()

    def save(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save settings for {self.user_id}: {e}")

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value):
        self._data[key] = value
        self.save()

    def reset(self):
        self._data = DEFAULT_SETTINGS.copy()
        self.save()

    def export_dict(self) -> dict:
        return self._data.copy()

    def import_dict(self, data: dict):
        merged = DEFAULT_SETTINGS.copy()
        merged.update(data)
        self._data = merged
        self.save()

    # Property accessors for common settings
    @property
    def upload_destination(self): return self._data["upload_destination"]
    @upload_destination.setter
    def upload_destination(self, v): self._data["upload_destination"] = v; self.save()

    @property
    def video_codec(self): return self._data["video_codec"]
    @video_codec.setter
    def video_codec(self, v): self._data["video_codec"] = v; self.save()

    @property
    def preset(self): return self._data["preset"]
    @preset.setter
    def preset(self, v): self._data["preset"] = v; self.save()

    @property
    def crf(self): return self._data["crf"]
    @crf.setter
    def crf(self, v): self._data["crf"] = v; self.save()

    @property
    def video_bitrate(self): return self._data["video_bitrate"]
    @video_bitrate.setter
    def video_bitrate(self, v): self._data["video_bitrate"] = v; self.save()

    @property
    def resolution(self): return self._data["resolution"]
    @resolution.setter
    def resolution(self, v): self._data["resolution"] = v; self.save()

    @property
    def audio_codec(self): return self._data["audio_codec"]
    @audio_codec.setter
    def audio_codec(self, v): self._data["audio_codec"] = v; self.save()

    @property
    def audio_bitrate(self): return self._data["audio_bitrate"]
    @audio_bitrate.setter
    def audio_bitrate(self, v): self._data["audio_bitrate"] = v; self.save()

    @property
    def upload_type(self): return self._data["upload_type"]
    @upload_type.setter
    def upload_type(self, v): self._data["upload_type"] = v; self.save()

    @property
    def split_size(self): return self._data["split_size"]
    @split_size.setter
    def split_size(self, v): self._data["split_size"] = v; self.save()

    @property
    def caption(self): return self._data["caption"]
    @caption.setter
    def caption(self, v): self._data["caption"] = v; self.save()

    @property
    def spoiler_effect(self): return self._data["spoiler_effect"]
    @spoiler_effect.setter
    def spoiler_effect(self, v): self._data["spoiler_effect"] = v; self.save()

    @property
    def text_watermark(self): return self._data["text_watermark"]
    @text_watermark.setter
    def text_watermark(self, v): self._data["text_watermark"] = v; self.save()

    @property
    def image_watermark(self): return self._data["image_watermark"]
    @image_watermark.setter
    def image_watermark(self, v): self._data["image_watermark"] = v; self.save()

    @property
    def metadata(self): return self._data["metadata"]
    @metadata.setter
    def metadata(self, v): self._data["metadata"] = v; self.save()

    @property
    def autorename_mode(self): return self._data["autorename_mode"]
    @autorename_mode.setter
    def autorename_mode(self, v): self._data["autorename_mode"] = v; self.save()

    @property
    def autorename_template(self): return self._data["autorename_template"]
    @autorename_template.setter
    def autorename_template(self, v): self._data["autorename_template"] = v; self.save()

    @property
    def excluded_extensions(self): return self._data["excluded_extensions"]
    @excluded_extensions.setter
    def excluded_extensions(self, v): self._data["excluded_extensions"] = v; self.save()

    @property
    def prefix(self): return self._data["prefix"]
    @prefix.setter
    def prefix(self, v): self._data["prefix"] = v; self.save()

    @property
    def suffix(self): return self._data["suffix"]
    @suffix.setter
    def suffix(self, v): self._data["suffix"] = v; self.save()

    @property
    def gdrive_token(self): return self._data["gdrive_token"]
    @gdrive_token.setter
    def gdrive_token(self, v): self._data["gdrive_token"] = v; self.save()

    @property
    def gdrive_id(self): return self._data["gdrive_id"]
    @gdrive_id.setter
    def gdrive_id(self, v): self._data["gdrive_id"] = v; self.save()

    @property
    def index_url(self): return self._data["index_url"]
    @index_url.setter
    def index_url(self, v): self._data["index_url"] = v; self.save()

    @property
    def stop_duplicate(self): return self._data["stop_duplicate"]
    @stop_duplicate.setter
    def stop_duplicate(self, v): self._data["stop_duplicate"] = v; self.save()


def get_user_settings(user_id: int) -> UserSettings:
    """Factory function untuk ambil settings user."""
    return UserSettings(user_id)
