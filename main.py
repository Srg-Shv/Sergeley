import sys
import logging
import tkinter as tk

from pdf_search_app import PDFSearchApp

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Main logger
logger = logging.getLogger(__name__)

# Ensure stdout supports UTF-8 encoding
sys.stdout.reconfigure(encoding='utf-8')

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFSearchApp(root)
    root.mainloop()
