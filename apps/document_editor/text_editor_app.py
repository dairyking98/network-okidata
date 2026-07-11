"""
Custom Text Editor and Printer Control with Multi-Emulation Support,
Proper Formatting Conversion, Default Configuration, and Debug Mode
(with a separate Debug Console window)

This program implements two main functions:
1. A text editor that allows the user to apply formatting (bold, italic, underline)
   and then print the text. The printed text is processed to insert appropriate printer
   escape codes where formatting is applied.
2. A separate printer control GUI to send individual printer control commands (e.g., line feed,
   carriage return) over Ethernet via HP JetDirect. The commands are generated based on the
   selected emulation (Okidata/MICROLINE, IBM Proprinter III, or Epson FX).

Command codes have been split into two sections:
  - Control Commands (for individual printer operations) are defined in OKI_COMMANDS,
    IBM_COMMANDS, and EPSON_COMMANDS.
  - Formatting Commands (for bold, italic, underline) are defined in FORMAT_COMMANDS.

Default configuration values (e.g., printer IP "192.168.4.28") are stored in DEFAULT_CONFIG.

A Debug Mode option is provided. When enabled, all command bytes (displayed in hexadecimal)
are printed to a separate debug console window.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import socket
import binascii

# ------------------ Default Configuration ------------------
DEFAULT_CONFIG = {
    "PRINTER_IP": "192.168.4.28",
    "PRINTER_PORT": 9100,
    "DEFAULT_EMULATION": "Okidata"
}

# ------------------ Control Command Dictionaries ------------------
# Okidata MICROLINE Commands
OKI_COMMANDS = {
    "Backspace": b"\x08",  # BS, 8
    "Carriage Return": b"\x0D",  # CR, 13
    "Select 10 cpi": b"\x1E",  # RS, 30
    "Select 12 cpi": b"\x1C",  # FS, 28
    "Select 15 cpi": b"\x1B\x67",  # ESC g, 27 103
    "Select 17.1 cpi": b"\x1D",  # GS, 29
    "Select 20 cpi": b"\x1B\x23\x33",  # ESC # 3, 27 35 51
    "Standard Character Set": b"\x1B\x21\x30",  # ESC ! 0, 27 33 48
    "Block Graphic Set": b"\x1B\x21\x31",  # ESC ! 1, 27 33 49
    "Line Graphics Set": b"\x1B\x21\x32",  # ESC ! 2, 27 33 50
    "Publisher Set": b"\x1B\x21\x5A",  # ESC ! Z, 27 33 90
    "Slashed Zero": b"\x1B\x21\x40",  # ESC ! @, 27 33 64
    "Unslashed Zero": b"\x1B\x21\x41",  # ESC ! A, 27 33 65
    "Double Height On": b"\x1B\x1F\x31",  # ESC US 1, 27 31 49
    "Double Height Off": b"\x1B\x1F\x30",  # ESC US 0, 27 31 48
    "Double Width Printing": b"\x1F",  # US, 31
    "Emphasized Printing On": b"\x1B\x54",  # ESC T, 27 84
    "Emphasized Printing Off": b"\x1B\x49",  # ESC I, 27 73
    "Enhanced Printing On": b"\x1B\x48",  # ESC H, 27 72
    "Enhanced Printing Off": b"\x1B\x49",  # ESC I, 27 73
    "Form Feed": b"\x0C",  # FF, 12
    "Horizontal Tab": b"\x09",  # HT, 9
    "Line Feed": b"\x0A",  # LF, 10
    "Line Feed w/o CR": b"\x1B\x12",  # ESC DC2, 27 18
    "Reverse Line Feed": b"\x1B\x0A",  # ESC LF, 27 10
    "Set Spacing to 1/6\"": b"\x1B\x36",  # ESC 6, 27 54
    "Set Spacing to 1/8\"": b"\x1B\x38",  # ESC 8, 27 56
    "Skip Over Perforation Default": b"\x1B\x25\x83\x30",  # ESC % 0, 27 37 83 48
    "Paper Out Sensor Off": b"\x1B\x45\x31",  # ESC E 1, 27 69 49
    "Paper Out Sensor On": b"\x1B\x45\x30",  # ESC E 0, 27 69 48
    "Print Quality Select HSD/SSD": b"\x1B\x23\x30",  # ESC # 0, 27 35 48
    "Select NLQ Courier": b"\x1B\x31",  # ESC 1, 27 49
    "Select NLQ Gothic": b"\x1B\x33",  # ESC 3, 27 51
    "Select Utility": b"\x1B\x30",  # ESC 0, 27 48
    "Print Speed Set to Full": b"\x1B\x3E",  # ESC >, 27 62
    "Print Speed Set to Half": b"\x1B\x3C",  # ESC <, 27 60
    "Print Suppress On": b"\x13",  # DC3, 19
    "Print Suppress Off": b"\x11",  # DC1, 17
    "Proportional Printing On": b"\x1B\x59",  # ESC Y, 27 89
    "Proportional Printing Off": b"\x1B\x5A",  # ESC Z, 27 90
    "Reset (Clear Print Buffer)": b"\x18",  # CAN, 24
}

# IBM Proprinter III Commands
IBM_COMMANDS = {
    "Backspace": b"\x08",
    "Carriage Return": b"\x0D",
    "Select 10 cpi": b"\x12",  # DC2, 18
    "Select 12 cpi": b"\x1B\x3A",  # ESC :, 27 58
    "Select 15 cpi": b"\x1B\x67",  # ESC g, 27 103
    "Select Condensed Print": b"\x1B\x0F",  # ESC SI, 27 15
    "IBM Set I": b"\x1B\x37",  # ESC 7, 27 55
    "IBM Set II": b"\x1B\x36",  # ESC 6, 27 54
    "Publisher Set": b"\x1B\x21\x5A",  # ESC ! Z, 27 33 90
    "Slashed Zero": b"\x1B\x21\x40",  # ESC ! @, 27 33 64
    "Unslashed Zero": b"\x1B\x21\x41",  # ESC ! A, 27 33 65
    "Double Width On": b"\x1B\x57\x31",  # ESC W 1, 27 87 49
    "Double Width Off": b"\x1B\x57\x30",  # ESC W 0, 27 87 48
    "Emphasized Printing On": b"\x1B\x45",  # ESC E, 27 69
    "Emphasized Printing Off": b"\x1B\x46",  # ESC F, 27 70
    "Enhanced Printing On": b"\x1B\x47",  # ESC G, 27 71
    "Enhanced Printing Off": b"\x1B\x48",  # ESC H, 27 72
    "Form Feed": b"\x0C",
    "Horizontal Tab": b"\x09",
    "Italics On": b"\x1B\x25\x47",  # ESC % G, 27 37 71
    "Italics Off": b"\x1B\x25\x48",  # ESC % H, 27 37 72
    "Line Feed": b"\x0A",
    "Reverse Line Feed": b"\x1B\x4A",  # ESC J, 27 74
    "Line Spacing 1/8\"": b"\x1B\x30",  # ESC 0, 27 48
    "Line Spacing 7/72\"": b"\x1B\x31",  # ESC 1, 27 49
    "Store Spacing Set": b"\x1B\x32",  # ESC 2, 27 50
    "Overscore On": b"\x1B\x5F\x31",  # ESC _ 1, 27 95 49
    "Overscore Off": b"\x1B\x5F\x30",  # ESC _ 0, 27 95 48
    "Paper Out Sensor Off": b"\x1B\x38",  # ESC 8, 27 56
    "Paper Out Sensor On": b"\x1B\x39",  # ESC 9, 27 57
    "Print Suppress On": b"\x13",
    "Print Suppress Off": b"\x11",
    "Proportional Spacing On": b"\x1B\x50\x31",  # ESC P 1, 27 80 49
    "Proportional Spacing Off": b"\x1B\x50\x30",  # ESC P 0, 27 80 48
    "Reset (Clear Print Buffer)": b"\x18",
}

# Epson FX Commands
EPSON_COMMANDS = {
    "Backspace": b"\x08",
    "Carriage Return": b"\x0D",
    "Select 10 cpi": b"\x1B\x50",  # ESC P, 27 80
    "Select 12 cpi": b"\x1B\x4D",  # ESC M, 27 77
    "Select 15 cpi": b"\x1B\x67",  # ESC g, 27 103
    "Begin 10 cpi": b"\x1B\x0F",  # ESC SI, 27 15
    "Cancel Condensed Print": b"\x12",  # DC2, 18
    "Delete": b"\x7F",  # DEL, 127
    "Double Height On": b"\x1B\x77\x31",  # ESC w 1, 27 119 49
    "Double Height Off": b"\x1B\x77\x30",  # ESC w 0, 27 119 48
    "Double Width On": b"\x1B\x57\x31",  # ESC W 1, 27 87 49
    "Double Width Off": b"\x1B\x57\x30",  # ESC W 0, 27 87 48
    "Emphasized Print On": b"\x1B\x45",  # ESC E, 27 69
    "Emphasized Print Off": b"\x1B\x46",  # ESC F, 27 70
    "Enhanced Print On": b"\x1B\x47",  # ESC G, 27 71
    "Enhanced Print Off": b"\x1B\x48",  # ESC H, 27 72
    "Italic On": b"\x1B\x34",  # ESC 4, 27 52
    "Italic Off": b"\x1B\x35",  # ESC 5, 27 53
    "Form Feed": b"\x0C",
    "Horizontal Tab": b"\x09",
    "Line Feed": b"\x0A",
    "Reset Printer": b"\x1B\x40",  # ESC @, 27 64
    "Software I-Prime": b"\x1B\x7D\x00",  # ESC } NUL, 27 125 0
}

# Mapping from emulation name to its control command dictionary.
EMULATION_COMMANDS = {
    "Okidata": OKI_COMMANDS,
    "IBM": IBM_COMMANDS,
    "Epson": EPSON_COMMANDS,
}

# ------------------ Formatting Command Dictionaries ------------------
# These commands are used to insert formatting escape sequences in the printed document.
FORMAT_COMMANDS = {
    "Okidata": {
        "bold": (b"\x1B\x54", b"\x1B\x49"),      # Emphasized Printing On / Off
        "italic": (b"\x1B\x21\x2F", b"\x1B\x21\x2A"),  # Example codes for italic (if supported)
        "underline": (b"", b"")  # Underline not defined for this example
    },
    "IBM": {
        "bold": (b"\x1B\x45", b"\x1B\x46"),       # Emphasized Printing On / Off
        "italic": (b"\x1B\x25\x47", b"\x1B\x25\x48"),
        "underline": (b"", b"")
    },
    "Epson": {
        "bold": (b"\x1B\x45", b"\x1B\x46"),       # Emphasized Print On / Off
        "italic": (b"\x1B\x34", b"\x1B\x35"),
        "underline": (b"", b"")
    }
}

# ------------------ Debug Console ------------------
# Global variable to hold the debug console instance.
debug_console = None

class DebugConsole:
    def __init__(self, master):
        self.window = tk.Toplevel(master)
        self.window.title("Debug Console")
        self.text = scrolledtext.ScrolledText(self.window, wrap="word", state=tk.DISABLED, width=80, height=20)
        self.text.pack(fill=tk.BOTH, expand=True)

    def log(self, message):
        self.text.config(state=tk.NORMAL)
        self.text.insert(tk.END, message + "\n")
        self.text.config(state=tk.DISABLED)
        self.text.see(tk.END)

def get_debug_console(master):
    global debug_console
    if debug_console is None or not debug_console.window.winfo_exists():
        debug_console = DebugConsole(master)
    return debug_console

# ------------------ Printer Emulator Class ------------------
class PrinterEmulator:
    """
    Converts formatted text into a printer command sequence based on the selected emulation.
    In this implementation, the text is assumed to have already been processed to include any
    formatting escape codes.
    """
    def __init__(self, emulation):
        self.emulation = emulation

    def generate_commands(self, formatted_text):
        # Simply return the processed text plus a newline.
        return formatted_text + b"\n"

# ------------------ Text Editor Class ------------------
class TextEditor:
    """
    Main application window for text editing and document printing.
    """
    def __init__(self, master):
        self.master = master
        master.title("Custom Text Editor & Printer Control")
        
        # Debug Mode variable
        self.debug_mode = tk.BooleanVar(value=False)
        
        # Create main frame for text editing area with scrollbar.
        self.main_frame = tk.Frame(master)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.text = tk.Text(self.main_frame, wrap="word", undo=True)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollbar = tk.Scrollbar(self.main_frame, command=self.text.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.config(yscrollcommand=self.scrollbar.set)

        # Control Panel for formatting and printer options.
        self.control_frame = tk.Frame(master)
        self.control_frame.pack(fill=tk.X)

        # Formatting Buttons
        self.bold_btn = tk.Button(self.control_frame, text="Bold", command=self.make_bold)
        self.bold_btn.pack(side=tk.LEFT, padx=2, pady=2)
        self.italic_btn = tk.Button(self.control_frame, text="Italic", command=self.make_italic)
        self.italic_btn.pack(side=tk.LEFT, padx=2, pady=2)
        self.underline_btn = tk.Button(self.control_frame, text="Underline", command=self.make_underline)
        self.underline_btn.pack(side=tk.LEFT, padx=2, pady=2)
        self.indent_btn = tk.Button(self.control_frame, text="Indent", command=self.indent_text)
        self.indent_btn.pack(side=tk.LEFT, padx=2, pady=2)

        # Printer Emulation Selection
        self.emulation_label = tk.Label(self.control_frame, text="Emulation:")
        self.emulation_label.pack(side=tk.LEFT, padx=(10, 0))
        self.emulation_var = tk.StringVar(value=DEFAULT_CONFIG["DEFAULT_EMULATION"])
        self.emulation_option = ttk.Combobox(self.control_frame, textvariable=self.emulation_var,
                                             values=["IBM", "Epson", "Okidata"], width=10)
        self.emulation_option.pack(side=tk.LEFT, padx=2, pady=2)

        # Printer Connection Info
        self.ip_label = tk.Label(self.control_frame, text="Printer IP:")
        self.ip_label.pack(side=tk.LEFT, padx=(10, 0))
        self.ip_entry = tk.Entry(self.control_frame, width=15)
        self.ip_entry.insert(0, DEFAULT_CONFIG["PRINTER_IP"])
        self.ip_entry.pack(side=tk.LEFT, padx=2, pady=2)

        self.port_label = tk.Label(self.control_frame, text="Port:")
        self.port_label.pack(side=tk.LEFT, padx=(10, 0))
        self.port_entry = tk.Entry(self.control_frame, width=5)
        self.port_entry.insert(0, str(DEFAULT_CONFIG["PRINTER_PORT"]))
        self.port_entry.pack(side=tk.LEFT, padx=2, pady=2)

        # Debug Mode Checkbox
        self.debug_checkbox = tk.Checkbutton(self.control_frame, text="Debug Mode", variable=self.debug_mode)
        self.debug_checkbox.pack(side=tk.LEFT, padx=10, pady=2)

        # Document Print Preview and Print Buttons
        self.preview_btn = tk.Button(self.control_frame, text="Print Preview", command=self.print_preview)
        self.preview_btn.pack(side=tk.LEFT, padx=(10, 2), pady=2)
        self.print_btn = tk.Button(self.control_frame, text="Print", command=self.print_document)
        self.print_btn.pack(side=tk.LEFT, padx=2, pady=2)

        # Button to open the Printer Control GUI
        self.control_gui_btn = tk.Button(self.control_frame, text="Printer Control", command=self.open_printer_control)
        self.control_gui_btn.pack(side=tk.LEFT, padx=10, pady=2)

        self.preview_window = None

    # ---------- Formatting Functions (for the text widget) ----------
    def make_bold(self):
        try:
            current_tags = self.text.tag_names("sel.first")
            if "bold" in current_tags:
                self.text.tag_remove("bold", "sel.first", "sel.last")
            else:
                self.text.tag_add("bold", "sel.first", "sel.last")
                self.text.tag_config("bold", font=("Helvetica", 12, "bold"))
        except tk.TclError:
            messagebox.showinfo("Info", "Please select text to bold.")

    def make_italic(self):
        try:
            current_tags = self.text.tag_names("sel.first")
            if "italic" in current_tags:
                self.text.tag_remove("italic", "sel.first", "sel.last")
            else:
                self.text.tag_add("italic", "sel.first", "sel.last")
                self.text.tag_config("italic", font=("Helvetica", 12, "italic"))
        except tk.TclError:
            messagebox.showinfo("Info", "Please select text to italicize.")

    def make_underline(self):
        try:
            current_tags = self.text.tag_names("sel.first")
            if "underline" in current_tags:
                self.text.tag_remove("underline", "sel.first", "sel.last")
            else:
                self.text.tag_add("underline", "sel.first", "sel.last")
                self.text.tag_config("underline", font=("Helvetica", 12, "underline"))
        except tk.TclError:
            messagebox.showinfo("Info", "Please select text to underline.")

    def indent_text(self):
        try:
            start = self.text.index("sel.first linestart")
            end = self.text.index("sel.last lineend")
            lines = self.text.get(start, end).split("\n")
            indented_lines = ["    " + line for line in lines]
            self.text.delete(start, end)
            self.text.insert(start, "\n".join(indented_lines))
        except tk.TclError:
            messagebox.showinfo("Info", "Please select text to indent.")

    # ---------- Converting Text with Formatting into Escape Codes ----------
    def get_formatted_text_with_formatting(self):
        """
        Iterate over the text widget content character by character.
        For each character, check if formatting tags (bold, italic, underline) are present.
        If so, insert the corresponding escape codes (based on the current emulation's formatting commands).
        For simplicity, each character is wrapped with the on/off codes if the tag is active.
        """
        result = bytearray()
        emulation = self.emulation_var.get()
        format_cmds = FORMAT_COMMANDS.get(emulation, {})
        
        index = "1.0"
        last_index = self.text.index(tk.END)
        while self.text.compare(index, "<", last_index):
            next_index = self.text.index(f"{index} +1c")
            char = self.text.get(index, next_index)
            tags = self.text.tag_names(index)
            
            prefix = b""
            suffix = b""
            # Wrap with bold codes if tag is active.
            if "bold" in tags and "bold" in format_cmds:
                on_code, off_code = format_cmds["bold"]
                prefix += on_code
                suffix = off_code + suffix
            # Wrap with italic codes if tag is active.
            if "italic" in tags and "italic" in format_cmds:
                on_code, off_code = format_cmds["italic"]
                prefix += on_code
                suffix = off_code + suffix
            # Wrap with underline codes if tag is active.
            if "underline" in tags and "underline" in format_cmds and format_cmds["underline"][0]:
                on_code, off_code = format_cmds["underline"]
                prefix += on_code
                suffix = off_code + suffix

            result.extend(prefix)
            result.extend(char.encode('utf-8'))
            result.extend(suffix)
            index = next_index
        return bytes(result)

    # ---------- Document Print Preview and Printing ----------
    def print_preview(self):
        formatted_text = self.get_formatted_text_with_formatting()
        preview_text = f"--- Print Preview ({self.emulation_var.get()} Emulation) ---\n"
        try:
            preview_text += formatted_text.decode('utf-8', errors='replace')
        except Exception:
            preview_text += "<Error decoding formatted text>"
            
        if self.preview_window and tk.Toplevel.winfo_exists(self.preview_window):
            self.preview_window.destroy()

        self.preview_window = tk.Toplevel(self.master)
        self.preview_window.title("Print Preview")
        preview_area = tk.Text(self.preview_window, wrap="word")
        preview_area.pack(fill=tk.BOTH, expand=True)
        preview_area.insert("1.0", preview_text)
        preview_area.config(state=tk.DISABLED)

    def print_document(self):
        formatted_text = self.get_formatted_text_with_formatting()
        emulation = self.emulation_var.get()
        emulator = PrinterEmulator(emulation)
        commands = emulator.generate_commands(formatted_text)

        # Debug: log commands in hex if debug mode is enabled.
        if self.debug_mode.get():
            debug_str = binascii.hexlify(commands).decode('utf-8')
            dc = get_debug_console(self.master)
            dc.log(f"[Document Print] Commands (hex): {debug_str}")

        printer_ip = self.ip_entry.get()
        try:
            printer_port = int(self.port_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid port number.")
            return

        try:
            with socket.create_connection((printer_ip, printer_port), timeout=10) as printer_socket:
                printer_socket.sendall(commands)
            messagebox.showinfo("Success", "Document sent to printer successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to print document: {e}")

    # ---------- Open Printer Control GUI ----------
    def open_printer_control(self):
        PrinterControlGUI(self.master, self.debug_mode)

# ------------------ Printer Control GUI Class ------------------
class PrinterControlGUI:
    """
    A separate window that allows the operator to send individual printer control commands.
    The available commands (from the control command dictionaries) are shown based on the selected emulation.
    """
    def __init__(self, parent, debug_mode):
        self.parent = parent
        self.debug_mode = debug_mode
        self.window = tk.Toplevel(parent)
        self.window.title("Printer Control")

        # Emulation selection (synchronized with main window if desired)
        self.emulation_label = tk.Label(self.window, text="Emulation:")
        self.emulation_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.emulation_var = tk.StringVar(value=DEFAULT_CONFIG["DEFAULT_EMULATION"])
        self.emulation_option = ttk.Combobox(self.window, textvariable=self.emulation_var,
                                             values=["IBM", "Epson", "Okidata"], width=10)
        self.emulation_option.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.emulation_option.bind("<<ComboboxSelected>>", self.update_command_list)

        # Printer connection info
        self.ip_label = tk.Label(self.window, text="Printer IP:")
        self.ip_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.ip_entry = tk.Entry(self.window, width=15)
        self.ip_entry.insert(0, DEFAULT_CONFIG["PRINTER_IP"])
        self.ip_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        self.port_label = tk.Label(self.window, text="Port:")
        self.port_label.grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.port_entry = tk.Entry(self.window, width=5)
        self.port_entry.insert(0, str(DEFAULT_CONFIG["PRINTER_PORT"]))
        self.port_entry.grid(row=1, column=3, padx=5, pady=5, sticky="w")

        # Listbox to display available control commands for the selected emulation
        self.command_listbox = tk.Listbox(self.window, height=15, width=40)
        self.command_listbox.grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky="nsew")
        self.update_command_list()

        # Button to send the selected command
        self.send_btn = tk.Button(self.window, text="Send Command", command=self.send_command)
        self.send_btn.grid(row=3, column=0, columnspan=4, padx=5, pady=5)

    def update_command_list(self, event=None):
        """Update the listbox with control commands from the selected emulation."""
        self.command_listbox.delete(0, tk.END)
        emulation = self.emulation_var.get()
        commands_dict = EMULATION_COMMANDS.get(emulation, {})
        for command in sorted(commands_dict.keys()):
            self.command_listbox.insert(tk.END, command)

    def send_command(self):
        """Send the selected control command to the printer via HP JetDirect."""
        selection = self.command_listbox.curselection()
        if not selection:
            messagebox.showinfo("Info", "Please select a command to send.")
            return

        command_name = self.command_listbox.get(selection[0])
        emulation = self.emulation_var.get()
        command_bytes = EMULATION_COMMANDS.get(emulation, {}).get(command_name, None)

        if command_bytes is None:
            messagebox.showerror("Error", "Selected command not found.")
            return

        # Debug: log command bytes in hex if debug mode is enabled.
        if self.debug_mode.get():
            debug_str = binascii.hexlify(command_bytes).decode('utf-8')
            dc = get_debug_console(self.parent)
            dc.log(f"[Control Command] '{command_name}' (hex): {debug_str}")

        printer_ip = self.ip_entry.get()
        try:
            printer_port = int(self.port_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid port number.")
            return

        try:
            with socket.create_connection((printer_ip, printer_port), timeout=10) as printer_socket:
                printer_socket.sendall(command_bytes)
            messagebox.showinfo("Success", f"Command '{command_name}' sent successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send command: {e}")

# ------------------ Main Application Entry Point ------------------
def main():
    root = tk.Tk()
    app = TextEditor(root)
    root.mainloop()

if __name__ == '__main__':
    main()
