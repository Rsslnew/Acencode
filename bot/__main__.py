"""
Bot Entry Point - FIXED: manual handler registration.
"""
import logging
import signal
import sys
from pathlib import Path
from pyrogram import Client, idle, filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from bot.config import Config
from bot.utils.cleanup import ensure_dirs, cleanup_old_temp
import asyncio

# Ensure directories exist BEFORE logging setup
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
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Config.LOG_PATH / "bot.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)


def setup_signal_handlers(app):
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(app.stop())
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main():
    app = Client(
        "encode_bot",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        bot_token=Config.BOT_TOKEN,
        workdir=str(Config.BASE_DIR / "sessions"),
    )

    logger.info("Registering handlers...")

    # === IMPORT HANDLER FUNCTIONS ===
    from bot.handlers.encode import handle_video, handle_video_doc, _encode_pipeline
    from bot.handlers.cancel import cancel_command
    from bot.handlers.callback import cancel_callback, refresh_callback
    from bot.handlers.settings import settings_command
    from bot.handlers.auth_handler import verify_callback, refresh_token_callback, start_command
    from bot.handlers.text_input import handle_text_input, handle_photo_input
    from bot.handlers.test_handler import test_all_messages, test_video_filter, test_command

    # === REGISTER HANDLERS ===
    # Test handlers
    app.add_handler(MessageHandler(test_all_messages, filters.group))
    app.add_handler(MessageHandler(test_video_filter, filters.video & filters.group))
    app.add_handler(MessageHandler(test_command, filters.command("test") & filters.group))

    # Encode handlers
    app.add_handler(MessageHandler(handle_video, filters.video & filters.group))
    app.add_handler(MessageHandler(handle_video_doc, filters.document & filters.group))

    # Cancel handler
    app.add_handler(MessageHandler(cancel_command, filters.command("cancel") & filters.group))

    # Callback handlers
    app.add_handler(CallbackQueryHandler(cancel_callback, filters.regex(r"^cancel:")))
    app.add_handler(CallbackQueryHandler(refresh_callback, filters.regex(r"^refresh:")))

    # Settings
    app.add_handler(MessageHandler(settings_command, filters.command("settings") & filters.group))

    # Auth
    app.add_handler(CallbackQueryHandler(verify_callback, filters.regex(r"^verify_me$")))
    app.add_handler(CallbackQueryHandler(refresh_token_callback, filters.regex(r"^refresh_token$")))
    app.add_handler(MessageHandler(start_command, filters.private & filters.command("start")))

    # Text input
    app.add_handler(MessageHandler(handle_text_input, filters.text & filters.private))
    app.add_handler(MessageHandler(handle_photo_input, filters.photo & filters.private))

    # Count total
    total = 0
    for group_num, handlers in app.dispatcher.groups.items():
        total += len(handlers)
        logger.info(f"Group {group_num}: {len(handlers)} handlers")
    logger.info(f"TOTAL HANDLERS REGISTERED: {total}")

    setup_signal_handlers(app)

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
