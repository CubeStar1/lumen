import base64
import io

from PIL import Image, ImageOps, UnidentifiedImageError

from floorplan.errors import InvalidImageError


def load_image(data: bytes) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(data))
        return ImageOps.exif_transpose(image).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidImageError("The uploaded file is not a readable image.") from exc


def to_data_url(image: Image.Image, max_side: int) -> str:
    encoded = base64.b64encode(_encode(image, max_side, "PNG")).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def to_jpeg(image: Image.Image, max_side: int) -> bytes:
    return _encode(image, max_side, "JPEG")


def _encode(image: Image.Image, max_side: int, fmt: str) -> bytes:
    resized = image.copy()
    resized.thumbnail((max_side, max_side))
    buffer = io.BytesIO()
    options = {"optimize": True} if fmt == "PNG" else {"quality": 85}
    resized.save(buffer, format=fmt, **options)
    return buffer.getvalue()
