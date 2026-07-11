"""
Persistent raw-socket client for the IBM Proprinter III emulation.
"""

import socket
from typing import Callable, Optional

from .ibm_proprinter import COMMANDS

_TOGGLE_COMMANDS = {
    "bold": ("Emphasized Printing On", "Emphasized Printing Off"),
    "italic": ("Italics On", "Italics Off"),
    "enhanced": ("Enhanced Printing On", "Enhanced Printing Off"),
    "underline": ("Underline On", "Underline Off"),
    "overscore": ("Overscore On", "Overscore Off"),
    "proportional": ("Proportional Spacing On", "Proportional Spacing Off"),
    "double_width": ("Double Width On", "Double Width Off"),
}

_CPI_COMMANDS = {
    10: "Select 10 cpi",
    12: "Select 12 cpi",
    15: "Select 15 cpi",
    "condensed": "Select Condensed Print",
}

_FONT_COMMANDS = {
    "IBM Set I": "IBM Set I",
    "IBM Set II": "IBM Set II",
}

_SCRIPT_COMMANDS = {
    "superscript": "Superscript On",
    "subscript": "Subscript On",
    "normal": "Script Off",
}


class Printer:
    """Persistent-connection client for an IBM Proprinter III over raw TCP (port 9100)."""

    def __init__(self, ip: str, port: int = 9100, on_log: Optional[Callable[[str], None]] = None):
        self.ip = ip
        self.port = port
        self.on_log = on_log or (lambda msg: None)
        self._sock: Optional[socket.socket] = None

    def __enter__(self) -> "Printer":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def connect(self) -> None:
        if self._sock is not None:
            return
        try:
            self._sock = socket.create_connection((self.ip, self.port), timeout=5)
            self.on_log(f"[Connection] Connected to {self.ip}:{self.port}")
        except OSError as e:
            self.on_log(f"[Connection] Error connecting: {e}")
            self._sock = None

    def close(self) -> None:
        if self._sock is None:
            return
        try:
            self._sock.close()
        finally:
            self._sock = None
            self.on_log("[Connection] Connection closed.")

    def _send(self, data: bytes, tag: str = "") -> None:
        if not data:
            return
        dec_str = " ".join(str(b) for b in data)
        self.on_log(f"{tag} {dec_str}".strip())
        self.connect()
        if self._sock is None:
            return
        try:
            self._sock.sendall(data)
        except OSError as e:
            self.on_log(f"{tag} Error sending command: {e}".strip())
            self.close()

    def command(self, name: str, *args, tag: Optional[str] = None) -> None:
        """Send a named command from printer.ibm_proprinter.COMMANDS, applying args to parameterized ones."""
        cmd = COMMANDS.get(name)
        if cmd is None:
            self.on_log(f"[{name}] Unknown command")
            return
        data = cmd(*args) if callable(cmd) else cmd
        self._send(data, tag or f"[{name}]")

    def raw(self, data: bytes, tag: str = "") -> None:
        """Send arbitrary bytes not in the canonical command table -- for diagnostics/one-off testing."""
        self._send(data, tag or "[raw]")

    def text(self, s: str) -> None:
        # Bare LF (\n) doesn't imply a carriage return on this printer --
        # without an explicit CR the head doesn't return to the left margin,
        # so consecutive lines drift diagonally across the page instead of
        # stacking. Normalize to CR+LF so plain "\n" in calling code behaves
        # as expected.
        self._send(s.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8"), tag="[Text]")

    def set(self, **kwargs) -> None:
        """Toggle formatting (bold=True/False, cpi=10, font='IBM Set I', script='superscript', spacing=(...))"""
        for key, value in kwargs.items():
            if key in _TOGGLE_COMMANDS:
                on_name, off_name = _TOGGLE_COMMANDS[key]
                self.command(on_name if value else off_name, tag=f"[{key}]")
            elif key == "cpi":
                name = _CPI_COMMANDS.get(value)
                if name is None:
                    self.on_log(f"[cpi] Unknown value: {value!r}")
                    continue
                self.command(name, tag="[cpi]")
            elif key == "font":
                name = _FONT_COMMANDS.get(value)
                if name is None:
                    self.on_log(f"[font] Unknown value: {value!r}")
                    continue
                self.command(name, tag="[font]")
            elif key == "script":
                name = _SCRIPT_COMMANDS.get(value)
                if name is None:
                    self.on_log(f"[script] Unknown value: {value!r}")
                    continue
                self.command(name, tag="[script]")
            elif key == "spacing":
                # value is ("1/8" | "7/72" | "n/144" | "n/216", n) -- n only used for the n/144, n/216 forms
                mode, n = value
                if mode == "1/8":
                    self.command("Line Spacing 1/8", tag="[spacing]")
                elif mode == "7/72":
                    self.command("Line Spacing 7/72", tag="[spacing]")
                elif mode == "n/144":
                    self.command("Set Spacing to n/144", n, tag="[spacing]")
                elif mode == "n/216":
                    self.command("Set Spacing to n/216", n, tag="[spacing]")
                else:
                    self.on_log(f"[spacing] Unknown mode: {mode!r}")
            else:
                self.on_log(f"[set] Unknown option: {key!r}")

    def form_feed(self) -> None:
        self.command("Form Feed", tag="[Form Feed]")

    def line_feed(self) -> None:
        self.command("Line Feed", tag="[Line Feed]")

    def carriage_return(self) -> None:
        self.command("Carriage Return", tag="[Carriage Return]")

    def horizontal_tab(self) -> None:
        self.command("Horizontal Tab", tag="[Horizontal Tab]")

    def backspace(self) -> None:
        self.command("Backspace", tag="[Backspace]")

    def reset(self) -> None:
        self.command("Reset (Clear Print Buffer)", tag="[Reset]")
        self.command("Master Select Reset", tag="[Reset]")
