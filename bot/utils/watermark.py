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

    Args:
        text: Watermark text
        position: Position key from TEXT_POSITIONS
        font_size: Font size in pixels
        font_color: Font color name or hex
        opacity: Opacity 0.0-1.0

    Returns:
        FFmpeg drawtext filter string
    """
    x, y = TEXT_POSITIONS.get(position, TEXT_POSITIONS["bottom-right"])

    # Escape special characters in text
    escaped_text = text.replace("'", "\'").replace(":", "\:").replace("\", "\\")

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

    Args:
        image_path: Path to watermark image (PNG with alpha recommended)
        position: Position key from IMAGE_POSITIONS
        scale: Scale ratio relative to video width (0.0-1.0)
        opacity: Opacity 0.0-1.0

    Returns:
        FFmpeg overlay filter string (requires movie input)
    """
    x, y = IMAGE_POSITIONS.get(position, IMAGE_POSITIONS["bottom-right"])

    # Build overlay filter
    # First scale the watermark, then overlay with opacity
    filter_str = (
        f"[1:v]scale=iw*{scale}:-1[wm];"
        f"[0:v][wm]overlay={x}:{y}:format=auto"
    )

    if opacity < 1.0:
        # Add opacity via format and colorchannelmixer
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

    Args:
        input_path: Input video path
        output_path: Output video path
        text: Text watermark string (optional)
        image_path: Image watermark path (optional)
        position: Watermark position

    Returns:
        Tuple of (command list, has_image_watermark bool)
    """
    cmd = ["ffmpeg", "-y"]

    has_image = False
    filters = []

    # Add main input
    cmd.extend(["-i", str(input_path)])

    # Image watermark input (if provided)
    if image_path and image_path.exists():
        cmd.extend(["-i", str(image_path)])
        has_image = True
        img_filter = build_image_watermark_filter(image_path, position)
        filters.append(img_filter)

    # Text watermark (if provided)
    if text:
        txt_filter = build_text_watermark_filter(text, position)
        if filters:
            # If image watermark exists, append text to the output of overlay
            # This is complex; for simplicity, we apply text after image
            # Actually, we need to chain filters properly
            last_filter = filters[-1]
            # Replace the last filter to chain with drawtext
            # [0:v][1:v]overlay=... -> result, then drawtext on result
            # This requires filter_complex with named outputs
            pass  # Will handle in combined filter below
        else:
            filters.append(txt_filter)

    # Build combined filter_complex if both watermarks exist
    if has_image and text:
        # Complex filter chain: overlay first, then drawtext
        x_img, y_img = IMAGE_POSITIONS.get(position, IMAGE_POSITIONS["bottom-right"])
        x_txt, y_txt = TEXT_POSITIONS.get(position, TEXT_POSITIONS["bottom-right"])

        escaped_text = text.replace("'", "\'").replace(":", "\:").replace("\", "\\")

        combined_filter = (
            f"[1:v]scale=iw*0.15:-1[wm];"
            f"[0:v][wm]overlay={x_img}:{y_img}:format=auto[tmp];"
            f"[tmp]drawtext=text='{escaped_text}':"
            f"x={x_txt}:y={y_txt}:"
            f"fontsize=24:fontcolor=white@0.7:"
            f"borderw=2:bordercolor=black@0.7:"
            f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        )
        filters = [combined_filter]

    if filters:
        cmd.extend(["-filter_complex", ";".join(filters)])

    # Output settings
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

    This modifies a standard command to add watermark before output.

    Args:
        base_cmd: Existing ffmpeg command list
        text: Text watermark
        image_path: Image watermark path
        position: Position string

    Returns:
        Modified command list
    """
    if not text and not (image_path and image_path.exists()):
        return base_cmd

    # Parse base_cmd to find input and output positions
    # Standard: ffmpeg -y -i input ... -c:v ... output

    cmd = ["ffmpeg", "-y"]
    has_image = False

    # Find input file index
    input_idx = base_cmd.index("-i") + 1 if "-i" in base_cmd else None

    if input_idx:
        input_path = base_cmd[input_idx]
        cmd.extend(["-i", input_path])

    # Add image watermark input if exists
    if image_path and image_path.exists():
        cmd.extend(["-i", str(image_path)])
        has_image = True

    # Build filter
    filters = []

    if has_image and text:
        # Both watermarks
        x_img, y_img = IMAGE_POSITIONS.get(position, IMAGE_POSITIONS["bottom-right"])
        x_txt, y_txt = TEXT_POSITIONS.get(position, TEXT_POSITIONS["bottom-right"])
        escaped_text = text.replace("'", "\'").replace(":", "\:").replace("\", "\\")

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
        # Only image
        x_img, y_img = IMAGE_POSITIONS.get(position, IMAGE_POSITIONS["bottom-right"])
        img_filter = (
            f"[1:v]scale=iw*0.15:-1[wm];"
            f"[0:v][wm]overlay={x_img}:{y_img}:format=auto"
        )
        filters.append(img_filter)
    elif text:
        # Only text
        txt_filter = build_text_watermark_filter(text, position)
        filters.append(txt_filter)

    if filters:
        cmd.extend(["-filter_complex", ";".join(filters)])

    # Copy remaining options from base_cmd (excluding input and output)
    # Find output (last item)
    output_path = base_cmd[-1]

    # Add video/audio codec options from base_cmd
    skip_next = False
    for i, arg in enumerate(base_cmd):
        if skip_next:
            skip_next = False
            continue
        if arg in ("-c:v", "-crf", "-preset", "-c:a", "-b:a", "-pix_fmt", "-movflags", "-vf"):
            cmd.extend([arg, base_cmd[i + 1]])
            skip_next = True
        elif arg == "-i":
            skip_next = True  # Skip input, already handled

    cmd.extend(["-pix_fmt", "yuv420p", "-movflags", "+faststart", output_path])

    return cmd
