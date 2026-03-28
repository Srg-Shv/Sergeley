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
    script_directory = os.path.dirname(os.path.abspath(__file__))
    default_dir_file = os.path.join(script_directory, 'default_directory.txt')

    if os.path.exists(default_dir_file):
        try:
            with open(default_dir_file, 'r', encoding='utf-8') as file:
                directory = file.readline().strip()
                return directory
        except Exception as e:
            logger.error(f"Error reading default directory: {e}")
            return ""
    else:
        logger.warning(f"Default directory file not found: {default_dir_file}")
    return ""

def generate_safe_filename_from_directory(directory):
    directory = re.sub(r'^[a-zA-Z]:\\', '', directory)
    safe_filename = re.sub(r'[<>:"/\\|?*]', '_', directory)
    safe_filename = safe_filename.replace(' ', '_')
    safe_filename = safe_filename[:200]
    return f"file_database_{safe_filename}.csv"

def load_database(csv_file):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, csv_file)
    
    # --- NEW: Added Title, Author, and Year to the schema ---
    columns =['Path', 'Name', 'Size', 'Modified Date', 'BibTeX', 'Comments', 'Last Used Time', 'Date Added', 'Title', 'Author', 'Year']
    
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, encoding='utf-8', dtype={'Modified Date': str})
        
        # Ensure new columns exist in older databases AND have the correct dtype
        for col in['Title', 'Author', 'Year']:
            if col not in df.columns:
                df[col] = pd.NA
            # FIX: Force the column to be 'object' (text) so Pandas doesn't complain 
            # when we insert strings into an empty column.
            df[col] = df[col].astype('object')
                
        df = df.loc[:, df.columns.intersection(columns)]
        
        # --- SELF-HEALING DATABASE LOGIC ---
        # Find rows that have BibTeX but are missing the extracted metadata
        mask = df['BibTeX'].notna() & (df['Title'].isna() | df['Author'].isna() | df['Year'].isna())
        
        if mask.any():
            print(f"Upgrading database: Extracting metadata for {mask.sum()} entries...")
            df.loc[mask, 'Title'] = df.loc[mask, 'BibTeX'].apply(lambda x: parse_bibtex_field(x, 'title'))
            df.loc[mask, 'Author'] = df.loc[mask, 'BibTeX'].apply(lambda x: parse_bibtex_field(x, 'author'))
            df.loc[mask, 'Year'] = df.loc[mask, 'BibTeX'].apply(lambda x: parse_bibtex_field(x, 'year'))
            
            # Save the upgraded database immediately
            df.to_csv(csv_path, index=False, encoding='utf-8')
            
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
        authors = " and ".join([f"{author['family']}, {author['given']}" for author in validation_info.get('author',[])])
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
    selected_file =[]

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

    selected_var = tk.StringVar(value="")

    for _, row in duplicates.iterrows():
        Radiobutton(
            frame,
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
    if not isinstance(bibtex_str, str):
        return ''
    doi = parse_bibtex_field(bibtex_str, 'doi')
    if not doi:
        doi = parse_bibtex_field(bibtex_str, 'DOI')
    return doi.strip() if doi else ''
    
def format_authors_apa(author_field):
    if not author_field:
        return ""

    first_author = author_field.split(' and ')[0].strip()

    if ',' in first_author:
        last, firsts =[x.strip() for x in first_author.split(',', 1)]
    else:
        parts = first_author.split()
        last = parts[-1]
        firsts = " ".join(parts[:-1])

    initials = "".join(f"{name[0]}." for name in firsts.split() if name)
    return f"{last}, {initials}"
    
def format_authors_aps(author_field):
    if not author_field:
        return ""

    authors =[a.strip() for a in author_field.split(' and ') if a.strip()]
    formatted =[]

    for author in authors:
        if ',' in author:
            last, firsts = [x.strip() for x in author.split(',', 1)]
            first_parts = firsts.split()
        else:
            parts = author.split()
            last = parts[-1]
            first_parts = parts[:-1]

        initials = " ".join(f"{name[0]}." for name in first_parts if name)
        formatted.append(f"{initials} {last}")

    if len(formatted) == 1:
        return formatted[0]
    elif len(formatted) == 2:
        return f"{formatted[0]} and {formatted[1]}"
    else:
        return ", ".join(formatted[:-1]) + ", and " + formatted[-1]

def bibtex_to_reference_aps(bibtex_str):
    if not isinstance(bibtex_str, str):
        return ""

    authors = parse_bibtex_field(bibtex_str, 'author')
    title = parse_bibtex_field(bibtex_str, 'title')
    journal = parse_bibtex_field(bibtex_str, 'journal')
    if journal:
        journal = abbreviate_journal(journal)
    year = parse_bibtex_field(bibtex_str, 'year')
    volume = parse_bibtex_field(bibtex_str, 'volume')
    number = parse_bibtex_field(bibtex_str, 'number')
    pages = parse_bibtex_field(bibtex_str, 'pages')
    doi = parse_doi_from_bibtex(bibtex_str)

    parts =[]

    if authors:
        parts.append(format_authors_aps(authors) + ",")
    if title:
        parts.append(f"\"{title},\"")

    journal_part = journal if journal else ""
    if volume:
        journal_part += f" {volume}"
    if number:
        journal_part += f"({number})"

    if journal_part:
        journal_part += ","
        parts.append(journal_part)

    if pages:
        parts.append(f"{pages}")
    if year:
        parts.append(f"({year}).")
    if doi:
        parts.append(f"https://doi.org/{doi}")

    return " ".join(parts)

def abbreviate_journal(journal_name):
    if not journal_name:
        return ""
        
    exact_matches = {
        "Physical Review A": "Phys. Rev. A",
        "Physical Review B": "Phys. Rev. B",
        "Physical Review C": "Phys. Rev. C",
        "Physical Review D": "Phys. Rev. D",
        "Physical Review E": "Phys. Rev. E",
        "Physical Review X": "Phys. Rev. X",
        "Physical Review Letters": "Phys. Rev. Lett.",
        "Applied Physics Letters": "Appl. Phys. Lett.",
        "Journal of Applied Physics": "J. Appl. Phys.",
        "Optics Letters": "Opt. Lett.",
        "Optics Express": "Opt. Express",
        "Nature Photonics": "Nat. Photonics",
        "Nature Communications": "Nat. Commun.",
        "Journal of the Optical Society of America A": "J. Opt. Soc. Am. A",
        "Journal of the Optical Society of America B": "J. Opt. Soc. Am. B",
        "Proceedings of the National Academy of Sciences": "Proc. Natl. Acad. Sci. U.S.A.",
        "Light: Science & Applications": "Light Sci. Appl."
    }
    
    exact_matches_lower = {k.lower(): v for k, v in exact_matches.items()}
    if journal_name.lower() in exact_matches_lower:
        return exact_matches_lower[journal_name.lower()]
        
    word_replacements = {
        r'\bJournal\b': 'J.', r'\bReview\b': 'Rev.', r'\bReviews\b': 'Rev.',
        r'\bPhysical\b': 'Phys.', r'\bPhysics\b': 'Phys.', r'\bApplied\b': 'Appl.',
        r'\bLetters\b': 'Lett.', r'\bOptics\b': 'Opt.', r'\bOptical\b': 'Opt.',
        r'\bSociety\b': 'Soc.', r'\bAmerica\b': 'Am.', r'\bAmerican\b': 'Am.',
        r'\bInternational\b': 'Int.', r'\bCommunications\b': 'Commun.',
        r'\bNature\b': 'Nat.', r'\bScience\b': 'Sci.', r'\bEngineering\b': 'Eng.',
        r'\bTechnology\b': 'Technol.', r'\bProceedings\b': 'Proc.',
        r'\bTransactions\b': 'Trans.', r'\bNational\b': 'Natl.',
        r'\bAcademy\b': 'Acad.', r'\bInstitute\b': 'Inst.', r'\bMaterials\b': 'Mater.',
        r'\bAdvanced\b': 'Adv.', r'\bAdvances\b': 'Adv.', r'\bQuantum\b': 'Quantum', 
        r'\bPhotonics\b': 'Photonics', r'\bChemistry\b': 'Chem.', r'\bChemical\b': 'Chem.',
        r'\bResearch\b': 'Res.', r'\bReports\b': 'Rep.', r'\bElectronics\b': 'Electron.',
        r'\bBiomedical\b': 'Biomed.', r'\bSpectroscopy\b': 'Spectrosc.',
        r'\bMeasurement\b': 'Meas.', r'\bInstruments\b': 'Instrum.', r'\bEuropean\b': 'Eur.',
        r'\bof\b': '', r'\bthe\b': '', r'\band\b': '', r'\b&\b': ''
    }
    
    abbr_name = journal_name
    for word, replacement in word_replacements.items():
        abbr_name = re.sub(word, replacement, abbr_name, flags=re.IGNORECASE)
        
    return re.sub(r'\s+', ' ', abbr_name).strip()
    
def format_authors_lc(author_field):
    r"""
    Converts BibTeX authors to Vancouver/NLM style (Lastname Initials).
    Example: "Livolant, Fran{\c{c}}oise and Bouligand, Yves" -> "Livolant F, Bouligand Y."
    """
    if not author_field:
        return ""
    
    authors = [a.strip() for a in author_field.split(" and ")]
    formatted_authors =[]
    
    for author in authors:
        if "," in author:
            parts = author.split(",", 1)
            last_name = parts[0].strip()
            first_names = parts[1].strip()
        else:
            parts = author.split()
            if len(parts) == 1:
                formatted_authors.append(parts[0])
                continue
            last_name = parts[-1]
            first_names = " ".join(parts[:-1])
        
        last_name = re.sub(r'\{|\}|\\\'|\\`|\\c|\\v|\\~|\\=', '', last_name)
        first_names = re.sub(r'\{|\}|\\\'|\\`|\\c|\\v|\\~|\\=', '', first_names)
        
        first_name_parts = re.split(r'[\s\-]+', first_names)
        initials = ""
        for part in first_name_parts:
            clean_part = re.sub(r'[^a-zA-Z]', '', part)
            if clean_part:
                initials += clean_part[0].upper()
        
        if initials:
            formatted_authors.append(f"{last_name} {initials}")
        else:
            formatted_authors.append(last_name)
            
    return ", ".join(formatted_authors) + "."

def bibtex_to_reference_lc(bibtex_str):
    """
    Convert BibTeX entry to Liquid Crystals (Vancouver/NLM) style reference.
    """
    if not isinstance(bibtex_str, str):
        return ""

    # --- NEW: Removed the nested dummy functions. 
    # It now correctly uses the global functions defined above! ---

    authors = parse_bibtex_field(bibtex_str, 'author')
    title = parse_bibtex_field(bibtex_str, 'title')
    journal = parse_bibtex_field(bibtex_str, 'journal')
    year = parse_bibtex_field(bibtex_str, 'year')
    volume = parse_bibtex_field(bibtex_str, 'volume')
    number = parse_bibtex_field(bibtex_str, 'number')
    pages = parse_bibtex_field(bibtex_str, 'pages')
    doi = parse_doi_from_bibtex(bibtex_str)

    parts =[]

    if authors:
        parts.append(format_authors_lc(authors))

    if title:
        title = title.strip()
        title = re.sub(r'[{}]', '', title)
        if not title.endswith('.'):
            title += '.'
        parts.append(title)

    if journal:
        journal_abbr = abbreviate_journal(journal)
        journal_abbr = journal_abbr.replace('.', '')
        parts.append(f"{journal_abbr}.")

    vol_issue_str = ""
    if year:
        vol_issue_str += f"{year};"
    if volume:
        vol_issue_str += f"{volume}"
    if number:
        vol_issue_str += f"({number})"
    if pages:
        pages_formatted = pages.replace('--', '–')
        vol_issue_str += f":{pages_formatted}"
        
    if vol_issue_str:
        if not vol_issue_str.endswith('.'):
            vol_issue_str += '.'
        parts.append(vol_issue_str)

    if doi:
        parts.append(f"doi: {doi}")

    return " ".join(parts)
