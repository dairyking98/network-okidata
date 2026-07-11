import os
import sys
import tkinter as tk

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "apps", "live_typewriter"))

from okidata_app import LiveKeystrokeEditor


def main():
    root = tk.Tk()
    app = LiveKeystrokeEditor(root)
    root.mainloop()


if __name__ == '__main__':
    main()
