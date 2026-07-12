import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from PIL import Image
import socket
import math
import time

# Global variable to hold the loaded image
loaded_image = None

# -------------------------------
# Printer Communication Function
# -------------------------------
def send_binary_command(byte_array):
    """Send the given list of integers as binary data via TCP."""
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

# -------------------------------
# Image Processing & Code Generation
# -------------------------------
def upload_image():
    """Upload a bitmap image (mode '1') within the width limits for the selected mode."""
    global loaded_image
    file_path = filedialog.askopenfilename(title="Select Bitmap Image",
                                           filetypes=[("Bitmap Images", "*.bmp"), ("All Files", "*.*")])
    if not file_path:
        return
    try:
        img = Image.open(file_path)
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open image: {e}")
        return

    # Check that image is entirely bitmap (mode "1")
    if img.mode != "1":
        messagebox.showerror("Error", "Image must be entirely bitmap (mode '1').")
        return

    # Check maximum width based on selected mode
    mode = mode_var.get()
    max_width = 480 if mode == "480" else 960
    if img.width > max_width:
        messagebox.showerror("Error", f"Image width must be no wider than {max_width} pixels for the selected mode.")
        return

    loaded_image = img
    log_debug(f"Image loaded: {file_path} ({img.width}x{img.height})")

def generate_code():
    """Process the loaded image and generate printer code."""
    global loaded_image
    if loaded_image is None:
        messagebox.showerror("Error", "No image loaded. Please upload an image first.")
        return

    mode = mode_var.get()
    max_width = 480 if mode == "480" else 960
    if loaded_image.width > max_width:
        messagebox.showerror("Error", f"Image width exceeds the maximum of {max_width} pixels for the selected mode.")
        return

    width, height = loaded_image.size
    num_stripes = math.ceil(height / 8)
    code_lines = []
    
    # --- Header: set line spacing with ESC 3 24 ---
    header_line = "27 51 24"  # ESC (27) + '3' (51) + 24
    code_lines.append(header_line)
    
    # Determine the command letter for each stripe based on mode:
    # For 480 mode 60x72 DPI mode) we use ESC K;
    # for 960 mode (120x72 DPI mode) we use ESC L.
    command_letter = 'K' if mode == "480" else 'L'

    # For each stripe, build a line of code.
    for stripe in range(num_stripes):
        col_bytes = []
        for col in range(width):
            byte_val = 0
            for row_offset in range(8):
                row = stripe * 8 + row_offset
                if row >= height:
                    continue
                pixel = loaded_image.getpixel((col, row))
                # In mode "1", pixel==0 means black (active)
                if pixel == 0:
                    byte_val += (128 >> row_offset)  # 128, 64, 32, ... , 1
            col_bytes.append(byte_val)
        total_cols = width
        n1 = total_cols % 256
        n2 = total_cols // 256
        # Command line for this stripe: ESC {command_letter} n1 n2 [column byte data] CR LF
        line_cmd = [27, ord(command_letter), n1, n2] + col_bytes + [13, 10]
        line_str = " ".join(str(num) for num in line_cmd)
        code_lines.append(line_str)
    
    # Suffix the entire code with CR LF FF (13 10 12)
    final_suffix = "13 10 12"
    code_lines.append(final_suffix)
    
    # Populate the generated code text widget.
    generated_code = "\n".join(code_lines)
    code_text.delete("1.0", tk.END)
    code_text.insert(tk.END, generated_code)
    
    # Calculate printed dimensions.
    # For 480 mode, we want 480 dots to span 8 inches => 60 DPI horizontally.
    # For 960 mode, 960 dots span 8 inches => 120 DPI horizontally.
    horiz_dpi = 60 if mode == "480" else 120
    printed_width = width / horiz_dpi
    # Vertical: each 8-pixel stripe prints at 8/72 inches (0.111 inches per stripe)
    printed_height = height / 72  
    dim_str = f"Printed Dimensions: {printed_width:.2f}\" x {printed_height:.2f}\" (W x H)"
    dim_label.config(text=dim_str)
    log_debug("Code generation complete.")

def print_code():
    """Send the generated code, line by line, to the printer."""
    code_str = code_text.get("1.0", tk.END).strip()
    if not code_str:
        messagebox.showerror("Error", "No generated code to print.")
        return
    lines = code_str.splitlines()
    for line in lines:
        try:
            tokens = line.strip().split()
            if not tokens:
                continue
            byte_list = [int(token) for token in tokens]
            send_binary_command(byte_list)
            time.sleep(0.05)
        except Exception as e:
            log_debug(f"Error printing line '{line}': {e}")
    log_debug("Printing complete.")

def log_debug(message):
    """Append a message to the debug output."""
    debug_text.insert(tk.END, message + "\n")
    debug_text.see(tk.END)

# -------------------------------
# Tkinter GUI Setup
# -------------------------------
root = tk.Tk()
root.title("Printer Control GUI (Image to Code)")

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

# Mode Selection Frame
frame_mode = ttk.Frame(root, padding="10")
frame_mode.grid(row=1, column=0, sticky="ew")
mode_var = tk.StringVar(value="480")
ttk.Label(frame_mode, text="Select Mode:").grid(row=0, column=0, sticky="w")
rbtn_480 = ttk.Radiobutton(frame_mode, text="480dots/8inch (60×72 DPI)", variable=mode_var, value="480")
rbtn_480.grid(row=0, column=1, padx=5)
rbtn_960 = ttk.Radiobutton(frame_mode, text="960dots/8inch (120×72 DPI)", variable=mode_var, value="960")
rbtn_960.grid(row=0, column=2, padx=5)

# Image Upload and Code Generation Frame
frame_image = ttk.Labelframe(root, text="Image to Printer Code", padding="10")
frame_image.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
btn_upload = ttk.Button(frame_image, text="Upload Bitmap Image", command=upload_image)
btn_upload.grid(row=0, column=0, padx=5, pady=5)
btn_generate = ttk.Button(frame_image, text="Generate Code", command=generate_code)
btn_generate.grid(row=0, column=1, padx=5, pady=5)
ttk.Label(frame_image, text="(Image must be mode '1'; max width = 480 px in 480 mode, 960 px in 960 mode)").grid(row=1, column=0, columnspan=2, sticky="w")

# Dimensions Display Label
dim_label = ttk.Label(root, text="Printed Dimensions: N/A", padding="5")
dim_label.grid(row=3, column=0, sticky="w", padx=10)

# Generated Code Text Window
frame_code = ttk.Labelframe(root, text="Generated Printer Code", padding="10")
frame_code.grid(row=4, column=0, sticky="nsew", padx=10, pady=5)
code_text = scrolledtext.ScrolledText(frame_code, height=15, width=80)
code_text.grid(row=0, column=0, sticky="nsew")

# Print Button
frame_print = ttk.Frame(root, padding="10")
frame_print.grid(row=5, column=0, sticky="ew", padx=10, pady=5)
btn_print = ttk.Button(frame_print, text="Print", command=print_code)
btn_print.grid(row=0, column=0, padx=5, pady=5)

# Debug Output Section
frame_debug = ttk.Labelframe(root, text="Debug Output", padding="10")
frame_debug.grid(row=6, column=0, sticky="nsew", padx=10, pady=5)
debug_text = scrolledtext.ScrolledText(frame_debug, height=10, width=80)
debug_text.grid(row=0, column=0, sticky="nsew")

root.mainloop()
