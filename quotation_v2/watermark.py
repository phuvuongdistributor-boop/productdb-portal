from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WATERMARK_TEXT = "0929.382.666"
FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\arialbd.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]


def _font(size: int):
    path = next((candidate for candidate in FONT_CANDIDATES if candidate.exists()), None)
    return ImageFont.truetype(str(path), size) if path else ImageFont.load_default()


def apply_phone_watermark(image: Image.Image, opacity: int = 48) -> Image.Image:
    base = image.convert("RGBA")
    font_size = max(11, min(base.size) // 7)
    font = _font(font_size)
    measure = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    box = measure.textbbox((0, 0), WATERMARK_TEXT, font=font)
    text_width = box[2] - box[0]
    text_height = box[3] - box[1]
    padding = max(6, font_size // 2)
    label = Image.new(
        "RGBA",
        (text_width + padding * 2, text_height + padding * 2),
        (255, 255, 255, 0),
    )
    draw = ImageDraw.Draw(label)
    draw.text(
        (padding, padding // 2),
        WATERMARK_TEXT,
        fill=(255, 255, 255, opacity),
        stroke_width=max(1, font_size // 16),
        stroke_fill=(20, 35, 50, max(18, opacity // 2)),
        font=font,
    )
    label = label.rotate(18, expand=True, resample=Image.Resampling.BICUBIC)
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    overlay.alpha_composite(
        label,
        ((base.width - label.width) // 2, (base.height - label.height) // 2),
    )
    return Image.alpha_composite(base, overlay).convert("RGB")

