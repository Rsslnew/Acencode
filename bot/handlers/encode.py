"""
Encode Handler v2 - dengan DM upload, task counter, speed tracking.
"""
import asyncio
import logging
import time
from pathlib import Path
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.config import Config
from bot.handlers.queue_manager import queue_manager
from bot.handlers.progress_v2 import ProgressTracker
from bot.utils.ffmpeg import build_ffmpeg_command, run_ffmpeg
from bot.utils.helpers import get_file_size, safe_filename, format_duration
from bot.utils.cleanup import cleanup_files

logger = logging.getLogger(__name__)

total_task_counter = 0
running_task_counter = 0


class EncodeHandler:
    
    @staticmethod
    @Client.on_message(filters.video & filters.group)
    async def handle_video(client: Client, message: Message):
        global total_task_counter, running_task_counter
        user_id = message.from_user.id
        
        if not await queue_manager.acquire_slot(user_id):
            await message.reply(
                f"⏳ **Queue penuh!**\n"
                f"Kamu punya {Config.MAX_QUEUE_PER_USER} job aktif. "
                f"Tunggu selesai atau /cancel."
            )
            return
        
        total_task_counter += 1
        running_task_counter += 1
        
        status_msg = await message.reply("⏳ Menyiapkan encode...")
        tracker = ProgressTracker(client, status_msg, message.id, user_id)
        tracker.task_position = running_task_counter
        tracker.total_tasks = total_task_counter
        
        try:
            await EncodeHandler._encode_pipeline(client, message, tracker)
        except Exception as e:
            logger.error(f"Encode failed: {e}", exc_info=True)
            await tracker.finish(success=False, error_msg=str(e))
        finally:
            await queue_manager.release_slot(user_id)
            await queue_manager.unregister_job(message.id)
            running_task_counter = max(0, running_task_counter - 1)
    
    @staticmethod
    async def _encode_pipeline(client: Client, message: Message, tracker: ProgressTracker):
        user_id = message.from_user.id
        
        await tracker.update(stage="waiting", extra={"Info": "Mengantri..."})
        
        async with queue_manager.encode_semaphore:
            if queue_manager.is_cancelled(message.id):
                await tracker.update(stage="cancelled")
                return
            
            await tracker.update(stage="downloading")
            
            timestamp = int(time.time())
            safe_name = safe_filename(message.video.file_name or f"video_{message.id}")
            input_path = Config.DOWNLOAD_PATH / f"{user_id}_{timestamp}_{safe_name}"
            output_path = Config.OUTPUT_PATH / f"{user_id}_{timestamp}_encoded_{safe_name}"
            
            try:
                start_dl = time.time()
                
                async def dl_progress(current, total):
                    await tracker.update(
                        current=current,
                        total=total,
                        stage="downloading",
                        extra={"File": safe_name[:30]}
                    )
                
                await message.download(
                    file_name=str(input_path),
                    progress=dl_progress,
                    progress_args=()
                )
                
                dl_time = time.time() - start_dl
                input_size = get_file_size(input_path)
                
                if queue_manager.is_cancelled(message.id):
                    await tracker.update(stage="cancelled")
                    return
                
                await tracker.update(
                    stage="encoding",
                    extra={"Input Size": input_size, "DL Time": f"{dl_time:.1f}s"}
                )
                
                await queue_manager.register_job(message.id, {
                    "user_id": user_id,
                    "cancelled": False,
                    "input": input_path,
                    "output": output_path,
                    "elapsed": format_duration(time.time() - tracker.start_time)
                })
                
                cmd = build_ffmpeg_command(input_path, output_path)
                
                async def enc_progress(current_time, total_duration):
                    if queue_manager.is_cancelled(message.id):
                        return
                    await tracker.update(
                        current=current_time,
                        total=total_duration,
                        stage="encoding"
                    )
                
                returncode, stdout, stderr = await run_ffmpeg(
                    cmd, progress_callback=enc_progress,
                    total_duration=message.video.duration or 0
                )
                
                if returncode != 0:
                    raise RuntimeError(f"FFmpeg failed: {stderr[-500:]}")
                
                if queue_manager.is_cancelled(message.id):
                    await tracker.update(stage="cancelled")
                    return
                
                await tracker.update(stage="uploading")
                output_size = get_file_size(output_path)
                
                # KIRIM KE DM USER (bukan grup)
                await client.send_video(
                    chat_id=user_id,
                    video=str(output_path),
                    caption=(
                        f"🎬 **Encoded Video**\n"
                        f"📦 {output_size}\n"
                        f"⏱️ {format_duration(time.time() - tracker.start_time)}"
                    ),
                    supports_streaming=True
                )
                
                await tracker.finish(success=True)
                await tracker.status_message.reply(
                    f"✅ **File has been sent in your DM.**\n"
                    f"@{message.from_user.username or message.from_user.first_name}"
                )
                
            finally:
                cleanup_files(input_path, output_path)