"""
Prints an image via IBM Proprinter III bit-image graphics (ESC K/L).

Usage:
    python3 printer_print_image.py [image_path] [ip] [port] [mode] [form_feed]

image_path defaults to a small built-in test pattern (fast to print) if
omitted or passed as "-".
mode is "480" (60 dpi horizontal, max 480px wide) or "960" (120 dpi
horizontal, max 960px wide). Defaults to "480".
form_feed is "1" (default, eject the page after) or "0" (skip the eject, so
a second print can follow on the same page).

Requires Pillow (pip install Pillow) -- printer.image is the one module in
printer/ with a dependency beyond stdlib.
"""

import sys

from printer.client import Printer
from printer.image import make_test_pattern, print_image


def main():
    image_arg = sys.argv[1] if len(sys.argv) > 1 else "-"
    ip = sys.argv[2] if len(sys.argv) > 2 else "192.168.4.21"
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 9100
    mode = sys.argv[4] if len(sys.argv) > 4 else "480"
    form_feed = (sys.argv[5] if len(sys.argv) > 5 else "1") not in ("0", "no", "false")

    image = make_test_pattern() if image_arg == "-" else image_arg

    with Printer(ip, port, on_log=print) as p:
        print_image(p, image, mode=mode, form_feed=form_feed)


if __name__ == "__main__":
    main()
