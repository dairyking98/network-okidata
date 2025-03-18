"""
Live Keystroke Printer – Okidata Only with Integrated Controls, Debug Panel, Mode Selection,
Line Length Display, and Additional Printing Options
------------------------------------------------------------------------------------------------

This program creates a single-window text editor that sends keystrokes to an Okidata printer.
It supports two printing modes:
  • Live mode: Each keystroke is sent immediately.
  • Line-by-Line mode (default): Text is printed only when Return is pressed.
    In Line-by-Line mode, when Return is pressed, the sequence is:
      - Carriage Return (CR)
      - Line Feed (LF)
      - A number of Horizontal Tabs (HT) based on the Left Margin spinbox value
      - The entire current line’s text as one command
      - A newline is inserted in the text widget.
Persistent formatting toggles (Italic, Emphasized, Underline Printing) send their command once.
Other integrated controls (character sets, CPI, spacing, print quality, speed, double height, proportional, skip over perforation) behave as before.
**Important:** In the CPI section, a “Double Wide” checkbox is provided. When checked, after the current CPI command is executed, the Double Wide code (ASCII 31, i.e. b"\x1F") is executed; when unchecked, the current CPI code is re-sent.
The effective CPI used for line-length calculations is halved when Double Wide is enabled.
The displayed line length (in inches) is computed as:
      (8 × left_margin_spinbox_value / numeric_CPI) + (char_count / effective_CPI)
where numeric_CPI is parsed from the CPI radio button and effective_CPI is that value halved if Double Wide is enabled.
A new “Zero” section provides radio buttons for “Slashed Zero” and “Unslashed Zero.” When a zero option is selected, its corresponding command is immediately sent.
The Print Quality section now includes a “Utility” option.
A new “Shift In/Out” checkbox in the Manual Commands section sends a Shift In (ASCII 15) or Shift Out (ASCII 14) command when toggled.
Additional Printing Options (Unidirectional Printing and Enhanced Printing) are in their own section.
Manual command buttons are provided for Line Feed, Carriage Return, Form Feed, Horizontal Tab, Backspace, Vertical Tab, Reverse Line Feed, and Reset (Clear Print Buffer).
Debug Mode is on by default, and all command bytes are logged (in decimal) in the integrated debug panel.
"""

import tkinter as tk
from tkinter import messagebox, scrolledtext
import socket

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

# ------------------ Main Application ------------------
class LiveKeystrokeEditor:
    def __init__(self, master):
        self.master = master
        master.title("Okidata Printer – Integrated Controls")
        
        self.debug_mode = tk.BooleanVar(value=True)
        
        # Persistent formatting state variables.
        self.option_italic = tk.BooleanVar(value=False)
        self.option_emphasized = tk.BooleanVar(value=False)
        self.underline_printing = tk.BooleanVar(value=False)
        self.unidirectional = tk.BooleanVar(value=False)
        self.enhanced_state = tk.BooleanVar(value=False)
        
        self.double_height = tk.BooleanVar(value=False)
        self.double_wide = tk.BooleanVar(value=False)  # Controls if double wide is enabled.
        self.proportional = tk.BooleanVar(value=False)
        
        self.cpi_var = tk.StringVar(value=DEFAULT_CONFIG["DEFAULT_CPI"])
        self.font_var = tk.StringVar(value="Block Graphic Set")
        self.spacing_var = tk.StringVar(value="1/6")
        self.spacing_n = tk.IntVar(value=9)
        self.quality_var = tk.StringVar(value="HSD/SSD")
        self.speed_var = tk.StringVar(value="Full")
        self.skip_perforation = tk.IntVar(value=DEFAULT_CONFIG["DEFAULT_SKIP_PERFORATION"])
        self.left_margin_count = tk.IntVar(value=DEFAULT_CONFIG["DEFAULT_LEFT_MARGIN"])
        
        self.mode_var = tk.StringVar(value="Line-by-Line")
        self.right_margin_var = tk.DoubleVar(value=7.5)
        
        # New: Zero section variable.
        self.zero_mode = tk.StringVar(value="Slashed Zero")
        
        # New: Shift state variable.
        self.shift_state = tk.BooleanVar(value=False)
        
        self.paned = tk.PanedWindow(master, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)
        
        self.main_frame = tk.Frame(self.paned)
        self.text = tk.Text(self.main_frame, wrap="word", undo=True)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar = tk.Scrollbar(self.main_frame, command=self.text.yview)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.config(yscrollcommand=self.scrollbar.set)
        self.text.bind("<KeyPress>", self.handle_key)
        self.text.bind("<KeyPress-Return>", self.handle_return)
        self.text.bind("<KeyRelease>", self.update_line_length_display)
        self.paned.add(self.main_frame, stretch="always")
        
        self.debug_frame = tk.Frame(self.paned)
        self.debug_text = scrolledtext.ScrolledText(self.debug_frame, wrap="word", state=tk.DISABLED, width=30)
        self.debug_text.pack(fill=tk.BOTH, expand=True)
        self.paned.add(self.debug_frame)
        
        self.control_frame = tk.Frame(master)
        self.control_frame.pack(fill=tk.X)
        
        self.ip_label = tk.Label(self.control_frame, text="Printer IP:")
        self.ip_label.grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.ip_entry = tk.Entry(self.control_frame, width=15)
        self.ip_entry.insert(0, DEFAULT_CONFIG["PRINTER_IP"])
        self.ip_entry.grid(row=0, column=1, padx=5, pady=2, sticky="w")
        self.port_label = tk.Label(self.control_frame, text="Port:")
        self.port_label.grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.port_entry = tk.Entry(self.control_frame, width=5)
        self.port_entry.insert(0, str(DEFAULT_CONFIG["PRINTER_PORT"]))
        self.port_entry.grid(row=0, column=3, padx=5, pady=2, sticky="w")
        self.debug_checkbox = tk.Checkbutton(self.control_frame, text="Debug Mode", variable=self.debug_mode)
        self.debug_checkbox.grid(row=0, column=4, padx=5, pady=2)
        
        self.mode_frame = tk.LabelFrame(self.control_frame, text="Mode")
        self.mode_frame.grid(row=0, column=5, padx=5, pady=2)
        self.mode_rb_live = tk.Radiobutton(self.mode_frame, text="Live", variable=self.mode_var, value="Live")
        self.mode_rb_live.pack(side=tk.LEFT, padx=2, pady=2)
        self.mode_rb_line = tk.Radiobutton(self.mode_frame, text="Line-by-Line", variable=self.mode_var, value="Line-by-Line")
        self.mode_rb_line.pack(side=tk.LEFT, padx=2, pady=2)
        
        self.italic_checkbox = tk.Checkbutton(self.control_frame, text="Italic", variable=self.option_italic, command=self.toggle_italic)
        self.italic_checkbox.grid(row=1, column=0, padx=5, pady=2)
        self.emph_checkbox = tk.Checkbutton(self.control_frame, text="Emphasized", variable=self.option_emphasized, command=self.toggle_emphasized)
        self.emph_checkbox.grid(row=1, column=1, padx=5, pady=2)
        self.underline_checkbox = tk.Checkbutton(self.control_frame, text="Underline Printing", variable=self.underline_printing, command=self.apply_underline)
        self.underline_checkbox.grid(row=1, column=2, padx=5, pady=2)
        
        self.add_options_frame = tk.LabelFrame(self.control_frame, text="Additional Printing Options")
        self.add_options_frame.grid(row=1, column=3, columnspan=2, padx=5, pady=2)
        self.unidir_checkbox = tk.Checkbutton(self.add_options_frame, text="Unidirectional Printing", variable=self.unidirectional, command=self.apply_unidirectional)
        self.unidir_checkbox.pack(side=tk.LEFT, padx=2, pady=2)
        self.enhanced_checkbox = tk.Checkbutton(self.add_options_frame, text="Enhanced Printing", variable=tk.BooleanVar(value=False), command=self.toggle_enhanced)
        self.enhanced_checkbox.config(variable=self.enhanced_state)
        self.enhanced_checkbox.pack(side=tk.LEFT, padx=2, pady=2)
        
        self.dheight_checkbox = tk.Checkbutton(self.control_frame, text="Double Height", variable=self.double_height, command=self.apply_double_height)
        self.dheight_checkbox.grid(row=2, column=0, padx=5, pady=2)
        self.proportional_checkbox = tk.Checkbutton(self.control_frame, text="Proportional", variable=self.proportional, command=self.apply_proportional)
        self.proportional_checkbox.grid(row=2, column=1, padx=5, pady=2)
        
        self.cpi_frame = tk.LabelFrame(self.control_frame, text="CPI")
        self.cpi_frame.grid(row=3, column=2, columnspan=2, padx=5, pady=2, sticky="w")
        self.cpi_rb1 = tk.Radiobutton(self.cpi_frame, text="10 cpi", variable=self.cpi_var, value="10 cpi", command=self.apply_cpi)
        self.cpi_rb1.pack(side=tk.LEFT, padx=2, pady=2)
        self.cpi_rb2 = tk.Radiobutton(self.cpi_frame, text="12 cpi", variable=self.cpi_var, value="12 cpi", command=self.apply_cpi)
        self.cpi_rb2.pack(side=tk.LEFT, padx=2, pady=2)
        self.cpi_rb3 = tk.Radiobutton(self.cpi_frame, text="15 cpi", variable=self.cpi_var, value="15 cpi", command=self.apply_cpi)
        self.cpi_rb3.pack(side=tk.LEFT, padx=2, pady=2)
        self.cpi_rb4 = tk.Radiobutton(self.cpi_frame, text="17.1 cpi", variable=self.cpi_var, value="17.1 cpi", command=self.apply_cpi)
        self.cpi_rb4.pack(side=tk.LEFT, padx=2, pady=2)
        self.cpi_rb5 = tk.Radiobutton(self.cpi_frame, text="20 cpi", variable=self.cpi_var, value="20 cpi", command=self.apply_cpi)
        self.cpi_rb5.pack(side=tk.LEFT, padx=2, pady=2)
        self.double_wide_checkbox = tk.Checkbutton(self.cpi_frame, text="Double Wide", variable=self.double_wide, command=self.toggle_double_wide)
        self.double_wide_checkbox.pack(side=tk.LEFT, padx=10, pady=2)
        
        self.zero_frame = tk.LabelFrame(self.control_frame, text="Zero")
        self.zero_frame.grid(row=3, column=4, padx=5, pady=2, sticky="w")
        self.zero_mode = tk.StringVar(value="Slashed Zero")
        self.zero_rb1 = tk.Radiobutton(self.zero_frame, text="Slashed Zero", variable=self.zero_mode, value="Slashed Zero", command=self.apply_zero)
        self.zero_rb1.pack(side=tk.LEFT, padx=2, pady=2)
        self.zero_rb2 = tk.Radiobutton(self.zero_frame, text="Unslashed Zero", variable=self.zero_mode, value="Unslashed Zero", command=self.apply_zero)
        self.zero_rb2.pack(side=tk.LEFT, padx=2, pady=2)
        
        self.font_frame = tk.LabelFrame(self.control_frame, text="Character Sets")
        self.font_frame.grid(row=3, column=0, columnspan=2, padx=5, pady=2, sticky="w")
        self.font_rb1 = tk.Radiobutton(self.font_frame, text="Block Graphic", variable=self.font_var, value="Block Graphic Set", command=self.apply_font)
        self.font_rb1.pack(side=tk.LEFT, padx=2, pady=2)
        self.font_rb2 = tk.Radiobutton(self.font_frame, text="Publisher", variable=self.font_var, value="Publisher Set", command=self.apply_font)
        self.font_rb2.pack(side=tk.LEFT, padx=2, pady=2)
        self.font_rb3 = tk.Radiobutton(self.font_frame, text="Line Graphics", variable=self.font_var, value="Line Graphics Set", command=self.apply_font)
        self.font_rb3.pack(side=tk.LEFT, padx=2, pady=2)
        self.font_rb4 = tk.Radiobutton(self.font_frame, text="Standard", variable=self.font_var, value="Standard Character Set", command=self.apply_font)
        self.font_rb4.pack(side=tk.LEFT, padx=2, pady=2)
        
        self.spacing_frame = tk.LabelFrame(self.control_frame, text="Spacing")
        self.spacing_frame.grid(row=4, column=0, columnspan=2, padx=5, pady=2, sticky="w")
        self.spacing_rb1 = tk.Radiobutton(self.spacing_frame, text="1/6", variable=self.spacing_var, value="1/6", command=self.apply_spacing)
        self.spacing_rb1.pack(side=tk.LEFT, padx=2, pady=2)
        self.spacing_rb2 = tk.Radiobutton(self.spacing_frame, text="1/8", variable=self.spacing_var, value="1/8", command=self.apply_spacing)
        self.spacing_rb2.pack(side=tk.LEFT, padx=2, pady=2)
        self.spacing_rb3 = tk.Radiobutton(self.spacing_frame, text="n/144", variable=self.spacing_var, value="n/144", command=self.apply_spacing)
        self.spacing_rb3.pack(side=tk.LEFT, padx=2, pady=2)
        self.spacing_n_entry = tk.Entry(self.spacing_frame, width=4, textvariable=self.spacing_n)
        self.spacing_n_entry.pack(side=tk.LEFT, padx=2, pady=2)
        
        self.quality_frame = tk.LabelFrame(self.control_frame, text="Print Quality")
        self.quality_frame.grid(row=4, column=2, columnspan=2, padx=5, pady=2, sticky="w")
        self.quality_rb1 = tk.Radiobutton(self.quality_frame, text="HSD/SSD", variable=self.quality_var, value="HSD/SSD", command=self.apply_quality)
        self.quality_rb1.pack(side=tk.LEFT, padx=2, pady=2)
        self.quality_rb2 = tk.Radiobutton(self.quality_frame, text="NLQ Courier", variable=self.quality_var, value="NLQ Courier", command=self.apply_quality)
        self.quality_rb2.pack(side=tk.LEFT, padx=2, pady=2)
        self.quality_rb3 = tk.Radiobutton(self.quality_frame, text="NLQ Gothic", variable=self.quality_var, value="NLQ Gothic", command=self.apply_quality)
        self.quality_rb3.pack(side=tk.LEFT, padx=2, pady=2)
        self.quality_rb4 = tk.Radiobutton(self.quality_frame, text="Utility", variable=self.quality_var, value="Utility", command=self.apply_quality)
        self.quality_rb4.pack(side=tk.LEFT, padx=2, pady=2)
        
        self.speed_frame = tk.LabelFrame(self.control_frame, text="Speed")
        self.speed_frame.grid(row=5, column=0, columnspan=2, padx=5, pady=2, sticky="w")
        self.speed_rb1 = tk.Radiobutton(self.speed_frame, text="Full", variable=self.speed_var, value="Full", command=self.apply_speed)
        self.speed_rb1.pack(side=tk.LEFT, padx=2, pady=2)
        self.speed_rb2 = tk.Radiobutton(self.speed_frame, text="Half", variable=self.speed_var, value="Half", command=self.apply_speed)
        self.speed_rb2.pack(side=tk.LEFT, padx=2, pady=2)
        
        self.skip_frame = tk.LabelFrame(self.control_frame, text="Skip Over Perforation")
        self.skip_frame.grid(row=5, column=2, padx=5, pady=2, sticky="w")
        self.skip_spinbox = tk.Spinbox(self.skip_frame, from_=0, to=9, width=3, textvariable=self.skip_perforation, command=self.apply_skip_over_perforation)
        self.skip_spinbox.pack(side=tk.LEFT, padx=2, pady=2)
        
        self.margin_frame = tk.LabelFrame(self.control_frame, text="Left Margin (HT count)")
        self.margin_frame.grid(row=5, column=3, padx=5, pady=2, sticky="w")
        self.margin_spinbox = tk.Spinbox(self.margin_frame, from_=0, to=20, width=3, textvariable=self.left_margin_count)
        self.margin_spinbox.pack(side=tk.LEFT, padx=2, pady=2)
        
        self.right_margin_label = tk.Label(self.control_frame, text="Right Margin (in):")
        self.right_margin_label.grid(row=6, column=3, padx=5, pady=2, sticky="w")
        self.right_margin_entry = tk.Entry(self.control_frame, width=5, textvariable=self.right_margin_var)
        self.right_margin_entry.grid(row=6, column=4, padx=5, pady=2, sticky="w")
        self.line_length_display = tk.Label(self.control_frame, text="Line Length: 0.00 in", width=20, bg="white")
        self.line_length_display.grid(row=6, column=5, padx=5, pady=2, sticky="w")
        
        self.manual_frame = tk.LabelFrame(self.control_frame, text="Manual Commands")
        self.manual_frame.grid(row=7, column=2, columnspan=3, padx=5, pady=2, sticky="w")
        self.btn_lf = tk.Button(self.manual_frame, text="Line Feed", command=lambda: self.send_manual_command("Line Feed"))
        self.btn_lf.pack(side=tk.LEFT, padx=2, pady=2)
        self.btn_cr = tk.Button(self.manual_frame, text="Carriage Return", command=lambda: self.send_manual_command("Carriage Return"))
        self.btn_cr.pack(side=tk.LEFT, padx=2, pady=2)
        self.btn_ff = tk.Button(self.manual_frame, text="Form Feed", command=lambda: self.send_manual_command("Form Feed"))
        self.btn_ff.pack(side=tk.LEFT, padx=2, pady=2)
        self.btn_ht = tk.Button(self.manual_frame, text="Horizontal Tab", command=lambda: self.send_manual_command("Horizontal Tab"))
        self.btn_ht.pack(side=tk.LEFT, padx=2, pady=2)
        self.btn_bs = tk.Button(self.manual_frame, text="Backspace", command=lambda: self.send_manual_command("Backspace"))
        self.btn_bs.pack(side=tk.LEFT, padx=2, pady=2)
        self.btn_vt = tk.Button(self.manual_frame, text="Vertical Tab", command=lambda: self.send_manual_command("Vertical Tab"))
        self.btn_vt.pack(side=tk.LEFT, padx=2, pady=2)
        self.btn_rlf = tk.Button(self.manual_frame, text="Reverse Line Feed", command=lambda: self.send_manual_command("Reverse Line Feed"))
        self.btn_rlf.pack(side=tk.LEFT, padx=2, pady=2)
        self.btn_reset = tk.Button(self.manual_frame, text="Reset (Clear Print Buffer)", command=lambda: self.send_manual_command("Reset (Clear Print Buffer)"))
        self.btn_reset.pack(side=tk.LEFT, padx=2, pady=2)
        self.shift_checkbox = tk.Checkbutton(self.manual_frame, text="Shift In/Out", variable=self.shift_state, command=self.send_shift)
        self.shift_checkbox.pack(side=tk.LEFT, padx=2, pady=2)
        
        self.status_label = tk.Label(self.control_frame, text="Live keystrokes are being sent.")
        self.status_label.grid(row=8, column=0, columnspan=2, padx=5, pady=2, sticky="w")
        self.restore_btn = tk.Button(self.control_frame, text="Send Defaults", command=self.send_all_defaults)
        self.restore_btn.grid(row=8, column=2, padx=5, pady=2, sticky="w")
        
        self.master.after(500, self.send_all_defaults)
    
    def send_manual_command(self, cmd_name):
        command = OKIDATA_COMMANDS.get(cmd_name, b"")
        if command:
            self.send_live_command(command)
    
    def send_shift(self):
        if self.shift_state.get():
            command = OKIDATA_COMMANDS.get("Shift In", b"")
            tag = "[Shift In]"
        else:
            command = OKIDATA_COMMANDS.get("Shift Out", b"")
            tag = "[Shift Out]"
        if command:
            self.send_live_command(command)
    
    def send_command_immediately(self, command_bytes, tag=""):
        dec_str = " ".join(str(b) for b in command_bytes)
        if self.debug_mode.get():
            self.debug_text.config(state=tk.NORMAL)
            self.debug_text.insert(tk.END, f"{tag} {dec_str}\n")
            self.debug_text.config(state=tk.DISABLED)
            self.debug_text.see(tk.END)
        printer_ip = self.ip_entry.get()
        try:
            printer_port = int(self.port_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid port number.")
            return
        try:
            with socket.create_connection((printer_ip, printer_port), timeout=5) as s:
                s.sendall(command_bytes)
        except Exception as e:
            self.debug_text.config(state=tk.NORMAL)
            self.debug_text.insert(tk.END, f"{tag} Error: {e}\n")
            self.debug_text.config(state=tk.DISABLED)
            self.debug_text.see(tk.END)
    
    def send_all_defaults(self):
        self.restore_defaults()
        self.apply_font()
        self.apply_cpi()
        self.apply_spacing()
        self.apply_quality()
        self.apply_speed()
        self.apply_double_height()
        self.apply_proportional()
        self.apply_skip_over_perforation()
    
    def restore_defaults(self):
        commands = OKIDATA_COMMANDS
        printer_ip = self.ip_entry.get()
        try:
            printer_port = int(self.port_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid port number.")
            return
        reset_cmd = commands.get("Reset (Clear Print Buffer)", b"")
        cpi_cmd = commands.get(f"Select {self.cpi_var.get()}", b"")
        skip_val = self.skip_perforation.get()
        skip_cmd = commands.get("Skip Over Perforation", lambda n: b"")(skip_val)
        full_cmd = reset_cmd + cpi_cmd + skip_cmd
        if self.debug_mode.get():
            dec_str = " ".join(str(b) for b in full_cmd)
            self.debug_text.config(state=tk.NORMAL)
            self.debug_text.insert(tk.END, f"[Restore Defaults] {dec_str}\n")
            self.debug_text.config(state=tk.DISABLED)
            self.debug_text.see(tk.END)
        try:
            with socket.create_connection((printer_ip, printer_port), timeout=5) as s:
                s.sendall(full_cmd)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send default commands: {e}")
    
    def apply_font(self):
        font = self.font_var.get()
        command = b""
        if font == "Block Graphic Set":
            command = OKIDATA_COMMANDS.get("Block Graphic Set", b"")
        elif font == "Publisher Set":
            command = OKIDATA_COMMANDS.get("Publisher Set", b"")
        elif font == "Line Graphics Set":
            command = OKIDATA_COMMANDS.get("Line Graphics Set", b"")
        elif font == "Standard Character Set":
            command = OKIDATA_COMMANDS.get("Standard Character Set", b"")
        if command:
            self.send_command_immediately(command, "[Character Set]")
    
    def apply_cpi(self):
        if self.cpi_var.get() != "Double Wide":
            key = f"Select {self.cpi_var.get()}"
            command = OKIDATA_COMMANDS.get(key, b"")
            if command:
                self.send_command_immediately(command, "[CPI]")
        # Double wide is controlled by the checkbox.
    
    def apply_spacing(self):
        spacing = self.spacing_var.get()
        command = b""
        if spacing == "1/6":
            command = OKIDATA_COMMANDS.get("Set Spacing to 1/6\"", b"")
        elif spacing == "1/8":
            command = OKIDATA_COMMANDS.get("Set Spacing to 1/8\"", b"")
        elif spacing == "n/144":
            n_val = self.spacing_n.get()
            command = OKIDATA_COMMANDS.get("Set Spacing to n/144", lambda n: b"")(n_val)
        if command:
            self.send_command_immediately(command, "[Spacing]")
    
    def apply_quality(self):
        quality = self.quality_var.get()
        command = b""
        if quality == "HSD/SSD":
            command = OKIDATA_COMMANDS.get("Print Quality Select HSD/SSD", b"")
        elif quality == "NLQ Courier":
            command = OKIDATA_COMMANDS.get("Select NLQ Courier", b"")
        elif quality == "NLQ Gothic":
            command = OKIDATA_COMMANDS.get("Select NLQ Gothic", b"")
        elif quality == "Utility":
            command = OKIDATA_COMMANDS.get("Select Utility", b"")
        if command:
            self.send_command_immediately(command, "[Quality]")
    
    def apply_speed(self):
        speed = self.speed_var.get()
        command = b""
        if speed == "Full":
            command = OKIDATA_COMMANDS.get("Print Speed Set to Full", b"")
        elif speed == "Half":
            command = OKIDATA_COMMANDS.get("Print Speed Set to Half", b"")
        if command:
            self.send_command_immediately(command, "[Speed]")
    
    def apply_double_height(self):
        command = b""
        if self.double_height.get():
            command = OKIDATA_COMMANDS.get("Double Height On", b"")
        else:
            command = OKIDATA_COMMANDS.get("Double Height Off", b"")
        if command:
            self.send_command_immediately(command, "[Double Height]")
    
    def apply_proportional(self):
        command = b""
        if self.proportional.get():
            command = OKIDATA_COMMANDS.get("Proportional Printing On", b"")
        else:
            command = OKIDATA_COMMANDS.get("Proportional Printing Off", b"")
        if command:
            self.send_command_immediately(command, "[Proportional]")
    
    def apply_skip_over_perforation(self):
        value = self.skip_perforation.get()
        command = OKIDATA_COMMANDS.get("Skip Over Perforation", lambda n: b"")(value)
        self.send_command_immediately(command, "[Skip Over Perforation]")
    
    def apply_underline(self):
        if self.underline_printing.get():
            command = OKIDATA_COMMANDS.get("Underline Printing On", b"")
        else:
            command = OKIDATA_COMMANDS.get("Underline Printing Off", b"")
        if command:
            self.send_command_immediately(command, "[Underline Printing]")
    
    def apply_unidirectional(self):
        if self.unidirectional.get():
            command = OKIDATA_COMMANDS.get("Unidirectional Printing On", b"")
        else:
            command = OKIDATA_COMMANDS.get("Unidirectional Printing Off", b"")
        if command:
            self.send_command_immediately(command, "[Unidirectional Printing]")
    
    def toggle_italic(self):
        if self.option_italic.get():
            command = b"\x1B\x21\x2F"
        else:
            command = b"\x1B\x21\x2A"
        if command:
            self.send_command_immediately(command, "[Italic]")
    
    def toggle_emphasized(self):
        if self.option_emphasized.get():
            command = OKIDATA_COMMANDS.get("Emphasized Printing On", b"")
        else:
            command = OKIDATA_COMMANDS.get("Emphasized Printing Off", b"")
        if command:
            self.send_command_immediately(command, "[Emphasized]")
    
    def toggle_enhanced(self):
        if self.enhanced_state.get():
            command = OKIDATA_COMMANDS.get("Enhanced Printing On", b"")
        else:
            command = OKIDATA_COMMANDS.get("Enhanced Printing Off", b"")
        if command:
            self.send_command_immediately(command, "[Enhanced Printing]")
    
    def toggle_double_wide(self):
        if self.double_wide.get():
            command = OKIDATA_COMMANDS.get("Double Width On", b"")
            if command:
                self.send_command_immediately(command, "[Double Wide ON]")
        else:
            self.apply_cpi()
        self.update_line_length_display()
    
    def apply_zero(self):
        if self.zero_mode.get() == "Slashed Zero":
            command = OKIDATA_COMMANDS.get("Slashed Zero", b"")
            tag = "[Slashed Zero]"
        else:
            command = OKIDATA_COMMANDS.get("Unslashed Zero", b"")
            tag = "[Unslashed Zero]"
        if command:
            self.send_command_immediately(command, tag)
    
    def send_live_command(self, command_bytes):
        dec_str = " ".join(str(b) for b in command_bytes)
        if self.debug_mode.get():
            self.debug_text.config(state=tk.NORMAL)
            self.debug_text.insert(tk.END, f"[Live Keystroke] {dec_str}\n")
            self.debug_text.config(state=tk.DISABLED)
            self.debug_text.see(tk.END)
        printer_ip = self.ip_entry.get()
        try:
            printer_port = int(self.port_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid port number.")
            return
        try:
            with socket.create_connection((printer_ip, printer_port), timeout=5) as s:
                s.sendall(command_bytes)
        except Exception as e:
            self.debug_text.config(state=tk.NORMAL)
            self.debug_text.insert(tk.END, f"[Live Keystroke] Error: {e}\n")
            self.debug_text.config(state=tk.DISABLED)
            self.debug_text.see(tk.END)
    
    def handle_key(self, event):
        if event.keysym == "Return":
            return
        if self.mode_var.get() == "Live":
            command = b""
            if event.keysym == "Tab":
                command = OKIDATA_COMMANDS.get("Horizontal Tab", b"\t")
            elif event.keysym == "BackSpace":
                command = OKIDATA_COMMANDS.get("Backspace", b"\x08")
            else:
                if event.char and ord(event.char) >= 32:
                    command = event.char.encode('utf-8')
            if command:
                self.send_live_command(command)
        else:
            return
    
    def handle_return(self, event):
        commands = OKIDATA_COMMANDS
        if self.mode_var.get() == "Line-by-Line":
            line_text = self.text.get("insert linestart", "insert lineend")
            cr = commands.get("Carriage Return", b"\r")
            lf = commands.get("Line Feed", b"\n")
            self.send_live_command(cr)
            self.master.after(10, lambda: self.send_live_command(lf))
            self.master.after(20, self.send_left_margin)
            self.master.after(30, lambda: self.send_live_command(line_text.encode('utf-8')))
            self.text.insert("insert", "\n")
            self.update_line_length_display()
            return None
        else:
            cr = commands.get("Carriage Return", b"\r")
            lf = commands.get("Line Feed", b"\n")
            self.send_live_command(cr)
            self.master.after(10, lambda: self.send_live_command(lf))
            self.master.after(20, self.send_left_margin)
            self.update_line_length_display()
            return None
    
    def send_left_margin(self):
        count = self.left_margin_count.get()
        for _ in range(count):
            self.send_live_command(OKIDATA_COMMANDS.get("Horizontal Tab", b"\t"))
    
    def update_line_length_display(self, event=None):
        line_text = self.text.get("insert linestart", "insert lineend")
        char_count = len(line_text)
        try:
            numeric_cpi = float(self.cpi_var.get().split()[0])
        except:
            numeric_cpi = 10.0
        if self.double_wide.get():
            effective_cpi = numeric_cpi / 2.0
        else:
            effective_cpi = numeric_cpi
        try:
            line_length = ((8.0 * self.left_margin_count.get()) / numeric_cpi) + (char_count / effective_cpi)
        except ZeroDivisionError:
            line_length = 0.0
        self.line_length_display.config(text=f"Line Length: {line_length:.2f} in")
        try:
            right_margin = float(self.right_margin_var.get())
        except:
            right_margin = 7.5
        gap = right_margin - line_length
        if gap >= 0.5:
            color = "green"
        elif 0 <= gap < 0.5:
            color = "yellow"
        else:
            color = "red"
        self.line_length_display.config(bg=color)

def main():
    root = tk.Tk()
    app = LiveKeystrokeEditor(root)
    root.mainloop()

if __name__ == '__main__':
    main()
