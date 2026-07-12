"""
Live keystroke-to-page typewriter for the IBM Proprinter III emulation, built
on printer.client.Printer instead of a hand-rolled command dict + socket.
"""

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from PySide6.QtCore import Qt, QTimer, QEvent, QRectF
from PySide6.QtGui import QFont, QPainter
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QSplitter, QPlainTextEdit, QScrollArea,
    QHBoxLayout, QVBoxLayout, QGridLayout, QLabel, QLineEdit, QCheckBox,
    QRadioButton, QButtonGroup, QGroupBox, QSpinBox, QDoubleSpinBox,
    QPushButton,
)

from printer.client import Printer
from config import DEFAULT_CONFIG


@dataclass(frozen=True)
class GlyphStyle:
    bold: bool = False
    italic: bool = False
    underline: bool = False
    overline: bool = False
    stretch: int = 100
    point_size: int = 12
    script: str = "normal"  # "normal" | "superscript" | "subscript"


class PreviewCanvas(QWidget):
    """
    Character-cell grid preview. Unlike a normal text widget, each cell holds
    a *list* of (char, GlyphStyle) layers -- typing over a position (after a
    non-destructive backspace) draws the new glyph on top of the old one in
    the same spot, instead of replacing it, mimicking impact-printer
    overstrike (e.g. backspacing over "e" and typing "h" shows both merged).

    Each row also carries its own pixel height, set from whatever line-
    spacing setting (1/8", 7/72", n/216) was active when that row was
    started -- so a spacing change mid-document is reflected at the row it
    actually took effect on, not retroactively.
    """

    CELL_W = 10
    DEFAULT_ROW_H = 18

    def __init__(self):
        super().__init__()
        self.rows = [self._new_row()]
        self.cursor_row = 0
        self.cursor_col = 0
        self.setMinimumSize(700, self.DEFAULT_ROW_H * 2)

    def _new_row(self, height=None):
        return {"height": height or self.DEFAULT_ROW_H, "cells": [], "page_break": False}

    def write(self, text: str, style: GlyphStyle) -> None:
        cells = self.rows[self.cursor_row]["cells"]
        for ch in text:
            while len(cells) <= self.cursor_col:
                cells.append([])
            cells[self.cursor_col].append((ch, style))
            self.cursor_col += 1
        self._grow()
        self.update()

    def backspace(self) -> None:
        # Non-destructive: move the position back without erasing, like a
        # print head -- the glyph(s) already there stay until overwritten.
        self.cursor_col = max(0, self.cursor_col - 1)
        self.update()

    def newline(self, height=None) -> None:
        self.cursor_row += 1
        self.cursor_col = 0
        while len(self.rows) <= self.cursor_row:
            self.rows.append(self._new_row())
        if height is not None:
            self.rows[self.cursor_row]["height"] = height
        self._grow()
        self.update()

    def page_break(self, height=None) -> None:
        if self.rows[self.cursor_row]["cells"]:
            self.newline(height)
        self.rows[self.cursor_row]["page_break"] = True
        self.newline(height)

    def _grow(self) -> None:
        widest = max((len(r["cells"]) for r in self.rows), default=0)
        width = max(700, (widest + 2) * self.CELL_W)
        height = sum(r["height"] for r in self.rows) + self.DEFAULT_ROW_H * 2
        self.setMinimumSize(width, height)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.white)
        y = 0
        for row in self.rows:
            h = row["height"]
            if row["page_break"]:
                painter.setPen(Qt.gray)
                painter.drawText(
                    QRectF(4, y, self.width() - 8, h),
                    Qt.AlignLeft | Qt.AlignVCenter, "─" * 3 + " page break " + "─" * 3,
                )
                y += h
                continue
            for col_idx, cell in enumerate(row["cells"]):
                x = col_idx * self.CELL_W
                for ch, style in cell:
                    font = QFont("Courier New")
                    font.setPointSize(style.point_size)
                    font.setBold(style.bold)
                    font.setItalic(style.italic)
                    font.setStretch(style.stretch)
                    painter.setFont(font)
                    painter.setPen(Qt.black)
                    cell_y = y
                    if style.script == "superscript":
                        cell_y -= h // 4
                    elif style.script == "subscript":
                        cell_y += h // 4
                    rect = QRectF(x, cell_y, self.CELL_W * 3, h)
                    painter.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, ch)
                    if style.underline:
                        painter.drawLine(x, y + h - 3, x + self.CELL_W, y + h - 3)
                    if style.overline:
                        painter.drawLine(x, y + 3, x + self.CELL_W, y + 3)
            y += h
        painter.end()


class IBMTypewriterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IBM Proprinter III – Live Typewriter")
        self.resize(1000, 700)

        self.printer: Printer | None = None
        self.left_margin_sent = False

        self._build_ui()
        self.editor.installEventFilter(self)

        QTimer.singleShot(500, self.send_all_defaults)

    # ------------------ UI ------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        splitter = QSplitter(Qt.Horizontal)
        self.editor = QPlainTextEdit()
        self.preview = PreviewCanvas()
        preview_scroll = QScrollArea()
        preview_scroll.setWidget(self.preview)
        preview_scroll.setWidgetResizable(False)
        self.preview_scroll = preview_scroll
        self.debug_text = QPlainTextEdit()
        self.debug_text.setReadOnly(True)
        self.debug_text.setMaximumWidth(320)
        splitter.addWidget(self.editor)
        splitter.addWidget(preview_scroll)
        splitter.addWidget(self.debug_text)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, stretch=1)

        controls = QGridLayout()
        root.addLayout(controls)

        # Row 0: connection + debug
        controls.addWidget(QLabel("Printer IP:"), 0, 0)
        self.ip_entry = QLineEdit(DEFAULT_CONFIG["PRINTER_IP"])
        controls.addWidget(self.ip_entry, 0, 1)
        controls.addWidget(QLabel("Port:"), 0, 2)
        self.port_entry = QLineEdit(str(DEFAULT_CONFIG["PRINTER_PORT"]))
        controls.addWidget(self.port_entry, 0, 3)
        self.debug_checkbox = QCheckBox("Debug Mode")
        self.debug_checkbox.setChecked(True)
        controls.addWidget(self.debug_checkbox, 0, 4)

        self.mode_group = self._radio_group(
            controls, 0, 5, "Mode", ["Live", "Line-by-Line"], default="Live"
        )

        # Row 1: formatting toggles
        self.bold_cb = QCheckBox("Emphasized")
        self.bold_cb.toggled.connect(lambda v: self.printer_set(bold=v))
        controls.addWidget(self.bold_cb, 1, 0)

        self.italic_cb = QCheckBox("Italics")
        self.italic_cb.toggled.connect(lambda v: self.printer_set(italic=v))
        controls.addWidget(self.italic_cb, 1, 1)

        self.enhanced_cb = QCheckBox("Enhanced")
        self.enhanced_cb.toggled.connect(lambda v: self.printer_set(enhanced=v))
        controls.addWidget(self.enhanced_cb, 1, 2)

        self.double_width_cb = QCheckBox("Double Wide")
        self.double_width_cb.toggled.connect(lambda v: self.printer_set(double_width=v))
        controls.addWidget(self.double_width_cb, 1, 3)

        # Row 2: extra formatting
        self.underline_cb = QCheckBox("Underline")
        self.underline_cb.toggled.connect(lambda v: self.printer_set(underline=v))
        self.overscore_cb = QCheckBox("Overscore")
        self.overscore_cb.toggled.connect(lambda v: self.printer_set(overscore=v))
        self.proportional_cb = QCheckBox("Proportional")
        self.proportional_cb.toggled.connect(lambda v: self.printer_set(proportional=v))
        extra_box = QGroupBox("Extra Formatting")
        extra_layout = QHBoxLayout(extra_box)
        extra_layout.addWidget(self.underline_cb)
        extra_layout.addWidget(self.overscore_cb)
        extra_layout.addWidget(self.proportional_cb)
        extra_layout.addWidget(QLabel("Script:"))
        self.script_group = QButtonGroup(extra_box)
        for i, label in enumerate(["Normal", "Superscript", "Subscript"]):
            rb = QRadioButton(label)
            rb.setChecked(label == "Normal")
            self.script_group.addButton(rb, i)
            extra_layout.addWidget(rb)
        self.script_group.idClicked.connect(self.apply_script)
        controls.addWidget(extra_box, 2, 0, 1, 6)

        # Row 3: font / cpi
        # Note: no "Publisher" font option and no "Zero style" group here --
        # both were removed from printer.ibm_proprinter.COMMANDS after being
        # confirmed on real hardware to collide with the ESC/P Master Select
        # command, getting the printer stuck with several unrelated
        # attributes (italic, elite pitch, etc.) turned on at once. See the
        # comment in printer/ibm_proprinter.py for details.
        self.font_group = self._radio_group(
            controls, 3, 0, "Character Set", ["IBM Set I", "IBM Set II"],
            default="IBM Set I", span=2,
        )
        self.cpi_group = self._radio_group(
            controls, 3, 2, "CPI", ["10", "12", "15", "Condensed"], default="10", span=2,
        )
        self.font_group.idClicked.connect(self.apply_font)
        self.cpi_group.idClicked.connect(self.apply_cpi)

        # Row 4: spacing / margins
        spacing_box = QGroupBox("Spacing")
        spacing_layout = QHBoxLayout(spacing_box)
        self.spacing_group = QButtonGroup(spacing_box)
        for i, label in enumerate(["1/8", "7/72", "n/144", "n/216"]):
            rb = QRadioButton(label)
            rb.setChecked(label == "1/8")
            if label == "n/144":
                # Confirmed on real hardware: this command has no effect on
                # this printer (n/216 does). See printer/ibm_proprinter.py.
                rb.setEnabled(False)
                rb.setToolTip("Confirmed non-functional on this printer -- use n/216 instead")
            self.spacing_group.addButton(rb, i)
            spacing_layout.addWidget(rb)
        self.spacing_n = QSpinBox()
        self.spacing_n.setRange(0, 255)
        self.spacing_n.setValue(9)
        spacing_layout.addWidget(self.spacing_n)
        self.spacing_group.idClicked.connect(self.apply_spacing)
        self.spacing_n.valueChanged.connect(lambda _: self.apply_spacing())
        controls.addWidget(spacing_box, 4, 0, 1, 2)

        margin_box = QGroupBox("Left Margin (HT count)")
        margin_layout = QHBoxLayout(margin_box)
        self.left_margin_count = QSpinBox()
        self.left_margin_count.setRange(0, 20)
        margin_layout.addWidget(self.left_margin_count)
        controls.addWidget(margin_box, 4, 2)

        controls.addWidget(QLabel("Right Margin (in):"), 4, 3)
        self.right_margin = QDoubleSpinBox()
        self.right_margin.setRange(0, 20)
        self.right_margin.setValue(7.5)
        controls.addWidget(self.right_margin, 4, 4)

        self.line_length_label = QLabel("Line Length: 0.00 in")
        self.line_length_label.setAutoFillBackground(True)
        controls.addWidget(self.line_length_label, 4, 5)

        # Row 5: manual commands
        manual_box = QGroupBox("Manual Commands")
        manual_layout = QHBoxLayout(manual_box)
        manual_commands = [
            ("Line Feed", lambda: (self.get_printer().line_feed(), self.preview_newline())),
            ("Carriage Return", lambda: self.get_printer().carriage_return()),
            ("Form Feed", lambda: (self.get_printer().form_feed(), self.preview_page_break())),
            ("Horizontal Tab", lambda: (self.get_printer().horizontal_tab(), self.preview_write("\t"))),
            ("Backspace", lambda: (self.get_printer().backspace(), self.preview_backspace())),
            ("Reset", lambda: self.get_printer().reset()),
        ]
        for label, action in manual_commands:
            btn = QPushButton(label)
            btn.clicked.connect(action)
            manual_layout.addWidget(btn)
        controls.addWidget(manual_box, 5, 0, 1, 6)

        # Row 6: defaults + status
        self.status_label = QLabel("Live keystrokes are being sent.")
        controls.addWidget(self.status_label, 6, 0, 1, 2)
        defaults_btn = QPushButton("Send Defaults")
        defaults_btn.clicked.connect(self.send_all_defaults)
        controls.addWidget(defaults_btn, 6, 2)

        self.editor.textChanged.connect(self.update_line_length_display)

    def _radio_group(self, layout, row, col, title, labels, default=None, span=1):
        box = QGroupBox(title)
        box_layout = QHBoxLayout(box)
        group = QButtonGroup(box)
        for i, label in enumerate(labels):
            rb = QRadioButton(label)
            if label == default:
                rb.setChecked(True)
            group.addButton(rb, i)
            box_layout.addWidget(rb)
        layout.addWidget(box, row, col, 1, span)
        return group

    def _checked_label(self, group: QButtonGroup) -> str:
        btn = group.checkedButton()
        return btn.text() if btn else ""

    # ------------------ Printer connection ------------------
    def get_printer(self) -> Printer:
        ip = self.ip_entry.text()
        try:
            port = int(self.port_entry.text())
        except ValueError:
            port = DEFAULT_CONFIG["PRINTER_PORT"]
        if self.printer is None or self.printer.ip != ip or self.printer.port != port:
            if self.printer is not None:
                self.printer.close()
            self.printer = Printer(ip, port, on_log=self.log)
        return self.printer

    def log(self, message: str) -> None:
        if self.debug_checkbox.isChecked():
            self.debug_text.appendPlainText(message)

    def printer_set(self, **kwargs) -> None:
        self.get_printer().set(**kwargs)

    # ------------------ WYSIWYG preview ------------------
    # Mirrors the app's own formatting state (the same checkboxes/radios
    # driving Printer.set()) into PreviewCanvas as text is sent, so the
    # preview can't drift from what's actually being sent to the printer.
    # This is not a byte-stream interpreter (see docs/similar-projects-and-
    # roadmap.md) -- it reads GUI state directly, so it's specific to this
    # app rather than reusable by a future headless pipeline.
    _CPI_POINT_SIZE = {"10": 12, "12": 10, "15": 8, "Condensed": 7}
    _CONDENSED_CPI = 17.0  # measured on real hardware, see docs/ibm-proprinter-hardware-findings.md
    _PREVIEW_PX_PER_INCH = 144  # arbitrary scale for the preview canvas, not a hardware value

    def preview_line_height(self) -> int:
        label = self._checked_label(self.spacing_group)
        if label == "7/72":
            inches = 7 / 72
        elif label == "n/216":
            n = self.spacing_n.value()
            inches = (n / 216) if n else (1 / 8)
        else:  # "1/8", or "n/144" (disabled, confirmed non-functional -- falls back to 1/8)
            inches = 1 / 8
        return max(8, round(inches * self._PREVIEW_PX_PER_INCH))

    def preview_style(self) -> GlyphStyle:
        cpi_label = self._checked_label(self.cpi_group)
        script_label = self._checked_label(self.script_group)
        return GlyphStyle(
            bold=self.bold_cb.isChecked() or self.enhanced_cb.isChecked(),
            italic=self.italic_cb.isChecked(),
            underline=self.underline_cb.isChecked(),
            overline=self.overscore_cb.isChecked(),
            stretch=200 if self.double_width_cb.isChecked() else 100,
            point_size=self._CPI_POINT_SIZE.get(cpi_label, 12),
            script=script_label.lower() if script_label in ("Superscript", "Subscript") else "normal",
        )

    def preview_write(self, text: str) -> None:
        self.preview.write(text, self.preview_style())
        self._scroll_preview_to_cursor()

    def preview_newline(self) -> None:
        self.preview.newline(self.preview_line_height())
        self._scroll_preview_to_cursor()

    def preview_backspace(self) -> None:
        self.preview.backspace()

    def preview_page_break(self) -> None:
        self.preview.page_break(self.preview_line_height())
        self._scroll_preview_to_cursor()

    def _scroll_preview_to_cursor(self) -> None:
        bar = self.preview_scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    # ------------------ Formatting application ------------------
    def send_all_defaults(self):
        self.get_printer().reset()
        self.apply_cpi()
        self.apply_font()
        self.apply_spacing()
        self.printer_set(bold=self.bold_cb.isChecked())
        self.printer_set(italic=self.italic_cb.isChecked())
        self.printer_set(enhanced=self.enhanced_cb.isChecked())
        self.printer_set(double_width=self.double_width_cb.isChecked())
        self.printer_set(underline=self.underline_cb.isChecked())
        self.printer_set(overscore=self.overscore_cb.isChecked())
        self.printer_set(proportional=self.proportional_cb.isChecked())
        self.apply_script()

    def apply_font(self, *_):
        label = self._checked_label(self.font_group)
        self.printer_set(font=label)

    def apply_cpi(self, *_):
        label = self._checked_label(self.cpi_group)
        value = "condensed" if label == "Condensed" else int(label)
        self.printer_set(cpi=value)

    def apply_spacing(self, *_):
        label = self._checked_label(self.spacing_group)
        self.printer_set(spacing=(label, self.spacing_n.value()))

    def apply_script(self, *_):
        label = self._checked_label(self.script_group)
        self.printer_set(script=label.lower())

    # ------------------ Live typing ------------------
    def eventFilter(self, obj, event):
        if obj is self.editor and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                self.handle_return()
                return True
            self.handle_key(event)
        return super().eventFilter(obj, event)

    def handle_key(self, event):
        if self._checked_label(self.mode_group) != "Live":
            return
        printer = self.get_printer()
        if event.key() == Qt.Key_Tab:
            printer.horizontal_tab()
            self.preview_write("\t")
        elif event.key() == Qt.Key_Backspace:
            printer.backspace()
            self.preview_backspace()
        else:
            text = event.text()
            if text and text.isprintable():
                printer.text(text)
                self.preview_write(text)

    def handle_return(self):
        printer = self.get_printer()
        cursor = self.editor.textCursor()
        line_text = cursor.block().text()
        line_by_line = self._checked_label(self.mode_group) == "Line-by-Line"

        cursor.insertText("\n")
        self.preview_newline()

        printer.carriage_return()
        QTimer.singleShot(10, printer.line_feed)
        QTimer.singleShot(20, self.send_left_margin)
        if line_by_line:
            QTimer.singleShot(30, lambda: (printer.text(line_text), self.preview_write(line_text)))
        self.update_line_length_display()

    def send_left_margin(self):
        printer = self.get_printer()
        for _ in range(self.left_margin_count.value()):
            printer.horizontal_tab()
            self.preview_write("\t")

    def update_line_length_display(self):
        cursor = self.editor.textCursor()
        line_text = cursor.block().text()
        char_count = len(line_text)
        cpi_label = self._checked_label(self.cpi_group)
        # Condensed measured on real hardware at ~17 cpi (not 10) -- see
        # docs/ibm-proprinter-hardware-findings.md.
        numeric_cpi = self._CONDENSED_CPI if cpi_label == "Condensed" else float(cpi_label or 10)
        effective_cpi = numeric_cpi / 2.0 if self.double_width_cb.isChecked() else numeric_cpi
        try:
            line_length = ((8.0 * self.left_margin_count.value()) / numeric_cpi) + (char_count / effective_cpi)
        except ZeroDivisionError:
            line_length = 0.0
        self.line_length_label.setText(f"Line Length: {line_length:.2f} in")

        gap = self.right_margin.value() - line_length
        color = "lightgreen" if gap >= 0.5 else ("khaki" if gap >= 0 else "salmon")
        self.line_length_label.setStyleSheet(f"background-color: {color};")

    def closeEvent(self, event):
        if self.printer is not None:
            self.printer.close()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    window = IBMTypewriterWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
