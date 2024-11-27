import sys
import logging
import tkinter as tk

from pdf_search_app import PDFSearchApp

# Ensure stdout supports UTF-8 encoding
sys.stdout.reconfigure(encoding='utf-8')

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFSearchApp(root)
    root.mainloop()
