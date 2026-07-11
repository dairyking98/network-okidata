import tkinter as tk
from tkinter import messagebox, scrolledtext
import socket
import calendar
from datetime import date, timedelta
import math

# ------------------ Default Configuration ------------------
DEFAULT_CONFIG = {
    "PRINTER_IP": "192.168.4.28",
    "PRINTER_PORT": 9100,
    "DEFAULT_YEAR": 2025,
    "DEFAULT_MONTH": 3,
    "DEFAULT_DAY": 17,  # Reference date for week/day views
    # Page dimensions for week view (in inches)
    "DEFAULT_WEEK_PAGE_WIDTH": 7.75,
    "DEFAULT_WEEK_PAGE_HEIGHT": 9.25,
}

# ------------------ IBM Command Dictionary ------------------
IBM_COMMANDS = {
    "Carriage Return": b"\x0D",          # CR (13)
    "Line Feed": b"\x0A",                # LF (10)
    "Form Feed": b"\x0C",                # FF (12)
    "Italics On": b"\x1B\x25\x47",       # ESC % G
    "Italics Off": b"\x1B\x25\x48",      # ESC % H
    "Emphasized Printing On": b"\x1B\x45",    # ESC E
    "Emphasized Printing Off": b"\x1B\x46",   # ESC F
    "Underline On": b"\x1B\x2D\x01",     # ESC - 1
    "Underline Off": b"\x1B\x2D\x00",    # ESC - 0
    "Overscore On": b"\x1B\x5F\x31",     # ESC _ 1
    "Overscore Off": b"\x1B\x5F\x30",    # ESC _ 0
    "Double Width On": b"\x1B\x57\x31",  # ESC W 1
    "Double Width Off": b"\x1B\x57\x30", # ESC W 0
    "Enhanced Printing On": b"\x1B\x3C",  # Example command; adjust if needed
    "Enhanced Printing Off": b"\x1B\x3E", # Example command; adjust if needed
    "Reset (Clear Print Buffer)": b"\x18"  # CAN (24)
}

# ------------------ Helper: get_embellishment_prefix ------------------
def get_embellishment_prefix(doublewide, emphasized, italic, underline, overscore):
    """Return a tuple (prefix, suffix) of IBM command bytes based on flags."""
    prefix = b""
    suffix = b""
    if doublewide:
        prefix += IBM_COMMANDS["Double Width On"]
        suffix = IBM_COMMANDS["Double Width Off"] + suffix
    if emphasized:
        prefix += IBM_COMMANDS["Emphasized Printing On"]
        suffix = IBM_COMMANDS["Emphasized Printing Off"] + suffix
    if italic:
        prefix += IBM_COMMANDS["Italics On"]
        suffix = IBM_COMMANDS["Italics Off"] + suffix
    if underline:
        prefix += IBM_COMMANDS["Underline On"]
        suffix = IBM_COMMANDS["Underline Off"] + suffix
    if overscore:
        prefix += IBM_COMMANDS["Overscore On"]
        suffix = IBM_COMMANDS["Overscore Off"] + suffix
    return prefix, suffix

# ------------------ Helper: get_embellishment_prefix_no_double ------------------
def get_embellishment_prefix_no_double(emphasized, italic, underline, overscore):
    """Return IBM command bytes for modifiers excluding double width."""
    prefix = b""
    suffix = b""
    if emphasized:
        prefix += IBM_COMMANDS["Emphasized Printing On"]
        suffix = IBM_COMMANDS["Emphasized Printing Off"] + suffix
    if italic:
        prefix += IBM_COMMANDS["Italics On"]
        suffix = IBM_COMMANDS["Italics Off"] + suffix
    if underline:
        prefix += IBM_COMMANDS["Underline On"]
        suffix = IBM_COMMANDS["Underline Off"] + suffix
    if overscore:
        prefix += IBM_COMMANDS["Overscore On"]
        suffix = IBM_COMMANDS["Overscore Off"] + suffix
    return prefix, suffix

# ------------------ Helper: embellish_portion ------------------
def embellish_portion(text, is_double, allocated_columns):
    """
    Returns a tuple (formatted_text, padding).
    - formatted_text: the text portion wrapped with double-wide commands if requested.
    - padding: a bytes string of spaces to reach the allocated_columns.
    
    The modifier commands are applied only to the text and not to the padding.
    """
    text = text.strip()
    if is_double:
        # When in double width, allow at most allocated_columns/2 characters.
        max_chars = allocated_columns // 2
        truncated = text[:max_chars]
        # The text portion is wrapped with the double width commands.
        text_bytes = IBM_COMMANDS["Double Width On"] + truncated.encode("utf-8") + IBM_COMMANDS["Double Width Off"]
        effective = len(truncated) * 2  # each character counts as 2 columns
    else:
        max_chars = allocated_columns
        truncated = text[:max_chars]
        text_bytes = truncated.encode("utf-8")
        effective = len(truncated)
    # Calculate how many (normal width) spaces are needed to fill the cell.
    padding_length = allocated_columns - effective
    padding = b" " * padding_length
    return text_bytes, padding

# ------------------ Helper: embellish_header_line ------------------
def embellish_header_line(header, total_width, day_double, date_double,
                          day_emph, day_italic, day_underline, day_overscore,
                          date_emph, date_italic, date_underline, date_overscore):
    """
    Splits the header string (e.g. "Monday 03/23") into two parts.
    For the first part (day), it applies the double-wide modifier if requested,
    but only to the text. It then pads with normal spaces. The same for the date part.
    Finally, non‐double modifiers (emphasis, italics, underline, overscore) are wrapped
    around the actual text portion only.
    """
    parts = header.split(maxsplit=1)
    if len(parts) == 2:
        day_text, date_text = parts
    else:
        # For a custom header (single string) treat it as a day label.
        text_bytes, padding = embellish_portion(header, day_double, total_width)
        return text_bytes + padding

    # Divide available width roughly equally (with one extra column for a space)
    allocated_day = total_width // 2
    allocated_date = total_width - allocated_day - 1

    # Get the separately formatted text and padding for day and date.
    day_text_bytes, day_padding = embellish_portion(day_text, day_double, allocated_day)
    date_text_bytes, date_padding = embellish_portion(date_text, date_double, allocated_date)

    # Apply non-double modifiers only to the text portions.
    d_prefix, d_suffix = get_embellishment_prefix_no_double(day_emph, day_italic, day_underline, day_overscore)
    dt_prefix, dt_suffix = get_embellishment_prefix_no_double(date_emph, date_italic, date_underline, date_overscore)

    final_day = d_prefix + day_text_bytes + d_suffix + day_padding
    final_date = dt_prefix + date_text_bytes + dt_suffix + date_padding

    # Combine the two parts with a single space separating them.
    return final_day + b" " + final_date

# ------------------ Calendar Printer Application ------------------
class CalendarPrinter:
    def __init__(self, master):
        self.master = master
        master.title("Calendar Generator & Printer")
        
        # Printer connection variables.
        self.printer_ip = tk.StringVar(value=DEFAULT_CONFIG["PRINTER_IP"])
        self.printer_port = tk.IntVar(value=DEFAULT_CONFIG["PRINTER_PORT"])
        
        # Calendar generation variables.
        self.year_var = tk.IntVar(value=DEFAULT_CONFIG["DEFAULT_YEAR"])
        self.month_var = tk.IntVar(value=DEFAULT_CONFIG["DEFAULT_MONTH"])
        self.day_var = tk.IntVar(value=DEFAULT_CONFIG["DEFAULT_DAY"])
        # Initialize week number to current week number
        self.week_var = tk.IntVar(value=date.today().isocalendar()[1])
        
        # Calendar type: Day, Week, Month
        self.cal_type = tk.StringVar(value="Week")
        
        # Week header embellishments.
        self.italic_header = tk.BooleanVar(value=True)
        self.emphasis_header = tk.BooleanVar(value=True)
        
        # Week view page dimensions (inches)
        self.week_page_width = tk.DoubleVar(value=DEFAULT_CONFIG["DEFAULT_WEEK_PAGE_WIDTH"])
        self.week_page_height = tk.DoubleVar(value=DEFAULT_CONFIG["DEFAULT_WEEK_PAGE_HEIGHT"])
        
        # Border character entry fields.
        self.vert_border = tk.StringVar(value="@")
        self.horiz_border = tk.StringVar(value="-")
        self.corner_border = tk.StringVar(value="+")
        
        # 8th Cell Option.
        self.add_eighth_cell = tk.BooleanVar(value=False)
        self.eighth_label = tk.StringVar(value="Custom")
        # 8th cell embellishment options.
        self.eighth_doublewide = tk.BooleanVar(value=False)
        self.eighth_emphasized = tk.BooleanVar(value=False)
        self.eighth_italic = tk.BooleanVar(value=False)
        self.eighth_underline = tk.BooleanVar(value=False)
        self.eighth_overscore = tk.BooleanVar(value=False)
        
        # Day embellishments (for normal cell header – the day portion).
        self.day_doublewide = tk.BooleanVar(value=False)
        self.day_emphasized = tk.BooleanVar(value=False)
        self.day_italic = tk.BooleanVar(value=False)
        self.day_underline = tk.BooleanVar(value=False)
        self.day_overscore = tk.BooleanVar(value=False)
        # Date embellishments (for normal cell header – the date portion).
        self.date_doublewide = tk.BooleanVar(value=False)
        self.date_emphasized = tk.BooleanVar(value=False)
        self.date_italic = tk.BooleanVar(value=False)
        self.date_underline = tk.BooleanVar(value=False)
        self.date_overscore = tk.BooleanVar(value=False)
        
        # Enhanced printing option.
        self.enhanced_printing = tk.BooleanVar(value=False)
        
        # Build input frame.
        input_frame = tk.Frame(master)
        input_frame.pack(padx=10, pady=10)
        
        # --- Date Mode Selection ---
        tk.Label(input_frame, text="Date Mode:").grid(row=0, column=0, sticky="w")
        # Default mode is now Week Number
        self.date_mode = tk.StringVar(value="WeekNumber")
        tk.Radiobutton(input_frame, text="Month/Day", variable=self.date_mode, value="MonthDay",
                       command=self.toggle_date_mode).grid(row=0, column=1, sticky="w", padx=5)
        tk.Radiobutton(input_frame, text="Week Number", variable=self.date_mode, value="WeekNumber",
                       command=self.toggle_date_mode).grid(row=0, column=2, sticky="w", padx=5)
        
        # --- Month/Day Entry Frame ---
        self.monthday_frame = tk.Frame(input_frame)
        self.monthday_frame.grid(row=1, column=0, columnspan=6, pady=5)
        tk.Label(self.monthday_frame, text="Year:").grid(row=0, column=0, sticky="e")
        tk.Entry(self.monthday_frame, textvariable=self.year_var, width=6).grid(row=0, column=1)
        tk.Label(self.monthday_frame, text="Month:").grid(row=0, column=2, sticky="e")
        tk.Entry(self.monthday_frame, textvariable=self.month_var, width=4).grid(row=0, column=3)
        tk.Label(self.monthday_frame, text="Day:").grid(row=0, column=4, sticky="e")
        tk.Entry(self.monthday_frame, textvariable=self.day_var, width=4).grid(row=0, column=5)
        
        # --- Week Number Entry Frame ---
        self.week_frame = tk.Frame(input_frame)
        self.week_frame.grid(row=2, column=0, columnspan=6, pady=5)
        tk.Label(self.week_frame, text="Year:").grid(row=0, column=0, sticky="e")
        tk.Entry(self.week_frame, textvariable=self.year_var, width=6).grid(row=0, column=1)
        tk.Label(self.week_frame, text="Week #:").grid(row=0, column=2, sticky="e")
        tk.Entry(self.week_frame, textvariable=self.week_var, width=4).grid(row=0, column=3)
        # self.week_frame.grid_remove()  # Hide week frame by default
        
        # --- Printer Info ---
        tk.Label(input_frame, text="Printer IP:").grid(row=3, column=0, sticky="e")
        tk.Entry(input_frame, textvariable=self.printer_ip, width=15).grid(row=3, column=1)
        tk.Label(input_frame, text="Port:").grid(row=3, column=2, sticky="e")
        tk.Entry(input_frame, textvariable=self.printer_port, width=6).grid(row=3, column=3)
        
        # --- Calendar Type ---
        cal_type_frame = tk.LabelFrame(input_frame, text="Calendar Type")
        cal_type_frame.grid(row=4, column=0, columnspan=6, pady=5)
        tk.Radiobutton(cal_type_frame, text="Day", variable=self.cal_type, value="Day").pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(cal_type_frame, text="Week (Portrait)", variable=self.cal_type, value="Week").pack(side=tk.LEFT, padx=5)
        tk.Radiobutton(cal_type_frame, text="Month (Landscape)", variable=self.cal_type, value="Month").pack(side=tk.LEFT, padx=5)
        
        # --- Week Header Embellishments ---
        header_emb_frame = tk.LabelFrame(input_frame, text="Week Header Embellishments")
        header_emb_frame.grid(row=5, column=0, columnspan=6, pady=5)
        tk.Checkbutton(header_emb_frame, text="Italic Header", variable=self.italic_header).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(header_emb_frame, text="Emphasized Header", variable=self.emphasis_header).pack(side=tk.LEFT, padx=5)
        
        # --- Enhanced Printing Option (aligned) ---
        tk.Checkbutton(input_frame, text="Enhanced Printing", variable=self.enhanced_printing)\
            .grid(row=6, column=0, columnspan=6, padx=10, pady=5)
        
        # --- Week Page Dimensions ---
        week_dim_frame = tk.LabelFrame(input_frame, text="Week Page Dimensions (inches)")
        week_dim_frame.grid(row=7, column=0, columnspan=6, pady=5)
        tk.Label(week_dim_frame, text="Width:").pack(side=tk.LEFT, padx=5)
        tk.Entry(week_dim_frame, textvariable=self.week_page_width, width=4).pack(side=tk.LEFT, padx=5)
        tk.Label(week_dim_frame, text="Height:").pack(side=tk.LEFT, padx=5)
        tk.Entry(week_dim_frame, textvariable=self.week_page_height, width=4).pack(side=tk.LEFT, padx=5)
        
        # --- Border Characters ---
        border_frame = tk.LabelFrame(input_frame, text="Border Characters")
        border_frame.grid(row=8, column=0, columnspan=6, pady=5)
        tk.Label(border_frame, text="Vertical:").pack(side=tk.LEFT, padx=5)
        tk.Entry(border_frame, textvariable=self.vert_border, width=3).pack(side=tk.LEFT, padx=5)
        tk.Label(border_frame, text="Horizontal:").pack(side=tk.LEFT, padx=5)
        tk.Entry(border_frame, textvariable=self.horiz_border, width=3).pack(side=tk.LEFT, padx=5)
        tk.Label(border_frame, text="Corner:").pack(side=tk.LEFT, padx=5)
        tk.Entry(border_frame, textvariable=self.corner_border, width=3).pack(side=tk.LEFT, padx=5)
        
        # --- 8th Cell Options ---
        eighth_frame = tk.LabelFrame(input_frame, text="8th Cell Options")
        eighth_frame.grid(row=9, column=0, columnspan=6, pady=5)
        tk.Checkbutton(eighth_frame, text="Add 8th Cell", variable=self.add_eighth_cell).pack(side=tk.LEFT, padx=5)
        tk.Label(eighth_frame, text="Label:").pack(side=tk.LEFT, padx=5)
        tk.Entry(eighth_frame, textvariable=self.eighth_label, width=10).pack(side=tk.LEFT, padx=5)
        tk.Label(eighth_frame, text="Embellishments:").pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(eighth_frame, text="Double Wide", variable=self.eighth_doublewide).pack(side=tk.LEFT, padx=2)
        tk.Checkbutton(eighth_frame, text="Emphasized", variable=self.eighth_emphasized).pack(side=tk.LEFT, padx=2)
        tk.Checkbutton(eighth_frame, text="Italic", variable=self.eighth_italic).pack(side=tk.LEFT, padx=2)
        tk.Checkbutton(eighth_frame, text="Underline", variable=self.eighth_underline).pack(side=tk.LEFT, padx=2)
        tk.Checkbutton(eighth_frame, text="Overscore", variable=self.eighth_overscore).pack(side=tk.LEFT, padx=2)
        
        # --- Day Embellishments ---
        day_emb_frame = tk.LabelFrame(input_frame, text="Day (e.g., Sunday) Embellishments")
        day_emb_frame.grid(row=10, column=0, columnspan=6, pady=5)
        tk.Checkbutton(day_emb_frame, text="Double Wide", variable=self.day_doublewide).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(day_emb_frame, text="Emphasized", variable=self.day_emphasized).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(day_emb_frame, text="Italic", variable=self.day_italic).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(day_emb_frame, text="Underline", variable=self.day_underline).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(day_emb_frame, text="Overscore", variable=self.day_overscore).pack(side=tk.LEFT, padx=5)
        
        # --- Date Embellishments ---
        date_emb_frame = tk.LabelFrame(input_frame, text="Date (e.g., 03/23) Embellishments")
        date_emb_frame.grid(row=11, column=0, columnspan=6, pady=5)
        tk.Checkbutton(date_emb_frame, text="Double Wide", variable=self.date_doublewide).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(date_emb_frame, text="Emphasized", variable=self.date_emphasized).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(date_emb_frame, text="Italic", variable=self.date_italic).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(date_emb_frame, text="Underline", variable=self.date_underline).pack(side=tk.LEFT, padx=5)
        tk.Checkbutton(date_emb_frame, text="Overscore", variable=self.date_overscore).pack(side=tk.LEFT, padx=5)
        
        # --- Buttons ---
        btn_frame = tk.Frame(input_frame)
        btn_frame.grid(row=12, column=0, columnspan=6, pady=5)
        tk.Button(btn_frame, text="Generate Calendar", command=self.generate_calendar).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Print Calendar", command=self.print_calendar).pack(side=tk.LEFT, padx=10)
        
        # --- Preview Widget ---
        self.preview = scrolledtext.ScrolledText(master, width=100, height=30)
        self.preview.pack(padx=10, pady=10)

        # At the end of __init__, update the visibility based on the default date mode.
        self.toggle_date_mode()
    
    def toggle_date_mode(self):
        """Show/hide entry fields based on the selected date mode."""
        if self.date_mode.get() == "MonthDay":
            self.monthday_frame.grid()
            self.week_frame.grid_remove()
        else:
            self.monthday_frame.grid_remove()
            self.week_frame.grid()
    
    def create_box(self, header, cell_width, cell_height, embellish=False, day_emb=None, date_emb=None,
                   vert=None, horiz=None, corner=None, day_double=False, date_double=False):
        """
        Create a boxed cell.
          - cell_width and cell_height include borders.
          - For normal cells, header is expected as "DayName MM/DD" and is split into two parts.
          - For custom cells (when date_emb is None), the entire header is wrapped with day modifiers.
          - If embellish is False, returns a list of plain text strings.
          - If True, returns a list of bytes with IBM command bytes applied.
        """
        if vert is None:
            vert = "|"
        if horiz is None:
            horiz = "-"
        if corner is None:
            corner = "+"
        int_width = cell_width - 2  # interior width
        int_height = cell_height - 2  # interior height
        
        if not embellish:
            top = corner + horiz * int_width + corner
            header_line = header[:int_width].ljust(int_width)
            mid = vert + header_line + vert
            interior = [vert + " " * int_width + vert for _ in range(int_height - 1)]
            bottom = corner + horiz * int_width + corner
            return [top, mid] + interior + [bottom]
        else:
            vert_b = vert.encode("utf-8")
            horiz_b = horiz.encode("utf-8")
            corner_b = corner.encode("utf-8")
            top = corner_b + horiz_b * int_width + corner_b
            if date_emb is not None:
                # Normal cell: split header into day and date parts.
                parts = header.split(maxsplit=1)
                if len(parts) == 2:
                    day_text, date_text = parts
                else:
                    day_text = header
                    date_text = ""
                final_line = embellish_header_line(header, int_width, day_double, date_double,
                                                   self.day_emphasized.get(), self.day_italic.get(),
                                                   self.day_underline.get(), self.day_overscore.get(),
                                                   self.date_emphasized.get(), self.date_italic.get(),
                                                   self.date_underline.get(), self.date_overscore.get())
            else:
                # Custom cell: wrap entire header with day modifiers.
                effective_width = int_width // 2 if day_double else int_width
                text_bytes = header.encode("utf-8")
                if len(text_bytes) > effective_width:
                    text_bytes = text_bytes[:effective_width]
                else:
                    text_bytes = text_bytes.ljust(effective_width, b" ")
                d_prefix, d_suffix = get_embellishment_prefix_no_double(
                    self.eighth_emphasized.get(), self.eighth_italic.get(),
                    self.eighth_underline.get(), self.eighth_overscore.get()
                )
                if day_double:
                    final_line = d_prefix + IBM_COMMANDS["Double Width On"] + text_bytes + IBM_COMMANDS["Double Width Off"] + d_suffix
                else:
                    final_line = d_prefix + text_bytes + d_suffix
            mid = vert_b + final_line + vert_b
            interior = [vert_b + b" " * int_width + vert_b for _ in range(int_height - 1)]
            bottom = corner_b + horiz_b * int_width + corner_b
            return [top, mid] + interior + [bottom]
    
    def generate_calendar(self):
        """Generate preview text (plain text, without embellishments) for the selected calendar type."""
        # Determine reference date based on selected date mode.
        if self.date_mode.get() == "MonthDay":
            year = self.year_var.get()
            month = self.month_var.get()
            day = self.day_var.get()
            try:
                ref_date = date(year, month, day)
            except Exception as e:
                messagebox.showerror("Error", f"Invalid date: {e}")
                return
        else:
            year = self.year_var.get()
            try:
                ref_date = date.fromisocalendar(year, self.week_var.get(), 1)  # Monday of the given ISO week
            except Exception as e:
                messagebox.showerror("Error", f"Invalid week number: {e}")
                return
        
        cal_type = self.cal_type.get()
        output = ""
        if cal_type == "Month":
            # For Month, if in Week Number mode, use the month from the computed reference date.
            month_to_print = ref_date.month if self.date_mode.get() == "WeekNumber" else self.month_var.get()
            output = calendar.month(ref_date.year, month_to_print)
        elif cal_type == "Day":
            output += "Day Calendar: " + ref_date.strftime("%A, %Y-%m-%d") + "\n"
            output += "-" * 40 + "\nNo appointments scheduled.\n"
        elif cal_type == "Week":
            # For week view, allow the schedule to start on the specified date.
            start_day = ref_date  # In Month/Day mode, the schedule starts on the entered day.
                                  # In Week Number mode, ref_date comes from ISO (Monday).
            week_number = start_day.isocalendar()[1]
            total_chars = int(self.week_page_width.get() * 10)  # 10 chars per inch
            total_lines = int(self.week_page_height.get() * 6)    # 6 lines per inch
            header_lines = 3  # Reserve 3 lines for week header.
            rows = 4        # 2 columns x 4 rows = 8 cells.
            gaps = rows - 1 # blank line between rows.
            available_lines = total_lines - header_lines - gaps
            cell_height = available_lines // rows
            cell_width = total_chars // 2
            week_header = f"Week of {start_day.strftime('%Y-%m-%d')} (Week {week_number}) - {start_day.strftime('%B %Y')}"
            horiz = self.horiz_border.get()
            header_line = week_header.center(total_chars, horiz)
            lines = [header_line, "", ""]
            cells = []
            for i in range(7):
                d = start_day + timedelta(days=i)
                cell_header = f"{d.strftime('%A')} {d.strftime('%m/%d')}"
                box = self.create_box(cell_header, cell_width, cell_height, embellish=False,
                                        vert=self.vert_border.get(),
                                        horiz=self.horiz_border.get(),
                                        corner=self.corner_border.get())
                cells.append(box)
            if self.add_eighth_cell.get():
                custom = self.eighth_label.get()
                box = self.create_box(custom, cell_width, cell_height, embellish=False,
                                      vert=self.vert_border.get(),
                                      horiz=self.horiz_border.get(),
                                      corner=self.corner_border.get())
            else:
                box = [" " * cell_width] * (cell_height + 2)
            cells.append(box)
            grid_lines = []
            for r in range(rows):
                left_box = cells[r * 2]
                right_box = cells[r * 2 + 1]
                for li in range(len(left_box)):
                    merged = left_box[li] + "  " + right_box[li]
                    grid_lines.append(merged)
                grid_lines.append("")
            lines.extend(grid_lines)
            output = "\n".join(lines)
        else:
            output = "Unsupported calendar type."
        self.preview.delete("1.0", tk.END)
        self.preview.insert(tk.END, output)
    
    def print_calendar(self):
        """Generate embellished output and send it to the printer (with Form Feed at the end)."""
        cal_type = self.cal_type.get()
        printer_ip = self.printer_ip.get()
        try:
            printer_port = int(self.printer_port.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid port number.")
            return
        
        # Determine reference date.
        if self.date_mode.get() == "MonthDay":
            year = self.year_var.get()
            month = self.month_var.get()
            day = self.day_var.get()
            try:
                ref_date = date(year, month, day)
            except Exception as e:
                messagebox.showerror("Error", f"Invalid date: {e}")
                return
        else:
            year = self.year_var.get()
            try:
                ref_date = date.fromisocalendar(year, self.week_var.get(), 1)
            except Exception as e:
                messagebox.showerror("Error", f"Invalid week number: {e}")
                return
        
        output_bytes = b""
        if cal_type in ["Day", "Month"]:
            cal_text = self.preview.get("1.0", tk.END)
            lines = cal_text.splitlines()
            header_applied = False
            for line in lines:
                if not header_applied and line.strip():
                    header_bytes = b""
                    if self.italic_header.get():
                        header_bytes += IBM_COMMANDS["Italics On"]
                    if self.emphasis_header.get():
                        header_bytes += IBM_COMMANDS["Emphasized Printing On"]
                    header_bytes += line.encode("utf-8")
                    if self.emphasis_header.get():
                        header_bytes += IBM_COMMANDS["Emphasized Printing Off"]
                    if self.italic_header.get():
                        header_bytes += IBM_COMMANDS["Italics Off"]
                    output_bytes += header_bytes + IBM_COMMANDS["Carriage Return"] + IBM_COMMANDS["Line Feed"]
                    header_applied = True
                else:
                    output_bytes += line.encode("utf-8") + IBM_COMMANDS["Carriage Return"] + IBM_COMMANDS["Line Feed"]
        elif cal_type == "Week":
            if self.date_mode.get() == "MonthDay":
                try:
                    current_date = date(self.year_var.get(), self.month_var.get(), self.day_var.get())
                except Exception as e:
                    messagebox.showerror("Error", f"Invalid date: {e}")
                    return
                start_day = current_date  # Use the entered date as the starting day
            else:
                try:
                    start_day = date.fromisocalendar(self.year_var.get(), self.week_var.get(), 1)
                except Exception as e:
                    messagebox.showerror("Error", f"Invalid week number: {e}")
                    return
            week_number = start_day.isocalendar()[1]
            total_chars = int(self.week_page_width.get() * 10)
            total_lines = int(self.week_page_height.get() * 6)
            header_lines = 3
            rows = 4
            gaps = rows - 1
            available_lines = total_lines - header_lines - gaps
            cell_height = available_lines // rows
            cell_width = total_chars // 2
            horiz = self.horiz_border.get()
            week_header = f"Week of {start_day.strftime('%Y-%m-%d')} (Week {week_number}) - {start_day.strftime('%B %Y')}"
            header_line = week_header.center(total_chars, horiz)
            header_bytes = b""
            if self.italic_header.get():
                header_bytes += IBM_COMMANDS["Italics On"]
            if self.emphasis_header.get():
                header_bytes += IBM_COMMANDS["Emphasized Printing On"]
            header_bytes += header_line.encode("utf-8")
            if self.emphasis_header.get():
                header_bytes += IBM_COMMANDS["Emphasized Printing Off"]
            if self.italic_header.get():
                header_bytes += IBM_COMMANDS["Italics Off"]
            out_lines = [header_bytes, b"", b""]
            # Build each header line with embellishments.
            day_emb = get_embellishment_prefix_no_double(
                self.day_emphasized.get(), self.day_italic.get(),
                self.day_underline.get(), self.day_overscore.get()
            )
            date_emb = get_embellishment_prefix_no_double(
                self.date_emphasized.get(), self.date_italic.get(),
                self.date_underline.get(), self.date_overscore.get()
            )
            cells = []
            for i in range(7):
                d = start_day + timedelta(days=i)
                cell_header = f"{d.strftime('%A')} {d.strftime('%m/%d')}"
                box = self.create_box(cell_header, cell_width, cell_height, embellish=True,
                                       day_emb=day_emb, date_emb=date_emb,
                                       vert=self.vert_border.get(), horiz=self.horiz_border.get(),
                                       corner=self.corner_border.get(),
                                       day_double=self.day_doublewide.get(),
                                       date_double=self.date_doublewide.get())
                cells.append(box)
            if self.add_eighth_cell.get():
                custom = self.eighth_label.get()
                box = self.create_box(custom, cell_width, cell_height, embellish=True,
                                      day_emb=get_embellishment_prefix_no_double(
                                          self.eighth_emphasized.get(), self.eighth_italic.get(),
                                          self.eighth_underline.get(), self.eighth_overscore.get()
                                      ),
                                      date_emb=None,  # For custom cell, wrap entire text
                                      vert=self.vert_border.get(), horiz=self.horiz_border.get(),
                                      corner=self.corner_border.get(),
                                      day_double=self.eighth_doublewide.get(),
                                      date_double=False)
            else:
                box = [b" " * cell_width] * (cell_height + 2)
            cells.append(box)
            grid_lines = []
            for r in range(rows):
                left_box = cells[r * 2]
                right_box = cells[r * 2 + 1]
                for li in range(len(left_box)):
                    merged = left_box[li] + b"  " + right_box[li]
                    grid_lines.append(merged)
                grid_lines.append(b"")
            for line in out_lines + grid_lines:
                output_bytes += line + IBM_COMMANDS["Carriage Return"] + IBM_COMMANDS["Line Feed"]
        else:
            output_bytes = b"Unsupported calendar type."
        
        if self.enhanced_printing.get():
            output_bytes = IBM_COMMANDS["Enhanced Printing On"] + output_bytes + IBM_COMMANDS["Enhanced Printing Off"]
        
        output_bytes += IBM_COMMANDS["Form Feed"]
        
        try:
            with socket.create_connection((printer_ip, printer_port), timeout=5) as s:
                s.sendall(output_bytes)
            messagebox.showinfo("Success", "Calendar sent to printer.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send calendar: {e}")

def main():
    root = tk.Tk()
    app = CalendarPrinter(root)
    root.mainloop()

if __name__ == '__main__':
    main()
