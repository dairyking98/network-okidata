"""
Bit-image graphics support for the IBM Proprinter III (ESC K / ESC L),
ported from oki-ctrl/ctrlimg.py's from-scratch Tkinter tool into the
printer/ package.

Requires Pillow (`pip install Pillow`) -- kept in this separate module
rather than printer/client.py so that client.py and the scripts that use it
(printer_selftest.py, printer_glyphs.py) stay stdlib-only.
"""

import math
import time
from typing import Union

from PIL import Image, ImageDraw

from .client import Printer

# 480 mode: 60 dots/inch horizontal (ESC K, "normal density").
# 960 mode: 120 dots/inch horizontal (ESC L, "dual density").
# Both modes print 8-dot-tall stripes at 72 dots/inch vertical.
_MAX_WIDTH = {"480": 480, "960": 960}
_COMMAND_LETTER = {"480": "K", "960": "L"}

# oki-ctrl/ctrlimg.py paced each stripe with a 0.05s sleep. Confirmed on
# hardware that sending stripes back-to-back with no delay overruns the
# printer's receive buffer partway through a large image (it printed ~80%,
# then the printer appeared to restart mid-job before finishing correctly
# on a second pass). Keep the same pacing to avoid that.
_STRIPE_DELAY_SECONDS = 0.05


def make_test_pattern(width: int = 120, height: int = 40) -> Image.Image:
    """A small, fast-to-print 1-bit test pattern (border + diagonal + checkerboard corner)."""
    img = Image.new("1", (width, height), color=1)  # 1 = white
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, width - 1, height - 1], outline=0)
    draw.line([(0, 0), (width - 1, height - 1)], fill=0)
    draw.line([(0, height - 1), (width - 1, 0)], fill=0)
    box = min(width, height) // 4
    for row in range(box):
        for col in range(box):
            if (row + col) % 2 == 0:
                img.putpixel((col, row), 0)
    return img


def print_image(
    printer: Printer,
    image: Union[str, Image.Image],
    mode: str = "480",
    form_feed: bool = True,
) -> None:
    """
    Convert an image to 1-bit and print it via ESC K (480 mode) or ESC L
    (960 mode) bit-image graphics. `image` is a file path or an already-open
    PIL Image. Raises ValueError if the image is wider than the mode allows.

    `form_feed=False` skips ejecting the page afterward, so a second image
    (or text) can follow on the same page for testing.
    """
    if mode not in _MAX_WIDTH:
        raise ValueError(f"mode must be '480' or '960', got {mode!r}")

    img = Image.open(image) if isinstance(image, str) else image
    img = img.convert("1")  # 1-bit, dithering non-bitmap images automatically

    max_width = _MAX_WIDTH[mode]
    if img.width > max_width:
        raise ValueError(f"image width {img.width}px exceeds max {max_width}px for mode {mode}")

    width, height = img.size
    num_stripes = math.ceil(height / 8)
    command_letter = _COMMAND_LETTER[mode]

    # ESC 3 24: set graphics line spacing to 24/216" so 8-dot stripes stack
    # with no gap (matches ctrlimg.py's header, confirmed on hardware).
    printer.raw(b"\x1B\x33\x18", tag="[image] line spacing")

    for stripe in range(num_stripes):
        col_bytes = bytearray(width)
        for col in range(width):
            byte_val = 0
            for row_offset in range(8):
                row = stripe * 8 + row_offset
                if row >= height:
                    continue
                if img.getpixel((col, row)) == 0:  # mode "1": 0 = black/active
                    byte_val |= 128 >> row_offset
            col_bytes[col] = byte_val
        n1, n2 = width % 256, width // 256
        line = bytes([0x1B, ord(command_letter), n1, n2]) + bytes(col_bytes) + b"\r\n"
        printer.raw(line, tag=f"[image] stripe {stripe + 1}/{num_stripes}")
        time.sleep(_STRIPE_DELAY_SECONDS)

    printer.raw(b"\r\n" + (b"\x0C" if form_feed else b""), tag="[image] end")
