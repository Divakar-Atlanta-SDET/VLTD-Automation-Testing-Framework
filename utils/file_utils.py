"""File upload helpers: paths to test files and runtime generation of images / invalid files."""

import base64
import os
import struct
import zlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FILES_DIR = PROJECT_ROOT / "data" / "files"

# Valid PDF used for certificates and the driver licence
TEST_PDF = FILES_DIR / "test.pdf"

KB = 1024
MB = 1024 * KB

# 1x1 transparent PNG
_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
_PNG_SIGNATURE = _PNG_BYTES[:8]
_PDF_HEADER = b"%PDF-1.4\n"


def create_test_png(directory: Path, name: str = "driver_photo.png") -> Path:
    """Write a minimal valid PNG into `directory` and return its path."""
    path = Path(directory) / name
    path.write_bytes(_PNG_BYTES)
    return path


def _png(width: int, height: int, rows: bytes, color_type: int, level: int = 6) -> bytes:
    def chunk(kind: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)
    return _PNG_SIGNATURE + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(rows, level)) + chunk(b"IEND", b"")


def png_bytes(size: int = 320, height: int | None = None) -> bytes:
    """A valid solid-colour PNG, size x height pixels (square by default); the Fitment Center image must be 300 to 4096 px a side."""
    height = height or size
    return _png(size, height, b"".join(b"\x00" + bytes([40, 120, 200]) * size for _ in range(height)), color_type=2)


def large_png_bytes(width: int, height: int) -> bytes:
    """A valid grey PNG of the given pixel size that stays small (one byte a pixel, compressed fast): for dimension limits."""
    return _png(width, height, b"".join(b"\x00" + bytes([128]) * width for _ in range(height)), color_type=0, level=1)


def noise_png_bytes(width: int, height: int) -> bytes:
    """A valid PNG of random pixels that cannot be compressed, so the file is about 3 * width * height bytes: for size limits."""
    return _png(width, height, b"".join(b"\x00" + os.urandom(3 * width) for _ in range(height)), color_type=2, level=0)


def create_sized_png(directory: Path, size: int = 320, name: str = "fitment_centre.png", height: int | None = None) -> Path:
    """Write a size x height PNG (square by default) into `directory` and return its path."""
    path = Path(directory) / name
    path.write_bytes(png_bytes(size, height))
    return path


def write_file(directory: Path, name: str, content: bytes | str) -> Path:
    """Write any content under any name (e.g. text called x.png) and return the path."""
    path = Path(directory) / name
    path.write_bytes(content.encode() if isinstance(content, str) else content)
    return path


# Smallest valid JPEG and WEBP (1 x 1 pixel): they prove a format is accepted without being large enough to pass a size rule
JPEG_1X1 = base64.b64decode(
    "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="
)
WEBP_1X1 = base64.b64decode("UklGRhoAAABXRUJQVlA4TA0AAAAvAAAAEAcQERGIiP4HAA==")
GIF_1X1 = b"GIF89a\x01\x00\x01\x00\x00\x00\x00;"
SVG_TEXT = '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400"><rect width="400" height="400"/></svg>'


def create_text_file(directory: Path, name: str = "not_an_upload.txt") -> Path:
    """A plain-text file, used where a PDF/image is required."""
    path = Path(directory) / name
    path.write_text("this is not a pdf or an image")
    return path


def create_oversized_pdf(directory: Path, size_bytes: int, name: str = "too_big.pdf") -> Path:
    """A file with a PDF header padded to exactly `size_bytes`."""
    path = Path(directory) / name
    path.write_bytes(_PDF_HEADER + b"0" * (size_bytes - len(_PDF_HEADER)))
    return path


def create_oversized_png(directory: Path, size_bytes: int, name: str = "too_big.png") -> Path:
    """A file with a PNG signature padded to exactly `size_bytes`."""
    path = Path(directory) / name
    path.write_bytes(_PNG_SIGNATURE + b"0" * (size_bytes - len(_PNG_SIGNATURE)))
    return path
