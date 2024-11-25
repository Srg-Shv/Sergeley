import os
import pandas as pd
from random import choice
from string import ascii_lowercase
from json import loads
from pdf2doi import pdf2doi
import re

def load_default_directory():
    """
    Load the default directory from a text file.
    """
    default_dir_file = 'default_directory.txt'

    # Check if the text file exists
    if os.path.exists(default_dir_file):
        # Read the directory from the file
        with open(default_dir_file, 'r') as file:
            directory = file.readline().strip()
            return directory
    else:
        # If the file does not exist, return an empty string or some default path
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
    columns = ['Path', 'Name', 'Size', 'Modified Date', 'BibTeX', 'Comments']
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
