import io

from PIL import Image


def load_image(image_bytes: bytes) -> Image.Image:
    return Image.open(io.BytesIO(image_bytes))


def resize_for_analysis(img: Image.Image, size: int = 512) -> Image.Image:
    return img.resize((size, size), Image.Resampling.LANCZOS)


def to_rgb(img: Image.Image) -> Image.Image:
    return img.convert("RGB")


def to_grayscale(img: Image.Image) -> Image.Image:
    return img.convert("L")
