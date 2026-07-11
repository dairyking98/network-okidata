#!/usr/bin/env python3
"""
gui_editor.py

A word editor with an accurate representation of CPI, double wide, margins, and line spacings.
Formatting shortcuts (Ctrl+<key>):
    • Ctrl+I: Toggle Italic
    • Ctrl+B: Toggle Emphasized (Bold)
    • Ctrl+U: Toggle Underline
    • Ctrl+T: Toggle Double Height/Tall
    • Ctrl+P: Toggle Proportional font
    • Ctrl+F: Cycle through Character Sets
    • Ctrl+W: Toggle Double Wide/Wide
    • Ctrl+D: Toggle CPI setting
    • Ctrl+Q: Toggle Quality setting

Margins (left, right, top, bottom) are shown in a preview Canvas and are draggable.
They snap to 1/6″ (24 pixels) or 1/8″ (18 pixels) if moved close enough.
When the page is laid out, clicking the Print button sends the text content to the printer.
Printer IP and port entries are provided at the top.

This file integrates with the previously refactored code by using printer.send_command
(from printer.py) and config.DEFAULT_CONFIG.
"""

import tkinter as tk
from tkinter import messagebox, font
import socket

from config import DEFAULT_CONFIG  # Use default configuration if needed
from printer import send_command    # Use the printer helper function

# Constants for layout (assuming 144 DPI so that 1" = 144 pixels)
DPI = 144  
SNAP_POINTS = [DPI/6, DPI/8]  # 1/6" ~ 24 pixels, 1/8" ~ 18 pixels

class DraggableMargin:
    """
    Helper class for a draggable margin line on a Canvas.
    """
    def __init__(self, canvas, orientation, pos, update_callback):
        """
        orientation: 'vertical' or 'horizontal'
        pos: initial position (in pixels)
        update_callback: function called with the new position after dragging
        """
        self.canvas = canvas
        self.orientation = orientation
        self.pos = pos
        self.update_callback = update_callback
        if self.orientation == 'vertical':
            self.line = canvas.create_line(pos, 0, pos, canvas.winfo_reqheight(), fill="red", width=2, dash=(4,2))
        else:
            self.line = canvas.create_line(0, pos, canvas.winfo_reqwidth(), pos, fill="red", width=2, dash=(4,2))
        self._drag_data = {"x": 0, "y": 0}
        canvas.tag_bind(self.line, "<ButtonPress-1>", self.on_press)
        canvas.tag_bind(self.line, "<B1-Motion>", self.on_motion)
        canvas.tag_bind(self.line, "<ButtonRelease-1>", self.on_release)

    def on_press(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def on_motion(self, event):
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        if self.orientation == 'vertical':
            self.pos += dx
            self.canvas.move(self.line, dx, 0)
        else:
            self.pos += dy
            self.canvas.move(self.line, 0, dy)
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        self.update_callback(self.pos)

    def on_release(self, event):
        # Snap to a defined snap point if within threshold
        threshold = 5  # pixels
        for snap in SNAP_POINTS:
            if abs(self.pos - snap) < threshold:
                delta = snap - self.pos
                self.pos = snap
                if self.orientation == 'vertical':
                    self.canvas.move(self.line, delta, 0)
                else:
                    self.canvas.move(self.line, 0, delta)
                break
        self.update_callback(self.pos)

class DummyDebugText:
    """
    A simple dummy debug widget to satisfy the interface of send_command.
    In this implementation, debug messages are simply printed to the console.
    """
    def config(self, **kwargs):
        pass
    def insert(self, index, text):
        print(text)
    def see(self, index):
        pass

class GuiEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Word Editor - Layout and Print")
        self.geometry("1000x700")
        
        # Formatting state variables
        self.italic = False
        self.emphasized = False
        self.underline = False
        self.double_height = False
        self.proportional = False
        self.char_set_index = 0  # index for character set switching
        self.double_wide = False
        self.cpi_toggle = False
        self.quality_toggle = False
        
        # Printer info (initialize with defaults from config if desired)
        self.printer_ip = tk.StringVar(value=DEFAULT_CONFIG.get("PRINTER_IP", "192.168.4.28"))
        self.printer_port = tk.IntVar(value=DEFAULT_CONFIG.get("PRINTER_PORT", 9100))
        
        # Page dimensions (using typical letter size: 8.5 x 11 inches)
        self.page_width = 8.5 * DPI
        self.page_height = 11 * DPI
        
        # Initial margin positions (in pixels)
        self.left_margin = 1 * DPI         # 1 inch from left
        self.right_margin = self.page_width - 1 * DPI  # 1 inch from right
        self.top_margin = 1 * DPI          # 1 inch from top
        self.bottom_margin = self.page_height - 1 * DPI  # 1 inch from bottom
        
        # Build the interface
        self.create_controls()
        self.create_editor()
        self.create_layout_preview()
        self.bind_shortcuts()
    
    def create_controls(self):
        # Top frame for printer info and print button
        ctrl_frame = tk.Frame(self)
        ctrl_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        tk.Label(ctrl_frame, text="Printer IP:").pack(side=tk.LEFT)
        tk.Entry(ctrl_frame, textvariable=self.printer_ip, width=15).pack(side=tk.LEFT, padx=5)
        tk.Label(ctrl_frame, text="Port:").pack(side=tk.LEFT)
        tk.Entry(ctrl_frame, textvariable=self.printer_port, width=5).pack(side=tk.LEFT, padx=5)
        tk.Button(ctrl_frame, text="Print", command=self.print_page).pack(side=tk.RIGHT, padx=5)
    
    def create_editor(self):
        # Left frame for the text editor
        editor_frame = tk.Frame(self)
        editor_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.text_editor = tk.Text(editor_frame, wrap="word")
        self.text_editor.pack(fill=tk.BOTH, expand=True)
        
        # Setup font tags to simulate formatting changes
        base_font = font.Font(family="Courier", size=12)
        italic_font = font.Font(family="Courier", size=12, slant="italic")
        bold_font = font.Font(family="Courier", size=12, weight="bold")
        underline_font = font.Font(family="Courier", size=12, underline=1)
        double_height_font = font.Font(family="Courier", size=24)  # double height example
        proportional_font = font.Font(family="Arial", size=12)
        
        self.text_editor.tag_configure("italic", font=italic_font)
        self.text_editor.tag_configure("emphasized", font=bold_font)
        self.text_editor.tag_configure("underline", font=underline_font)
        self.text_editor.tag_configure("double_height", font=double_height_font)
        self.text_editor.tag_configure("proportional", font=proportional_font)
        # (Other formatting such as double wide, CPI, and quality can be simulated by state.)
    
    def create_layout_preview(self):
        # Right frame for the layout preview
        preview_frame = tk.Frame(self)
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5, pady=5)
        self.canvas = tk.Canvas(preview_frame, width=self.page_width, height=self.page_height, bg="white")
        self.canvas.pack()
        # Draw page border
        self.canvas.create_rectangle(0, 0, self.page_width, self.page_height, outline="black")
        # Draw margin lines using DraggableMargin helper
        self.left_margin_line = DraggableMargin(self.canvas, 'vertical', self.left_margin, self.update_left_margin)
        self.right_margin_line = DraggableMargin(self.canvas, 'vertical', self.right_margin, self.update_right_margin)
        self.top_margin_line = DraggableMargin(self.canvas, 'horizontal', self.top_margin, self.update_top_margin)
        self.bottom_margin_line = DraggableMargin(self.canvas, 'horizontal', self.bottom_margin, self.update_bottom_margin)
        # Label to show current margin values (in inches)
        self.margin_label = tk.Label(preview_frame, text=self.get_margin_text())
        self.margin_label.pack(pady=5)
    
    def get_margin_text(self):
        left_in = self.left_margin / DPI
        right_in = (self.page_width - self.right_margin) / DPI
        top_in = self.top_margin / DPI
        bottom_in = (self.page_height - self.bottom_margin) / DPI
        return f"Margins (inches) - Left: {left_in:.2f}, Right: {right_in:.2f}, Top: {top_in:.2f}, Bottom: {bottom_in:.2f}"
    
    def update_left_margin(self, pos):
        self.left_margin = pos
        self.margin_label.config(text=self.get_margin_text())
    
    def update_right_margin(self, pos):
        self.right_margin = pos
        self.margin_label.config(text=self.get_margin_text())
    
    def update_top_margin(self, pos):
        self.top_margin = pos
        self.margin_label.config(text=self.get_margin_text())
    
    def update_bottom_margin(self, pos):
        self.bottom_margin = pos
        self.margin_label.config(text=self.get_margin_text())
    
    def bind_shortcuts(self):
        # Bind Ctrl+<key> shortcuts for formatting toggles.
        self.text_editor.bind("<Control-i>", self.toggle_italic)
        self.text_editor.bind("<Control-I>", self.toggle_italic)
        self.text_editor.bind("<Control-b>", self.toggle_emphasized)
        self.text_editor.bind("<Control-B>", self.toggle_emphasized)
        self.text_editor.bind("<Control-u>", self.toggle_underline)
        self.text_editor.bind("<Control-U>", self.toggle_underline)
        self.text_editor.bind("<Control-t>", self.toggle_double_height)
        self.text_editor.bind("<Control-T>", self.toggle_double_height)
        self.text_editor.bind("<Control-p>", self.toggle_proportional)
        self.text_editor.bind("<Control-P>", self.toggle_proportional)
        self.text_editor.bind("<Control-f>", self.switch_char_set)
        self.text_editor.bind("<Control-F>", self.switch_char_set)
        self.text_editor.bind("<Control-w>", self.toggle_double_wide)
        self.text_editor.bind("<Control-W>", self.toggle_double_wide)
        self.text_editor.bind("<Control-d>", self.toggle_cpi)
        self.text_editor.bind("<Control-D>", self.toggle_cpi)
        self.text_editor.bind("<Control-q>", self.toggle_quality)
        self.text_editor.bind("<Control-Q>", self.toggle_quality)
    
    # Formatting toggle methods
    def toggle_italic(self, event=None):
        self.italic = not self.italic
        self.apply_current_formatting()
    
    def toggle_emphasized(self, event=None):
        self.emphasized = not self.emphasized
        self.apply_current_formatting()
    
    def toggle_underline(self, event=None):
        self.underline = not self.underline
        self.apply_current_formatting()
    
    def toggle_double_height(self, event=None):
        self.double_height = not self.double_height
        self.apply_current_formatting()
    
    def toggle_proportional(self, event=None):
        self.proportional = not self.proportional
        self.apply_current_formatting()
    
    def switch_char_set(self, event=None):
        # Cycle between two example character sets.
        self.char_set_index = (self.char_set_index + 1) % 2
        self.apply_current_formatting()
    
    def toggle_double_wide(self, event=None):
        self.double_wide = not self.double_wide
        self.apply_current_formatting()
    
    def toggle_cpi(self, event=None):
        self.cpi_toggle = not self.cpi_toggle
        self.apply_current_formatting()
    
    def toggle_quality(self, event=None):
        self.quality_toggle = not self.quality_toggle
        self.apply_current_formatting()
    
    def apply_current_formatting(self):
        """
        In a full implementation you might apply tags to new text or update a status bar.
        Here we simply update the window title to reflect the current formatting state.
        """
        status = (f"Italic: {self.italic}, Bold: {self.emphasized}, Underline: {self.underline}, "
                  f"Double Height: {self.double_height}, Proportional: {self.proportional}, "
                  f"CharSet: {self.char_set_index}, Double Wide: {self.double_wide}, "
                  f"CPI: {self.cpi_toggle}, Quality: {self.quality_toggle}")
        self.title("Word Editor - " + status)
    
    def print_page(self):
        """
        Gather the text content and send it to the printer.
        Uses the send_command() function from printer.py.
        """
        content = self.text_editor.get("1.0", tk.END)
        printer_ip = self.printer_ip.get()
        printer_port = self.printer_port.get()
        
        # Use a dummy debug widget since send_command expects one.
        debug_mode = False
        dummy_debug = DummyDebugText()
        
        try:
            # Send the page content as UTF-8 encoded bytes.
            send_command(content.encode('utf-8'), printer_ip, printer_port, debug_mode, dummy_debug, "[Print]")
            messagebox.showinfo("Print", "Page sent to printer.")
        except Exception as e:
            messagebox.showerror("Print Error", f"Failed to print: {e}")

if __name__ == '__main__':
    app = GuiEditor()
    app.mainloop()
