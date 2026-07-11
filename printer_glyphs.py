"""
Prints the glyph set for each of the two IBM Proprinter III font sets
(IBM Set I, IBM Set II), 16 characters per row so lines stay narrow at
10 CPI on letter paper.

Restricted to standard printable ASCII (0x20-0x7E). The extended range
(0x80-0xFF) was tested and dropped: on real hardware it triggered unwanted
mode changes (a stray Form Feed mid-row, an unwanted switch to condensed
print), unreliably depending on which font was active -- not a single fixed
alias, just generally unreliable on this printer. Not worth chasing further
since this project's apps only ever send plain ASCII text anyway.

"Publisher" is intentionally not included -- it was a guessed command (ESC !
Z) that turned out to collide with the real ESC/P "Master Select" bitmask
command, getting the printer stuck with several attributes on at once. See
printer/ibm_proprinter.py for details.

Usage:
    python3 printer_glyphs.py [ip] [port]

No PySide6/venv required -- printer.client is stdlib-only.
"""

import sys

from printer.client import Printer

FONTS = ("IBM Set I", "IBM Set II")
ROW_WIDTH = 16


def glyph_dump(printer: Printer, font: str) -> None:
    printer.text(f"\n\n--- {font} ---\n")
    printer.set(font=font)
    printer.set(cpi=10)

    codes = list(range(0x20, 0x7F))  # standard printable ASCII, skip DEL
    for i in range(0, len(codes), ROW_WIDTH):
        row = codes[i:i + ROW_WIDTH]
        label = f"[{row[0]:3d}-{row[-1]:3d}]"
        printer.text(f"{label}\n")

        row_bytes = bytearray()
        for j, code in enumerate(row):
            if j > 0:
                row_bytes.append(0x20)
            row_bytes.append(code)
        row_bytes += b"\r\n"
        printer.raw(bytes(row_bytes), tag=label)


def main():
    ip = sys.argv[1] if len(sys.argv) > 1 else "192.168.4.21"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9100

    with Printer(ip, port, on_log=print) as p:
        p.reset()
        p.text("=== IBM Proprinter III full glyph dump (10 CPI) ===\n")
        for font in FONTS:
            glyph_dump(p, font)
        p.set(font="IBM Set I")
        p.text("\n=== End of glyph dump ===\n")
        p.form_feed()


if __name__ == "__main__":
    main()
