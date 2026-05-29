"""
FFmpeg wrapper - enhanced with user settings and watermark support.
"""
import asyncio
import logging
import re
from pathlib import Path
from bot.config import Config
from bot.utils.watermark import apply_watermark_to_cmd

logger = logging.getLogger(__name__)


def build_ffmpeg_command(input_path: Path, output_path: Path, settings=None) -> list:
    """
    Build ffmpeg command from user settings or config default.

    Args:
        input_path: Path input video
        output_path: Path output video
        settings: UserSettings object (optional)
    """
    cmd = [
        "ffmpeg",
        "-y",                       # overwrite output
        "-i", str(input_path),      # input
    ]

    if settings:
        # === VIDEO ===
        cmd.extend(["-c:v", settings.video_codec])

        # Bitrate mode OR CRF mode
        if settings.video_bitrate:
            cmd.extend(["-b:v", str(settings.video_bitrate)])
        else:
            cmd.extend(["-crf", str(settings.crf)])

        cmd.extend(["-preset", settings.preset])

        # Resolution scaling
        if settings.resolution:
            cmd.extend(["-vf", f"scale=-2:{settings.resolution}"])

        # === AUDIO ===
        cmd.extend(["-c:a", settings.audio_codec])
        if settings.audio_codec != "copy" and settings.audio_bitrate != "copy":
            cmd.extend(["-b:a", str(settings.audio_bitrate)])

        # === METADATA ===
        meta = settings.metadata
        if meta.get("video_title"):
            cmd.extend(["-metadata", f"title={meta['video_title']}"])
        if meta.get("video_author"):
            cmd.extend(["-metadata", f"artist={meta['video_author']}"])

    else:
        # Fallback ke config global
        cmd.extend(["-c:v", Config.VIDEO_CODEC])
        cmd.extend(["-crf", str(Config.FFMPEG_CRF)])
        cmd.extend(["-preset", Config.FFMPEG_PRESET])
        cmd.extend(["-c:a", Config.AUDIO_CODEC])
        cmd.extend(["-b:a", Config.AUDIO_BITRATE])

    # Common flags
    cmd.extend([
        "-pix_fmt", "yuv420p",      # compatibility
        "-movflags", "+faststart",  # web streaming ready
    ])

    cmd.append(str(output_path))

    # === WATERMARK INJECTION ===
    if settings and (settings.text_watermark or settings.image_watermark):
        image_wm_path = None
        if settings.image_watermark:
            image_wm_path = Path(settings.image_watermark)
            if not image_wm_path.exists():
                image_wm_path = None
                logger.warning(f"Image watermark not found: {settings.image_watermark}")

        cmd = apply_watermark_to_cmd(
            cmd,
            text=settings.text_watermark,
            image_path=image_wm_path,
            position=settings.watermark_position
        )

    return cmd


async def run_ffmpeg(cmd: list, progress_callback=None, total_duration: float = 0):
    """
    Run ffmpeg dengan timeout dan progress parsing.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")
        stderr_data = []

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

                if progress_callback and total_duration > 0:
                    match = time_pattern.search(decoded)
                    if match:
                        h, m, s = map(float, match.groups())
                        current_time = h * 3600 + m * 60 + s
                        await progress_callback(current_time, total_duration)

            except asyncio.TimeoutError:
                if proc.returncode is not None:
                    break
                continue

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
