"""
Cancel Handler - handle /cancel command.
"""
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.handlers.queue_manager import queue_manager

logger = logging.getLogger(__name__)


@Client.on_message(filters.command("cancel") & filters.group)
async def cancel_command(client: Client, message: Message):
    """Cancel job user."""
    user_id = message.from_user.id

    cancelled = False
    for msg_id, job in list(queue_manager.active_jobs.items()):
        if job.get("user_id") == user_id:
            if await queue_manager.cancel_job(msg_id):
                cancelled = True
                break

    if cancelled:
        await message.reply("🚫 Job di-cancel.")
    else:
        await message.reply("❌ Tidak ada job aktif untuk di-cancel.")
