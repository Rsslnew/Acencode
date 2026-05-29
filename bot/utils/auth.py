"""
Auth system - JSON-based user verification.
Bisa upgrade ke MongoDB nanti.
"""
import json
import logging
from pathlib import Path
from bot.config import Config

logger = logging.getLogger(__name__)

AUTH_FILE = Config.BASE_DIR / "auth_db.json"


def _load_db() -> dict:
    if AUTH_FILE.exists():
        try:
            with open(AUTH_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_db(db: dict):
    try:
        with open(AUTH_FILE, "w") as f:
            json.dump(db, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save auth db: {e}")


def is_verified(user_id: int) -> bool:
    db = _load_db()
    return str(user_id) in db.get("verified_users", {})


def verify_user(user_id: int, username: str = None):
    db = _load_db()
    if "verified_users" not in db:
        db["verified_users"] = {}
    db["verified_users"][str(user_id)] = {
        "username": username,
        "verified_at": _now()
    }
    _save_db(db)


def _now():
    from datetime import datetime
    return datetime.now().isoformat()


def get_pending_verification_msg(user_id: int, username: str = None) -> str:
    name = username or f"User_{user_id}"
    return (
        f"Hey, @{name},\n"
        f"1: Verify yourself to use me !"
    )


def get_verify_buttons():
    from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👉 Verify", callback_data="verify_me")],
        [InlineKeyboardButton("Buy Subscription | No Ads", url="https://t.me/your_channel")]
    ])
    