"""Create a branded automotive MP4 without paid media services."""

import math
import tempfile
import textwrap
from dataclasses import dataclass
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


@dataclass(frozen=True)
class TemporaryVideo:
    path: Path
    mime_type: str
    size_bytes: int


class VideoGenerationError(Exception):
    """Expected failure while rendering a video post."""


def generate_video_temp(news_item, settings, image_path=None):
    """Render one vertical H.264 video into the system temp directory."""

    width = int(settings["width"])
    height = int(settings["height"])
    fps = int(settings["fps"])
    duration = int(settings["duration_seconds"])
    temp_file = tempfile.NamedTemporaryFile(
        prefix="auto-news-video-", suffix=".mp4", delete=False
    )
    output_path = Path(temp_file.name)
    temp_file.close()
    writer = None

    try:
        writer = imageio_ffmpeg.write_frames(
            str(output_path),
            (width, height),
            fps=fps,
            codec="libx264",
            pix_fmt_in="rgb24",
            pix_fmt_out="yuv420p",
            output_params=[
                "-movflags", "+faststart", "-preset", "veryfast",
                "-crf", "25",
            ],
        )
        writer.send(None)

        for frame_index in range(fps * duration):
            progress = frame_index / max(1, (fps * duration) - 1)
            frame = _render_frame(
                news_item, settings, image_path, progress
            )
            writer.send(frame.tobytes())

        writer.close()
        size_bytes = output_path.stat().st_size
        if size_bytes == 0:
            raise VideoGenerationError("renderer returned an empty video")
        return TemporaryVideo(output_path, "video/mp4", size_bytes)
    except (OSError, ValueError, RuntimeError) as error:
        if writer is not None:
            try:
                writer.close()
            except (OSError, RuntimeError):
                pass
        if output_path.exists():
            output_path.unlink()
        raise VideoGenerationError(type(error).__name__) from error


def _render_frame(news_item, settings, image_path, progress):
    width = int(settings["width"])
    height = int(settings["height"])
    frame = Image.new("RGB", (width, height), settings["background"])

    if image_path:
        frame = _image_background(Path(image_path), width, height, progress)

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle((0, 0, width, height), fill=(4, 8, 12, 105))
    draw.rectangle((0, height * 0.46, width, height), fill=(8, 13, 19, 234))
    accent_x = int(54 + 16 * math.sin(progress * math.pi))
    draw.rounded_rectangle(
        (accent_x, 585, accent_x + 118, 599),
        radius=7,
        fill=settings["accent"],
    )

    title_font = _font(54, bold=True)
    body_font = _font(31)
    label_font = _font(25, bold=True)
    title = _wrap(news_item.get("title", "Без заголовка"), 21, 5)
    body_text = (
        news_item.get("description")
        or news_item.get("article_text", "")
    )
    body = _wrap(body_text, 36, 3)
    source = str(news_item.get("source", "АВТО НОВОСТИ")).upper()[:34]
    opacity = min(1.0, progress * 5)

    text_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)
    text_draw.text(
        (54, 70), "АВТО НОВОСТИ", font=label_font,
        fill=_rgba(settings["highlight"], opacity),
    )
    text_draw.multiline_text(
        (54, 630), title, font=title_font,
        fill=_rgba(settings["foreground"], opacity), spacing=12,
    )
    title_box = text_draw.multiline_textbbox(
        (54, 630), title, font=title_font, spacing=12
    )
    body_y = min(1040, title_box[3] + 38)
    text_draw.multiline_text(
        (54, body_y), body, font=body_font,
        fill=_rgba(settings["muted"], opacity), spacing=10,
    )
    text_draw.text(
        (54, 1205), source, font=label_font,
        fill=_rgba(settings["accent"], opacity),
    )

    composed = Image.alpha_composite(frame.convert("RGBA"), overlay)
    return Image.alpha_composite(composed, text_layer).convert("RGB")


def _image_background(path, width, height, progress):
    with Image.open(path) as source:
        source = source.convert("RGB")
        scale = max(width / source.width, height / source.height)
        scale *= 1.0 + (0.06 * progress)
        resized = source.resize(
            (math.ceil(source.width * scale), math.ceil(source.height * scale)),
            Image.Resampling.LANCZOS,
        )
        left = max(0, (resized.width - width) // 2)
        top = max(0, (resized.height - height) // 2)
        crop = resized.crop((left, top, left + width, top + height))
        crop = crop.filter(ImageFilter.GaussianBlur(radius=1.4))
        return ImageEnhance.Color(crop).enhance(1.15)


def _font(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(name, size=size)
    except OSError:
        return ImageFont.load_default()


def _wrap(value, width, max_lines):
    lines = textwrap.wrap(
        " ".join(str(value or "").split()),
        width=width,
        break_long_words=True,
    )[:max_lines]
    return "\n".join(lines)


def _rgba(hex_color, opacity):
    value = hex_color.lstrip("#")
    rgb = tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))
    return (*rgb, round(255 * opacity))
