"""
Live Keystroke Printer with Full Command GUI,
Formatting Options, Default Restoration, CPI and LF Adjustment,
Multi-Emulation Support, Default Configuration, and Debug Console

Upon startup (or via the “Restore Defaults” button), the printer is sent a reset command,
a CPI command, and a line feed adjustment command.
The Printer Control GUI lists all possible command codes (using full dictionaries for each emulation).
Live keystrokes are sent as they’re typed (with optional formatting) and special keys (Enter, Tab, BackSpace)
are mapped to control commands.
Debug Mode logs all commands (in hex) to a separate Debug Console window.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
import socket
import binascii

# ------------------ Default Configuration ------------------
DEFAULT_CONFIG = {
    "PRINTER_IP": "192.168.4.28",
    "PRINTER_PORT": 9100,
    "DEFAULT_EMULATION": "IBM",   # IBM set as default
    "DEFAULT_CPI": "10 cpi",
    "DEFAULT_LF_ADJUST": 0
}

# ------------------ Full Command Dictionaries (all possible commands) ------------------
# IBM Proprinter III Full Commands (used as default)
ALL_IBM_COMMANDS = {
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
    "Line Feed Adjust": lambda n: b"\x1B\x25\x39" + bytes([n])
}

# Also include full dictionaries for Okidata and Epson.
ALL_OKI_COMMANDS = {
    "Backspace": b"\x08",
    "Carriage Return": b"\x0D",
    "Select 10 cpi": b"\x1E",
    "Select 12 cpi": b"\x1C",
    "Select 15 cpi": b"\x1B\x67",
    "Select 17.1 cpi": b"\x1D",
    "Select 20 cpi": b"\x1B\x23\x33",
    "Standard Character Set": b"\x1B\x21\x30",
    "Block Graphic Set": b"\x1B\x21\x31",
    "Line Graphics Set": b"\x1B\x21\x32",
    "Publisher Set": b"\x1B\x21\x5A",
    "Slashed Zero": b"\x1B\x21\x40",
    "Unslashed Zero": b"\x1B\x21\x41",
    "Double Height On": b"\x1B\x1F\x31",
    "Double Height Off": b"\x1B\x1F\x30",
    "Double Width Printing": b"\x1F",
    "Emphasized Printing On": b"\x1B\x54",
    "Emphasized Printing Off": b"\x1B\x49",
    "Enhanced Printing On": b"\x1B\x48",
    "Enhanced Printing Off": b"\x1B\x49",
    "Form Feed": b"\x0C",
    "Horizontal Tab": b"\x09",
    "Italic On": b"\x1B\x21\x2F",
    "Italic Off": b"\x1B\x21\x2A",
    "Line Feed": b"\x0A",
    "Line Feed w/o CR": b"\x1B\x12",
    "Reverse Line Feed": b"\x1B\x0A",
    "Set Spacing to 1/6\"": b"\x1B\x36",
    "Set Spacing to 1/8\"": b"\x1B\x38",
    "Skip Over Perforation Default": b"\x1B\x25\x83\x30",
    "Paper Out Sensor Off": b"\x1B\x45\x31",
    "Paper Out Sensor On": b"\x1B\x45\x30",
    "Print Quality Select HSD/SSD": b"\x1B\x23\x30",
    "Select NLQ Courier": b"\x1B\x31",
    "Select NLQ Gothic": b"\x1B\x33",
    "Select Utility": b"\x1B\x30",
    "Print Speed Set to Full": b"\x1B\x3E",
    "Print Speed Set to Half": b"\x1B\x3C",
    "Print Suppress On": b"\x13",
    "Print Suppress Off": b"\x11",
    "Proportional Printing On": b"\x1B\x59",
    "Proportional Printing Off": b"\x1B\x5A",
    "Reset (Clear Print Buffer)": b"\x18",
    "Line Feed Adjust": lambda n: b"\x1B\x25\x35" + bytes([n])
}

ALL_EPSON_COMMANDS = {
    "Backspace": b"\x08",
    "Carriage Return": b"\x0D",
    "Select 10 cpi": b"\x1B\x50",
    "Select 12 cpi": b"\x1B\x4D",
    "Select 15 cpi": b"\x1B\x67",
    "Begin 10 cpi": b"\x1B\x0F",
    "Cancel Condensed Print": b"\x12",
    "Delete": b"\x7F",
    "Double Height On": b"\x1B\x77\x31",
    "Double Height Off": b"\x1B\x77\x30",
    "Double Width On": b"\x1B\x57\x31",
    "Double Width Off": b"\x1B\x57\x30",
    "Emphasized Print On": b"\x1B\x45",
    "Emphasized Print Off": b"\x1B\x46",
    "Enhanced Print On": b"\x1B\x47",
    "Enhanced Print Off": b"\x1B\x48",
    "Italic On": b"\x1B\x34",
    "Italic Off": b"\x1B\x35",
    "Form Feed": b"\x0C",
    "Horizontal Tab": b"\x09",
    "Line Feed": b"\x0A",
    "Reset Printer": b"\x1B\x40",
    "Software I-Prime": b"\x1B\x7D\x00",
    "Line Feed Adjust": lambda n: b"\x1B\x25\x39" + bytes([n])
}

# For the full Printer Control GUI, we use the full dictionaries.
EMULATION_COMMANDS = {
    "IBM": ALL_IBM_COMMANDS,
    "Okidata": ALL_OKI_COMMANDS,
    "Epson": ALL_EPSON_COMMANDS,
}

# ------------------ Formatting Command Dictionaries ------------------
FORMAT_COMMANDS = {
    "IBM": {
        "bold": (b"\x1B\x45", b"\x1B\x46"),
        "italic": (b"\x1B\x25\x47", b"\x1B\x25\x48"),
        "underline": (b"", b""),
        "emphasized": (b"\x1B\x45", b"\x1B\x46"),
    },
    "Okidata": {
        "bold": (b"\x1B\x54", b"\x1B\x49"),
        "italic": (b"\x1B\x21\x2F", b"\x1B\x21\x2A"),
        "underline": (b"", b""),
        "emphasized": (b"\x1B\x54", b"\x1B\x49"),
    },
    "Epson": {
        "bold": (b"\x1B\x45", b"\x1B\x46"),
        "italic": (b"\x1B\x34", b"\x1B\x35"),
        "underline": (b"", b""),
        "emphasized": (b"\x1B\x45", b"\x1B\x46"),
    }
}

# ------------------ Debug Console ------------------
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

# ------------------ Live Keystroke Printer Class ------------------
class LiveKeystrokeEditor:
    """
    GUI for live keystroke printing with default restoration, CPI and LF adjustment,
    formatting options, and full Printer Control GUI access.
    Captures key events from a text widget and sends them live to the printer.
    """
    def __init__(self, master):
        self.master = master
        master.title("Live Keystroke Printer")
        
        self.debug_mode = tk.BooleanVar(value=False)
        self.option_bold = tk.BooleanVar(value=False)
        self.option_italic = tk.BooleanVar(value=False)
        self.option_underline = tk.BooleanVar(value=False)
        self.option_emphasized = tk.BooleanVar(value=False)
        self.cpi_var = tk.StringVar(value=DEFAULT_CONFIG["DEFAULT_CPI"])
        self.lf_adjust_var = tk.IntVar(value=DEFAULT_CONFIG["DEFAULT_LF_ADJUST"])
        
        self.main_frame = tk.Frame(master)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        self.text = tk.Text(self.main_frame, wrap="word", undo=True)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar = tk.Scrollbar(self.main_frame, command=self.text.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.config(yscrollcommand=self.scrollbar.set)
        
        # Bind key events; dedicated binding for Return.
        self.text.bind("<KeyPress>", self.handle_key)
        self.text.bind("<KeyPress-Return>", self.handle_return)
        
        self.control_frame = tk.Frame(master)
        self.control_frame.pack(fill=tk.X)
        
        self.emulation_label = tk.Label(self.control_frame, text="Emulation:")
        self.emulation_label.pack(side=tk.LEFT, padx=(10, 0))
        self.emulation_var = tk.StringVar(value=DEFAULT_CONFIG["DEFAULT_EMULATION"])
        self.emulation_option = ttk.Combobox(self.control_frame, textvariable=self.emulation_var,
                                             values=["IBM", "Epson", "Okidata"], width=10)
        self.emulation_option.pack(side=tk.LEFT, padx=2, pady=2)
        
        self.cpi_label = tk.Label(self.control_frame, text="CPI:")
        self.cpi_label.pack(side=tk.LEFT, padx=(10, 0))
        self.cpi_option = ttk.Combobox(self.control_frame, textvariable=self.cpi_var,
                                       values=["10 cpi", "12 cpi", "15 cpi", "20 cpi"], width=8)
        self.cpi_option.pack(side=tk.LEFT, padx=2, pady=2)
        
        self.lf_label = tk.Label(self.control_frame, text="LF Adj:")
        self.lf_label.pack(side=tk.LEFT, padx=(10, 0))
        self.lf_spinbox = tk.Spinbox(self.control_frame, from_=0, to=9, width=3, textvariable=self.lf_adjust_var)
        self.lf_spinbox.pack(side=tk.LEFT, padx=2, pady=2)
        
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
        
        self.debug_checkbox = tk.Checkbutton(self.control_frame, text="Debug Mode", variable=self.debug_mode, command=self.toggle_debug)
        self.debug_checkbox.pack(side=tk.LEFT, padx=10, pady=2)
        
        self.bold_checkbox = tk.Checkbutton(self.control_frame, text="Bold", variable=self.option_bold)
        self.bold_checkbox.pack(side=tk.LEFT, padx=5, pady=2)
        self.italic_checkbox = tk.Checkbutton(self.control_frame, text="Italic", variable=self.option_italic)
        self.italic_checkbox.pack(side=tk.LEFT, padx=5, pady=2)
        self.underline_checkbox = tk.Checkbutton(self.control_frame, text="Underline", variable=self.option_underline)
        self.underline_checkbox.pack(side=tk.LEFT, padx=5, pady=2)
        self.emph_checkbox = tk.Checkbutton(self.control_frame, text="Emphasized", variable=self.option_emphasized)
        self.emph_checkbox.pack(side=tk.LEFT, padx=5, pady=2)
        
        self.status_label = tk.Label(self.control_frame, text="Live keystrokes are being sent.")
        self.status_label.pack(side=tk.LEFT, padx=10, pady=2)
        self.control_gui_btn = tk.Button(self.control_frame, text="Printer Control", command=self.open_printer_control)
        self.control_gui_btn.pack(side=tk.LEFT, padx=10, pady=2)
        self.restore_btn = tk.Button(self.control_frame, text="Restore Defaults", command=self.restore_defaults)
        self.restore_btn.pack(side=tk.LEFT, padx=10, pady=2)
        
        # Automatically send default restoration commands on startup.
        self.master.after(500, self.restore_defaults)
    
    def toggle_debug(self):
        if self.debug_mode.get():
            get_debug_console(self.master)
    
    def restore_defaults(self):
        emulation = self.emulation_var.get()
        commands_dict = EMULATION_COMMANDS.get(emulation, {})
        printer_ip = self.ip_entry.get()
        try:
            printer_port = int(self.port_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid port number.")
            return
        reset_cmd = commands_dict.get("Reset", b"")
        cpi_cmd = commands_dict.get(f"Select {self.cpi_var.get()}", b"")
        lf_adj_value = self.lf_adjust_var.get()
        lf_adj_cmd = b""
        if "Line Feed Adjust" in commands_dict:
            lf_adj_cmd = commands_dict["Line Feed Adjust"](lf_adj_value)
        full_cmd = reset_cmd + cpi_cmd + lf_adj_cmd
        if self.debug_mode.get():
            dc = get_debug_console(self.master)
            debug_str = binascii.hexlify(full_cmd).decode('utf-8')
            dc.log(f"[Restore Defaults] Commands (hex): {debug_str}")
        try:
            with socket.create_connection((printer_ip, printer_port), timeout=5) as printer_socket:
                printer_socket.sendall(full_cmd)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send default commands: {e}")
    
    def handle_key(self, event):
        if event.keysym == "Return":
            return  # Return is handled separately.
        emulation = self.emulation_var.get()
        commands_dict = EMULATION_COMMANDS.get(emulation, {})
        command = b""
        if event.keysym == "Tab":
            command = commands_dict.get("Horizontal Tab", b"\t")
        elif event.keysym == "BackSpace":
            command = commands_dict.get("Backspace", b"\x08")
        else:
            if event.char and ord(event.char) >= 32:
                command = event.char.encode('utf-8')
                prefix = b""
                suffix = b""
                format_cmds = FORMAT_COMMANDS.get(emulation, {})
                if self.option_bold.get() and "bold" in format_cmds:
                    on_code, off_code = format_cmds["bold"]
                    prefix += on_code
                    suffix = off_code + suffix
                if self.option_italic.get() and "italic" in format_cmds:
                    on_code, off_code = format_cmds["italic"]
                    prefix += on_code
                    suffix = off_code + suffix
                if self.option_underline.get() and "underline" in format_cmds and format_cmds["underline"][0]:
                    on_code, off_code = format_cmds["underline"]
                    prefix += on_code
                    suffix = off_code + suffix
                if self.option_emphasized.get() and "emphasized" in format_cmds:
                    on_code, off_code = format_cmds["emphasized"]
                    prefix += on_code
                    suffix = off_code + suffix
                command = prefix + command + suffix
        if command:
            self.send_live_command(command)
    
    def handle_return(self, event):
        emulation = self.emulation_var.get()
        commands_dict = EMULATION_COMMANDS.get(emulation, {})
        cr = commands_dict.get("Carriage Return", b"\r")
        lf = commands_dict.get("Line Feed", b"\n")
        self.send_live_command(cr)
        self.master.after(10, lambda: self.send_live_command(lf))
        return None
    
    def send_live_command(self, command_bytes):
        if self.debug_mode.get():
            dc = get_debug_console(self.master)
            debug_str = binascii.hexlify(command_bytes).decode('utf-8')
            dc.log(f"[Live Keystroke] Command (hex): {debug_str}")
        printer_ip = self.ip_entry.get()
        try:
            printer_port = int(self.port_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid port number.")
            return
        try:
            with socket.create_connection((printer_ip, printer_port), timeout=5) as printer_socket:
                printer_socket.sendall(command_bytes)
        except Exception as e:
            dc = get_debug_console(self.master)
            dc.log(f"[Error] Failed to send live command: {e}")
    
    def open_printer_control(self):
        PrinterControlGUI(self.master, self.debug_mode)

# ------------------ Printer Control GUI Class ------------------
class PrinterControlGUI:
    """
    A separate window that displays all possible command codes (from the full command dictionaries)
    for the selected emulation so you can manually send any command.
    """
    def __init__(self, parent, debug_mode):
        self.parent = parent
        self.debug_mode = debug_mode
        self.window = tk.Toplevel(parent)
        self.window.title("Printer Control")
        
        self.emulation_label = tk.Label(self.window, text="Emulation:")
        self.emulation_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.emulation_var = tk.StringVar(value=DEFAULT_CONFIG["DEFAULT_EMULATION"])
        self.emulation_option = ttk.Combobox(self.window, textvariable=self.emulation_var,
                                             values=["IBM", "Epson", "Okidata"], width=10)
        self.emulation_option.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.emulation_option.bind("<<ComboboxSelected>>", self.update_command_list)
        
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
        
        self.command_listbox = tk.Listbox(self.window, height=20, width=50)
        self.command_listbox.grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky="nsew")
        self.update_command_list()
        
        self.send_btn = tk.Button(self.window, text="Send Command", command=self.send_command)
        self.send_btn.grid(row=3, column=0, columnspan=4, padx=5, pady=5)
    
    def update_command_list(self, event=None):
        self.command_listbox.delete(0, tk.END)
        emulation = self.emulation_var.get()
        commands_dict = EMULATION_COMMANDS.get(emulation, {})
        for command in sorted(commands_dict.keys()):
            self.command_listbox.insert(tk.END, command)
    
    def send_command(self):
        selection = self.command_listbox.curselection()
        if not selection:
            messagebox.showinfo("Info", "Please select a command to send.")
            return
        command_name = self.command_listbox.get(selection[0])
        emulation = self.emulation_var.get()
        command_value = EMULATION_COMMANDS.get(emulation, {}).get(command_name, None)
        if command_value is None:
            messagebox.showerror("Error", "Selected command not found.")
            return
        if callable(command_value):
            value = simpledialog.askinteger("Input", f"Enter value for '{command_name}' (0-255):", minvalue=0, maxvalue=255)
            if value is None:
                return
            command_bytes = command_value(value)
        else:
            command_bytes = command_value
        if self.debug_mode.get():
            dc = get_debug_console(self.parent)
            debug_str = binascii.hexlify(command_bytes).decode('utf-8')
            dc.log(f"[Control Command] '{command_name}' (hex): {debug_str}")
        printer_ip = self.ip_entry.get()
        try:
            printer_port = int(self.port_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid port number.")
            return
        try:
            with socket.create_connection((printer_ip, printer_port), timeout=5) as printer_socket:
                printer_socket.sendall(command_bytes)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send command: {e}")

# ------------------ Main Application Entry Point ------------------
def main():
    root = tk.Tk()
    app = LiveKeystrokeEditor(root)
    root.mainloop()

if __name__ == '__main__':
    main()
