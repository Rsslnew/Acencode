"""
Callback Query Handler - handle Cancel & Refresh buttons.
"""
import logging
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from bot.handlers.queue_manager import queue_manager

logger = logging.getLogger(__name__)


@Client.on_callback_query(filters.regex(r"^cancel:"))
async def cancel_callback(client: Client, callback: CallbackQuery):
    job_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id

    job = queue_manager.active_jobs.get(job_id)
    if not job or job.get("user_id") != user_id:
        await callback.answer("Job ini bukan milikmu!", show_alert=True)
        return

    if await queue_manager.cancel_job(job_id):
        await callback.answer("Task di-cancel!", show_alert=False)
        try:
            await callback.message.edit_text(
                f"**Download Has Been Stopped! ‼️**\n\n"
                f"cc: @{callback.from_user.username or callback.from_user.first_name}\n"
                f"Elapsed: {job.get('elapsed', 'N/A')}\n"
                f"Mode: Telegram\n"
                f"Due to: Stopped by user!"
            )
        except Exception:
            pass
    else:
        await callback.answer("Job sudah selesai atau tidak ditemukan.", show_alert=True)


@Client.on_callback_query(filters.regex(r"^refresh:"))
async def refresh_callback(client: Client, callback: CallbackQuery):
    await callback.answer("Refreshed!", show_alert=False)
