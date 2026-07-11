"""
Live keystroke-to-page typewriter for the IBM Proprinter III emulation, built
on printer.client.Printer instead of a hand-rolled command dict + socket.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from PySide6.QtCore import Qt, QTimer, QEvent
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QSplitter, QPlainTextEdit,
    QHBoxLayout, QVBoxLayout, QGridLayout, QLabel, QLineEdit, QCheckBox,
    QRadioButton, QButtonGroup, QGroupBox, QSpinBox, QDoubleSpinBox,
    QPushButton,
)

from printer.client import Printer
from config import DEFAULT_CONFIG


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
        self.debug_text = QPlainTextEdit()
        self.debug_text.setReadOnly(True)
        self.debug_text.setMaximumWidth(320)
        splitter.addWidget(self.editor)
        splitter.addWidget(self.debug_text)
        splitter.setStretchFactor(0, 1)
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
            ("Line Feed", lambda: self.get_printer().line_feed()),
            ("Carriage Return", lambda: self.get_printer().carriage_return()),
            ("Form Feed", lambda: self.get_printer().form_feed()),
            ("Horizontal Tab", lambda: self.get_printer().horizontal_tab()),
            ("Backspace", lambda: self.get_printer().backspace()),
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
        elif event.key() == Qt.Key_Backspace:
            printer.backspace()
        else:
            text = event.text()
            if text and text.isprintable():
                printer.text(text)

    def handle_return(self):
        printer = self.get_printer()
        cursor = self.editor.textCursor()
        line_text = cursor.block().text()
        line_by_line = self._checked_label(self.mode_group) == "Line-by-Line"

        cursor.insertText("\n")

        printer.carriage_return()
        QTimer.singleShot(10, printer.line_feed)
        QTimer.singleShot(20, self.send_left_margin)
        if line_by_line:
            QTimer.singleShot(30, lambda: printer.text(line_text))
        self.update_line_length_display()

    def send_left_margin(self):
        printer = self.get_printer()
        for _ in range(self.left_margin_count.value()):
            printer.horizontal_tab()

    def update_line_length_display(self):
        cursor = self.editor.textCursor()
        line_text = cursor.block().text()
        char_count = len(line_text)
        cpi_label = self._checked_label(self.cpi_group)
        numeric_cpi = 10.0 if cpi_label == "Condensed" else float(cpi_label or 10)
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
