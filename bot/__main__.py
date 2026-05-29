"""
Bot Entry Point - TEST VERSION with minimal handlers.
"""
import logging
import signal
import sys
from pathlib import Path
from pyrogram import Client, idle
from bot.config import Config
import asyncio

# Setup logging
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
Config.LOG_PATH.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,  # DEBUG level for testing
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Config.LOG_PATH / "bot.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

# Import test handler FIRST (before other handlers)
from bot.handlers.test_handler import test_all_messages, test_video_filter, test_command

# Import other handlers
from bot.handlers.encode import EncodeHandler
from bot.handlers.cancel import CancelHandler
from bot.handlers.callback import CallbackHandler
from bot.handlers.text_input import TextInputHandler
from bot.handlers.settings import SettingsHandler
from bot.handlers.auth_handler import AuthHandler

app: Client = None


def setup_signal_handlers():
    def signal_handler(signum, frame):
        logger.info(f"Signal {signum}, shutting down...")
        if app:
            asyncio.create_task(app.stop())
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main():
    global app

    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Config error: {e}")
        sys.exit(1)

    sessions_dir = Config.BASE_DIR / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    app = Client(
        "encode_bot",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        bot_token=Config.BOT_TOKEN,
        workdir=str(sessions_dir),
    )

    setup_signal_handlers()
    logger.info("Starting TEST bot...")
    await app.start()

    if Config.OWNER_ID:
        try:
            await app.send_message(Config.OWNER_ID, "Bot TEST started!")
        except Exception as e:
            logger.warning(f"Could not notify owner: {e}")

    logger.info("Bot is running. Send /test in group or any video.")
    await idle()

    logger.info("Stopping bot...")
    await app.stop()
    logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
