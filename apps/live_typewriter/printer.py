import socket
from tkinter import messagebox

def send_command(command_bytes, printer_ip, printer_port, debug_mode, debug_text, tag=""):
    """
    Sends the given command_bytes to the printer using the provided IP and port.
    Logs the command and any errors to the debug_text widget if debug_mode is enabled.
    """
    dec_str = " ".join(str(b) for b in command_bytes)
    if debug_mode:
        debug_text.config(state="normal")
        debug_text.insert("end", f"{tag} {dec_str}\n")
        debug_text.config(state="disabled")
        debug_text.see("end")
    try:
        with socket.create_connection((printer_ip, printer_port), timeout=5) as s:
            s.sendall(command_bytes)
    except Exception as e:
        debug_text.config(state="normal")
        debug_text.insert("end", f"{tag} Error: {e}\n")
        debug_text.config(state="disabled")
        debug_text.see("end")
