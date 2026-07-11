# Related projects: dot-matrix printer plaintext / control-code generators

Research notes on existing repositories covering plaintext printing, ESC/P-style
control codes, and dot-matrix printer emulation — for comparison against this
project's approach (`oki.py`, `ibm.py`, `printer.py`, `proprintercodes.txt`,
`cleanibmcodes.txt`).

## Control-code generation (closest match to this repo's structure)

- [Printer-Coder](https://github.com/Magnetic-Fox/Printer-Coder) — Python
  scripts for generating dot-matrix control codes, including an Epson FX-80
  code dictionary tool.
- [COPRIS](https://github.com/bertronika/copris) — a dot-matrix printer server
  that reads plaintext and recodes/sends it to a printer, with charset
  conversion for locale-specific characters.

## ESC/P protocol tools

- [escparser](https://github.com/nzeemin/escparser) — ESC/P command-line
  emulator/parser.
- [dotprint](https://github.com/zub2/dotprint) — converts text files with
  embedded ESC/P escape sequences into PDF.

## Virtual / emulated printers

- [vp](https://github.com/freedosproject/vp) — emulates a simplified 9-pin
  dot matrix printer for plain text/CR-LF output.
- [dot-matrix-printer (reversenorm)](https://github.com/reversenorm/dot-matrix-printer) —
  JS demo parsing a string and rendering it like dot-matrix output.

## Fonts (for authentic glyph rendering)

- [font_DotMatrix](https://github.com/Gissio/font_DotMatrix) — includes the
  Epson FX-80 character set.
- [robotron-dotmatrix-font](https://github.com/nzeemin/robotron-dotmatrix-font) —
  re-engineered from a printer ROM.

## ASCII art angle

- [ASCII-printer](https://github.com/manorius/ASCII-printer) — converts
  images to ASCII art and prints on a dot matrix printer.

## Possible next step

Printer-Coder and COPRIS look most aligned with what this repo is building.
Worth pulling either down and comparing its code-table approach against
`proprintercodes.txt` / `cleanibmcodes.txt`.
