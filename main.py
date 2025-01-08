#Sergeley 3.4
import sys
import tkinter as tk

from pdf_search_app import PDFSearchApp

sys.stdout.reconfigure(encoding='utf-8')

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFSearchApp(root)
    root.mainloop()
