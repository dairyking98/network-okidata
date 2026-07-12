# IBM Proprinter III: hardware findings (2026-07-11)

Empirical findings from testing `printer/client.py` against the real printer
(an Okidata MICROLINE unit at `192.168.4.21:9100`, running in IBM Proprinter
III emulation) using `printer_selftest.py`, `printer_glyphs.py`, and
`printer_print_image.py`. These
supplement [`printer-commands-ibm-proprinter.md`](printer-commands-ibm-proprinter.md)
(the vendor manual transcription) with what this specific printer actually
does, which in a few cases disagrees with either the vendor doc or the old
per-app command dicts in `archive2/`.

## Confirmed working

Bold (Emphasized, `ESC E`/`ESC F`), Enhanced/double-strike (`ESC G`/`ESC H`),
Underline (`ESC - n`, see below), Overscore (`ESC _ n`), Double Width
(`ESC W n`), all 4 CPI settings, IBM Set I/II switching, line spacing 1/8,
7/72, and n/216, and superscript/subscript/normal (`ESC S n` / `ESC T`) all
print correctly and toggle cleanly on and off.

## Bugs found in the old code, now fixed in `printer/ibm_proprinter.py`

- **Italics**: the old `ibm_app.py` used `ESC % G` / `ESC % H`
  (`\x1B\x25\x47`/`\x1B\x25\x48`) — not a real command, doesn't appear
  anywhere in the vendor manual. It "turned on" italics but the "off" never
  actually undid it. The real command is `ESC I n` (Select Print Mode):
  `n=0x0B` selects "Alternate NLQ II (Italic)", `n=0x00` returns to Draft.
- **Underline**: the vendor manual scan transcription gives `ESC \` n\`
  (`0x1B 0x60`) for "Continuous Underscore". Tested on hardware and it did
  **not** work. `ESC - n` (`0x1B 0x2D`, the Epson/generic ESC/P convention
  used by every old per-app dict) does. Likely an OCR mix-up of "-" and "`"
  in the scanned manual page.
- **Superscript/Subscript**: the old code had these marked `(Custom guess)`
  using `ESC s n` (`0x1B 0x73`). The vendor manual gives the real command:
  `ESC S n` (`0x1B 0x53`, `n=0` superscript / `n=1` subscript), cancelled by
  `ESC T` (`0x1B 0x54`) — a single cancel command, not separate per-mode
  off commands.

## `n/144` line spacing does not work; `n/216` does

`Set Spacing to n/144` (`ESC % 9 n`) has no visible effect on this printer,
confirmed via `printer_selftest.py`. `Set Spacing to n/216` (`ESC 3 n`) does
work. Both are in the vendor manual with no "not available" caveat (unlike
Proportional Spacing), so this is an emulation gap specific to this printer,
not a documented limitation. `ibm_typewriter.py` disables the `n/144` radio
button (greyed out, with a tooltip) rather than silently doing nothing when
selected.

## Condensed print measures ~17 CPI, not 10

The app's line-length calculation and preview font sizing initially assumed
Condensed print was still 10 characters per inch (just visually condensed).
Measured on real hardware, Condensed is closer to **17 CPI** — consistent
with the well-known industry convention that condensed mode is roughly
1.7x the base pitch (10 CPI x 1.71 ≈ 17.1). `ibm_typewriter.py`'s
`update_line_length_display` now uses 17.0 for Condensed instead of 10.0.

## Bare LF does not carriage-return

Sending `\n` alone (LF, `0x0A`) advances the line but does **not** return
the print head to the left margin on this printer. Without an explicit CR,
consecutive lines drift diagonally across the page (easy to mistake for an
italic/slanted font, which is what happened during initial GUI testing).
`printer.client.Printer.text()` now normalizes all `\n` to `\r\n` internally
so callers can use plain `\n` and get the expected behavior.

## No real "reset everything" command

`CAN` (`Reset (Clear Print Buffer)`, `0x18`) only cancels data sitting in the
print buffer — it does **not** reset font/print-mode state (italics,
underline, CPI, etc). Unlike Epson's `ESC @`, the vendor manual has no
documented master-initialize command for the Proprinter III. If a mode gets
stuck, the only fully reliable fix found was a power cycle.

## `ESC !` is the real ESC/P "Master Select" command — dangerous to guess

The old code used `ESC !` followed by various bytes for three different,
unrelated-looking features: `Publisher Set` (`ESC ! Z`, `0x5A`), `Slashed
Zero` (`ESC ! @`, `0x40`), and `Unslashed Zero` (`ESC ! A`, `0x41`). None of
these appear in the vendor manual. `ESC !` is actually the standard ESC/P
**Master Select** command: a bitmask byte where each bit independently
toggles elite pitch / proportional / condensed / emphasized / double-strike
/ double-width / italic / underline, all at once.

Confirmed on hardware: selecting "Publisher" (byte `0x5A`, which decodes to
several of those bits set) visibly changed glyph rendering (brackets
rendered as a degree symbol and curly quotes), but also left the printer
stuck with several attributes on simultaneously. Selecting a different
character set afterward (`ESC 7`/`ESC 6`, an unrelated command) never
cleared it. Sending `ESC ! 0` (all bits off) cleared the *attribute* bits,
but not the glyph substitution — that required a full power cycle to clear,
exactly like the italics-stuck case above. `Printer.reset()` now also sends
`ESC ! 0` as a partial mitigation, but it is not a substitute for a power
cycle if something gets fully stuck.

Given there's no vendor-documented safe byte for a distinct "Publisher"
font, and any other `ESC !` guess risks the same stuck-state bug, `Publisher
Set` / `Slashed Zero` / `Unslashed Zero` were removed entirely rather than
guessed again. `ESC ! 0` (Master Select Reset) is the only `ESC !` use kept.

## Extended character range (0x80-0xFF) is unreliable

Tested sending raw bytes 0x80-0xFF as glyph data (`printer_glyphs.py`).
Some bytes in this range triggered unwanted mode changes — a stray Form
Feed mid-row, an unexpected switch to condensed print — but *which* byte
caused it moved between runs and between which font was active (first seen
under IBM Set I, then under Publisher on a later run). This rules out a
simple "high bit stripped, aliases to the C0 control code" theory as the
full explanation. Not worth chasing further: none of this project's apps
send anything but plain ASCII text anyway. `printer_glyphs.py` is now
restricted to the standard printable range (`0x20`-`0x7E`).

## Font sets

IBM Set I and IBM Set II render **identically** on this printer, including
in the specific byte range (`` ` { | } ~ @ [ \ ] ^ ``) where the two
national character sets are supposed to differ — likely only one resident
character set is actually installed on this unit. Not a code bug, just this
hardware's limitation.

## Proportional Spacing

The vendor manual explicitly notes `ESC P n` (Proportional Space Mode) is
"Not available on the Proprinter." Kept in the command table for
completeness (other IBM printers support it) but expect it to be a no-op on
a real Proprinter III.

## Bit-image graphics (`ESC K`/`ESC L`) need paced sends, not back-to-back

`printer/image.py`'s `print_image()` sends one `ESC K`/`ESC L` command per
8-dot-tall stripe. Sending every stripe back-to-back with no delay overran
the printer's receive buffer partway through a larger image (`460x272`,
34 stripes): it printed roughly 80%, then the printer appeared to restart
mid-job before completing correctly on a second pass. `oki-ctrl/ctrlimg.py`
(the tool this was ported from) already paced each stripe with a
`time.sleep(0.05)` — `print_image()` now does the same
(`_STRIPE_DELAY_SECONDS`). Worth re-testing with a still-larger image if
this becomes a bottleneck; 0.05s/stripe hasn't been pushed further than the
one 34-stripe test yet.

## Reproducing these findings

```
python3 printer_selftest.py [ip] [port]                      # one labeled sample per toggle/CPI/font/spacing/script
python3 printer_glyphs.py [ip] [port]                        # full ASCII glyph dump per font, 10 CPI
python3 printer_print_image.py [image_path] [ip] [port]      # bit-image graphics; omit image_path for a small built-in test pattern
```

`printer_selftest.py`/`printer_glyphs.py` need no venv/PySide6 --
`printer.client` is stdlib-only. `printer_print_image.py` needs Pillow
(`pip install Pillow`, or the venv from `setup.sh`/`setup.bat`).
