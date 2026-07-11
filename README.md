# network-okidata

Tkinter tools for driving a network dot-matrix printer (an Okidata MICROLINE
unit, reachable over Ethernet via a JetDirect-style raw socket on port 9100)
by sending its raw escape-code command language directly. The printer can run
in one of three emulation modes — **IBM Proprinter III** (its default),
**Okidata MICROLINE**, or **Epson FX** — and different tools here target
different modes or workflows.

Default target: `192.168.4.28:9100` (override per-app; see `apps/*/config.py`
or each script's `DEFAULT_CONFIG` dict).

**Roadmap:** the longer-term goal is a Markdown-based WYSIWYG editor with
accurate print preview for the Oki ML-421, plus a PDF-to-Markdown ingestion
step. See [`docs/similar-projects-and-roadmap.md`](docs/similar-projects-and-roadmap.md)
for a survey of existing open-source projects relevant to that direction and
concrete next steps.

## Quick start

```
start.bat
```

This runs `main.py`, which launches the primary live-typing app
(`apps/live_typewriter/okidata_app.py`) for the printer's native Okidata mode.

## Apps

### `apps/live_typewriter/` — type-and-it-prints-immediately

Each keystroke (or each line, depending on mode) is sent straight to the
printer as you type — no separate "print" step.

- **`okidata_app.py`** — Okidata MICROLINE mode. The main, most complete app;
  this is what `main.py`/`start.bat` launches. Full controls for CPI,
  print quality/speed, spacing, double-height/width, zero style, and more.
- **`ibm_app.py`** — IBM Proprinter III mode (the printer's power-on default).
  Same integrated-window design as `okidata_app.py`, with IBM-specific
  commands and a persistent socket connection instead of one-shot sends.
- **`multi_emulation_app.py`** — switches between all three emulations
  (IBM / Okidata / Epson) from one dropdown, with a separate "Printer
  Control" popup window for manual commands. Less polished per-mode
  controls than the two apps above, but useful when you're not sure what
  mode the printer is currently in.
- **`config.py`** / **`printer.py`** — shared default config and the raw
  `send_command()` socket helper used by `okidata_app.py`.

### `apps/document_editor/` — compose first, then print

You type and format a whole document, optionally preview it, and only then
send it to the printer — as opposed to the live-typewriter workflow above.

- **`text_editor_app.py`** — a text editor with bold/italic/underline
  buttons, a print preview, and multi-emulation support (IBM/Epson/Okidata).
- **`page_layout_app.py`** — a paginated editor with draggable left/right/
  top/bottom margins (snapping to 1/6" or 1/8"), showing an accurate visual
  preview of CPI, double-wide text, and margins before printing.

### `apps/calendar_printer/`

- **`calendar_app.py`** — prints Day / Week (portrait) / Month (landscape)
  calendar pages, with a Date Mode toggle to navigate by Month+Day or by
  Week Number, plus configurable embellishments (bold/italic/underline/
  double-width) per header.

### `tools/`

- **`printer_status_check.py`** — standalone script that pings the printer
  with an ENQ (0x05) byte and reports whether it responds. Useful as a quick
  "is the printer reachable" check before firing up one of the GUI apps.

## Printer command reference

[`docs/printer-commands-ibm-proprinter.md`](docs/printer-commands-ibm-proprinter.md)
is a cleaned-up, deduplicated table of the full IBM Proprinter III escape-code
set, merged from two independent transcriptions of the manual scans in
[`docs/scans/`](docs/scans/).

The Okidata MICROLINE and Epson FX command dictionaries are documented
in-code (with comments) in each app's `*_COMMANDS` dict rather than as a
separate reference doc — see `apps/live_typewriter/config.py` and
`apps/document_editor/text_editor_app.py`.

## `archive/`

The original, pre-reorganization file layout, kept intact (nothing was
deleted) for history. Notably includes two scripts not carried forward into
the apps above because they were superseded by other files in this repo:

- `oki.py` — an earlier, unmodularized version of `okidata_app.py` (same
  app, before it was split into `config.py`/`printer.py`/`main.py`).
- `typewriter.py` — an incomplete rewrite attempt, missing most of
  `okidata_app.py`'s controls.
- `calprint.py` — an earlier version of `calendar_app.py`, missing the
  Week Number date mode.

## `misc/`

`commodore-control-codes.png` — a Commodore printer control-code reference
image that ended up in this repo. Nothing here implements Commodore
emulation; kept in case it's relevant to a future printer, otherwise safe
to remove.
