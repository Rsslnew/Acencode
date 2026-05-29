"""
Queue Manager - kontrol concurrent encode dan rate limit per user.
Tahan banting: semaphore + lock per user + auto cleanup.
"""
import asyncio
import logging
from collections import defaultdict
from bot.config import Config

logger = logging.getLogger(__name__)


class QueueManager:
    """Singleton queue manager untuk seluruh bot."""
    
    def __init__(self):
        # Semaphore global: max X encode bersamaan
        self.encode_semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT_ENCODE)
        
        # Lock per user: cegah 1 user spam banyak job
        self.user_locks = {}
        self.user_queue_counts = defaultdict(int)
        
        # Set untuk tracking job yang bisa di-cancel
        self.active_jobs = {}  # message_id -> {"proc", "cancelled"}
        self._lock = asyncio.Lock()
    
    def get_user_lock(self, user_id: int) -> asyncio.Lock:
        """Ambil atau buat lock untuk user."""
        if user_id not in self.user_locks:
            self.user_locks[user_id] = asyncio.Lock()
        return self.user_locks[user_id]
    
    async def acquire_slot(self, user_id: int) -> bool:
        """
        Coba ambil slot untuk user.
        Return True kalau berhasil, False kalau queue penuh.
        """
        async with self._lock:
            if self.user_queue_counts[user_id] >= Config.MAX_QUEUE_PER_USER:
                return False
            self.user_queue_counts[user_id] += 1
            return True
    
    async def release_slot(self, user_id: int):
        """Lepaskan slot user setelah selesai."""
        async with self._lock:
            self.user_queue_counts[user_id] = max(0, self.user_queue_counts[user_id] - 1)
    
    async def register_job(self, message_id: int, job_info: dict):
        """Register job aktif untuk cancel tracking."""
        async with self._lock:
            self.active_jobs[message_id] = job_info
    
    async def unregister_job(self, message_id: int):
        """Hapus job dari tracking."""
        async with self._lock:
            self.active_jobs.pop(message_id, None)
    
    async def cancel_job(self, message_id: int) -> bool:
        """
        Cancel job yang sedang berjalan.
        Return True kalau berhasil di-cancel.
        """
        async with self._lock:
            job = self.active_jobs.get(message_id)
            if not job:
                return False
            job["cancelled"] = True
            if "proc" in job and job["proc"]:
                try:
                    job["proc"].kill()
                except Exception:
                    pass
            return True
    
    def is_cancelled(self, message_id: int) -> bool:
        """Cek apakah job sudah di-cancel."""
        job = self.active_jobs.get(message_id)
        return job.get("cancelled", False) if job else False
    
    async def get_queue_position(self, user_id: int) -> int:
        """Hitung posisi antrian user (estimasi)."""
        async with self._lock:
            return self.user_queue_counts[user_id]


# Global instance
queue_manager = QueueManager()
