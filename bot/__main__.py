"""
Bot Entry Point - start Pyrogram client dengan reconnect logic.
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
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Config.LOG_PATH / "bot.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

# === IMPORT HANDLERS (auto-register decorators) ===
# WAJIB import module, bukan class, agar @Client.on_message tereksekusi
import bot.handlers.encode
import bot.handlers.cancel
import bot.handlers.callback
import bot.handlers.settings
import bot.handlers.auth_handler
import bot.handlers.text_input
import bot.handlers.test_handler
from bot.utils.safelinku import cleanup_expired_tokens

# Global client untuk shutdown
app: Client = None


def setup_signal_handlers():
    """Handle SIGINT/SIGTERM untuk graceful shutdown."""
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
    logger.info("🚀 Starting Encode Bot...")
    await app.start()

    # 6. Send startup notif ke owner
    if Config.OWNER_ID:
        try:
            await app.send_message(
                Config.OWNER_ID,
                "✅ **Bot Started**\nEncode bot siap melayani grup."
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
