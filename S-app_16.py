import sys
import pandas as pd
from os import path, walk, startfile, remove, makedirs
from time import ctime
from random import choice
from string import ascii_lowercase
from json import loads
from pdf2doi import pdf2doi
from pyperclip import copy
from fuzzywuzzy import fuzz
import tkinter as tk
from tkinter import END, DISABLED, messagebox, Button, Toplevel, Text, Frame, Label, Canvas, Scrollbar
from tkinter import font as tkfont
from subprocess import call
from datetime import datetime, timedelta
from dateutil.parser import parse


# Ensure stdout supports UTF-8 encoding
sys.stdout.reconfigure(encoding='utf-8')

def load_database(csv_file):
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Combine the script directory with the csv_file name
    csv_path = os.path.join(script_dir, csv_file)
    
    # Define the columns we need
    columns = ['Path', 'Name', 'Size', 'Modified Date', 'BibTeX', 'Comments']
    
    # Check if the CSV file exists
    if os.path.exists(csv_path):
        # Read the CSV without parsing 'Modified Date'
        df = pd.read_csv(csv_path, encoding='utf-8', dtype={'Modified Date': str})
        # Ensure only the columns we need are in the DataFrame
        df = df.loc[:, df.columns.intersection(columns)]
        return df
    else:
        # Create an empty DataFrame with the defined columns
        df = pd.DataFrame(columns=columns)
        # Save the empty DataFrame to a CSV file
        df.to_csv(csv_path, index=False, encoding='utf-8')
        return df

def generate_unique_key(authors, year):
    """
    Generate a unique key based on the first author's last name, year, and a random letter.
    """
    if not authors or not year:
        return "unknown"
    first_author_last_name = authors.split(",")[0].split(" ")[0]
    random_letter = random.choice(string.ascii_lowercase)
    return f"{first_author_last_name}{year}{random_letter}"

def extract_doi(pdf_path):
    """
    Extract DOI and BibTeX information from a PDF file.
    """
    try:
        result = pdf2doi.pdf2doi(pdf_path)
        doi = result['identifier']
        validation_info = json.loads(result['validation_info'])
        
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

def scan_directory(directory, existing_files_info):
    """
    Scan a directory to collect PDF file information and extract BibTeX details.
    """
    # Check if the directory exists
    if not os.path.exists(directory):
        messagebox.showerror("Error", f"The directory '{directory}' does not exist.")
        return

    new_data = []
    updated_data = []
    new_files_found = 0
    updated_files_found = 0

    for root, _, files in os.walk(directory):
        for file in files:
            full_path = os.path.join(root, file)
            size = os.path.getsize(full_path)
            modified_date = time.ctime(os.path.getmtime(full_path))  # Keep using time.ctime()
            extension = os.path.splitext(file)[1].lower()
            if extension == '.pdf':
                if full_path not in existing_files_info:
                    if confirm_extraction(file):
                        bib_info = extract_doi(full_path)
                    else:
                        bib_info = ''
                    new_data.append([full_path, file, extension, size, modified_date, bib_info, ''])
                    new_files_found += 1
                elif size != existing_files_info[full_path]['size'] or modified_date != existing_files_info[full_path]['modified_date']:
                    updated_data.append([full_path, file, extension, size, modified_date])
                    updated_files_found += 1
    return new_data, updated_data, new_files_found, updated_files_found

def check_database_validity(directory, csv_file):
    """
    Check and update the file database for a directory.
    """
    df = load_database(csv_file)
    existing_files_info = {
        row['Path']: {'size': row['Size'], 'modified_date': row['Modified Date']}
        for _, row in df.iterrows()
    }
    missing_files = [file_path for file_path in existing_files_info if not os.path.exists(file_path)]
    
    messages = []
    if missing_files:
        messages.append(f"Removing {len(missing_files)} missing file(s) from the database.")
        df = df[~df['Path'].isin(missing_files)]
    
    new_data, updated_data, new_files_found, updated_files_found = scan_directory(directory, existing_files_info)
    if new_files_found > 0:
        columns = ['Path', 'Name', 'Extension', 'Size', 'Modified Date', 'BibTeX', 'Comments']
        new_df = pd.DataFrame(new_data, columns=columns)
        df = pd.concat([df, new_df], ignore_index=True)
        messages.append(f"Database has been updated with {new_files_found} new file(s).")
    else:
        messages.append(f"Database has been updated with 0 new file(s).")
    
    if updated_files_found > 0:
        for updated_row in updated_data:
            full_path = updated_row[0]
            df.loc[df['Path'] == full_path, ['Size', 'Modified Date']] = updated_row[3:5]
        messages.append(f"Database has been updated with {updated_files_found} modified file(s).")
    else:
        messages.append(f"Database has been updated with 0 modified file(s).")
    
    df.to_csv(csv_file, index=False, encoding='utf-8')
    messages.append(f"Database has been cleaned by removing {len(missing_files)} missing file(s).")
    
    messagebox.showinfo("Database Update", "\n".join(messages))
    return df

def confirm_deletion(item):
    """
    Create a confirmation window to ask the user whether to delete the given file.
    """
    confirmed = []

    def on_yes():
        confirmed.append(True)
        confirmation_window.destroy()

    def on_no():
        confirmed.append(False)
        confirmation_window.destroy()

    confirmation_window = Toplevel()
    confirmation_window.title("Confirm Deletion")
    confirmation_window.geometry("400x300")

    frame = Frame(confirmation_window)
    frame.pack(pady=10, padx=10, fill="both", expand=True)
    
    details = f"Found duplicate:\nName: {item['Name']}\nPath: {item['Path']}"
    details_label = Label(frame, text=details, wraplength=380, justify="left")
    details_label.pack(pady=10)

    button_frame = Frame(confirmation_window)
    button_frame.pack(pady=20)
    
    Button(button_frame, text="Yes", command=on_yes, width=10).pack(side="left", padx=20)
    Button(button_frame, text="No", command=on_no, width=10).pack(side="right", padx=20)

    confirmation_window.grab_set()
    confirmation_window.wait_window()

    return confirmed[0]

def confirm_extraction(name):
    """
    Create a confirmation window to ask the user whether to extract DOI for the given file.
    """
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

def parse_bibtex_field(bibtex_str, field_name):
    import re
    if not isinstance(bibtex_str, str):
        return ''
    pattern = re.compile(rf'{field_name}\s*=\s*\{{(.*?)\}}', re.IGNORECASE | re.DOTALL)
    match = pattern.search(bibtex_str)
    if match:
        return match.group(1).replace('\n', ' ').strip()
    else:
        return ''

def remove_duplicates(df, csv_file):
    """
    Remove duplicate entries based on the DOI extracted from the 'BibTeX' column and delete corresponding PDF files.
    """
    # Function to extract DOI from BibTeX
    def extract_doi_from_bibtex(bibtex_str):
        return parse_bibtex_field(bibtex_str, 'DOI')
    
    # Extract DOI from 'BibTeX' column and create a new column 'DOI_extracted'
    df['DOI_extracted'] = df['BibTeX'].apply(extract_doi_from_bibtex)
    
    # Separate rows with and without extracted DOI
    df_with_doi = df[df['DOI_extracted'].notna() & df['DOI_extracted'].str.strip().astype(bool)]
    df_without_doi = df[~df.index.isin(df_with_doi.index)]
    
    # Find duplicates within rows that have DOI
    duplicates = df_with_doi[df_with_doi.duplicated(subset='DOI_extracted', keep=False)]
    
    # Group duplicates by DOI
    grouped_duplicates = duplicates.groupby('DOI_extracted')
    
    files_to_delete = []
    indices_to_delete = []
    
    for doi, group in grouped_duplicates:
        first_entry = group.iloc[0]
        duplicates_to_delete = group.iloc[1:]
    
        for _, item in duplicates_to_delete.iterrows():
            if confirm_deletion(item):
                files_to_delete.append(item['Path'])
                indices_to_delete.append(item.name)
    
    df_with_doi = df_with_doi.drop(index=indices_to_delete)
    
    # Drop the 'DOI_extracted' column
    df_with_doi = df_with_doi.drop(columns=['DOI_extracted'])
    
    # Combine the rows with and without DOI back together
    updated_df = pd.concat([df_with_doi, df_without_doi])
    updated_df.to_csv(csv_file, index=False, encoding='utf-8')
    
    deleted_files = []
    for file_path in files_to_delete:
        if os.path.exists(file_path):
            os.remove(file_path)
            deleted_files.append(file_path)

import pandas as pd
import os
import time
import random
import string
import json
import pdf2doi
import sys
import pyperclip
from fuzzywuzzy import fuzz
import tkinter as tk
from tkinter import END, DISABLED, messagebox, Button, Toplevel, Text, Frame, Label, Canvas, Scrollbar, Listbox
from tkinter import font as tkfont
import subprocess
import datetime
from dateutil import parser
import re  # Added for regex operations

# Ensure stdout supports UTF-8 encoding
sys.stdout.reconfigure(encoding='utf-8')

# ... [Assuming other functions like load_database, parse_bibtex_field, etc., remain unchanged] ...

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

class PDFSearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Search")
        self.root.geometry("1200x800")

        self.df = load_database('file_database.csv')
        self.results = pd.DataFrame()

        self.custom_font = tkfont.Font(family="Helvetica", size=11)
        self.title_font = tkfont.Font(family="Helvetica", size=11, weight="bold")
        
        # Frame for directory and update        
        dir_update_frame = Frame(root)
        dir_update_frame.pack(pady=10)
        
        # Running message label
        self.running_label = tk.Label(root, text="", font=self.custom_font, fg="red")
        self.running_label.pack(pady=10)

        tk.Label(dir_update_frame, text="Set Directory to Scan:", font=self.custom_font).pack()
        self.entry_directory = tk.Entry(dir_update_frame, font=self.custom_font)
        self.entry_directory.pack()

        # Load the default directory from the text file
        default_directory = load_default_directory()
        self.entry_directory.insert(0, default_directory if default_directory else 'F:\\_Papers\\2024')

        update_button = tk.Button(dir_update_frame, text="Update Database", command=self.update_database, font=self.custom_font)
        update_button.pack()

        # Frame for search options
        search_frame = Frame(root)
        search_frame.pack(pady=10)
        
        # Add the "Show Tags" button
        tag_button = tk.Button(search_frame, text="Show {Tags}", command=self.show_tags, font=self.custom_font)
        tag_button.pack()
        
        recent_button = tk.Button(search_frame, text="Show Recent Papers", command=self.show_recent_papers, font=self.custom_font)
        recent_button.pack()

        tk.Label(search_frame, text="Enter search keywords:", font=self.custom_font).pack()
        self.entry_keywords = tk.Entry(search_frame, font=self.custom_font)
        self.entry_keywords.pack()

        tk.Label(search_frame, text="Enter similarity threshold (0-100):", font=self.custom_font).pack()
        self.entry_threshold = tk.Entry(search_frame, font=self.custom_font)
        self.entry_threshold.pack()
        if not self.entry_threshold.get():
            self.entry_threshold.insert(0, "70")

        search_button = tk.Button(search_frame, text="Search", command=self.search, font=self.custom_font)
        search_button.pack()


        
        self.root.bind('<Return>', lambda event: self.search())

        self.results_container = Frame(root)
        self.results_container.pack(fill=tk.BOTH, expand=True)

        self.canvas = Canvas(self.results_container)
        self.scrollbar = Scrollbar(self.results_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind_all("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind_all("<Button-4>", self._on_mouse_wheel)
        self.canvas.bind_all("<Button-5>", self._on_mouse_wheel)

    def _on_mouse_wheel(self, event):
        if event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")

    def fuzzy_search_database(self, df, keywords, threshold=70):
        keywords = [keyword.lower() for keyword in keywords]
        columns_to_search = ['Path', 'Name', 'BibTeX', 'Comments']

        def match_row(row, keywords):
            row_str = ' '.join(str(row[col]) for col in columns_to_search if col in row).lower()
            individual_scores = [fuzz.partial_ratio(keyword, row_str) for keyword in keywords]
            combined_keywords = ' '.join(keywords)
            combined_score = fuzz.token_set_ratio(combined_keywords, row_str)
            return all(score >= threshold for score in individual_scores) or combined_score >= threshold

        mask = df.apply(lambda row: match_row(row, keywords), axis=1)
        result_df = df[mask].reset_index(drop=True)

        return result_df

    def open_pdf(self, file_path):
        if os.path.exists(file_path):
            os.startfile(file_path)
        else:
            messagebox.showerror("Error", f"File not found: {file_path}")

    def copy_bibtex(self, index):
        bib_info = self.results.iloc[index]['BibTeX']
        if pd.notna(bib_info):
            pyperclip.copy(bib_info)
        else:
            messagebox.showerror("Error", "BibTeX info not available for this entry.")

    def open_comments_window(self, index):
        comments = self.results.iloc[index]['Comments']

        def save_comments():
            new_comments = text_comments.get("1.0", END).strip()
            self.results.at[index, 'Comments'] = new_comments
            self.df.loc[self.df['Path'] == self.results.iloc[index]['Path'], 'Comments'] = new_comments
            self.save_to_csv('file_database.csv')
            messagebox.showinfo("Success", "Comments updated.")
            comment_window.destroy()

        comment_window = Toplevel(self.root)
        comment_window.title("Edit Comments")

        text_comments = Text(comment_window, width=100, height=20, font=self.custom_font)
        text_comments.pack()
        text_comments.insert(END, comments if pd.notna(comments) else "")

        save_button = Button(comment_window, text="Save", command=save_comments, font=self.custom_font)
        save_button.pack()

    def open_bibtex_window(self, index):
        """
        Open a window to edit the BibTeX information for the selected paper.
        """
        bibtex_info = self.results.iloc[index]['BibTeX']

        def save_bibtex():
            new_bibtex = text_bibtex.get("1.0", END).strip()
            self.results.at[index, 'BibTeX'] = new_bibtex
            self.df.loc[self.df['Path'] == self.results.iloc[index]['Path'], 'BibTeX'] = new_bibtex
            self.save_to_csv('file_database.csv')
            messagebox.showinfo("Success", "BibTeX information updated.")
            bibtex_window.destroy()

        bibtex_window = Toplevel(self.root)
        bibtex_window.title("Edit BibTeX")

        text_bibtex = Text(bibtex_window, width=100, height=20, font=self.custom_font)
        text_bibtex.pack()
        text_bibtex.insert(END, bibtex_info if pd.notna(bibtex_info) else "")

        save_button = Button(bibtex_window, text="Save", command=save_bibtex, font=self.custom_font)
        save_button.pack()

    def save_to_csv(self, csv_file):
        self.df.to_csv(csv_file, index=False, encoding='utf-8')

    def search(self):
        keywords = self.entry_keywords.get().split()
        threshold = int(self.entry_threshold.get())

        if not keywords:
            messagebox.showerror("Error", "Please enter search keywords.")
            return

        self.results = self.fuzzy_search_database(self.df, keywords, threshold).copy()  # Add .copy()
        self.display_results()


    def display_results(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        if self.results.empty:
            messagebox.showinfo("No Results", "No matching results found.")
            return

        # Extract 'year' from BibTeX and add it as a column in the results DataFrame
        self.results['Year'] = self.results['BibTeX'].apply(lambda bibtex: parse_bibtex_field(bibtex, 'year'))
        
        # Convert 'Year' column to numeric values for sorting, non-numeric values will be set as NaN
        self.results['Year'] = pd.to_numeric(self.results['Year'], errors='coerce')
        
        # Sort the DataFrame by 'Year' in descending order
        self.results = self.results.sort_values(by='Year', ascending=False, na_position='last').reset_index(drop=True)

        # Get the default background color of the app window
        default_bg_color = self.root.cget("bg")

        for index, row in self.results.iterrows():
            bibtex_str = row['BibTeX']
            if not isinstance(bibtex_str, str):
                bibtex_str = ''
            elif pd.isna(bibtex_str):
                bibtex_str = ''

            title = parse_bibtex_field(bibtex_str, 'title')
            author = parse_bibtex_field(bibtex_str, 'author')
            year = row['Year']  # We have already extracted and sorted by year

            # If title is empty, display the file path instead
            if not title:
                title = f"Path: {row['Path']}"

            # If the year is NaN (missing), display it as '-'
            year = '-' if pd.isna(year) else int(year)

            # Frame for bibliography information, expanding horizontally
            frame_biblio = Frame(self.scrollable_frame, pady=5)
            frame_biblio.pack(fill=tk.X, padx=10, pady=5, expand=True)

            # Construct bibliography text
            bibliography_text = f"{year} - {title} - {author}"

            # Text widget to display bibliography text with wrapping
            text_biblio = Text(
                frame_biblio,
                font=self.title_font,
                fg="blue",
                bg=default_bg_color,
                wrap='word',
                height=2,
                borderwidth=0,
                width=130  # Adjust the width as needed
            )
            text_biblio.insert(tk.END, bibliography_text)
            text_biblio.config(state=tk.DISABLED)
            text_biblio.pack(anchor="w", fill='x', expand=True)

            # Frame for buttons
            frame_buttons = Frame(self.scrollable_frame)
            frame_buttons.pack(fill=tk.X, padx=10, pady=5)

            Button(
                frame_buttons,
                text="Open PDF",
                command=lambda p=row['Path']: self.open_pdf(p),
                font=self.custom_font
            ).pack(side="left", padx=(0, 10))
            Button(
                frame_buttons,
                text="Copy BibTeX",
                command=lambda i=index: self.copy_bibtex(i),
                font=self.custom_font
            ).pack(side="left", padx=(0, 10))
            Button(
                frame_buttons,
                text="Edit BibTeX",
                command=lambda i=index: self.open_bibtex_window(i),
                font=self.custom_font
            ).pack(side="left", padx=(0, 10))
            Button(
                frame_buttons,
                text="Edit Comments",
                command=lambda i=index: self.open_comments_window(i),
                font=self.custom_font
            ).pack(side="left", padx=(0, 10))

    def show_running_message(self):
        self.running_label.config(text="Running...")
        self.root.update_idletasks()

    def hide_running_message(self):
        self.running_label.config(text="")
        self.root.update_idletasks()

    def update_database(self):
        try:
            self.show_running_message()
            directory_to_scan = self.entry_directory.get()
            if not directory_to_scan:
                messagebox.showerror("Error", "Please set a directory to scan first.")
                return
            df = check_database_validity(directory_to_scan, 'file_database.csv')
            remove_duplicates(df, 'file_database.csv')
            self.df = load_database('file_database.csv')
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update database: {e}")
        finally:
            self.hide_running_message()
            
    def show_recent_papers(self):
        today = datetime.datetime.now()
        four_weeks_ago = today - datetime.timedelta(days=7)#(weeks=4)
        
        if 'Modified Date' in self.df.columns:
            # Parse 'Modified Date' strings to datetime objects
            def parse_date(date_str):
                try:
                    return parser.parse(date_str)
                except (ValueError, TypeError):
                    return pd.NaT  # Return Not-a-Time for unparseable dates
            
            # Apply the parsing function to the 'Modified Date' column
            self.df['Parsed Modified Date'] = self.df['Modified Date'].apply(parse_date)
            
            # Filter the DataFrame for recent papers
            recent_papers = self.df[
                self.df['Parsed Modified Date'].notna() &
                (self.df['Parsed Modified Date'] >= four_weeks_ago)
            ]
            
            # Sort the recent papers by 'Parsed Modified Date' in descending order
            recent_papers = recent_papers.sort_values(by='Parsed Modified Date', ascending=False)
            
            if recent_papers.empty:
                messagebox.showinfo("No Recent Papers", "No papers added or modified in the last 4 weeks.")
            else:
                self.results = recent_papers.reset_index(drop=True)
                self.display_results()
        else:
            messagebox.showinfo("Error", "'Modified Date' column not found in the database.")

    # New methods for handling tags
    def extract_tags(self):
        tags = set()
        for comments in self.df['Comments']:
            if pd.notna(comments):
                # Use regex to find all tags in {}
                tags_in_comments = re.findall(r'\{(.*?)\}', comments)
                tags.update(tags_in_comments)
        return sorted(tags)

    def show_tags(self):
        tags = self.extract_tags()
        if not tags:
            messagebox.showinfo("No Tags", "No tags found in the database.")
            return

        # Create a new window
        tags_window = Toplevel(self.root)
        tags_window.title("Tags")

        # Create a Listbox to show tags
        listbox = Listbox(tags_window, font=self.custom_font)

        for tag in tags:
            listbox.insert(END, tag)

        listbox.pack(fill=tk.BOTH, expand=True)

        # Bind double-click event to the listbox items
        listbox.bind('<Double-1>', lambda event: self.show_papers_with_tag(event, listbox))

    def show_papers_with_tag(self, event, listbox):
        selection = listbox.curselection()
        if selection:
            index = selection[0]
            tag = listbox.get(index)
            # Filter the dataframe
            # Use regex to match the tag within {}
            pattern = r'\{' + re.escape(tag) + r'\}'
            self.results = self.df[self.df['Comments'].str.contains(pattern, na=False, flags=re.IGNORECASE)].copy()  # Add .copy()
            if self.results.empty:
                messagebox.showinfo("No Results", f"No papers found with tag '{tag}'.")
            else:
                self.display_results()



if __name__ == "__main__":
    root = tk.Tk()
    app = PDFSearchApp(root)
    root.mainloop()
