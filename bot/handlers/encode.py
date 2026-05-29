"""
Encode Handler - FIXED: handle video AND document.
"""
import asyncio
import logging
import time
from pathlib import Path
from pyrogram import Client, filters
from pyrogram.types import Message
from bot.config import Config
from bot.handlers.queue_manager import queue_manager
from bot.handlers.progress import ProgressTracker
from bot.utils import (
    is_verified,
    get_pending_verification_msg,
    get_verify_buttons,
    get_user_settings,
    build_ffmpeg_command,
    run_ffmpeg,
    get_file_size,
    safe_filename,
    format_duration,
    cleanup_files,
)
from bot.utils.upload_progress import UploadProgressTracker, safe_upload_video, safe_upload_document
from bot.utils.thumbnail import (
    generate_and_save_thumbnail,
    get_thumbnail_for_upload,
    has_custom_thumbnail,
)
from bot.utils.screenshot import (
    generate_screenshots,
    send_screenshots_as_album,
    cleanup_screenshots,
)

logger = logging.getLogger(__name__)

total_task_counter = 0
running_task_counter = 0

# DEBUG: Set True to bypass auth for testing
DEBUG_BYPASS_AUTH = True


def is_video_file(message: Message) -> bool:
    """Check if message contains video or video document."""
    if message.video:
        return True
    if message.document and message.document.mime_type:
        return message.document.mime_type.startswith("video/")
    return False


class EncodeHandler:

    @staticmethod
    @Client.on_message(filters.group)
    async def debug_all(client: Client, message: Message):
        """Log ALL group messages for debugging."""
        media_type = "none"
        if message.video:
            media_type = "VIDEO"
        elif message.document:
            media_type = f"DOC:{message.document.mime_type}"
        elif message.text:
            media_type = f"TEXT:{message.text[:20]}"

        logger.info(f"DEBUG: chat={message.chat.id} user={message.from_user.id if message.from_user else 'N/A'} media={media_type}")

    @staticmethod
    @Client.on_message(filters.group, group=1)
    async def handle_video_doc(client: Client, message: Message):
        """Handle both video and video documents."""
        if not is_video_file(message):
            return

        global total_task_counter, running_task_counter
        user_id = message.from_user.id
        username = message.from_user.username or message.from_user.first_name

        logger.info(f"VIDEO_HANDLER: user={user_id} chat={message.chat.id} video={message.video is not None} doc={message.document is not None}")

        # === 1. CHECK AUTH ===
        if not DEBUG_BYPASS_AUTH and not is_verified(user_id):
            logger.info(f"User {user_id} not verified")
            try:
                await message.reply_text(
                    get_pending_verification_msg(user_id, username),
                    reply_markup=get_verify_buttons()
                )
            except Exception as e:
                logger.error(f"Auth msg failed: {e}")
            return

        # === 2. CHECK QUEUE SLOT ===
        if not await queue_manager.acquire_slot(user_id):
            await message.reply(f"Queue full! You have {Config.MAX_QUEUE_PER_USER} active jobs.")
            return

        # === 3. DELETE ORIGINAL ===
        try:
            await message.delete()
        except Exception as e:
            logger.warning(f"Could not delete: {e}")

        # === 4. LOAD SETTINGS ===
        settings = get_user_settings(user_id)

        # === 5. ADD TO QUEUE ===
        total_task_counter += 1
        running_task_counter += 1

        queue_msg = await message.reply_text("Added to queue...")
        status_msg = await message.reply("Preparing...")
        tracker = ProgressTracker(client, status_msg, message.id, user_id)
        tracker.task_position = running_task_counter
        tracker.total_tasks = total_task_counter

        try:
            await EncodeHandler._pipeline(client, message, tracker, queue_msg, settings)
        except Exception as e:
            logger.error(f"Encode failed: {e}", exc_info=True)
            await tracker.finish(success=False, error_msg=str(e))
        finally:
            await queue_manager.release_slot(user_id)
            await queue_manager.unregister_job(message.id)
            running_task_counter = max(0, running_task_counter - 1)
            try:
                await queue_msg.delete()
            except Exception:
                pass

    @staticmethod
    async def _pipeline(client, message, tracker, queue_msg, settings):
        user_id = message.from_user.id
        username = message.from_user.username or message.from_user.first_name
        chat_id = message.chat.id

        # Get video info
        if message.video:
            video = message.video
        else:
            video = message.document

        video_name = video.file_name or f"video_{message.id}"
        screenshot_paths = []

        await tracker.update(stage="waiting", extra={"Info": "Queueing..."})

        async with queue_manager.encode_semaphore:
            if queue_manager.is_cancelled(message.id):
                await tracker.update(stage="cancelled")
                return

            await tracker.update(stage="downloading")

            timestamp = int(time.time())
            safe_name = safe_filename(video_name)
            input_path = Config.DOWNLOAD_PATH / f"{user_id}_{timestamp}_{safe_name}"
            output_path = Config.OUTPUT_PATH / f"{user_id}_{timestamp}_encoded_{safe_name}"

            try:
                # === DOWNLOAD ===
                start_dl = time.time()

                async def dl_progress(current, total):
                    await tracker.update(
                        current=current, total=total,
                        stage="downloading",
                        extra={"File": safe_name[:30]}
                    )

                await message.download(
                    file_name=str(input_path),
                    progress=dl_progress,
                    progress_args=()
                )

                dl_time = time.time() - start_dl
                input_size_bytes = input_path.stat().st_size
                input_size = get_file_size(input_path)

                if queue_manager.is_cancelled(message.id):
                    await tracker.update(stage="cancelled")
                    return

                # === THUMBNAIL ===
                thumb_path = None
                if not settings.disable_thumbnail:
                    if has_custom_thumbnail(user_id):
                        thumb_path = get_thumbnail_for_upload(user_id, input_path, video_name)
                    else:
                        auto_thumb = await generate_and_save_thumbnail(
                            input_path, user_id, video_name, position_percent=50.0
                        )
                        if auto_thumb:
                            thumb_path = str(auto_thumb)

                # === ENCODE ===
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

                cmd = build_ffmpeg_command(input_path, output_path, settings=settings)
                logger.info(f"FFmpeg: {' '.join(cmd)}")

                async def enc_progress(current_time, total_duration):
                    if queue_manager.is_cancelled(message.id):
                        return
                    await tracker.update(
                        current=current_time, total=total_duration,
                        stage="encoding"
                    )

                returncode, stdout, stderr = await run_ffmpeg(
                    cmd, progress_callback=enc_progress,
                    total_duration=getattr(video, "duration", 0) or 0
                )

                if returncode != 0:
                    raise RuntimeError(f"FFmpeg failed: {stderr[-500:]}")

                if queue_manager.is_cancelled(message.id):
                    await tracker.update(stage="cancelled")
                    return

                # === SCREENSHOTS ===
                ss_count = settings.get("screenshot_count", 3)
                if ss_count > 0:
                    screenshot_paths = await generate_screenshots(
                        output_path, user_id, video_name, count=ss_count
                    )

                # === UPLOAD ===
                await tracker.update(stage="uploading")
                output_size_bytes = output_path.stat().st_size
                output_size = get_file_size(output_path)

                saved_mb = (input_size_bytes - output_size_bytes) / (1024 * 1024)
                saved_text = ""
                if saved_mb > 0:
                    saved_text = f"Saved: {saved_mb:.0f}MB"
                elif saved_mb < 0:
                    saved_text = f"Size up: {abs(saved_mb):.0f}MB"

                total_time = time.time() - tracker.start_time

                caption = (
                    f"Compressed Video"
                    f"{output_size}"
                    f"{saved_text}"
                    f"Time: {format_duration(total_time)}"
                )
                if settings.caption:
                    caption += f"{settings.caption}"

                upload_kwargs = {
                    "caption": caption,
                    "supports_streaming": True,
                }
                if settings.spoiler_effect:
                    upload_kwargs["has_spoiler"] = True
                if thumb_path and not settings.disable_thumbnail:
                    upload_kwargs["thumb"] = thumb_path

                upload_tracker = UploadProgressTracker(
                    client=client, status_message=tracker.status_message,
                    file_path=output_path, user_id=user_id,
                    stage_name="Uploading to Telegram"
                )

                if settings.upload_type == "DOCUMENT":
                    await safe_upload_document(
                        client, chat_id=user_id, document_path=output_path,
                        tracker=upload_tracker, **upload_kwargs
                    )
                else:
                    await safe_upload_video(
                        client, chat_id=user_id, video_path=output_path,
                        tracker=upload_tracker, **upload_kwargs
                    )

                await upload_tracker.finish(success=True)

                # === SCREENSHOTS ALBUM ===
                if screenshot_paths:
                    await send_screenshots_as_album(
                        client, user_id, screenshot_paths,
                        caption=f"Screenshots from {video_name[:50]}"
                    )

                # === GROUP NOTIF ===
                try:
                    await tracker.status_message.delete()
                except Exception:
                    pass

                notif = f"@{username} - File compressed!{output_size} (from {input_size})"
                if saved_mb > 0:
                    notif += f"Saved: {saved_mb:.0f}MB"
                notif += f"Time: {format_duration(total_time)}Check DM for download"
                if screenshot_paths:
                    notif += f"{len(screenshot_paths)} screenshots sent"

                await client.send_message(chat_id=chat_id, text=notif)

            finally:
                cleanup_files(input_path, output_path)
                cleanup_screenshots(user_id, video_name)
