# network-okidata

Tools for driving a network dot-matrix printer (an Okidata MICROLINE unit,
reachable over Ethernet via a JetDirect-style raw socket on port 9100) by
sending its raw escape-code command language directly. The printer can run
in one of three emulation modes — **IBM Proprinter III** (its default),
**Okidata MICROLINE**, or **Epson FX**. Active development currently targets
IBM Proprinter III only; see `archive2/` for the prior Okidata/multi-emulation/
document-editor/calendar tools.

Default target: `192.168.4.21:9100` (override in `apps/live_typewriter/config.py`,
or via the IP/port fields in the app itself).

**Roadmap:** the longer-term goal is a Markdown-based WYSIWYG editor with
accurate print preview for the Oki ML-421, plus a PDF-to-Markdown ingestion
step. See [`docs/similar-projects-and-roadmap.md`](docs/similar-projects-and-roadmap.md)
for a survey of existing open-source projects relevant to that direction and
concrete next steps.

## Quick start

```
setup.bat   # Windows: creates .venv, installs PySide6
setup.sh    # Linux/macOS: same

start.bat   # Windows: runs setup.bat if needed, then launches the app
start.sh    # Linux/macOS: same
```

This launches `apps/live_typewriter/ibm_typewriter.py`, a live-typing app for
IBM Proprinter III — each keystroke (or each line, in Line-by-Line mode) is
sent straight to the printer as you type.

## `printer/` — the shared library

- **`ibm_proprinter.py`** — the canonical IBM Proprinter III command table,
  cross-checked against [`docs/printer-commands-ibm-proprinter.md`](docs/printer-commands-ibm-proprinter.md)
  and against real hardware behavior. See
  [`docs/ibm-proprinter-hardware-findings.md`](docs/ibm-proprinter-hardware-findings.md)
  for what was found/fixed during testing.
- **`client.py`** — `Printer`, a persistent-socket client class with a
  method-call API (`.text()`, `.set(bold=True, cpi=12, ...)`, `.form_feed()`,
  etc.) instead of per-app hand-rolled command dicts and inline sockets.
  Takes an `on_log` callback instead of coupling to any particular GUI
  widget, so it works headlessly (scripts, tests) or from any GUI.

## Apps

### `apps/live_typewriter/ibm_typewriter.py`

A PySide6 GUI: IP/port fields, a debug pane, Live vs Line-by-Line typing
mode, CPI/font/spacing/script selectors, formatting toggles (bold, italic,
enhanced, underline, overscore, proportional, double-width), manual command
buttons, and a left/right margin + line-length display. Built entirely on
`printer.client.Printer`.

## Diagnostics

- **`printer_selftest.py`** — prints one labeled sample line per
  toggle/CPI/font/spacing/script setting, so you can read the physical page
  and see exactly what the printer actually honors. Stdlib-only, no venv
  needed: `python3 printer_selftest.py [ip] [port]`.
- **`printer_glyphs.py`** — prints the full standard-ASCII glyph set (10
  CPI, narrow rows for letter paper) for each font. Same stdlib-only usage.

## Printer command reference

[`docs/printer-commands-ibm-proprinter.md`](docs/printer-commands-ibm-proprinter.md)
is a cleaned-up, deduplicated table of the full IBM Proprinter III escape-code
set, merged from two independent transcriptions of the manual scans in
[`docs/scans/`](docs/scans/).

[`docs/ibm-proprinter-hardware-findings.md`](docs/ibm-proprinter-hardware-findings.md)
documents where real hardware disagreed with that reference doc or with the
prior per-app command dicts (wrong/guessed escape codes, the `ESC !` Master
Select gotcha, the bare-LF-needs-CR gotcha, the unreliable extended
character range, etc).

## `archive2/`

The `apps/` and `tools/` layout as of the last reorganization, before the
`printer/` package + `ibm_typewriter.py` rewrite. Includes the Okidata
MICROLINE app, the multi-emulation app, the document editor, the calendar
printer, and the original `printer_status_check.py` — none of these were
migrated to the new `printer/` library; they still use their own per-app
command dicts and socket handling. Kept for reference/future migration, not
actively maintained.

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
