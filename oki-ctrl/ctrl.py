import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import socket

# Mapping for common ASCII command tokens.
COMMAND_MAPPING = {
    "ESC": 27,
    "CR": 13,
    "LF": 10,
    "BEL": 7,
    "BS": 8,
    "CAN": 24,
    "FF": 12,
    "HT": 9,
    "VT": 11,
    "SI": 15,
    "SO": 14,
    "SP": 32,
    "DC1": 17,
    "DC2": 18,
    "DC3": 19,
    "DC4": 20
    # Add more tokens as needed.
}

def send_binary_command(byte_array):
    """Send the given list of integer values as binary data via a TCP socket."""
    printer_ip = ip_entry.get().strip()
    try:
        printer_port = int(port_entry.get().strip())
    except ValueError:
        log_debug("Invalid port number.")
        return

    log_debug(f"Sending binary command: {byte_array} to {printer_ip}:{printer_port}")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((printer_ip, printer_port))
            s.sendall(bytes(byte_array))
            log_debug("Data sent to printer successfully.")
    except Exception as e:
        log_debug(f"Error sending data: {e}")

def send_raw_text():
    """Get the raw text from the widget, encode it (latin-1) and send as binary."""
    text = raw_text.get("1.0", tk.END).rstrip("\n")
    # Using latin-1 so that byte values 0-255 are preserved.
    try:
        byte_array = list(text.encode("latin-1"))
    except Exception as e:
        log_debug(f"Encoding error: {e}")
        return
    send_binary_command(byte_array)

def send_decimal_codes():
    """Parse the decimal/control code entry and send the corresponding byte values."""
    codes_str = decimal_entry.get().strip()
    if not codes_str:
        log_debug("No control codes entered.")
        return
    tokens = codes_str.split()
    byte_array = []
    for token in tokens:
        token_upper = token.upper()
        if token_upper in COMMAND_MAPPING:
            byte_array.append(COMMAND_MAPPING[token_upper])
        else:
            try:
                # If token is numeric (more than one character) convert it to int.
                if len(token) > 1 or token.isdigit():
                    byte_array.append(int(token))
                else:
                    # If single character, use its ASCII code.
                    byte_array.append(ord(token))
            except Exception as e:
                log_debug(f"Error processing token '{token}': {e}")
    send_binary_command(byte_array)

def send_preset_command(byte_array):
    """Helper to send a preset command from a given byte array."""
    send_binary_command(byte_array)

def send_set_text_line_spacing():
    """Example: Send 'ESC A n' command (n is provided in the entry)."""
    n_val = stls_entry.get().strip()
    try:
        n_int = int(n_val)
    except ValueError:
        log_debug("Invalid number for text line spacing.")
        return
    # Construct the command: ESC (27) followed by 'A' (65) and then the value.
    command = [27, ord('A'), n_int]
    send_preset_command(command)

def log_debug(message):
    """Append a message to the debug output."""
    debug_text.insert(tk.END, message + "\n")
    debug_text.see(tk.END)

# --- Tkinter GUI setup ---

root = tk.Tk()
root.title("Printer Control GUI (Tkinter)")

# Printer Connection Frame
frame_conn = ttk.Frame(root, padding="10")
frame_conn.grid(row=0, column=0, sticky="ew")
ttk.Label(frame_conn, text="Printer IP:").grid(row=0, column=0, sticky="w")
ip_entry = ttk.Entry(frame_conn, width=15)
ip_entry.grid(row=0, column=1, padx=5)
ip_entry.insert(0, "192.168.4.28")
ttk.Label(frame_conn, text="Port:").grid(row=0, column=2, sticky="w")
port_entry = ttk.Entry(frame_conn, width=6)
port_entry.grid(row=0, column=3, padx=5)
port_entry.insert(0, "9100")

# Section 1: Send Raw Text
frame_raw = ttk.Labelframe(root, text="Send Raw Text", padding="10")
frame_raw.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
raw_text = tk.Text(frame_raw, height=4, width=50)
raw_text.grid(row=0, column=0, padx=5, pady=5)
btn_send_raw = ttk.Button(frame_raw, text="Send Raw Text", command=send_raw_text)
btn_send_raw.grid(row=1, column=0, padx=5, pady=5)

# Section 2: Send Decimal Control Codes
frame_decimal = ttk.Labelframe(root, text="Send Decimal Control Codes", padding="10")
frame_decimal.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
decimal_entry = ttk.Entry(frame_decimal, width=50)
decimal_entry.grid(row=0, column=0, padx=5, pady=5)
btn_send_decimal = ttk.Button(frame_decimal, text="Send Control Codes", command=send_decimal_codes)
btn_send_decimal.grid(row=0, column=1, padx=5, pady=5)
ttk.Label(frame_decimal, text="Example: ESC K 1 0 255 CR LF").grid(row=1, column=0, columnspan=2, sticky="w")

# Section 3: Preset Command Codes
frame_preset = ttk.Labelframe(root, text="Preset Command Codes", padding="10")
frame_preset.grid(row=3, column=0, sticky="ew", padx=10, pady=5)
# Example preset buttons:
btn_beeper = ttk.Button(frame_preset, text="Beeper (BEL, 7)", command=lambda: send_preset_command([7]))
btn_beeper.grid(row=0, column=0, padx=5, pady=5)
btn_backspace = ttk.Button(frame_preset, text="Backspace (BS, 8)", command=lambda: send_preset_command([8]))
btn_backspace.grid(row=0, column=1, padx=5, pady=5)
btn_cr = ttk.Button(frame_preset, text="Carriage Return (CR, 13)", command=lambda: send_preset_command([13]))
btn_cr.grid(row=0, column=2, padx=5, pady=5)
# Preset with an additional parameter (Set Text Line Spacing: ESC A n)
ttk.Label(frame_preset, text="Set Text Line Spacing (ESC A n):").grid(row=1, column=0, padx=5, pady=5)
stls_entry = ttk.Entry(frame_preset, width=5)
stls_entry.grid(row=1, column=1, padx=5, pady=5)
btn_set_line_spacing = ttk.Button(frame_preset, text="Send", command=send_set_text_line_spacing)
btn_set_line_spacing.grid(row=1, column=2, padx=5, pady=5)
# (Additional preset buttons can be added similarly.)

# Debug Output Section
frame_debug = ttk.Labelframe(root, text="Debug Output", padding="10")
frame_debug.grid(row=4, column=0, sticky="nsew", padx=10, pady=5)
debug_text = scrolledtext.ScrolledText(frame_debug, height=10, width=60)
debug_text.grid(row=0, column=0, sticky="nsew")

root.mainloop()
