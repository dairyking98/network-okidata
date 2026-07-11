"""
Prints one labeled sample line per escape code / setting in
printer.ibm_proprinter.COMMANDS, so you can read the physical page and see
exactly which commands the printer actually honors.

Usage:
    python3 printer_selftest.py [ip] [port]

No PySide6/venv required -- printer.client is stdlib-only.
"""

import sys

from printer.client import Printer

SAMPLE = "The quick brown fox jumps 0123456789"
SPECIAL_CHARS = "` { | } ~ @ [ \\ ] ^"  # bytes where IBM Set I/II actually differ


def section(printer: Printer, title: str) -> None:
    printer.text(f"\n\n--- {title} ---\n")


def toggle_test(printer: Printer, label: str, **kwarg) -> None:
    (key, value), = kwarg.items()
    off = {key: False}
    on = {key: True}
    printer.set(**off)
    printer.text(f"[{label} OFF]\n{SAMPLE}\n")
    printer.set(**on)
    printer.text(f"[{label} ON ]\n{SAMPLE}\n")
    printer.set(**off)


def main():
    ip = sys.argv[1] if len(sys.argv) > 1 else "192.168.4.21"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9100

    with Printer(ip, port, on_log=print) as p:
        p.reset()
        p.text("=== IBM Proprinter III escape code self-test ===\n")

        section(p, "Toggles")
        toggle_test(p, "Emphasized (bold)", bold=True)
        toggle_test(p, "Italic", italic=True)
        toggle_test(p, "Enhanced (double-strike)", enhanced=True)
        toggle_test(p, "Underline", underline=True)
        toggle_test(p, "Overscore", overscore=True)
        toggle_test(p, "Proportional (doc: unsupported on Proprinter)", proportional=True)
        toggle_test(p, "Double Width", double_width=True)

        section(p, "CPI")
        for cpi in (10, 12, 15, "condensed"):
            p.set(cpi=cpi)
            p.text(f"[CPI {cpi}]\n{SAMPLE}\n")
        p.set(cpi=10)

        section(p, "Character set / font")
        for font in ("IBM Set I", "IBM Set II"):
            p.set(font=font)
            p.text(f"[Font {font}]\n{SAMPLE}\n{SPECIAL_CHARS}\n")
        p.set(font="IBM Set I")

        section(p, "Line spacing")
        for mode, n in (("1/8", None), ("7/72", None), ("n/144", 20), ("n/216", 30)):
            p.set(spacing=(mode, n))
            p.text(f"[Spacing {mode}{f' n={n}' if n else ''}]\nline one\nline two\n")
        p.set(spacing=("1/8", None))

        section(p, "Superscript / subscript")
        for script in ("superscript", "subscript", "normal"):
            p.set(script=script)
            p.text(f"[Script {script}]\n{SAMPLE}\n")
        p.set(script="normal")

        p.text("\n=== End of self-test ===\n")
        p.form_feed()


if __name__ == "__main__":
    main()
