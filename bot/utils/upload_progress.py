"""
Upload Progress Tracker with FloodWait handling.
Tracks Telegram upload progress and handles rate limits gracefully.
"""
import asyncio
import logging
import time
from pathlib import Path
from pyrogram.errors import FloodWait
from bot.utils.helpers import get_file_size, format_duration, generate_progress_bar

logger = logging.getLogger(__name__)


class UploadProgressTracker:
    """
    Tracks upload progress to Telegram with FloodWait handling.
    """

    def __init__(self, client, status_message, file_path: Path, 
                 user_id: int, stage_name: str = "Uploading"):
        self.client = client
        self.status_message = status_message
        self.file_path = file_path
        self.user_id = user_id
        self.stage_name = stage_name

        self.start_time = time.time()
        self.last_update = 0
        self.update_interval = 4.0  # Update every 4 seconds
        self._cancelled = False

        self.total_bytes = file_path.stat().st_size
        self.uploaded_bytes = 0
        self.last_uploaded = 0
        self.last_time = time.time()

        # FloodWait handling
        self.flood_wait_count = 0
        self.max_flood_retries = 5
        self.base_retry_delay = 5

    def cancel(self):
        self._cancelled = True

    @property
    def is_cancelled(self):
        return self._cancelled

    async def _update_status(self):
        """Update status message with current progress."""
        now = time.time()
        if now - self.last_update < self.update_interval:
            return

        elapsed = now - self.start_time

        if self.uploaded_bytes > 0:
            percent = min(100, (self.uploaded_bytes / self.total_bytes) * 100)
            speed_bps = self.uploaded_bytes / elapsed if elapsed > 0 else 0

            # Calculate ETA
            remaining_bytes = self.total_bytes - self.uploaded_bytes
            eta_seconds = remaining_bytes / speed_bps if speed_bps > 0 else 0

            bar = generate_progress_bar(self.uploaded_bytes, self.total_bytes)

            text = (
                f"{self.stage_name}\n"
                f"{bar} {percent:.1f}%\n"
                f"Speed: {format_speed(speed_bps)} | "
                f"ETA: {format_duration(eta_seconds)}"
            )

            if self.flood_wait_count > 0:
                text += f"\n(Rate limited: {self.flood_wait_count}x)"

            try:
                await self.status_message.edit_text(text)
                self.last_update = now
            except FloodWait as e:
                logger.warning(f"FloodWait during status update: {e.value}s")
                await asyncio.sleep(min(e.value, 10))
            except Exception as e:
                logger.debug(f"Failed to update upload status: {e}")

    async def progress_callback(self, current: int, total: int):
        """
        Callback for Pyrogram upload/download progress.

        Args:
            current: Bytes uploaded so far
            total: Total bytes to upload
        """
        self.uploaded_bytes = current
        self.total_bytes = total
        await self._update_status()

    async def upload_with_retry(self, upload_func, *args, **kwargs):
        """
        Execute upload function with FloodWait retry logic.

        Args:
            upload_func: Pyrogram upload method (send_video/send_document/etc)
            *args, **kwargs: Arguments for upload function

        Returns:
            Result from upload function
        """
        for attempt in range(self.max_flood_retries):
            try:
                # Inject progress callback
                kwargs["progress"] = self.progress_callback
                kwargs["progress_args"] = ()

                result = await upload_func(*args, **kwargs)
                return result

            except FloodWait as e:
                self.flood_wait_count += 1
                wait_time = e.value

                logger.warning(
                    f"FloodWait hit for user {self.user_id}: "
                    f"{wait_time}s (attempt {attempt + 1}/{self.max_flood_retries})"
                )

                # Notify user about wait
                try:
                    await self.status_message.edit_text(
                        f"Rate limited by Telegram!\n"
                        f"Waiting {wait_time}s before retry...\n"
                        f"Attempt {attempt + 1}/{self.max_flood_retries}"
                    )
                except Exception:
                    pass

                # Wait with cap
                await asyncio.sleep(min(wait_time, 60))

                # Exponential backoff for next attempt
                if attempt < self.max_flood_retries - 1:
                    backoff = self.base_retry_delay * (2 ** attempt)
                    await asyncio.sleep(backoff)

            except Exception as e:
                logger.error(f"Upload error: {e}")
                raise

        raise RuntimeError(
            f"Upload failed after {self.max_flood_retries} attempts "
            f"due to persistent FloodWait"
        )

    async def finish(self, success: bool = True):
        """Mark upload as finished."""
        elapsed = time.time() - self.start_time

        if success:
            text = (
                f"Upload complete!\n"
                f"Time: {format_duration(elapsed)}\n"
                f"Size: {get_file_size(self.file_path)}"
            )
        else:
            text = "Upload failed or cancelled."

        try:
            await self.status_message.edit_text(text)
        except Exception:
            pass


def format_speed(bps: float) -> str:
    """Format bytes per second to human readable."""
    if bps >= 1024 * 1024:
        return f"{bps / (1024 * 1024):.1f} MB/s"
    elif bps >= 1024:
        return f"{bps / 1024:.1f} KB/s"
    else:
        return f"{bps:.1f} B/s"


async def safe_upload_video(client, chat_id, video_path, **kwargs):
    """
    Safe video upload with FloodWait handling.
    Wrapper untuk client.send_video dengan retry.
    """
    tracker = kwargs.pop("tracker", None)

    if tracker:
        return await tracker.upload_with_retry(
            client.send_video,
            chat_id=chat_id,
            video=str(video_path),
            **kwargs
        )
    else:
        return await client.send_video(
            chat_id=chat_id,
            video=str(video_path),
            **kwargs
        )


async def safe_upload_document(client, chat_id, document_path, **kwargs):
    """
    Safe document upload with FloodWait handling.
    Wrapper untuk client.send_document dengan retry.
    """
    tracker = kwargs.pop("tracker", None)

    if tracker:
        return await tracker.upload_with_retry(
            client.send_document,
            chat_id=chat_id,
            document=str(document_path),
            **kwargs
        )
    else:
        return await client.send_document(
            chat_id=chat_id,
            document=str(document_path),
            **kwargs
        )
        