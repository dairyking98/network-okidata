"""
Configuration and Command Definitions for the Live Keystroke Printer.
"""

# ------------------ Default Configuration ------------------
DEFAULT_CONFIG = {
    "PRINTER_IP": "192.168.4.28",
    "PRINTER_PORT": 9100,
    "DEFAULT_EMULATION": "Okidata",
    "DEFAULT_CPI": "10 cpi",
    "DEFAULT_SKIP_PERFORATION": 0,
    "DEFAULT_LEFT_MARGIN": 0
}

# ------------------ Okidata MICROLINE Command Dictionary ------------------
OKIDATA_COMMANDS = {
    "Backspace": b"\x08",
    "Carriage Return": b"\x0D",
    "Select 10 cpi": b"\x1E",
    "Select 12 cpi": b"\x1C",
    "Select 15 cpi": b"\x1B\x67",
    "Select 17.1 cpi": b"\x1D",
    "Select 20 cpi": b"\x1B\x23\x33",
    "Standard Character Set": b"\x1B\x21\x30",
    "Block Graphic Set": b"\x1B\x21\x31",
    "Publisher Set": b"\x1B\x21\x5A",
    "Line Graphics Set": b"\x1B\x21\x32",
    "Select Utility": b"\x1B\x30",
    "Slashed Zero": b"\x1B\x21\x40",
    "Unslashed Zero": b"\x1B\x21\x41",
    "Double Height On": b"\x1B\x1F\x31",
    "Double Height Off": b"\x1B\x1F\x30",
    "Double Width On": b"\x1F",  # Double Wide command (ASCII 31)
    "Double Width Off": b"\x1B\x21\x30",
    "Emphasized Printing On": b"\x1B\x54",
    "Emphasized Printing Off": b"\x1B\x49",
    "Enhanced Printing On": b"\x1B\x48",
    "Enhanced Printing Off": b"\x1B\x49",
    "Underline Printing On": b"\x1B\x2D\x01",
    "Underline Printing Off": b"\x1B\x2D\x00",
    "Unidirectional Printing On": b"\x1B\x2D\x02",
    "Unidirectional Printing Off": b"\x1B\x2D\x00",
    "Form Feed": b"\x0C",
    "Horizontal Tab": b"\x09",
    "Vertical Tab": b"\x0B",
    "Line Feed": b"\x0A",
    "Line Feed w/o CR": b"\x1B\x12",
    "Reverse Line Feed": b"\x1B\x0A",
    "Set Spacing to 1/6\"": b"\x1B\x36",
    "Set Spacing to 1/8\"": b"\x1B\x38",
    "Set Spacing to n/144": lambda n: b"\x1B\x25\x39" + bytes([n]),
    "Print Quality Select HSD/SSD": b"\x1B\x23\x30",
    "Select NLQ Courier": b"\x1B\x31",
    "Select NLQ Gothic": b"\x1B\x33",
    "Print Speed Set to Full": b"\x1B\x3E",
    "Print Speed Set to Half": b"\x1B\x3C",
    "Proportional Printing On": b"\x1B\x59",
    "Proportional Printing Off": b"\x1B\x5A",
    "Reset (Clear Print Buffer)": b"\x18",
    "Skip Over Perforation": lambda n: b"\x1B\x25\x53\x30" if n == 0 else b"\x1B\x47" + bytes([n]) + bytes([n]),
    "Shift In": b"\x0F",
    "Shift Out": b"\x0E"
}

# ------------------ Integrated Formatting Commands ------------------
FORMAT_COMMANDS = {
    "Okidata": {
        "italic": (b"\x1B\x21\x2F", b"\x1B\x21\x2A"),
        "emphasized": (b"\x1B\x54", b"\x1B\x49"),
    }
}
