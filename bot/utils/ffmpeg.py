"""
FFmpeg wrapper - run encode dengan subprocess async.
Tahan banting: timeout, kill zombie process, catch all errors.
"""
import asyncio
import logging
import re
from pathlib import Path
from bot.config import Config

logger = logging.getLogger(__name__)


def build_ffmpeg_command(input_path: Path, output_path: Path) -> list:
    """Build ffmpeg command dari config."""
    return [
        "ffmpeg",
        "-y",                       # overwrite output
        "-i", str(input_path),      # input
        "-c:v", Config.VIDEO_CODEC,
        "-crf", str(Config.FFMPEG_CRF),
        "-preset", Config.FFMPEG_PRESET,
        "-c:a", Config.AUDIO_CODEC,
        "-b:a", Config.AUDIO_BITRATE,
        "-pix_fmt", "yuv420p",      # compatibility
        "-movflags", "+faststart",  # web streaming ready
        str(output_path)
    ]


async def run_ffmpeg(cmd: list, progress_callback=None, total_duration: float = 0):
    """
    Run ffmpeg dengan timeout dan progress parsing.
    
    Args:
        cmd: ffmpeg command list
        progress_callback: async callable(time) untuk update progress
        total_duration: total video duration dalam detik (untuk progress %)
    
    Returns:
        (returncode, stdout, stderr)
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        # Pattern untuk parse time dari stderr ffmpeg
        time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")
        
        stderr_data = []
        
        # Baca stderr line by line untuk progress
        while True:
            try:
                line = await asyncio.wait_for(
                    proc.stderr.readline(),
                    timeout=5.0
                )
                if not line:
                    break
                decoded = line.decode("utf-8", errors="ignore")
                stderr_data.append(decoded)
                
                # Parse progress
                if progress_callback and total_duration > 0:
                    match = time_pattern.search(decoded)
                    if match:
                        h, m, s = map(float, match.groups())
                        current_time = h * 3600 + m * 60 + s
                        await progress_callback(current_time, total_duration)
                        
            except asyncio.TimeoutError:
                # Cek apakah process masih jalan
                if proc.returncode is not None:
                    break
                continue
        
        # Wait dengan timeout global
        try:
            returncode = await asyncio.wait_for(
                proc.wait(),
                timeout=Config.FFMPEG_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.error("FFmpeg timeout! Killing process...")
            proc.kill()
            await proc.wait()
            raise TimeoutError(f"FFmpeg exceeded {Config.FFMPEG_TIMEOUT}s timeout")
        
        stdout = (await proc.stdout.read()).decode("utf-8", errors="ignore")
        stderr = "".join(stderr_data)
        
        return returncode, stdout, stderr
        
    except FileNotFoundError:
        raise RuntimeError("ffmpeg tidak ditemukan! Install ffmpeg terlebih dahulu.")
    except Exception as e:
        logger.error(f"FFmpeg error: {e}")
        raise
        