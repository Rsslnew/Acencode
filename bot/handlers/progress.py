"""
Progress Tracker v2 - dengan speed, ETA, inline buttons, task counter.
"""
import asyncio
import logging
import time
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils.helpers import generate_progress_bar, format_duration

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Advanced progress tracker dengan speed & ETA."""
    
    def __init__(self, client, status_message: Message, job_id: str, user_id: int):
        self.client = client
        self.status_message = status_message
        self.job_id = job_id
        self.user_id = user_id
        
        self.start_time = time.time()
        self.last_update = 0
        self.update_interval = 2
        self._lock = asyncio.Lock()
        
        self.downloaded = 0
        self.total = 0
        self.stage = "waiting"
        self.extra_info = {}
        
        # Speed tracking
        self.last_bytes = 0
        self.last_speed_time = time.time()
        self.speed = 0
        
        # Global task counter
        self.task_position = 0
        self.total_tasks = 0
    
    async def update(self, current: int = None, total: int = None,
                     stage: str = None, extra: dict = None):
        now = time.time()
        
        async with self._lock:
            if current is not None:
                if current > self.last_bytes and now > self.last_speed_time:
                    self.speed = (current - self.last_bytes) / (now - self.last_speed_time)
                self.last_bytes = current
                self.last_speed_time = now
                self.downloaded = current
            
            if total is not None:
                self.total = total
            if stage:
                self.stage = stage
            if extra:
                self.extra_info.update(extra)
            
            if now - self.last_update < self.update_interval and stage not in ["done", "error", "cancelled"]:
                return
            self.last_update = now
            
            try:
                text = self._build_text()
                buttons = self._build_buttons()
                await self.status_message.edit_text(text, reply_markup=buttons)
            except Exception as e:
                if "FLOOD_WAIT" in str(e):
                    self.update_interval += 2
                logger.debug(f"Progress update failed: {e}")
    
    def _build_text(self) -> str:
        elapsed = time.time() - self.start_time
        
        emojis = {
            "waiting": "⏳", "downloading": "📥",
            "encoding": "🎬", "uploading": "📤",
            "done": "✅", "error": "❌", "cancelled": "🚫"
        }
        emoji = emojis.get(self.stage, "⏳")
        
        lines = [
            f"**Task Running: {self.task_position}/{self.total_tasks}**",
            f"",
            f"1.**{self.stage.title()}:**",
        ]
        
        if self.total > 0 and self.stage in ["downloading", "encoding", "uploading"]:
            pct = min((self.downloaded / self.total) * 100, 100)
            bar = generate_progress_bar(int(self.downloaded), int(self.total), length=12)
            lines.append(f"{bar} {pct:.2f}%")
            
            if self.total > 0:
                proc_mb = self.downloaded / (1024 * 1024)
                total_mb = self.total / (1024 * 1024)
                lines.append(f"Processed: {proc_mb:.2f}MB")
                lines.append(f"Size: {total_mb:.2f}MB")
            
            if self.speed > 0:
                speed_mb = self.speed / (1024 * 1024)
                lines.append(f"Speed: {speed_mb:.2f}MB/s")
                remaining = self.total - self.downloaded
                eta = remaining / self.speed if self.speed > 0 else 0
                lines.append(f"ETA: {format_duration(eta)}")
        
        lines.append(f"Elapsed: {format_duration(elapsed)}")
        lines.append(f"Upload: Telegram")
        lines.append(f"Engine: Pyrogram + FFmpeg")
        lines.append(f"`{self.user_id}`")
        
        return "\n".join(lines)
    
    def _build_buttons(self):
        if self.stage in ["done", "error", "cancelled"]:
            return None
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel Task", callback_data=f"cancel:{self.job_id}")],
            [InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh:{self.job_id}")]
        ])
    
    async def finish(self, success: bool = True, error_msg: str = None, cancelled: bool = False):
        if cancelled:
            self.stage = "cancelled"
        else:
            self.stage = "done" if success else "error"
        if error_msg:
            self.extra_info["Error"] = error_msg
        
        try:
            text = self._build_text()
            await self.status_message.edit_text(text, reply_markup=None)
        except Exception as e:
            logger.warning(f"Final update failed: {e}")
