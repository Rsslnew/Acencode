"""
Watermark module for FFmpeg - text and image watermark support.
"""
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Position mapping for text watermark (x, y coordinates)
TEXT_POSITIONS = {
    "top-left":      ("10", "10"),
    "top-right":     ("w-text_w-10", "10"),
    "bottom-left":   ("10", "h-text_h-10"),
    "bottom-right":  ("w-text_w-10", "h-text_h-10"),
    "center":        ("(w-text_w)/2", "(h-text_h)/2"),
}

# Position mapping for image watermark (x, y coordinates)
IMAGE_POSITIONS = {
    "top-left":      ("10", "10"),
    "top-right":     ("W-w-10", "10"),
    "bottom-left":   ("10", "H-h-10"),
    "bottom-right":  ("W-w-10", "H-h-10"),
    "center":        ("(W-w)/2", "(H-h)/2"),
}


def build_text_watermark_filter(text: str, position: str = "bottom-right",
                                 font_size: int = 24, font_color: str = "white",
                                 opacity: float = 0.7) -> str:
    """
    Build FFmpeg drawtext filter for text watermark.
    """
    x, y = TEXT_POSITIONS.get(position, TEXT_POSITIONS["bottom-right"])

    # Escape special characters in text for FFmpeg drawtext
    escaped_text = text.replace("\\", "\\\\")
    escaped_text = escaped_text.replace("'", "\\'")
    escaped_text = escaped_text.replace(":", "\\:")
    escaped_text = escaped_text.replace("%", "\\%")

    # Build drawtext filter
    filter_str = (
        f"drawtext=text='{escaped_text}':"
        f"x={x}:y={y}:"
        f"fontsize={font_size}:"
        f"fontcolor={font_color}@{opacity}:"
        f"borderw=2:bordercolor=black@{opacity}:"
        f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    )

    return filter_str


def build_image_watermark_filter(image_path: Path, position: str = "bottom-right",
                                  scale: float = 0.15, opacity: float = 0.7) -> str:
    """
    Build FFmpeg overlay filter for image watermark.
    """
    x, y = IMAGE_POSITIONS.get(position, IMAGE_POSITIONS["bottom-right"])

    filter_str = (
        f"[1:v]scale=iw*{scale}:-1[wm];"
        f"[0:v][wm]overlay={x}:{y}:format=auto"
    )

    if opacity < 1.0:
        filter_str = (
            f"[1:v]scale=iw*{scale}:-1,format=rgba,"
            f"colorchannelmixer=aa={opacity}[wm];"
            f"[0:v][wm]overlay={x}:{y}:format=auto"
        )

    return filter_str


def build_watermark_cmd(input_path: Path, output_path: Path,
                        text: Optional[str] = None,
                        image_path: Optional[Path] = None,
                        position: str = "bottom-right") -> Tuple[list, bool]:
    """
    Build full FFmpeg command with watermark(s).
    """
    cmd = ["ffmpeg", "-y"]

    has_image = False
    filters = []

    cmd.extend(["-i", str(input_path)])

    if image_path and image_path.exists():
        cmd.extend(["-i", str(image_path)])
        has_image = True

    if has_image and text:
        x_img, y_img = IMAGE_POSITIONS.get(position, IMAGE_POSITIONS["bottom-right"])
        x_txt, y_txt = TEXT_POSITIONS.get(position, TEXT_POSITIONS["bottom-right"])

        escaped_text = text.replace("\\", "\\\\")
        escaped_text = escaped_text.replace("'", "\\'")
        escaped_text = escaped_text.replace(":", "\\:")
        escaped_text = escaped_text.replace("%", "\\%")

        combined_filter = (
            f"[1:v]scale=iw*0.15:-1[wm];"
            f"[0:v][wm]overlay={x_img}:{y_img}:format=auto[tmp];"
            f"[tmp]drawtext=text='{escaped_text}':"
            f"x={x_txt}:y={y_txt}:"
            f"fontsize=24:fontcolor=white@0.7:"
            f"borderw=2:bordercolor=black@0.7:"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        )
        filters.append(combined_filter)
    elif has_image:
        x_img, y_img = IMAGE_POSITIONS.get(position, IMAGE_POSITIONS["bottom-right"])
        img_filter = (
            f"[1:v]scale=iw*0.15:-1[wm];"
            f"[0:v][wm]overlay={x_img}:{y_img}:format=auto"
        )
        filters.append(img_filter)
    elif text:
        txt_filter = build_text_watermark_filter(text, position)
        filters.append(txt_filter)

    if filters:
        cmd.extend(["-filter_complex", ";".join(filters)])

    cmd.extend([
        "-c:v", "libx264",
        "-crf", "23",
        "-preset", "veryfast",
        "-c:a", "copy",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_path)
    ])

    return cmd, has_image


def apply_watermark_to_cmd(base_cmd: list, text: Optional[str] = None,
                           image_path: Optional[Path] = None,
                           position: str = "bottom-right") -> list:
    """
    Inject watermark filters into existing FFmpeg command.
    """
    if not text and not (image_path and image_path.exists()):
        return base_cmd

    cmd = ["ffmpeg", "-y"]
    has_image = False

    input_idx = base_cmd.index("-i") + 1 if "-i" in base_cmd else None

    if input_idx:
        input_path = base_cmd[input_idx]
        cmd.extend(["-i", input_path])

    if image_path and image_path.exists():
        cmd.extend(["-i", str(image_path)])
        has_image = True

    filters = []

    if has_image and text:
        x_img, y_img = IMAGE_POSITIONS.get(position, IMAGE_POSITIONS["bottom-right"])
        x_txt, y_txt = TEXT_POSITIONS.get(position, TEXT_POSITIONS["bottom-right"])
        escaped_text = text.replace("\\", "\\\\")
        escaped_text = escaped_text.replace("'", "\\'")
        escaped_text = escaped_text.replace(":", "\\:")
        escaped_text = escaped_text.replace("%", "\\%")

        combined = (
            f"[1:v]scale=iw*0.15:-1[wm];"
            f"[0:v][wm]overlay={x_img}:{y_img}:format=auto[tmp];"
            f"[tmp]drawtext=text='{escaped_text}':"
            f"x={x_txt}:y={y_txt}:"
            f"fontsize=24:fontcolor=white@0.7:"
            f"borderw=2:bordercolor=black@0.7"
        )
        filters.append(combined)
    elif has_image:
        x_img, y_img = IMAGE_POSITIONS.get(position, IMAGE_POSITIONS["bottom-right"])
        img_filter = (
            f"[1:v]scale=iw*0.15:-1[wm];"
            f"[0:v][wm]overlay={x_img}:{y_img}:format=auto"
        )
        filters.append(img_filter)
    elif text:
        txt_filter = build_text_watermark_filter(text, position)
        filters.append(txt_filter)

    if filters:
        cmd.extend(["-filter_complex", ";".join(filters)])

    output_path = base_cmd[-1]

    skip_next = False
    for i, arg in enumerate(base_cmd):
        if skip_next:
            skip_next = False
            continue
        if arg in ("-c:v", "-crf", "-preset", "-c:a", "-b:a", "-pix_fmt", "-movflags", "-vf"):
            cmd.extend([arg, base_cmd[i + 1]])
            skip_next = True
        elif arg == "-i":
            skip_next = True

    cmd.extend(["-pix_fmt", "yuv420p", "-movflags", "+faststart", output_path])

    return cmd
