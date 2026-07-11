import tkinter as tk
from gui import LiveKeystrokeEditor

def main():
    root = tk.Tk()
    app = LiveKeystrokeEditor(root)
    root.mainloop()

if __name__ == '__main__':
    main()
