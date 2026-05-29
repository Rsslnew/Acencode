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

# === FIX: Ensure directories exist BEFORE logging setup ===
try:
    Config.validate()
except ValueError as e:
    print(f"Config error: {e}", file=sys.stderr)
    sys.exit(1)

ensure_dirs()
cleanup_old_temp(max_age_hours=24)

# Setup logging (sekarang folder logs/ sudah ada)
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
import bot.handlers.encode
import bot.handlers.cancel
import bot.handlers.callback
import bot.handlers.settings
import bot.handlers.auth_handler
import bot.handlers.text_input
import bot.handlers.test_handler
from bot.utils.safelinku import cleanup_expired_tokens

app: Client = None


def setup_signal_handlers():
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        if app:
            asyncio.create_task(app.stop())
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main():
    global app

    # 3. Create client
    app = Client(
        "encode_bot",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        bot_token=Config.BOT_TOKEN,
        workdir=str(Config.BASE_DIR / "sessions"),
    )

    setup_signal_handlers()

    logger.info("🚀 Starting Encode Bot...")
    await app.start()

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

    logger.info("Stopping bot...")
    await app.stop()
    logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
