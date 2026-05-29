"""
Bot Entry Point - DEBUG VERSION.
"""
import logging
import signal
import sys
import traceback
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

# Setup logging
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(
    level=logging.DEBUG,  # DEBUG untuk verbose
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Config.LOG_PATH / "bot.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

# Global client
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

    # Create client
    app = Client(
        "encode_bot",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        bot_token=Config.BOT_TOKEN,
        workdir=str(Config.BASE_DIR / "sessions"),
    )

    logger.info(f"Client created. Dispatcher groups before import: {len(app.dispatcher.groups)}")

    # === IMPORT HANDLERS WITH DEBUG ===
    logger.info("=== IMPORTING HANDLERS ===")

    modules_to_import = [
        ("bot.handlers.test_handler", "test"),
        ("bot.handlers.encode", "encode"),
        ("bot.handlers.cancel", "cancel"),
        ("bot.handlers.callback", "callback"),
        ("bot.handlers.settings", "settings"),
        ("bot.handlers.auth_handler", "auth"),
        ("bot.handlers.text_input", "text_input"),
    ]

    for module_name, label in modules_to_import:
        try:
            __import__(module_name)
            logger.info(f"✅ [{label}] imported successfully")
        except Exception as e:
            logger.error(f"❌ [{label}] FAILED: {e}")
            traceback.print_exc()

    # Count handlers
    total_handlers = 0
    for group_num, handlers in app.dispatcher.groups.items():
        count = len(handlers)
        total_handlers += count
        logger.info(f"Group {group_num}: {count} handlers")

    logger.info(f"TOTAL HANDLERS REGISTERED: {total_handlers}")

    setup_signal_handlers()

    logger.info("🚀 Starting Encode Bot...")
    await app.start()

    if Config.OWNER_ID:
        try:
            await app.send_message(Config.OWNER_ID, "✅ **Bot Started**")
        except Exception as e:
            logger.warning(f"Could not notify owner: {e}")

    logger.info("Bot is running. Press Ctrl+C to stop.")
    await idle()

    logger.info("Stopping bot...")
    await app.stop()
    logger.info("Bot stopped.")

if __name__ == "__main__":
    asyncio.run(main())
