import os
import logging
import pandas as pd
from random import choice
from string import ascii_lowercase
from json import loads
from pdf2doi import pdf2doi
import re
import tkinter as tk
from tkinter import Toplevel, Label, Frame, Button, Radiobutton



def load_default_directory():
    logger = logging.getLogger(__name__)
    # Get the directory of the running Python file
    script_directory = os.path.dirname(os.path.abspath(__file__))
    default_dir_file = os.path.join(script_directory, 'default_directory.txt')


    # Check if the text file exists
    if os.path.exists(default_dir_file):
        try:
            with open(default_dir_file, 'r', encoding='utf-8') as file:
                directory = file.readline().strip()
                #logger.debug(f"Loaded default directory: {directory}")
                return directory
        except Exception as e:
            logger.error(f"Error reading default directory: {e}")
            return ""
    else:
        logger.warning(f"Default directory file not found: {default_dir_file}")
    return ""

def generate_safe_filename_from_directory(directory):
    # Remove drive letter (e.g., 'C:\')
    directory = re.sub(r'^[a-zA-Z]:\\', '', directory)
    # Replace invalid filename characters with underscores
    safe_filename = re.sub(r'[<>:"/\\|?*]', '_', directory)
    # Replace spaces with underscores
    safe_filename = safe_filename.replace(' ', '_')
    # Limit the filename length if necessary
    safe_filename = safe_filename[:200]  # Adjust as needed
    return f"file_database_{safe_filename}.csv"

def load_database(csv_file):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, csv_file)
    columns = ['Path', 'Name', 'Size', 'Modified Date', 'BibTeX', 'Comments','Last Used Time','Date Added']
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, encoding='utf-8', dtype={'Modified Date': str})
        df = df.loc[:, df.columns.intersection(columns)]
        return df
    else:
        df = pd.DataFrame(columns=columns)
        df.to_csv(csv_path, index=False, encoding='utf-8')
        return df

def generate_unique_key(authors, year):
    if not authors or not year:
        return "unknown"
    first_author_last_name = authors.split(",")[0].split(" ")[0]
    random_letter = choice(ascii_lowercase)
    return f"{first_author_last_name}{year}{random_letter}"

def extract_doi(pdf_path):
    try:
        result = pdf2doi(pdf_path)
        doi = result['identifier']
        validation_info = loads(result['validation_info'])
        title = validation_info.get('title', '')
        authors = " and ".join([f"{author['family']}, {author['given']}" for author in validation_info.get('author', [])])
        year = validation_info.get('created', {}).get('date-parts', [['']])[0][0]
        volume = validation_info.get('volume', '')
        pages = validation_info.get('page', '')
        number = validation_info.get('issue', '')
        journal = validation_info.get('container-title', '')
        publisher = validation_info.get('publisher', '')
        unique_key = generate_unique_key(authors, year)
        bib_info = (
            f"@article{{{unique_key},\n"
            f"  title = {{{title}}},\n"
            f"  author = {{{authors}}},\n"
            f"  year = {{{year}}},\n"
            f"  volume = {{{volume}}},\n"
            f"  pages = {{{pages}}},\n"
            f"  number = {{{number}}},\n"
            f"  journal = {{{journal}}},\n"
            f"  publisher = {{{publisher}}},\n"
            f"  DOI = {{{doi}}},\n"
            f"}}"
        )
        return bib_info
    except Exception as e:
        print(f"Error extracting DOI from {pdf_path}: {e}")
        return ''

def parse_bibtex_field(bibtex_str, field_name):
    if not isinstance(bibtex_str, str):
        return ''
    pattern = re.compile(rf'{field_name}\s*=\s*\{{(.*?)\}}', re.IGNORECASE | re.DOTALL)
    match = pattern.search(bibtex_str)
    if match:
        return match.group(1).replace('\n', ' ').strip()
    else:
        return ''


def show_duplicates_dialog(root, duplicates, font):
    """
    Show a dialog with duplicate files and allow the user to choose which one to delete.

    Parameters:
        root (tk.Tk): The parent window for the dialog.
        duplicates (DataFrame): A DataFrame containing duplicate file information.
        font (tkFont): Font to style the labels and buttons.

    Returns:
        list: A list containing the path of the selected file to delete.
    """
    selected_file = []

    def on_confirm():
        if selected_var.get():
            selected_file.append(selected_var.get())
        dialog_window.destroy()

    dialog_window = Toplevel(root)
    dialog_window.title("Select File to Delete")
    dialog_window.geometry("1150x200")

    frame = Frame(dialog_window)
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    Label(frame, text="Select the file you want to DELETE:", font=font).pack(anchor="w", pady=(0, 10))

    # Create a variable to hold the selected file
    selected_var = tk.StringVar(value="")  # No default selection

    # Display all duplicates with Radiobuttons
    for _, row in duplicates.iterrows():
        Radiobutton(
            frame,
            #text=f"Name: {row['Name']} | Path: {row['Path']}",
            text=f"Path: {row['Path']}",
            variable=selected_var,
            value=row['Path'],
            anchor="w",
            justify="left"
        ).pack(anchor="w")

    Button(
        dialog_window, text="Confirm", command=on_confirm, font=font, width=10
    ).pack(pady=10)

    dialog_window.grab_set()
    dialog_window.wait_window()

    return selected_file
def parse_doi_from_bibtex(bibtex_str):
    """
    Extract DOI field from a BibTeX string.
    """
    if not isinstance(bibtex_str, str):
        return ''
    doi = parse_bibtex_field(bibtex_str, 'doi')
    if not doi:
        doi = parse_bibtex_field(bibtex_str, 'DOI')
    return doi.strip() if doi else ''
    
def format_authors_apa(author_field):
    """
    Convert BibTeX author field to:
    Lastname, I.C.
    Uses only the first author.
    """
    if not author_field:
        return ""

    # BibTeX authors may be separated by 'and'
    first_author = author_field.split(' and ')[0].strip()

    # Handle "Last, First Middle" or "First Middle Last"
    if ',' in first_author:
        last, firsts = [x.strip() for x in first_author.split(',', 1)]
    else:
        parts = first_author.split()
        last = parts[-1]
        firsts = " ".join(parts[:-1])

    initials = "".join(f"{name[0]}." for name in firsts.split() if name)
    return f"{last}, {initials}"
    
def format_authors_aps(author_field):
    """
    Convert BibTeX author field to APS style:
    A. V. Lastname, B. C. Lastname, and D. E. Lastname
    """
    if not author_field:
        return ""

    authors = [a.strip() for a in author_field.split(' and ') if a.strip()]
    formatted = []

    for author in authors:
        # Handle "Last, First Middle" format
        if ',' in author:
            last, firsts = [x.strip() for x in author.split(',', 1)]
            first_parts = firsts.split()
        else:
            parts = author.split()
            last = parts[-1]
            first_parts = parts[:-1]

        initials = " ".join(f"{name[0]}." for name in first_parts if name)
        formatted.append(f"{initials} {last}")

    # APS punctuation rules
    if len(formatted) == 1:
        return formatted[0]
    elif len(formatted) == 2:
        return f"{formatted[0]} and {formatted[1]}"
    else:
        return ", ".join(formatted[:-1]) + ", and " + formatted[-1]


def bibtex_to_reference_aps(bibtex_str):
    """
    Convert BibTeX entry to APS-style reference:

    A. B. Author, C. D. Author, and E. F. Author,
    "Title of the article,"
    Journal Abbrev. Volume(Issue), pages (Year).
    https://doi.org/...

    """
    if not isinstance(bibtex_str, str):
        return ""

    authors = parse_bibtex_field(bibtex_str, 'author')
    title = parse_bibtex_field(bibtex_str, 'title')
    journal = parse_bibtex_field(bibtex_str, 'journal')
    year = parse_bibtex_field(bibtex_str, 'year')
    volume = parse_bibtex_field(bibtex_str, 'volume')
    number = parse_bibtex_field(bibtex_str, 'number')
    pages = parse_bibtex_field(bibtex_str, 'pages')
    doi = parse_doi_from_bibtex(bibtex_str)

    parts = []

    # --- Authors ---
    author_str = format_authors_aps(authors)
    if author_str:
        parts.append(author_str + ",")

    # --- Title ---
    if title:
        parts.append(f"\"{title},\"")

    # --- Journal, volume, issue ---
    journal_part = journal if journal else ""
    if volume:
        journal_part += f" {volume}"
    if number:
        journal_part += f"({number})"

    if journal_part:
        journal_part += ","
        parts.append(journal_part)

    # --- Pages ---
    if pages:
        parts.append(f"{pages}")

    # --- Year ---
    if year:
        parts.append(f"({year}).")

    # --- DOI ---
    if doi:
        parts.append(f"https://doi.org/{doi}")

    return " ".join(parts)
