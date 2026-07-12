# Similar Projects & Roadmap

Research report on existing open-source projects relevant to where this
repo is headed, plus concrete recommendations. Written 2026-07-11.

## Where this project is going

From an interview with the project owner, the goal isn't just "control an
Okidata ML-421 over the network" (which the current apps already do) — it's
a fuller pipeline:

1. **Personal typewriter replacement** — live keystroke-to-page printing
   (covered today by `apps/live_typewriter/`).
2. **Document/calendar printing tool** — compose then print
   (covered today by `apps/document_editor/`, `apps/calendar_printer/`).
3. **Print preview** — see the page *before* committing it to paper/ribbon,
   accurately reflecting the Oki ML-421's actual output (CPI, double-wide,
   margins, etc.) — **not yet implemented**. `page_layout_app.py` previews
   margins on a canvas but doesn't render actual glyph-accurate output.
4. **A WYSIWYG text editor purpose-built for this printer** — bigger than
   today's apps, which each print immediately or preview only layout, not
   rendered text.
5. **A Markdown → preview/adjust → print pipeline** — write in Markdown,
   see an accurate preview, adjust, then send to the printer. **Nothing in
   this repo does this today** — none of the current apps parse Markdown.
6. **A PDF → Markdown ingestion step**, presumably to pull existing
   documents into that pipeline. **Not implemented.**

Items 5 and 6 are net-new capabilities, not reorganizations of existing code.

## What exists already that's relevant

### ESC/P command libraries (could replace/validate the hand-rolled command dicts)

Every app in this repo (`config.py`'s `OKIDATA_COMMANDS`, and the inline
`IBM_COMMANDS`/`OKI_COMMANDS`/`EPSON_COMMANDS` dicts scattered across
`apps/document_editor/text_editor_app.py` and `archive/live.py`) hand-encodes
escape sequences as raw byte literals. A few existing libraries cover
overlapping ground:

- **[python-escp](https://github.com/yackx/python-escp)** — the closest
  match in spirit: targets **ESC/P** specifically (not ESC/POS), which is
  the actual command family this printer speaks. Tested against a 9-pin
  Epson LX-300+II; the author notes "all 9-pin printers should work." USB
  only (no network backend) and fairly minimal (text + CR/LF + init) — 5
  stars, low activity, GPLv3. Worth reading for its command constants even
  if not adopted directly; not mature enough to depend on.
- **[python-escpos](https://github.com/python-escpos/python-escpos)** — the
  most mature/active project in this space (1.3k stars, MIT license,
  releases through Dec 2023), but targets **ESC/POS** (receipt/thermal
  printers), a different-but-related command set from ESC/P and IBM
  Proprinter. Not a drop-in fit, but its **architecture is worth copying**:
  a `Network` connection class alongside `Usb`/`Serial` ones, and a clean
  method-call API (`p.text(...)`, `p.set(bold=True)`, `p.cut()`) instead of
  raw byte dicts. This repo's `printer.py`/`send_command()` helper could be
  refactored toward this shape — a `Printer` class with `.text()`,
  `.set(cpi=12, emphasized=True)`, etc., instead of every app reaching into
  a `COMMANDS` dict directly.
- **[IBM's own PPDS/Epson ESC/P control code reference](https://www.ibm.com/support/pages/list-ibm-ppds-and-epson-escp-control-codes-and-escape-sequences)**
  — worth cross-checking `docs/printer-commands-ibm-proprinter.md` against,
  as a second independent source beyond the two manual-scan transcriptions
  already merged there.

**Verdict:** nothing here is mature/complete enough to replace this repo's
command dictionaries outright, but `python-escpos`'s connection/API design
is a good template for a refactor, and `python-escp`'s command constants are
worth a cross-check.

### Print preview / WYSIWYG rendering — the actual missing piece

This is the interesting find. Getting a *visually accurate* preview of dot
matrix output means actually interpreting the escape codes and rendering
glyphs/spacing the way the physical printer would — this repo doesn't do
that anywhere (`page_layout_app.py`'s canvas preview only shows margin
boxes, not rendered text).

- **[EPHEX-80](https://github.com/MurphyMc/EPHEX-80)** — a Python **Epson
  FX-80 emulator** that interprets ESC/P command streams and renders them
  (currently to SVG). Built to sit behind an Apple II emulator, but
  architecturally it's exactly the missing piece: an ESC/P *interpreter*
  that turns a byte stream into a rendered page. The author calls it
  "incredibly rough," so not usable as-is, but the approach —
  render-the-actual-command-stream rather than approximate-it-in-a-GUI-canvas
  — is the right one for a truly WYSIWYG preview. Worth reading
  `ephex_core.py`/`ephex_charset.py` for the character-set/command-dispatch
  structure.
- **[freedosproject/vp](https://github.com/freedosproject/vp)** — a
  simplified 9-pin dot matrix virtual printer (plain text + CR/LF only,
  less relevant since it doesn't handle formatting commands).

**Verdict:** no ready-made solution, but EPHEX-80 shows the right shape for
building one — a shared ESC/P interpreter used both to (a) drive the real
socket connection and (b) render a preview, so preview and physical output
can never drift apart. That interpreter could reuse this repo's own
existing command dictionaries as its lookup table.

### Markdown → print pipeline

No existing project takes Markdown straight to ESC/P — this is genuinely a
gap the user's tools would fill.

- **[WeasyPrint](https://github.com/Kozea/WeasyPrint)** — HTML/CSS → PDF.
  The common approach for Markdown→PDF is Markdown → HTML → WeasyPrint,
  using CSS for page/print layout. Not applicable directly (targets modern
  laser/PDF output, not ESC/P), but CSS's print-layout model (page size,
  margins, `@page` rules) is a reasonable reference for designing the
  page-layout data model this project needs internally.
- **[ReportLab](https://www.reportlab.com/)** — programmatic, pixel-precise
  PDF generation via a Canvas API (explicit coordinates, fonts). Closer in
  spirit to what dot-matrix printing actually needs (precise character-cell
  positioning) than WeasyPrint's CSS flow model — worth looking at for how
  it models a page/canvas abstraction, even though the actual output target
  here is ESC/P bytes, not PDF.
- Any standard Markdown parser (Python's `markdown` or `mistune` packages)
  handles the Markdown→AST step; the novel work is entirely in the
  AST→ESC/P-with-accurate-line-breaking layer, which nothing off-the-shelf
  provides.

**Verdict:** build this specifically for this printer. Use a standard
Markdown parser for the parsing step, but the "lay out text into fixed
character cells honoring CPI/margins/page-length, emit ESC/P, and render an
identical preview" layer is bespoke — informed by ReportLab's page/canvas
model and rendered via an EPHEX-80-style interpreter.

### PDF → Markdown ingestion

Unlike the print pipeline, this direction is well covered by existing tools
— no need to build it.

- **[markitdown](https://github.com/microsoft/markitdown)** (Microsoft) —
  actively maintained, converts PDF/Office/etc. to Markdown, designed for
  feeding LLM pipelines (which matches "PDF → markdown → pipeline" well).
  Good default choice.
- **[marker](https://github.com/datalab-to/marker)** — higher-accuracy,
  ML-based PDF→Markdown/JSON, handles PDFs/images/PPTX/DOCX/XLSX/HTML/EPUB.
  Heavier dependency footprint than markitdown but more accurate on complex
  layouts/tables.

**Verdict:** don't build a PDF→Markdown converter — use `markitdown` for
simple cases, fall back to `marker` if a specific PDF's layout/tables come
out mangled.

### Raw socket (port 9100 / JetDirect) printing — architecture reference

This repo's `printer.py` already does the right thing (open a TCP socket to
`:9100` and write bytes). One reference project confirms this is the
standard, minimal approach:

- **[p910nd](https://github.com/kenyapcomau/p910nd)** — a small Linux
  daemon that accepts connections on port 9100+n and forwards the stream
  straight to a printer device, with no protocol translation. Confirms raw
  9100 printing really is just "open socket, write bytes" — nothing to
  adopt here, but useful confirmation that this repo isn't missing some
  handshake/negotiation step.

## Recommendations, roughly prioritized

1. **Don't build a PDF→Markdown converter.** Wire up `markitdown` (or
   `marker` for harder PDFs) as a preprocessing step and move on — this was
   the easiest gap to close with existing tools.
2. **Build the ESC/P interpreter before the Markdown pipeline.** It's the
   dependency both "WYSIWYG editor" and "preview, then print" need, and
   it's also the thing that turns `page_layout_app.py`'s margin-only
   preview into a real WYSIWYG preview. Model it on EPHEX-80's
   interpret-and-render approach, but feed it from this repo's own
   `OKIDATA_COMMANDS`/IBM command dictionaries so the interpreter and the
   thing sending bytes to the real printer are guaranteed to agree.
3. **Refactor the command-dict-per-app pattern into a `Printer` class**
   with a method-call API (`python-escpos`'s design is a good template),
   shared by all the live-typewriter/document-editor apps, so command
   definitions live in one place instead of being copy-pasted across
   `okidata_app.py`, `ibm_app.py`, `multi_emulation_app.py`, and
   `text_editor_app.py` as they are today.
4. **Markdown → layout → ESC/P is the one genuinely novel piece.** Use a
   standard Markdown parser for parsing; write the character-cell layout
   engine yourself, informed by ReportLab's precise-positioning model
   rather than WeasyPrint's CSS-flow model (dot matrix output is fixed-cell
   text, not flowed boxes). Feed its output through the same interpreter
   from step 2 for the preview, and through `printer.py`'s socket code for
   the real send — that's the "preview + adjust, then print" workflow.

## Addendum (2026-07-11, second pass)

- **[nzeemin/escparser](https://github.com/nzeemin/escparser)** — a C
  command-line ESC/P interpreter: takes a raw escape-code log file and
  renders it to PostScript/SVG/PDF, using an actual dot-matrix ROM font
  bitmap (tuned to a Robotron CM 6329.01M) rather than approximating with a
  system font. Not adopted directly -- it's C, batch/offline (log file in,
  document out, no live preview), and tuned to a different printer's exact
  command set than the IBM Proprinter III quirks confirmed in
  [`ibm-proprinter-hardware-findings.md`](ibm-proprinter-hardware-findings.md).
  Kept as the reference for when the real byte-stream interpreter (item 2
  above) gets built: its rendered sample was visually recognized as close to
  this project's actual dot-matrix output, so a real bitmap font (rather
  than a system TTF with bold/italic faked) is worth prioritizing then,
  the same way `EPHEX-80` was already flagged for its interpret-and-render
  architecture.
- In the meantime, a **live preview pane inside `ibm_typewriter.py`** was
  built as a lighter first step: it mirrors the app's own formatting state
  (the same checkboxes/radios driving `Printer.set()` calls) into a
  `QTextEdit` as text is typed, using Qt's native bold/italic/underline/
  overline/superscript-subscript/font-stretch support. This is not the
  "interpret the raw byte stream" architecture item 2 calls for -- it can't
  be reused by a future non-GUI pipeline (e.g. Markdown -> preview) -- but
  it's a fast, immediately useful WYSIWYG check for this one app, and can't
  drift from what's sent since it reads the same state.

## Sources

- [python-escp](https://github.com/yackx/python-escp)
- [python-escpos](https://github.com/python-escpos/python-escpos)
- [python-printer-escpos](https://github.com/shantanubhadoria/python-printer-escpos)
- [pyescpos](https://github.com/base4sistemas/pyescpos)
- [IBM PPDS / Epson ESC/P control code reference](https://www.ibm.com/support/pages/list-ibm-ppds-and-epson-escp-control-codes-and-escape-sequences)
- [EPHEX-80](https://github.com/MurphyMc/EPHEX-80)
- [freedosproject/vp](https://github.com/freedosproject/vp)
- [markitdown](https://github.com/microsoft/markitdown)
- [marker](https://github.com/datalab-to/marker)
- [p910nd](https://github.com/kenyapcomau/p910nd)
- [WeasyPrint](https://github.com/Kozea/WeasyPrint)
- [ReportLab](https://www.reportlab.com/)
- [nzeemin/escparser](https://github.com/nzeemin/escparser)
