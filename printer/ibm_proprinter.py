"""
Canonical IBM Proprinter III command table.

Cross-checked against docs/printer-commands-ibm-proprinter.md (itself
transcribed from the vendor manual scans in docs/scans/). Superseded the
previous per-app copies, which had drifted from each other and, in the case
of Superscript/Subscript, from the vendor spec (see note below).
"""

COMMANDS = {
    "Backspace": b"\x08",                          # BS (8)
    "Carriage Return": b"\x0D",                    # CR (13)
    "Select 10 cpi": b"\x12",                      # DC2 (18)
    "Select 12 cpi": b"\x1B\x3A",                  # ESC : (27 58)
    "Select 15 cpi": b"\x1B\x67",                  # ESC g (27 103)
    "Select Condensed Print": b"\x1B\x0F",         # ESC SI (27 15)
    # Confirmed via printer_selftest.py: Set I and Set II render identically
    # on this printer (likely only one resident national character set is
    # installed). Not a code bug.
    "IBM Set I": b"\x1B\x37",                      # ESC 7 (27 55)
    "IBM Set II": b"\x1B\x36",                     # ESC 6 (27 54)
    # REMOVED: "Publisher Set" (ESC ! Z, 1B215A) and "Slashed/Unslashed Zero"
    # (ESC ! @ / ESC ! A) from the old ibm_app.py. None of these appear in
    # docs/printer-commands-ibm-proprinter.md -- they were guesses, and
    # "ESC !" is actually the real ESC/P "Master Select" command: a bitmask
    # byte where each bit independently toggles elite/proportional/condensed/
    # emphasized/double-strike/double-width/italic/underline. Confirmed on
    # real hardware: selecting "Publisher" (byte 0x5A) got the printer stuck
    # with several of those attributes on simultaneously, and switching
    # character sets afterward (ESC 7/6, an unrelated command) never cleared
    # it -- only sending "ESC ! 0" (all bits off) did. Since there's no
    # vendor-confirmed correct byte for a distinct "Publisher" font or zero
    # style, and any other "ESC !" guess risks the same stuck-attribute bug,
    # these are dropped rather than guessed again. "Master Select Reset" below
    # is the one ESC ! use confirmed safe.
    "Master Select Reset": b"\x1B\x21\x00",        # ESC ! 0 (27 33 0)
    "Double Width On": b"\x1B\x57\x31",            # ESC W 1 (27 87 49)
    "Double Width Off": b"\x1B\x57\x30",           # ESC W 0 (27 87 48)
    "Emphasized Printing On": b"\x1B\x45",         # ESC E (27 69)
    "Emphasized Printing Off": b"\x1B\x46",        # ESC F (27 70)
    "Enhanced Printing On": b"\x1B\x47",           # ESC G (27 71) -- doc calls this "Double-Strike"
    "Enhanced Printing Off": b"\x1B\x48",          # ESC H (27 72)
    "Form Feed": b"\x0C",                          # FF (12)
    "Horizontal Tab": b"\x09",                     # HT (9)
    # The old ibm_app.py had "Italics On/Off" as ESC % G / ESC % H (1B2547/1B2548)
    # -- this is not a real IBM Proprinter III command (confirmed: it doesn't
    # appear anywhere in docs/printer-commands-ibm-proprinter.md), which is why
    # it got "stuck" and never actually turned italics off on real hardware.
    # The real command is "Select Print Mode" (ESC I n, 1B 49 n): n=0x0B
    # selects "Alternate NLQ II (Italic)"; n=0x00 returns to Draft (non-italic).
    "Italics On": b"\x1B\x49\x0B",                 # ESC I 11 (27 73 11)
    "Italics Off": b"\x1B\x49\x00",                # ESC I 0 (27 73 0)
    "Line Feed": b"\x0A",                          # LF (10)
    "Reverse Line Feed": b"\x1B\x4A",              # ESC J (27 74)
    "Line Spacing 1/8": b"\x1B\x30",               # ESC 0 (27 48)
    "Line Spacing 7/72": b"\x1B\x31",               # ESC 1 (27 49)
    "Set Spacing to n/72": lambda n: b"\x1B\x41" + bytes([n]),      # ESC A n (27 65 n)
    "Store Spacing Set": b"\x1B\x32",              # ESC 2 (27 50)
    # Confirmed on real hardware: "Set Spacing to n/144" (ESC % 9 n) has no
    # effect on this printer -- "Set Spacing to n/216" (ESC 3 n) does work.
    # Kept in the table (matches the vendor doc), but the app disables the
    # n/144 radio button since selecting it silently does nothing here.
    "Set Spacing to n/144": lambda n: b"\x1B\x25\x39" + bytes([n]), # ESC % 9 n (27 37 57 n)
    "Set Spacing to n/216": lambda n: b"\x1B\x33" + bytes([n]),     # ESC 3 n (27 51 n)
    "Overscore On": b"\x1B\x5F\x31",               # ESC _ 1 (27 95 49)
    "Overscore Off": b"\x1B\x5F\x30",              # ESC _ 0 (27 95 48)
    "Paper Out Sensor Off": b"\x1B\x38",           # ESC 8 (27 56)
    "Paper Out Sensor On": b"\x1B\x39",            # ESC 9 (27 57)
    "Print Suppress On": b"\x13",                  # DC3 (19)
    "Print Suppress Off": b"\x11",                 # DC1 (17)
    # Proportional Spacing (ESC P n): docs/printer-commands-ibm-proprinter.md
    # explicitly notes this is "Not available on the Proprinter" -- kept here
    # for completeness/other IBM printers, but expect this toggle to be a
    # no-op (or worse, unrecognized) on a real Proprinter III.
    "Proportional Spacing On": b"\x1B\x50\x31",    # ESC P 1 (27 80 49)
    "Proportional Spacing Off": b"\x1B\x50\x30",   # ESC P 0 (27 80 48)
    # NOTE: CAN only cancels data sitting in the print buffer, not print-mode
    # state (italics, underline, etc). There's no single vendor-documented
    # "Initialize" command for the Proprinter III (unlike Epson's ESC @), but
    # Printer.reset() also sends "Master Select Reset" above, which clears at
    # least the Master-Select-controlled attributes. Modes set via other
    # commands (e.g. Italics On via ESC I n) still need their own explicit
    # Off command, or a power cycle if truly stuck.
    "Reset (Clear Print Buffer)": b"\x18",         # CAN (24)
    "Vertical Tab": b"\x0B",                       # VT (11)
    # Underline: docs/printer-commands-ibm-proprinter.md (transcribed from
    # the vendor manual scans) lists "Continuous Underscore" as ESC ` n
    # (1B 60), but confirmed on real hardware via printer_selftest.py that
    # this printer's Proprinter III emulation does NOT honor that -- ESC - n
    # (1B 2D, the Epson/generic ESC/P convention that the old per-app dicts
    # all used) is the one that actually works. The doc transcription is
    # likely an OCR mix-up of "-" and "`" in the scanned manual.
    "Underline On": b"\x1B\x2D\x01",               # ESC - 1 (27 45 49)
    "Underline Off": b"\x1B\x2D\x00",              # ESC - 0 (27 45 48)
    # Superscript/Subscript: the old ibm_app.py dict had these marked
    # "(Custom guess)" using ESC s n (1B 73). docs/printer-commands-ibm-proprinter.md
    # (transcribed from the vendor manual) gives the real command: ESC S n
    # (1B 53) with n=0 for superscript, n=1 for subscript, and a single
    # cancel command ESC T (1B 54) -- not separate on/off pairs per mode.
    "Superscript On": b"\x1B\x53\x00",             # ESC S 0 (27 83 0)
    "Subscript On": b"\x1B\x53\x01",               # ESC S 1 (27 83 1)
    "Script Off": b"\x1B\x54",                     # ESC T (27 84) -- cancels either
}
