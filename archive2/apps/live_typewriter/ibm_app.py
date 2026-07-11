import tkinter as tk
from tkinter import messagebox, scrolledtext
import socket

# ------------------ Default Configuration ------------------
DEFAULT_CONFIG = {
    "PRINTER_IP": "192.168.4.28",
    "PRINTER_PORT": 9100,
    "DEFAULT_CPI": "10 cpi",  # Options: "10 cpi", "12 cpi", "15 cpi", "Condensed"
    "DEFAULT_LEFT_MARGIN": 0
}

# ------------------ IBM Command Dictionary ------------------
IBM_COMMANDS = {
    "Backspace": b"\x08",                          # BS (8)
    "Carriage Return": b"\x0D",                    # CR (13)
    "Select 10 cpi": b"\x12",                      # DC2 (18)
    "Select 12 cpi": b"\x1B\x3A",                  # ESC : (27 58)
    "Select 15 cpi": b"\x1B\x67",                  # ESC g (27 103)
    "Select Condensed Print": b"\x1B\x0F",         # ESC SI (27 15)
    "IBM Set I": b"\x1B\x37",                      # ESC 7 (27 55)
    "IBM Set II": b"\x1B\x36",                     # ESC 6 (27 54)
    "Publisher Set": b"\x1B\x21\x5A",              # ESC ! Z (27 33 90)
    "Slashed Zero": b"\x1B\x21\x40",               # ESC ! @ (27 33 64)
    "Unslashed Zero": b"\x1B\x21\x41",             # ESC ! A (27 33 65)
    "Double Width On": b"\x1B\x57\x31",            # ESC W 1 (27 87 49)
    "Double Width Off": b"\x1B\x57\x30",           # ESC W 0 (27 87 48)
    "Emphasized Printing On": b"\x1B\x45",         # ESC E (27 69)
    "Emphasized Printing Off": b"\x1B\x46",        # ESC F (27 70)
    "Enhanced Printing On": b"\x1B\x47",           # ESC G (27 71)
    "Enhanced Printing Off": b"\x1B\x48",          # ESC H (27 72)
    "Form Feed": b"\x0C",                          # FF (12)
    "Horizontal Tab": b"\x09",                     # HT (9)
    "Italics On": b"\x1B\x25\x47",                 # ESC % G (27 37 71)
    "Italics Off": b"\x1B\x25\x48",                # ESC % H (27 37 72)
    "Line Feed": b"\x0A",                          # LF (10)
    "Reverse Line Feed": b"\x1B\x4A",              # ESC J (27 74)
    "Line Spacing 1/8": b"\x1B\x30",               # ESC 0 (27 48)
    "Line Spacing 7/72": b"\x1B\x31",              # ESC 1 (27 49)
    "Set Spacing to n/72": lambda n: b"\x1B\x41" + bytes([n]),      # ESC A n (27 65 n)
    "Store Spacing Set": b"\x1B\x32",              # ESC 2 (27 50)
    "Set Spacing to n/144": lambda n: b"\x1B\x25\x39" + bytes([n]), # ESC % 9 n (27 37 57 n)
    "Set Spacing to n/216": lambda n: b"\x1B\x33" + bytes([n]),     # ESC 3 n (27 51 n)
    "Overscore On": b"\x1B\x5F\x31",               # ESC _ 1 (27 95 49)
    "Overscore Off": b"\x1B\x5F\x30",              # ESC _ 0 (27 95 48)
    "Paper Out Sensor Off": b"\x1B\x38",           # ESC 8 (27 56)
    "Paper Out Sensor On": b"\x1B\x39",            # ESC 9 (27 57)
    "Print Suppress On": b"\x13",                  # DC3 (19)
    "Print Suppress Off": b"\x11",                 # DC1 (17)
    "Proportional Spacing On": b"\x1B\x50\x31",    # ESC P 1 (27 80 49)
    "Proportional Spacing Off": b"\x1B\x50\x30",   # ESC P 0 (27 80 48)
    "Reset (Clear Print Buffer)": b"\x18",         # CAN (24)
    "Vertical Tab": b"\x0B",                       # VT (11)
    "Underline On": b"\x1B\x2D\x01",               # ESC - 1
    "Underline Off": b"\x1B\x2D\x00",              # ESC - 0
    "Superscript On": b"\x1B\x73\x01",             # (Custom guess)
    "Superscript Off": b"\x1B\x73\x00",            # (Custom guess)
    "Subscript On": b"\x1B\x73\x02",               # (Custom guess)
    "Subscript Off": b"\x1B\x73\x00"               # (Custom guess; same as turning off superscript)
}

# ------------------ Main Application ------------------
class LiveKeystrokeEditor:
    def __init__(self, master):
        self.master = master
        master.title("IBM Printer – Integrated Controls")
        
        # Use the full IBM command set.
        self.commands = IBM_COMMANDS
        
        # Persistent socket connection
        self.sock = None
        
        # Debug mode for logging sent command bytes.
        self.debug_mode = tk.BooleanVar(value=True)
        
        # Persistent formatting state variables.
        self.option_italic = tk.BooleanVar(value=False)
        self.option_emphasized = tk.BooleanVar(value=False)
        self.option_enhanced = tk.BooleanVar(value=False)
        self.double_wide = tk.BooleanVar(value=False)
        
        # Additional formatting toggles.
        self.option_underline = tk.BooleanVar(value=False)
        self.option_overscore = tk.BooleanVar(value=False)
        self.option_proportional = tk.BooleanVar(value=False)
        # Script mode: Normal, Superscript, or Subscript.
        self.script_mode = tk.StringVar(value="Normal")
        
        # CPI: Options: "10 cpi", "12 cpi", "15 cpi", "Condensed"
        self.cpi_var = tk.StringVar(value=DEFAULT_CONFIG["DEFAULT_CPI"])
        # Font selection: Options: "IBM Set I", "IBM Set II", "Publisher Set"
        self.font_var = tk.StringVar(value="IBM Set I")
        # Spacing options.
        self.spacing_var = tk.StringVar(value="1/8")
        self.spacing_n = tk.IntVar(value=9)
        
        self.left_margin_count = tk.IntVar(value=DEFAULT_CONFIG["DEFAULT_LEFT_MARGIN"])
        self.mode_var = tk.StringVar(value="Line-by-Line")
        self.right_margin_var = tk.DoubleVar(value=7.5)
        
        # Zero option.
        self.zero_mode = tk.StringVar(value="Slashed Zero")
        
        # ------------------ Paned Window and Text/Debug ------------------
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
        
        # ------------------ Control Frame ------------------
        self.control_frame = tk.Frame(master)
        self.control_frame.pack(fill=tk.X)
        
        # Printer connection controls.
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
        
        # Mode selection.
        self.mode_frame = tk.LabelFrame(self.control_frame, text="Mode")
        self.mode_frame.grid(row=0, column=5, padx=5, pady=2)
        self.mode_rb_live = tk.Radiobutton(self.mode_frame, text="Live", variable=self.mode_var, value="Live")
        self.mode_rb_live.pack(side=tk.LEFT, padx=2, pady=2)
        self.mode_rb_line = tk.Radiobutton(self.mode_frame, text="Line-by-Line", variable=self.mode_var, value="Line-by-Line")
        self.mode_rb_line.pack(side=tk.LEFT, padx=2, pady=2)
        
        # Formatting toggles.
        self.italic_checkbox = tk.Checkbutton(self.control_frame, text="Italics", variable=self.option_italic, command=self.toggle_italic)
        self.italic_checkbox.grid(row=1, column=0, padx=5, pady=2)
        self.emph_checkbox = tk.Checkbutton(self.control_frame, text="Emphasized", variable=self.option_emphasized, command=self.toggle_emphasized)
        self.emph_checkbox.grid(row=1, column=1, padx=5, pady=2)
        self.enhanced_checkbox = tk.Checkbutton(self.control_frame, text="Enhanced", variable=self.option_enhanced, command=self.toggle_enhanced)
        self.enhanced_checkbox.grid(row=1, column=2, padx=5, pady=2)
        self.double_wide_checkbox = tk.Checkbutton(self.control_frame, text="Double Wide", variable=self.double_wide, command=self.toggle_double_wide)
        self.double_wide_checkbox.grid(row=1, column=3, padx=5, pady=2)
        
        # Extra formatting options.
        self.extra_format_frame = tk.LabelFrame(self.control_frame, text="Extra Formatting")
        self.extra_format_frame.grid(row=2, column=0, columnspan=6, padx=5, pady=2, sticky="w")
        self.underline_checkbox = tk.Checkbutton(self.extra_format_frame, text="Underline", variable=self.option_underline, command=self.toggle_underline)
        self.underline_checkbox.pack(side=tk.LEFT, padx=2, pady=2)
        self.overscore_checkbox = tk.Checkbutton(self.extra_format_frame, text="Overscore", variable=self.option_overscore, command=self.toggle_overscore)
        self.overscore_checkbox.pack(side=tk.LEFT, padx=2, pady=2)
        self.proportional_checkbox = tk.Checkbutton(self.extra_format_frame, text="Proportional", variable=self.option_proportional, command=self.toggle_proportional)
        self.proportional_checkbox.pack(side=tk.LEFT, padx=2, pady=2)
        tk.Label(self.extra_format_frame, text="Script:").pack(side=tk.LEFT, padx=5)
        self.script_normal_rb = tk.Radiobutton(self.extra_format_frame, text="Normal", variable=self.script_mode, value="Normal", command=self.apply_script)
        self.script_normal_rb.pack(side=tk.LEFT, padx=2)
        self.script_super_rb = tk.Radiobutton(self.extra_format_frame, text="Superscript", variable=self.script_mode, value="Superscript", command=self.apply_script)
        self.script_super_rb.pack(side=tk.LEFT, padx=2)
        self.script_sub_rb = tk.Radiobutton(self.extra_format_frame, text="Subscript", variable=self.script_mode, value="Subscript", command=self.apply_script)
        self.script_sub_rb.pack(side=tk.LEFT, padx=2)
        
        # Font selection.
        self.font_frame = tk.LabelFrame(self.control_frame, text="Character Sets")
        self.font_frame.grid(row=3, column=0, columnspan=2, padx=5, pady=2, sticky="w")
        self.font_rb1 = tk.Radiobutton(self.font_frame, text="IBM Set I", variable=self.font_var, value="IBM Set I", command=self.apply_font)
        self.font_rb1.pack(side=tk.LEFT, padx=2, pady=2)
        self.font_rb2 = tk.Radiobutton(self.font_frame, text="IBM Set II", variable=self.font_var, value="IBM Set II", command=self.apply_font)
        self.font_rb2.pack(side=tk.LEFT, padx=2, pady=2)
        self.font_rb3 = tk.Radiobutton(self.font_frame, text="Publisher", variable=self.font_var, value="Publisher Set", command=self.apply_font)
        self.font_rb3.pack(side=tk.LEFT, padx=2, pady=2)
        
        # CPI selection.
        self.cpi_frame = tk.LabelFrame(self.control_frame, text="CPI")
        self.cpi_frame.grid(row=3, column=2, columnspan=2, padx=5, pady=2, sticky="w")
        self.cpi_rb1 = tk.Radiobutton(self.cpi_frame, text="10 cpi", variable=self.cpi_var, value="10 cpi", command=self.apply_cpi)
        self.cpi_rb1.pack(side=tk.LEFT, padx=2, pady=2)
        self.cpi_rb2 = tk.Radiobutton(self.cpi_frame, text="12 cpi", variable=self.cpi_var, value="12 cpi", command=self.apply_cpi)
        self.cpi_rb2.pack(side=tk.LEFT, padx=2, pady=2)
        self.cpi_rb3 = tk.Radiobutton(self.cpi_frame, text="15 cpi", variable=self.cpi_var, value="15 cpi", command=self.apply_cpi)
        self.cpi_rb3.pack(side=tk.LEFT, padx=2, pady=2)
        self.cpi_rb4 = tk.Radiobutton(self.cpi_frame, text="Condensed", variable=self.cpi_var, value="Condensed", command=self.apply_cpi)
        self.cpi_rb4.pack(side=tk.LEFT, padx=2, pady=2)
        
        # Zero selection.
        self.zero_frame = tk.LabelFrame(self.control_frame, text="Zero")
        self.zero_frame.grid(row=3, column=4, padx=5, pady=2, sticky="w")
        self.zero_rb1 = tk.Radiobutton(self.zero_frame, text="Slashed Zero", variable=self.zero_mode, value="Slashed Zero", command=self.apply_zero)
        self.zero_rb1.pack(side=tk.LEFT, padx=2, pady=2)
        self.zero_rb2 = tk.Radiobutton(self.zero_frame, text="Unslashed Zero", variable=self.zero_mode, value="Unslashed Zero", command=self.apply_zero)
        self.zero_rb2.pack(side=tk.LEFT, padx=2, pady=2)
        
        # Spacing options.
        self.spacing_frame = tk.LabelFrame(self.control_frame, text="Spacing")
        self.spacing_frame.grid(row=4, column=0, columnspan=2, padx=5, pady=2, sticky="w")
        self.spacing_rb1 = tk.Radiobutton(self.spacing_frame, text="1/8", variable=self.spacing_var, value="1/8", command=self.apply_spacing)
        self.spacing_rb1.pack(side=tk.LEFT, padx=2, pady=2)
        self.spacing_rb2 = tk.Radiobutton(self.spacing_frame, text="7/72", variable=self.spacing_var, value="7/72", command=self.apply_spacing)
        self.spacing_rb2.pack(side=tk.LEFT, padx=2, pady=2)
        self.spacing_rb3 = tk.Radiobutton(self.spacing_frame, text="n/144", variable=self.spacing_var, value="n/144", command=self.apply_spacing)
        self.spacing_rb3.pack(side=tk.LEFT, padx=2, pady=2)
        self.spacing_rb4 = tk.Radiobutton(self.spacing_frame, text="n/216", variable=self.spacing_var, value="n/216", command=self.apply_spacing)
        self.spacing_rb4.pack(side=tk.LEFT, padx=2, pady=2)
        self.spacing_n_entry = tk.Entry(self.spacing_frame, width=4, textvariable=self.spacing_n)
        self.spacing_n_entry.pack(side=tk.LEFT, padx=2, pady=2)
        
        # Left Margin.
        self.margin_frame = tk.LabelFrame(self.control_frame, text="Left Margin (HT count)")
        self.margin_frame.grid(row=4, column=2, padx=5, pady=2, sticky="w")
        self.margin_spinbox = tk.Spinbox(self.margin_frame, from_=0, to=20, width=3, textvariable=self.left_margin_count)
        self.margin_spinbox.pack(side=tk.LEFT, padx=2, pady=2)
        
        # Right Margin and Line Length Display.
        self.right_margin_label = tk.Label(self.control_frame, text="Right Margin (in):")
        self.right_margin_label.grid(row=5, column=2, padx=5, pady=2, sticky="w")
        self.right_margin_entry = tk.Entry(self.control_frame, width=5, textvariable=self.right_margin_var)
        self.right_margin_entry.grid(row=5, column=3, padx=5, pady=2, sticky="w")
        self.line_length_display = tk.Label(self.control_frame, text="Line Length: 0.00 in", width=20, bg="white")
        self.line_length_display.grid(row=5, column=4, padx=5, pady=2, sticky="w")
        
        # Manual Commands.
        self.manual_frame = tk.LabelFrame(self.control_frame, text="Manual Commands")
        self.manual_frame.grid(row=6, column=0, columnspan=4, padx=5, pady=2, sticky="w")
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
        
        # Status and Restore Defaults.
        self.status_label = tk.Label(self.control_frame, text="Live keystrokes are being sent.")
        self.status_label.grid(row=7, column=0, columnspan=2, padx=5, pady=2, sticky="w")
        self.restore_btn = tk.Button(self.control_frame, text="Send Defaults", command=self.send_all_defaults)
        self.restore_btn.grid(row=7, column=2, padx=5, pady=2, sticky="w")
        
        self.master.after(500, self.send_all_defaults)
        
        # Bind close window event to clean up socket.
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def open_connection(self):
        """Open a persistent socket connection if not already open."""
        if self.sock is not None:
            return self.sock
        printer_ip = self.ip_entry.get()
        try:
            printer_port = int(self.port_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid port number.")
            return None
        try:
            self.sock = socket.create_connection((printer_ip, printer_port), timeout=5)
            if self.debug_mode.get():
                self.debug_text.config(state=tk.NORMAL)
                self.debug_text.insert(tk.END, "[Connection] Connected to printer.\n")
                self.debug_text.config(state=tk.DISABLED)
                self.debug_text.see(tk.END)
            return self.sock
        except Exception as e:
            if self.debug_mode.get():
                self.debug_text.config(state=tk.NORMAL)
                self.debug_text.insert(tk.END, f"[Connection] Error connecting: {e}\n")
                self.debug_text.config(state=tk.DISABLED)
                self.debug_text.see(tk.END)
            return None
    
    def close_connection(self):
        """Close the persistent socket connection."""
        if self.sock is not None:
            try:
                self.sock.close()
                self.sock = None
                if self.debug_mode.get():
                    self.debug_text.config(state=tk.NORMAL)
                    self.debug_text.insert(tk.END, "[Connection] Connection closed.\n")
                    self.debug_text.config(state=tk.DISABLED)
                    self.debug_text.see(tk.END)
            except Exception as e:
                if self.debug_mode.get():
                    self.debug_text.config(state=tk.NORMAL)
                    self.debug_text.insert(tk.END, f"[Connection] Error closing connection: {e}\n")
                    self.debug_text.config(state=tk.DISABLED)
                    self.debug_text.see(tk.END)
    
    def on_closing(self):
        """Handle application close event."""
        self.close_connection()
        self.master.destroy()
    
    def send_manual_command(self, cmd_name):
        command = self.commands.get(cmd_name, b"")
        if command:
            self.send_command_immediately(command)
    
    def send_command_immediately(self, command_bytes, tag=""):
        dec_str = " ".join(str(b) for b in command_bytes)
        if self.debug_mode.get():
            self.debug_text.config(state=tk.NORMAL)
            self.debug_text.insert(tk.END, f"{tag} {dec_str}\n")
            self.debug_text.config(state=tk.DISABLED)
            self.debug_text.see(tk.END)
        sock = self.open_connection()
        if sock:
            try:
                sock.sendall(command_bytes)
            except Exception as e:
                if self.debug_mode.get():
                    self.debug_text.config(state=tk.NORMAL)
                    self.debug_text.insert(tk.END, f"{tag} Error sending command: {e}\n")
                    self.debug_text.config(state=tk.DISABLED)
                    self.debug_text.see(tk.END)
                # If sending fails, close the connection so we can reconnect next time.
                self.close_connection()
    
    def send_all_defaults(self):
        self.restore_defaults()
        self.apply_font()
        self.apply_cpi()
        self.apply_spacing()
        self.toggle_italic()
        self.toggle_emphasized()
        self.toggle_enhanced()
        self.toggle_double_wide()
        self.toggle_underline()
        self.toggle_overscore()
        self.toggle_proportional()
        self.apply_script()
        self.apply_zero()
    
    def restore_defaults(self):
        reset_cmd = self.commands.get("Reset (Clear Print Buffer)", b"")
        cpi_cmd = self.commands.get(f"Select {self.cpi_var.get()}", b"")
        full_cmd = reset_cmd + cpi_cmd
        if self.debug_mode.get():
            dec_str = " ".join(str(b) for b in full_cmd)
            self.debug_text.config(state=tk.NORMAL)
            self.debug_text.insert(tk.END, f"[Restore Defaults] {dec_str}\n")
            self.debug_text.config(state=tk.DISABLED)
            self.debug_text.see(tk.END)
        self.send_command_immediately(full_cmd)
    
    def apply_font(self):
        font = self.font_var.get()
        command = self.commands.get(font, b"")
        if command:
            self.send_command_immediately(command, "[Font]")
    
    def apply_cpi(self):
        value = self.cpi_var.get()
        if value == "Condensed":
            command = self.commands.get("Select Condensed Print", b"")
        else:
            key = f"Select {value}"
            command = self.commands.get(key, b"")
        if command:
            self.send_command_immediately(command, "[CPI]")
    
    def apply_spacing(self):
        spacing = self.spacing_var.get()
        if spacing == "1/8":
            command = self.commands.get("Line Spacing 1/8", b"")
        elif spacing == "7/72":
            command = self.commands.get("Line Spacing 7/72", b"")
        elif spacing == "n/144":
            n_val = self.spacing_n.get()
            command = self.commands.get("Set Spacing to n/144", lambda n: b"")(n_val)
        elif spacing == "n/216":
            n_val = self.spacing_n.get()
            command = self.commands.get("Set Spacing to n/216", lambda n: b"")(n_val)
        else:
            command = b""
        if command:
            self.send_command_immediately(command, "[Spacing]")
    
    def toggle_italic(self):
        if self.option_italic.get():
            command = self.commands.get("Italics On", b"")
            tag = "[Italics On]"
        else:
            command = self.commands.get("Italics Off", b"")
            tag = "[Italics Off]"
        if command:
            self.send_command_immediately(command, tag)
    
    def toggle_emphasized(self):
        if self.option_emphasized.get():
            command = self.commands.get("Emphasized Printing On", b"")
            tag = "[Emphasized On]"
        else:
            command = self.commands.get("Emphasized Printing Off", b"")
            tag = "[Emphasized Off]"
        if command:
            self.send_command_immediately(command, tag)
    
    def toggle_enhanced(self):
        if self.option_enhanced.get():
            command = self.commands.get("Enhanced Printing On", b"")
            tag = "[Enhanced On]"
        else:
            command = self.commands.get("Enhanced Printing Off", b"")
            tag = "[Enhanced Off]"
        if command:
            self.send_command_immediately(command, tag)
    
    def toggle_double_wide(self):
        if self.double_wide.get():
            command = self.commands.get("Double Width On", b"")
            tag = "[Double Wide On]"
        else:
            command = self.commands.get("Double Width Off", b"")
            tag = "[Double Wide Off]"
        if command:
            self.send_command_immediately(command, tag)
        self.update_line_length_display()
    
    def toggle_underline(self):
        if self.option_underline.get():
            command = self.commands.get("Underline On", b"")
            tag = "[Underline On]"
        else:
            command = self.commands.get("Underline Off", b"")
            tag = "[Underline Off]"
        if command:
            self.send_command_immediately(command, tag)
    
    def toggle_overscore(self):
        if self.option_overscore.get():
            command = self.commands.get("Overscore On", b"")
            tag = "[Overscore On]"
        else:
            command = self.commands.get("Overscore Off", b"")
            tag = "[Overscore Off]"
        if command:
            self.send_command_immediately(command, tag)
    
    def toggle_proportional(self):
        if self.option_proportional.get():
            command = self.commands.get("Proportional Spacing On", b"")
            tag = "[Proportional On]"
        else:
            command = self.commands.get("Proportional Spacing Off", b"")
            tag = "[Proportional Off]"
        if command:
            self.send_command_immediately(command, tag)
    
    def apply_script(self):
        mode = self.script_mode.get()
        if mode == "Superscript":
            command = self.commands.get("Superscript On", b"")
            tag = "[Superscript On]"
        elif mode == "Subscript":
            command = self.commands.get("Subscript On", b"")
            tag = "[Subscript On]"
        else:  # Normal mode turns off any script
            command = self.commands.get("Superscript Off", b"")
            tag = "[Script Off]"
        if command:
            self.send_command_immediately(command, tag)
    
    def apply_zero(self):
        if self.zero_mode.get() == "Slashed Zero":
            command = self.commands.get("Slashed Zero", b"")
            tag = "[Slashed Zero]"
        else:
            command = self.commands.get("Unslashed Zero", b"")
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
        self.send_command_immediately(command_bytes)
    
    def handle_key(self, event):
        if event.keysym == "Return":
            return
        if self.mode_var.get() == "Live":
            command = b""
            if event.keysym == "Tab":
                command = self.commands.get("Horizontal Tab", b"\t")
            elif event.keysym == "BackSpace":
                command = self.commands.get("Backspace", b"\x08")
            else:
                if event.char and ord(event.char) >= 32:
                    command = event.char.encode('utf-8')
            if command:
                self.send_live_command(command)
        else:
            return
    
    def handle_return(self, event):
        if self.mode_var.get() == "Line-by-Line":
            # Get the current line's text BEFORE inserting a newline.
            line_text = self.text.get("insert linestart", "insert lineend")
            self.text.insert(tk.INSERT, "\n")
            cr = self.commands.get("Carriage Return", b"\r")
            lf = self.commands.get("Line Feed", b"\n")
            self.send_live_command(cr)
            self.master.after(10, lambda: self.send_live_command(lf))
            self.master.after(20, self.send_left_margin)
            self.master.after(30, lambda: self.send_live_command(line_text.encode('utf-8')))
        else:
            self.text.insert(tk.INSERT, "\n")
            cr = self.commands.get("Carriage Return", b"\r")
            lf = self.commands.get("Line Feed", b"\n")
            self.send_live_command(cr)
            self.master.after(10, lambda: self.send_live_command(lf))
            self.master.after(20, self.send_left_margin)
        self.update_line_length_display()
        return "break"
    
    def send_left_margin(self):
        count = self.left_margin_count.get()
        for _ in range(count):
            self.send_live_command(self.commands.get("Horizontal Tab", b"\t"))
    
    def update_line_length_display(self, event=None):
        line_text = self.text.get("insert linestart", "insert lineend")
        char_count = len(line_text)
        try:
            if self.cpi_var.get() == "Condensed":
                numeric_cpi = 10.0
            else:
                numeric_cpi = float(self.cpi_var.get().split()[0])
        except:
            numeric_cpi = 10.0
        effective_cpi = (numeric_cpi / 2.0) if self.double_wide.get() else numeric_cpi
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
