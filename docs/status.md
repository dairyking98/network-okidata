# Project status / where we left off (2026-07-11)

Project is paused here. This note is for picking the work back up later.

## Current state

- `printer/` package rebuilt for IBM Proprinter III only (Okidata/Epson/
  multi-emulation/document-editor/calendar apps stayed in `archive2/`,
  not migrated):
  - `ibm_proprinter.py` — canonical command table. Several commands were
    wrong in the old code and only surfaced by testing against real
    hardware; see `docs/ibm-proprinter-hardware-findings.md` for the full
    list (italics, underline, superscript/subscript, the `ESC !` Master
    Select gotcha, n/144 spacing, Condensed CPI).
  - `client.py` — `Printer`, persistent-socket client with a method-call
    API and an `on_log` callback instead of GUI coupling.
  - `image.py` — bit-image graphics (`ESC K`/`ESC L`), ported from
    `oki-ctrl/ctrlimg.py`.
- `apps/live_typewriter/ibm_typewriter.py` — PySide6 GUI with a live
  WYSIWYG preview canvas (custom-painted character grid, not a rich-text
  widget, so backspace-and-retype overlays glyphs like real impact-printer
  overstrike; row height tracks the line-spacing setting).
- Diagnostics, all runnable directly against `192.168.4.21:9100`:
  `printer_selftest.py`, `printer_glyphs.py`, `printer_print_image.py`.
- `oki-ctrl/` was recovered from a sibling directory outside this repo;
  documented in the README. `image.py` ports its useful part
  (`ctrlimg.py`); the rest (raw-command senders, an unfinished Express +
  browser frontend) wasn't migrated.

## Not yet re-verified on hardware

`printer_print_image.py` originally overran the printer's receive buffer on
a 34-stripe image (printed ~80%, then the printer restarted mid-job). Added
a 0.05s per-stripe delay to fix it (matching `oki-ctrl/ctrlimg.py`'s
original pacing), but **this fix has not been re-tested end-to-end** --
the printer was too loud to run late at night. First thing next session:
re-run `python3 printer_print_image.py oki-ctrl/Untitled.bmp` (or the
faster built-in test pattern with no args) and confirm it completes in one
clean pass.

## Idea logged, not implemented

Multi-pass offset image printing for higher effective resolution (mimicking
how driver-based PDF/image printing fills gaps between physical pin dots
with a second pass offset by a fraction of a pin-pitch). Candidate commands
(`ESC J n` for fine vertical offset, `ESC d n1 n2` for fine horizontal
offset) and the design sketch are in
`docs/ibm-proprinter-hardware-findings.md`'s "Future experiment" section.
Not started.

## Resuming

1. Re-verify the pending image-printing fix above.
2. Then pick up `docs/similar-projects-and-roadmap.md`'s "Recommendations"
   list -- the real ESC/P byte-stream interpreter (item 2) is the next
   unstarted piece, followed eventually by the Markdown -> preview ->
   print pipeline (item 4).
