import tkinter as tk
from tkinter import Toplevel, Label, Frame, Button

def confirm_extraction(name):
    confirmed = []

    def on_yes():
        confirmed.append(True)
        confirmation_window.destroy()

    def on_no():
        confirmed.append(False)
        confirmation_window.destroy()

    confirmation_window = Toplevel()
    confirmation_window.title("Confirm Extraction")
    confirmation_window.geometry("400x200")

    frame = Frame(confirmation_window)
    frame.pack(pady=10, padx=10, fill="both", expand=True)

    name_label = Label(frame, text=f"Do you want to extract DOI for '{name}'?", wraplength=380, justify="left")
    name_label.pack(pady=10)

    button_frame = Frame(confirmation_window)
    button_frame.pack(pady=20)

    Button(button_frame, text="Yes", command=on_yes, width=10).pack(side="left", padx=20)
    Button(button_frame, text="No", command=on_no, width=10).pack(side="right", padx=20)

    confirmation_window.grab_set()
    confirmation_window.wait_window()

    return confirmed[0]
