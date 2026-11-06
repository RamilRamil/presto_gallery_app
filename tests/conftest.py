import io

import pytest
from PIL import Image


def png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def gradient() -> Image.Image:
    """Deterministic 120x80 RGB test picture with many colors."""
    image = Image.new("RGB", (120, 80))
    image.putdata([(x * 2, y * 3, (x + y) % 256) for y in range(80) for x in range(120)])
    return image
