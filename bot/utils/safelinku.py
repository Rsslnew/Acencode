"""
SafeLinkU integration - REST API v1 with Bearer token.
Supports both legacy API key and modern API token.
"""
import aiohttp
import logging
import random
import string
from datetime import datetime, timedelta
from pathlib import Path
from bot.config import Config

logger = logging.getLogger(__name__)

TOKEN_STORE = Path("safelinku_tokens.json")


def _load_tokens() -> dict:
    if TOKEN_STORE.exists():
        import json
        try:
            with open(TOKEN_STORE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_tokens(data: dict):
    import json
    try:
        with open(TOKEN_STORE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save tokens: {e}")


def generate_token() -> str:
    """Generate random verification token."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))


def store_token(user_id: int, token: str):
    """Store token with expiration."""
    tokens = _load_tokens()
    tokens[str(user_id)] = {
        "token": token,
        "expires": (datetime.now() + timedelta(seconds=Config.TOKEN_EXPIRE_SECONDS)).isoformat(),
        "used": False
    }
    _save_tokens(tokens)


def verify_token(user_id: int, token: str) -> bool:
    """Verify if token is valid and not expired."""
    tokens = _load_tokens()
    user_data = tokens.get(str(user_id))

    if not user_data:
        return False

    if user_data.get("used"):
        return False

    expires = datetime.fromisoformat(user_data["expires"])
    if datetime.now() > expires:
        return False

    if user_data["token"] != token:
        return False

    # Mark as used
    user_data["used"] = True
    _save_tokens(tokens)
    return True


# Alias for backward compatibility
validate_token = verify_token


def is_token_valid(user_id: int) -> bool:
    """Check if user has a valid unused token."""
    tokens = _load_tokens()
    user_data = tokens.get(str(user_id))

    if not user_data or user_data.get("used"):
        return False

    expires = datetime.fromisoformat(user_data["expires"])
    return datetime.now() <= expires


def cleanup_expired_tokens():
    """Remove expired tokens from store."""
    tokens = _load_tokens()
    now = datetime.now()
    cleaned = {}

    for user_id, data in tokens.items():
        expires = datetime.fromisoformat(data["expires"])
        if now <= expires and not data.get("used"):
            cleaned[user_id] = data

    _save_tokens(cleaned)
    logger.info(f"Cleaned tokens. Active: {len(cleaned)}")


async def create_shortlink(target_url: str, alias: str = None) -> dict:
    """
    Create shortlink using SafeLinkU REST API v1.

    Args:
        target_url: URL to shorten
        alias: Custom alias (optional)

    Returns:
        dict with shortlink data or error
    """
    api_token = getattr(Config, "SAFELINKU_API_TOKEN", None) or getattr(Config, "SAFELINKU_API_KEY", None)

    if not api_token:
        logger.error("No SafeLinkU API token configured")
        return {"error": "API token not configured"}

    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "url": target_url
    }

    if alias:
        payload["alias"] = alias

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://safelinku.com/api/v1/links",
                headers=headers,
                json=payload
            ) as resp:
                data = await resp.json()

                if resp.status == 201:
                    return {
                        "success": True,
                        "shortlink": data.get("data", {}).get("shortlink"),
                        "original": target_url
                    }
                else:
                    logger.error(f"SafeLinkU API error: {data}")
                    return {"error": data.get("message", "Unknown error")}

    except Exception as e:
        logger.error(f"SafeLinkU request failed: {e}")
        return {"error": str(e)}


async def create_shortlink_legacy(target_url: str) -> dict:
    """
    Create shortlink using legacy API key endpoint.
    Fallback if REST API fails.
    """
    api_key = getattr(Config, "SAFELINKU_API_KEY", None)

    if not api_key:
        return {"error": "API key not configured"}

    try:
        async with aiohttp.ClientSession() as session:
            params = {
                "api": api_key,
                "url": target_url
            }
            async with session.get("https://safelinku.com/api", params=params) as resp:
                data = await resp.json()

                if data.get("status") == "success":
                    return {
                        "success": True,
                        "shortlink": data.get("shortenedUrl"),
                        "original": target_url
                    }
                else:
                    return {"error": data.get("message", "Unknown error")}

    except Exception as e:
        logger.error(f"Legacy API failed: {e}")
        return {"error": str(e)}


async def get_verification_link(user_id: int, username: str = None) -> str:
    """
    Generate verification shortlink for user.

    Returns:
        Shortlink URL or None if failed
    """
    token = generate_token()
    store_token(user_id, token)

    target = f"{Config.BYPASS_TARGET_URL}?user={user_id}&token={token}"

    # Try REST API first
    result = await create_shortlink(target)

    if result.get("success"):
        return result["shortlink"]

    # Fallback to legacy API
    result = await create_shortlink_legacy(target)

    if result.get("success"):
        return result["shortlink"]

    logger.error(f"Failed to create shortlink: {result.get('error')}")
    return None


def get_verify_safelink_text(user_id: int, username: str = None) -> str:
    """Get verification message text with SafeLinkU link."""
    name = username or f"User_{user_id}"
    return (
        f"Hey @{name},\n\n"
        f"Please verify yourself to use this bot!\n"
        f"Click the button below to verify."
    )


def get_safelink_url(user_id: int, username: str = None) -> str:
    """Get or create SafeLinkU verification URL for user."""
    # This is a synchronous wrapper - in production, use async get_verification_link
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(get_verification_link(user_id, username))
    except Exception:
        return None
