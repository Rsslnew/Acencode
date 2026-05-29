"""
Bot Entry Point - start Pyrogram client with reconnect logic.
"""
import logging
import signal
import sys
from pathlib import Path
from pyrogram import Client, idle
from bot.config import Config
from bot.utils.cleanup import ensure_dirs, cleanup_old_temp
import asyncio

# Setup logging
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Ensure log directory exists BEFORE creating FileHandler
Config.LOG_PATH.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Config.LOG_PATH / "bot.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

# Import handlers (auto-register decorators)
from bot.handlers.encode import EncodeHandler
from bot.handlers.cancel import CancelHandler
from bot.handlers.callback import CallbackHandler
from bot.handlers.text_input import TextInputHandler
from bot.handlers.settings import SettingsHandler
from bot.handlers.auth_handler import AuthHandler
from bot.utils.safelinku import cleanup_expired_tokens

# Global client for shutdown
app: Client = None


def setup_signal_handlers():
    """Handle SIGINT/SIGTERM for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        if app:
            asyncio.create_task(app.stop())
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main entry point."""
    global app

    # 1. Validate config
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Config error: {e}")
        sys.exit(1)

    # 2. Ensure directories
    ensure_dirs()
    cleanup_old_temp(max_age_hours=24)

    # 3. Create client
    app = Client(
        "encode_bot",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        bot_token=Config.BOT_TOKEN,
        workdir=str(Config.BASE_DIR / "sessions"),
    )

    # 4. Setup signal handlers
    setup_signal_handlers()

    # 5. Start
    logger.info("Starting Encode Bot...")
    await app.start()

    # 6. Send startup notif to owner (optional)
    if Config.OWNER_ID:
        try:
            await app.send_message(
                Config.OWNER_ID,
                "Bot Started\nEncode bot is ready to serve groups."
            )
        except Exception as e:
            logger.warning(f"Could not notify owner: {e}")

    logger.info("Bot is running. Press Ctrl+C to stop.")
    await idle()

    # 7. Shutdown
    logger.info("Stopping bot...")
    await app.stop()
    logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
