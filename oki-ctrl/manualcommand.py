import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import socket

# -------------------------------
# Helper for sending binary commands
# -------------------------------
def send_binary_command(byte_array):
    """Send the given list of integer values as binary data via TCP."""
    ip = ip_entry.get().strip()
    try:
        port = int(port_entry.get().strip())
    except ValueError:
        log_debug("Invalid port number.")
        return
    log_debug(f"Sending: {byte_array} to {ip}:{port}")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, port))
            s.sendall(bytes(byte_array))
            log_debug("Command sent successfully.")
    except Exception as e:
        log_debug(f"Error sending command: {e}")

def send_cmd(cmd_list):
    """Wrapper to send a command list."""
    send_binary_command(cmd_list)

def log_debug(msg):
    debug_text.insert(tk.END, msg + "\n")
    debug_text.see(tk.END)

# -------------------------------
# Manual Command Parsing
# -------------------------------
manual_mapping = {
    "ESC": 27,
    "BEL": 7,
    "BS": 8,
    "CAN": 24,
    "CR": 13,
    "DC1": 17,
    "DC2": 18,
    "DC3": 19,
    "DC4": 20,
    "FF": 12,
    "HT": 9,
    "LF": 10,
    "NUL": 0,
    "SI": 15,
    "SO": 14,
    "SP": 32,
    "VT": 11
    # Additional tokens can be added.
}

def parse_manual_command(cmd_str):
    """Parse a command string like 'ESC K 1 0 255 CR LF' into a list of ints."""
    tokens = cmd_str.split()
    result = []
    for token in tokens:
        token_upper = token.upper()
        if token_upper in manual_mapping:
            result.append(manual_mapping[token_upper])
        else:
            try:
                num = int(token)
                result.append(num)
            except ValueError:
                for ch in token:
                    result.append(ord(ch))
    return result

# -------------------------------
# Main GUI
# -------------------------------
root = tk.Tk()
root.title("Printer Command Sender")

# --- Printer Connection Frame ---
frame_conn = ttk.Frame(root, padding="5")
frame_conn.pack(fill="x")
ttk.Label(frame_conn, text="Printer IP:").pack(side="left")
ip_entry = ttk.Entry(frame_conn, width=15)
ip_entry.pack(side="left", padx=5)
ip_entry.insert(0, "192.168.4.28")
ttk.Label(frame_conn, text="Port:").pack(side="left")
port_entry = ttk.Entry(frame_conn, width=6)
port_entry.pack(side="left", padx=5)
port_entry.insert(0, "9100")

# --- Notebook for Command Categories ---
notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=5, pady=5)

# Tab 1: Basic Control Characters
tab_basic = ttk.Frame(notebook)
notebook.add(tab_basic, text="Basic Control")
def add_button(frame, text, cmd):
    btn = ttk.Button(frame, text=text, command=lambda: send_cmd(cmd))
    btn.pack(anchor="w", pady=2)
add_button(tab_basic, "Beeper (BEL)", [7])
add_button(tab_basic, "Backspace (BS)", [8])
add_button(tab_basic, "Cancel Data (CAN)", [24])
add_button(tab_basic, "Carriage Return (CR)", [13])
add_button(tab_basic, "Select Printer (DC1)", [17])
add_button(tab_basic, "10 CPI Print (DC2)", [18])
add_button(tab_basic, "Deselect Printer (DC3)", [19])
add_button(tab_basic, "Cancel Double-Wide (DC4)", [20])

# Tab 2: Whitespace & Text Spacing
tab_whitespace = ttk.Frame(notebook)
notebook.add(tab_whitespace, text="Whitespace & Text")
add_button(tab_whitespace, "Form Feed (FF)", [12])
add_button(tab_whitespace, "Horizontal Tab (HT)", [9])
add_button(tab_whitespace, "Line Feed (LF)", [10])
add_button(tab_whitespace, "Null (NUL)", [0])
add_button(tab_whitespace, "Condensed Printing (SI)", [15])
add_button(tab_whitespace, "Double-Wide Printing (SO)", [14])
add_button(tab_whitespace, "Space (SP)", [32])
add_button(tab_whitespace, "Vertical Tab (VT)", [11])
# Set Text Line Spacing: ESC A n
frame_stls = ttk.Frame(tab_whitespace)
frame_stls.pack(anchor="w", pady=2)
ttk.Label(frame_stls, text="Set Text Line Spacing (ESC A n):").pack(side="left")
stls_entry = ttk.Entry(frame_stls, width=5)
stls_entry.pack(side="left", padx=5)
ttk.Button(frame_stls, text="Send", command=lambda: send_cmd([27, ord('A'), int(stls_entry.get())])).pack(side="left")
ttk.Label(tab_whitespace, text="Set Vertical Tabs (ESC B ...): Not implemented").pack(anchor="w", pady=2)

# Tab 3: Page Layout & Tab Settings
tab_page = ttk.Frame(notebook)
notebook.add(tab_page, text="Page Layout")
frame_form = ttk.Frame(tab_page)
frame_form.pack(anchor="w", pady=2)
ttk.Label(frame_form, text="Set Form Length (ESC C):").pack(side="left")
form_mode_var = tk.StringVar(value="lines")
ttk.Radiobutton(frame_form, text="Lines", variable=form_mode_var, value="lines").pack(side="left", padx=5)
ttk.Radiobutton(frame_form, text="Inches", variable=form_mode_var, value="inches").pack(side="left", padx=5)
form_entry = ttk.Entry(frame_form, width=5)
form_entry.pack(side="left", padx=5)
def send_form_length():
    try:
        val = int(form_entry.get())
    except:
        log_debug("Invalid number for form length.")
        return
    if form_mode_var.get() == "lines":
        cmd = [27, ord('C'), val]
    else:
        cmd = [27, ord('C'), 0, val]
    send_cmd(cmd)
ttk.Button(frame_form, text="Send", command=send_form_length).pack(side="left", padx=5)
ttk.Label(tab_page, text="Set Horizontal Tabs (ESC D ...): Not implemented").pack(anchor="w", pady=2)
add_button(tab_page, "Emphasized Printing (ESC E)", [27, ord('E')])
add_button(tab_page, "Cancel Emphasized Printing (ESC F)", [27, ord('F')])
add_button(tab_page, "Double-Strike Printing (ESC G)", [27, ord('G')])
add_button(tab_page, "Cancel Double-Strike Printing (ESC H)", [27, ord('H')])

# Tab 4: Print Mode Commands
tab_printmode = ttk.Frame(notebook)
notebook.add(tab_printmode, text="Print Mode")
frame_pm = ttk.Frame(tab_printmode)
frame_pm.pack(anchor="w", pady=2)
ttk.Label(frame_pm, text="Select Print Mode (ESC I n):").pack(side="left")
pm_entry = ttk.Entry(frame_pm, width=5)
pm_entry.pack(side="left", padx=5)
ttk.Button(frame_pm, text="Send", command=lambda: send_cmd([27, ord('I'), int(pm_entry.get())])).pack(side="left", padx=5)
# Add a label with additional information using decimal values:
info_text = ("Modes: 0 = DP Resident, 1 = Fastfont (12 CPI) Resident, 2 = NLQ Resident, 3 = NLQ II Resident, "
             "4 = DP Download, 5 = Fastfont (12 CPI) Download, 6 = NLQ Download, 7 = NLQ II Download, "
             "11 = Alternate NLQ II (Italic) Resident, 15 = Alternate NLQ II Download")
ttk.Label(tab_printmode, text=info_text, wraplength=400).pack(anchor="w", pady=5)

# Tab 5: Miscellaneous Print Settings
tab_misc = ttk.Frame(notebook)
notebook.add(tab_misc, text="Misc. Print Settings")
add_button(tab_misc, "Set All Tabs to Power On Settings (ESC R)", [27, ord('R')])
frame_sub = ttk.Frame(tab_misc)
frame_sub.pack(anchor="w", pady=2)
ttk.Label(frame_sub, text="Subscript/Superscript (ESC S n):").pack(side="left")
sub_var = tk.IntVar(value=0)
ttk.Radiobutton(frame_sub, text="Superscript (0)", variable=sub_var, value=0).pack(side="left", padx=5)
ttk.Radiobutton(frame_sub, text="Subscript (1)", variable=sub_var, value=1).pack(side="left", padx=5)
ttk.Button(frame_sub, text="Send", command=lambda: send_cmd([27, ord('S'), sub_var.get()])).pack(side="left", padx=5)
add_button(tab_misc, "Cancel Subscript/Superscript (ESC T)", [27, ord('T')])
frame_dir = ttk.Frame(tab_misc)
frame_dir.pack(anchor="w", pady=2)
ttk.Label(frame_dir, text="Print in One Direction (ESC U n):").pack(side="left")
dir_var = tk.IntVar(value=0)
ttk.Radiobutton(frame_dir, text="Bidirectional (0)", variable=dir_var, value=0).pack(side="left", padx=5)
ttk.Radiobutton(frame_dir, text="Left-to-Right (1)", variable=dir_var, value=1).pack(side="left", padx=5)
ttk.Button(frame_dir, text="Send", command=lambda: send_cmd([27, ord('U'), dir_var.get()])).pack(side="left", padx=5)
frame_dw = ttk.Frame(tab_misc)
frame_dw.pack(anchor="w", pady=2)
ttk.Label(frame_dw, text="Continuous Double-Wide (ESC W n):").pack(side="left")
dw_var = tk.IntVar(value=0)
ttk.Radiobutton(frame_dw, text="Ends (0)", variable=dw_var, value=0).pack(side="left", padx=5)
ttk.Radiobutton(frame_dw, text="Begins (1)", variable=dw_var, value=1).pack(side="left", padx=5)
ttk.Button(frame_dw, text="Send", command=lambda: send_cmd([27, ord('W'), dw_var.get()])).pack(side="left", padx=5)
ttk.Label(tab_misc, text="(Dual-/High-Density Bit-Image Commands: Not implemented)").pack(anchor="w", pady=2)

# Tab 6: Line Spacing & Character Set Commands
tab_line = ttk.Frame(notebook)
notebook.add(tab_line, text="Line Spacing & Char Set")
add_button(tab_line, "1/8-Inch Line Spacing (ESC 0)", [27, ord('0')])
add_button(tab_line, "7/72-Inch Line Spacing (ESC 1)", [27, ord('1')])
add_button(tab_line, "Start Text Line Spacing (ESC 2)", [27, ord('2')])
frame_gls = ttk.Frame(tab_line)
frame_gls.pack(anchor="w", pady=2)
ttk.Label(frame_gls, text="Graphics Line Spacing (ESC 3 n):").pack(side="left")
gls_entry = ttk.Entry(frame_gls, width=5)
gls_entry.pack(side="left", padx=5)
ttk.Button(frame_gls, text="Send", command=lambda: send_cmd([27, ord('3'), int(gls_entry.get())])).pack(side="left", padx=5)
add_button(tab_line, "Set Top of Form (ESC 4)", [27, ord('4')])
frame_lf = ttk.Frame(tab_line)
frame_lf.pack(anchor="w", pady=2)
ttk.Label(frame_lf, text="Automatic Line Feed (ESC 5 n):").pack(side="left")
lf_var = tk.IntVar(value=0)
ttk.Radiobutton(frame_lf, text="Cancel (0)", variable=lf_var, value=0).pack(side="left", padx=5)
ttk.Radiobutton(frame_lf, text="Begin (1)", variable=lf_var, value=1).pack(side="left", padx=5)
ttk.Button(frame_lf, text="Send", command=lambda: send_cmd([27, ord('5'), lf_var.get()])).pack(side="left", padx=5)
add_button(tab_line, "Select Character Set 2 (ESC 6)", [27, ord('6')])
add_button(tab_line, "Select Character Set 1 (ESC 7)", [27, ord('7')])
frame_over = ttk.Frame(tab_line)
frame_over.pack(anchor="w", pady=2)
ttk.Label(frame_over, text="Continuous Overscore (ESC _ n):").pack(side="left")
over_var = tk.IntVar(value=0)
ttk.Radiobutton(frame_over, text="Cancel (0)", variable=over_var, value=0).pack(side="left", padx=5)
ttk.Radiobutton(frame_over, text="Begin (1)", variable=over_var, value=1).pack(side="left", padx=5)
ttk.Button(frame_over, text="Send", command=lambda: send_cmd([27, 95, over_var.get()])).pack(side="left", padx=5)
frame_under = ttk.Frame(tab_line)
frame_under.pack(anchor="w", pady=2)
ttk.Label(frame_under, text="Continuous Underscore (ESC ` n):").pack(side="left")
under_var = tk.IntVar(value=0)
ttk.Radiobutton(frame_under, text="Cancel (0)", variable=under_var, value=0).pack(side="left", padx=5)
ttk.Radiobutton(frame_under, text="Begin (1)", variable=under_var, value=1).pack(side="left", padx=5)
ttk.Button(frame_under, text="Send", command=lambda: send_cmd([27, 96, under_var.get()])).pack(side="left", padx=5)

# Tab 7: Manual Command
tab_manual = ttk.Frame(notebook)
notebook.add(tab_manual, text="Manual Command")
ttk.Label(tab_manual, text="Enter command (e.g., 'ESC K 1 0 255 CR LF'):").pack(anchor="w", pady=2)
manual_entry = ttk.Entry(tab_manual, width=50)
manual_entry.pack(anchor="w", padx=5, pady=2)
ttk.Button(tab_manual, text="Send Command", command=lambda: send_cmd(parse_manual_command(manual_entry.get()))).pack(anchor="w", padx=5, pady=2)

# --- Debug Output Section ---
frame_debug = ttk.Frame(root, padding="5")
frame_debug.pack(fill="both", expand=True)
ttk.Label(frame_debug, text="Debug Output:").pack(anchor="w")
debug_text = scrolledtext.ScrolledText(frame_debug, height=10)
debug_text.pack(fill="both", expand=True)

root.mainloop()
