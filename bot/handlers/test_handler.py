"""
Minimal test to verify Pyrogram receives group messages.
"""
import logging
from pyrogram import Client, filters
from pyrogram.types import Message

logger = logging.getLogger(__name__)


@Client.on_message(filters.group)
async def test_all_messages(client: Client, message: Message):
    """Log every single message in any group."""
    user = message.from_user.id if message.from_user else "N/A"
    chat = message.chat.id

    if message.video:
        logger.info(f"[TEST] VIDEO received: chat={chat} user={user} file_id={message.video.file_id}")
    elif message.document:
        logger.info(f"[TEST] DOCUMENT received: chat={chat} user={user} mime={message.document.mime_type} file_id={message.document.file_id}")
    elif message.text:
        logger.info(f"[TEST] TEXT received: chat={chat} user={user} text={message.text[:30]}")
    else:
        logger.info(f"[TEST] OTHER received: chat={chat} user={user} type={message.media}")


@Client.on_message(filters.video & filters.group)
async def test_video_filter(client: Client, message: Message):
    """Test if filters.video works."""
    logger.info(f"[TEST] filters.video MATCHED: user={message.from_user.id}")
    await message.reply("Video detected! Bot is working.")


@Client.on_message(filters.command("test") & filters.group)
async def test_command(client: Client, message: Message):
    """Test if commands work."""
    logger.info(f"[TEST] /test command: user={message.from_user.id}")
    await message.reply("Test command works! Bot is alive.")
    