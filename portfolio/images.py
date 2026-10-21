"""Картинки: всё, что загружают в админке, перекодируется в webp и уменьшается."""
from io import BytesIO
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_SIDE = 1600
WEBP_QUALITY = 82


def validate_image_size(file) -> None:
    if file.size > MAX_UPLOAD_BYTES:
        raise ValidationError("Файл больше 5 МБ — уменьшите картинку.")


def to_webp(file, max_side: int = MAX_SIDE) -> ContentFile:
    """Открыть картинку, повернуть по EXIF, уменьшить до max_side и вернуть webp без метаданных."""
    file.seek(0)
    with Image.open(file) as source:
        image = ImageOps.exif_transpose(source)
        image = image.convert("RGBA" if image.mode in ("RGBA", "LA", "P") else "RGB")
        image.thumbnail((max_side, max_side))
        buffer = BytesIO()
        image.save(buffer, "WEBP", quality=WEBP_QUALITY, method=6)
    return ContentFile(buffer.getvalue(), name=Path(file.name).stem + ".webp")
