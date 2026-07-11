import tkinter as tk
from tkinter import ttk, simpledialog
import socket

# ------------------ IBM Command Dictionary ------------------
IBM_COMMANDS = {
    "Backspace": b"\x08",            # BS (8)
    "Carriage Return": b"\x0D",      # CR (13)
    "Select 10 cpi": b"\x12",        # DC2 (18)
    "Select 12 cpi": b"\x1B\x3A",    # ESC : (27 58)
    "Select 15 cpi": b"\x1B\x67",    # ESC g (27 103)
    "Select Condensed Print": b"\x1B\x0F",  # ESC SI (27 15)
    "IBM Set I": b"\x1B\x37",        # ESC 7 (27 55)
    "IBM Set II": b"\x1B\x36",       # ESC 6 (27 54)
    "Publisher Set": b"\x1B\x21\x5A",# ESC ! Z (27 33 90)
    "Slashed Zero": b"\x1B\x21\x40", # ESC ! @ (27 33 64)
    "Unslashed Zero": b"\x1B\x21\x41",# ESC ! A (27 33 65)
    "Double Width On": b"\x1B\x57\x31",   # ESC W 1 (27 87 49)
    "Double Width Off": b"\x1B\x57\x30",  # ESC W 0 (27 87 48)
    "Emphasized Printing On": b"\x1B\x45",  # ESC E (27 69)
    "Emphasized Printing Off": b"\x1B\x46", # ESC F (27 70)
    "Enhanced Printing On": b"\x1B\x47",    # ESC G (27 71)
    "Enhanced Printing Off": b"\x1B\x48",   # ESC H (27 72)
    "Form Feed": b"\x0C",            # FF (12)
    "Horizontal Tab": b"\x09",       # HT (9)
    "Italics On": b"\x1B\x25\x47",   # ESC % G (27 37 71)
    "Italics Off": b"\x1B\x25\x48",  # ESC % H (27 37 72)
    "Line Feed": b"\x0A",            # LF (10)
    "Reverse Line Feed": b"\x1B\x4A",# ESC J (27 74)
    "Line Spacing 1/8": b"\x1B\x30", # ESC 0 (27 48)
    "Line Spacing 7/72": b"\x1B\x31",# ESC 1 (27 49)
    "Set Spacing to n/72": lambda n: b"\x1B\x41" + bytes([n]),
    "Store Spacing Set": b"\x1B\x32",
    "Set Spacing to n/144": lambda n: b"\x1B\x25\x39" + bytes([n]),
    "Set Spacing to n/216": lambda n: b"\x1B\x33" + bytes([n]),
    "Overscore On": b"\x1B\x5F\x31",
    "Overscore Off": b"\x1B\x5F\x30",
    "Paper Out Sensor Off": b"\x1B\x38",
    "Paper Out Sensor On": b"\x1B\x39",
    "Print Suppress On": b"\x13",
    "Print Suppress Off": b"\x11",
    "Proportional Spacing On": b"\x1B\x50\x31",
    "Proportional Spacing Off": b"\x1B\x50\x30",
    "Reset (Clear Print Buffer)": b"\x18",
    "Vertical Tab": b"\x0B",
    "Underline On": b"\x1B\x2D\x01",
    "Underline Off": b"\x1B\x2D\x00",
    "Superscript On": b"\x1B\x73\x01",
    "Superscript Off": b"\x1B\x73\x00",
    "Subscript On": b"\x1B\x73\x02",
    "Subscript Off": b"\x1B\x73\x00"
}

# ------------------ Toggle States ------------------
toggle_states = {
    "IBM Set": "IBM Set I",  # starting with IBM Set I
    "Double Width": False,
    "Emphasized Printing": False,
    "Enhanced Printing": False,
    "Italics": False,
    "Overscore": False,
    "Print Suppress": False,
    "Proportional Spacing": False,
    "Underline": False,
    "Superscript": False,
    "Subscript": False
}

# ------------------ Shortcut Mapping ------------------
# When CTRL is held, the keystroke is interpreted as a command.
# Otherwise, it is sent as text.
SHORTCUTS = {
    "backspace": "Backspace",
    "return": "Carriage Return",
    "f1": "Select 10 cpi",
    "f2": "Select 12 cpi",
    "f3": "Select 15 cpi",
    "f4": "Select Condensed Print",
    "t": "Toggle IBM Set",
    "p": "Publisher Set",
    "z": "Slashed Zero",
    "u": "Unslashed Zero",
    "d": "Toggle Double Width",
    "e": "Toggle Emphasized Printing",
    "g": "Toggle Enhanced Printing",
    "f5": "Form Feed",
    "f6": "Horizontal Tab",
    "i": "Toggle Italics",
    "l": "Line Feed",
    "r": "Reverse Line Feed",
    "1": "Line Spacing 1/8",
    "2": "Line Spacing 7/72",
    "3": "Set Spacing to n/72",
    "4": "Set Spacing to n/144",
    "5": "Set Spacing to n/216",
    "o": "Toggle Overscore",
    "x": "Paper Out Sensor Off",
    "c": "Paper Out Sensor On",
    "s": "Toggle Print Suppress",
    "q": "Toggle Proportional Spacing",
    "0": "Reset (Clear Print Buffer)",
    "v": "Vertical Tab",
    "w": "Toggle Underline",
    "y": "Toggle Superscript",
    "h": "Toggle Subscript"
}

# ------------------ Sending Commands ------------------
def send_command(command_bytes):
    ip = ip_entry.get().strip()
    try:
        port = int(port_entry.get().strip())
    except ValueError:
        log_debug("Invalid port number.")
        return
    log_debug(f"Sending: {command_bytes} to {ip}:{port}")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, port))
            s.sendall(command_bytes)
        log_debug("Command sent successfully.")
    except Exception as e:
        log_debug(f"Error sending command: {e}")

# ------------------ Toggle Helpers ------------------
def toggle_command(toggle_name, on_command, off_command):
    toggle_states[toggle_name] = not toggle_states[toggle_name]
    state = toggle_states[toggle_name]
    if state:
        send_command(on_command)
        log_debug(f"{toggle_name} turned ON")
    else:
        send_command(off_command)
        log_debug(f"{toggle_name} turned OFF")
    update_shortcuts_display()

def toggle_ibm_set():
    current = toggle_states["IBM Set"]
    if current == "IBM Set I":
        toggle_states["IBM Set"] = "IBM Set II"
        send_command(IBM_COMMANDS["IBM Set II"])
        log_debug("IBM Set changed to IBM Set II")
    else:
        toggle_states["IBM Set"] = "IBM Set I"
        send_command(IBM_COMMANDS["IBM Set I"])
        log_debug("IBM Set changed to IBM Set I")
    update_shortcuts_display()

# ------------------ Parameter Command Helper ------------------
def send_parameter_command(command_func, description):
    n = simpledialog.askinteger("Input", f"Enter parameter for {description} (0-255):", minvalue=0, maxvalue=255)
    if n is not None:
        command_bytes = command_func(n)
        send_command(command_bytes)
        log_debug(f"{description} with parameter {n} sent.")
    command_entry.focus_set()

# ------------------ Shortcuts Display (Two Columns) ------------------
def update_shortcuts_display():
    for widget in shortcuts_frame.winfo_children():
        widget.destroy()
    items = list(SHORTCUTS.items())
    col_count = 2
    rows = (len(items) + col_count - 1) // col_count
    for i, (key, action) in enumerate(items):
        key_display = f"Ctrl+{key}" if key.isalpha() else key
        if action.startswith("Toggle "):
            toggle_name = action.replace("Toggle ", "")
            if toggle_name == "IBM Set":
                state = (toggle_states["IBM Set"] == "IBM Set II")
                state_str = toggle_states["IBM Set"]
            elif toggle_name in toggle_states:
                state = toggle_states[toggle_name]
                state_str = "ON" if state else "OFF"
            else:
                state = None
                state_str = ""
            text = f"{key_display}: {action} (Current: {state_str})"
            color = "green" if state else "red"
        else:
            text = f"{key_display}: {action}"
            color = "black"
        row = i % rows
        col = i // rows
        lbl = tk.Label(shortcuts_frame, text=text, fg=color, anchor="w")
        lbl.grid(row=row, column=col, padx=5, pady=2, sticky="w")

# ------------------ Debug Logging ------------------
def log_debug(msg):
    debug_text.insert(tk.END, msg + "\n")
    debug_text.see(tk.END)

# ------------------ Command Input Processing ------------------
def process_command(event):
    # Check if CTRL is held (bitmask 0x4)
    ctrl_held = (event.state & 0x4) != 0

    # Get the key symbol in lower-case (for letters)
    key = event.keysym.lower() if event.keysym.isalpha() else event.keysym

    if ctrl_held:
        # Interpret as a command using the shortcut mapping.
        if key in SHORTCUTS:
            action = SHORTCUTS[key]
            log_debug(f"(CTRL) Command Input: Key '{key}' mapped to '{action}'")
            if action == "Backspace":
                send_command(IBM_COMMANDS["Backspace"])
            elif action == "Carriage Return":
                send_command(IBM_COMMANDS["Carriage Return"])
            elif action == "Select 10 cpi":
                send_command(IBM_COMMANDS["Select 10 cpi"])
            elif action == "Select 12 cpi":
                send_command(IBM_COMMANDS["Select 12 cpi"])
            elif action == "Select 15 cpi":
                send_command(IBM_COMMANDS["Select 15 cpi"])
            elif action == "Select Condensed Print":
                send_command(IBM_COMMANDS["Select Condensed Print"])
            elif action == "Toggle IBM Set":
                toggle_ibm_set()
            elif action == "Publisher Set":
                send_command(IBM_COMMANDS["Publisher Set"])
            elif action == "Slashed Zero":
                send_command(IBM_COMMANDS["Slashed Zero"])
            elif action == "Unslashed Zero":
                send_command(IBM_COMMANDS["Unslashed Zero"])
            elif action == "Toggle Double Width":
                toggle_command("Double Width", IBM_COMMANDS["Double Width On"], IBM_COMMANDS["Double Width Off"])
            elif action == "Toggle Emphasized Printing":
                toggle_command("Emphasized Printing", IBM_COMMANDS["Emphasized Printing On"], IBM_COMMANDS["Emphasized Printing Off"])
            elif action == "Toggle Enhanced Printing":
                toggle_command("Enhanced Printing", IBM_COMMANDS["Enhanced Printing On"], IBM_COMMANDS["Enhanced Printing Off"])
            elif action == "Form Feed":
                send_command(IBM_COMMANDS["Form Feed"])
            elif action == "Horizontal Tab":
                send_command(IBM_COMMANDS["Horizontal Tab"])
            elif action == "Toggle Italics":
                toggle_command("Italics", IBM_COMMANDS["Italics On"], IBM_COMMANDS["Italics Off"])
            elif action == "Line Feed":
                send_command(IBM_COMMANDS["Line Feed"])
            elif action == "Reverse Line Feed":
                send_command(IBM_COMMANDS["Reverse Line Feed"])
            elif action == "Line Spacing 1/8":
                send_command(IBM_COMMANDS["Line Spacing 1/8"])
            elif action == "Line Spacing 7/72":
                send_command(IBM_COMMANDS["Line Spacing 7/72"])
            elif action == "Set Spacing to n/72":
                send_parameter_command(IBM_COMMANDS["Set Spacing to n/72"], "Set Spacing to n/72")
            elif action == "Set Spacing to n/144":
                send_parameter_command(IBM_COMMANDS["Set Spacing to n/144"], "Set Spacing to n/144")
            elif action == "Set Spacing to n/216":
                send_parameter_command(IBM_COMMANDS["Set Spacing to n/216"], "Set Spacing to n/216")
            elif action == "Toggle Overscore":
                toggle_command("Overscore", IBM_COMMANDS["Overscore On"], IBM_COMMANDS["Overscore Off"])
            elif action == "Paper Out Sensor Off":
                send_command(IBM_COMMANDS["Paper Out Sensor Off"])
            elif action == "Paper Out Sensor On":
                send_command(IBM_COMMANDS["Paper Out Sensor On"])
            elif action == "Toggle Print Suppress":
                toggle_command("Print Suppress", IBM_COMMANDS["Print Suppress On"], IBM_COMMANDS["Print Suppress Off"])
            elif action == "Toggle Proportional Spacing":
                toggle_command("Proportional Spacing", IBM_COMMANDS["Proportional Spacing On"], IBM_COMMANDS["Proportional Spacing Off"])
            elif action == "Reset (Clear Print Buffer)":
                send_command(IBM_COMMANDS["Reset (Clear Print Buffer)"])
            elif action == "Vertical Tab":
                send_command(IBM_COMMANDS["Vertical Tab"])
            elif action == "Toggle Underline":
                toggle_command("Underline", IBM_COMMANDS["Underline On"], IBM_COMMANDS["Underline Off"])
            elif action == "Toggle Superscript":
                toggle_command("Superscript", IBM_COMMANDS["Superscript On"], IBM_COMMANDS["Superscript Off"])
            elif action == "Toggle Subscript":
                toggle_command("Subscript", IBM_COMMANDS["Subscript On"], IBM_COMMANDS["Subscript Off"])
            else:
                log_debug(f"Action '{action}' not implemented.")
        else:
            log_debug(f"(CTRL) Unmapped command key: '{key}'")
    else:
        # No CTRL: send the character as text.
        if event.char:
            text = event.char
            log_debug(f"Text Input: Sending '{text}' as text to printer")
            send_command(text.encode('ascii', errors='ignore'))
    command_entry.delete(0, tk.END)

# ------------------ Main GUI ------------------
root = tk.Tk()
root.title("Keyboard Operated Printer Command Sender")

# Printer connection frame
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

# Command input frame
command_frame = ttk.Frame(root, padding="5")
command_frame.pack(fill="x", padx=5, pady=5)
ttk.Label(command_frame, text="Command Input (CTRL+key = command; otherwise, text):").pack(side="left")
command_entry = ttk.Entry(command_frame, width=40)
command_entry.pack(side="left", padx=5)
command_entry.bind("<KeyRelease>", process_command)
command_entry.focus_set()

# Shortcuts display frame (two-column grid)
shortcuts_frame = ttk.Frame(root, padding="5", borderwidth=2, relief="groove")
shortcuts_frame.pack(fill="both", expand=True, padx=5, pady=5)
ttk.Label(shortcuts_frame, text="Keyboard Shortcuts:", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")
update_shortcuts_display()

# Debug output frame
frame_debug = ttk.Frame(root, padding="5")
frame_debug.pack(fill="both", expand=True, padx=5, pady=5)
ttk.Label(frame_debug, text="Debug Output:", font=("Arial", 10, "bold")).pack(anchor="w")
debug_text = tk.Text(frame_debug, height=10, wrap="word")
debug_text.pack(fill="both", expand=True)

root.mainloop()
