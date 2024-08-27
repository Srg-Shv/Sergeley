#####Python 3.10.10
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
from tkinter import END, messagebox, Button, Toplevel, Text, Frame, Label, Canvas, Scrollbar,Frame
from tkinter import font as tkfont
import subprocess

# Ensure stdout supports UTF-8 encoding
sys.stdout.reconfigure(encoding='utf-8')

def load_database(csv_file):
    """
    Load the CSV database.
    
    Parameters:
    csv_file (str): Name of the CSV file (without path)
    
    Returns:
    DataFrame: Loaded pandas DataFrame.
    """
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Combine the script directory with the csv_file name
    csv_path = os.path.join(script_dir, csv_file)
    
    # Check if the CSV file exists
    if os.path.exists(csv_path):
        return pd.read_csv(csv_path, encoding='utf-8')
    else:
        # Define the columns
        columns = ['Path', 'Name', 'Extension', 'Size', 'Modified Date', 'DOI', 'Year', 'Author', 'Title', 'Volume', 'Pages', 'Number', 'Journal', 'Publisher', 'BibTeX', 'Comments']
        # Create an empty DataFrame with the defined columns
        df = pd.DataFrame(columns=columns)
        # Save the empty DataFrame to a CSV file
        df.to_csv(csv_path, index=False, encoding='utf-8')
        return df

def generate_unique_key(authors, year):
    """
    Generate a unique key based on the first author's last name, year, and a random letter.
    
    Parameters:
    authors (str): Comma-separated string of authors.
    year (str/int): Year of publication.
    
    Returns:
    str: Generated unique key.
    """
    if not authors or not year:
        return "unknown"
    first_author_last_name = authors.split(",")[0].split(" ")[-1]
    random_letter = random.choice(string.ascii_lowercase)
    return f"{first_author_last_name}{year}{random_letter}"

def extract_doi(pdf_path):
    """
    Extract DOI and additional information from a PDF file.
    
    Parameters:
    pdf_path (str): Path to the PDF file.
    
    Returns:
    tuple: Extracted DOI, title, authors, year, volume, pages, number, journal, publisher, and BibTeX information.
    """
    try:
        result = pdf2doi.pdf2doi(pdf_path)
        doi = result['identifier']
        validation_info = json.loads(result['validation_info'])
        title = validation_info.get('title', '')
        authors = ", ".join([f"{author['given']} {author['family']}" for author in validation_info.get('author', [])])
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
        return doi, title, authors, year, volume, pages, number, journal, publisher, bib_info
    except Exception as e:
        print(f"Error extracting DOI from {pdf_path}: {e}")
        return None, None, None, None, None, None, None, None, None, None

def scan_directory(directory, existing_files_info):
    """
    Scan a directory to collect PDF file information and extract DOI details.
    
    Parameters:
    directory (str): Directory to scan.
    existing_files_info (dict): Dictionary of existing file paths to their sizes and modified times.
    
    Returns:
    tuple: Lists of new file data, updated file data, and counts of new and updated files.
    """
    # Check if the directory exists¶
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
            modified_date = time.ctime(os.path.getmtime(full_path))
            extension = os.path.splitext(file)[1].lower()
            if extension == '.pdf':
                if full_path not in existing_files_info:
                    if confirm_extraction(file):
                        doi, title, authors, year, volume, pages, number, journal, publisher, bib_info = extract_doi(full_path)
                    else:
                        doi, title, authors, year, volume, pages, number, journal, publisher, bib_info = ('', '', '', '', '', '', '', '', '', '')
                    new_data.append([full_path, file, extension, size, modified_date, doi, year, authors, title, volume, pages, number, journal, publisher, bib_info, ''])
                    new_files_found += 1
                elif size != existing_files_info[full_path]['size'] or modified_date != existing_files_info[full_path]['modified_date']:
                    updated_data.append([full_path, file, extension, size, modified_date])
                    updated_files_found += 1
    return new_data, updated_data, new_files_found, updated_files_found

def check_database_validity(directory, csv_file):
    """
    Check and update the file database for a directory.
    
    Parameters:
    directory (str): Directory to scan.
    csv_file (str): Path to the CSV file containing the database.
    
    Returns:
    DataFrame: Updated DataFrame after scanning the directory and updating the database.
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
        new_df = pd.DataFrame(new_data, columns=['Path', 'Name', 'Extension', 'Size', 'Modified Date', 'DOI', 'Year', 'Author', 'Title', 'Volume', 'Pages', 'Number', 'Journal', 'Publisher', 'BibTeX', 'Comments'])
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
    
    Parameters:
    item (Series): The row of the DataFrame corresponding to the duplicate file.
    
    Returns:
    bool: True if the user confirms deletion, False otherwise.
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
    
    details = f"Found duplicate:\nName: {item['Name']}\nTitle: {item['Title']}\nPath: {item['Path']}"
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
    
    Parameters:
    name (str): Name of the PDF file.
    
    Returns:
    bool: True if the user confirms extraction, False otherwise.
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

def remove_duplicates(df, csv_file):
    """
    Remove duplicate entries based on the "DOI" column and delete corresponding PDF files.
    
    Parameters:
    df (DataFrame): DataFrame containing the database.
    csv_file (str): Path to the CSV file.
    """
    # Separate rows with and without DOI
    df_with_doi = df[df['DOI'].notna() & df['DOI'].str.strip().astype(bool)]
    df_without_doi = df[~df.index.isin(df_with_doi.index)]
    
    # Find duplicates within rows that have DOI
    duplicates = df_with_doi[df_with_doi.duplicated(subset='DOI', keep=False)]
    
    #if duplicates.empty:
    #    messagebox.showinfo("Duplicates Check", "No duplicates found.")
    #    return
    
    # Group duplicates by DOI
    grouped_duplicates = duplicates.groupby('DOI')

    files_to_delete = []
    indices_to_delete = []

    for doi, group in grouped_duplicates:
        first_entry = group.iloc[0]
        duplicates_to_delete = group.iloc[1:]

        for _, item in duplicates_to_delete.iterrows():
            if confirm_deletion(item):
                files_to_delete.append(item['Path'])
                indices_to_delete.append(item.name)

    df_with_doi.drop(index=indices_to_delete, inplace=True)
    
    # Combine the rows with and without DOI back together
    updated_df = pd.concat([df_with_doi, df_without_doi])
    updated_df.to_csv(csv_file, index=False, encoding='utf-8')
    
    deleted_files = []
    #not_found_files = []
    for file_path in files_to_delete:
        if os.path.exists(file_path):
            os.remove(file_path)
            deleted_files.append(file_path)
        #else:
         #   not_found_files.append(file_path)

    #messages = [f"Removed {len(indices_to_delete)} duplicate file(s) from the database."]
    
    #if deleted_files:
    #    messages.append(f"Deleted files:\n" + "\n".join(deleted_files))
    #if not_found_files:
    #    messages.append(f"Files not found:\n" + "\n".join(not_found_files))
    
    #messagebox.showinfo("Duplicates Removal", "\n".join(messages))

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
        self.entry_directory.insert(0, 'F:\\_Papers\\2024')

        update_button = tk.Button(dir_update_frame, text="Update Database", command=self.update_database, font=self.custom_font)
        update_button.pack()

        # Frame for search options
        search_frame = Frame(root)
        search_frame.pack(pady=10)

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
        columns_to_search = ['Path', 'Name', 'DOI', 'Year', 'Author', 'Title', 'Journal', 'Publisher', 'Comments']

        missing_columns = [col for col in columns_to_search if col not in df.columns]
        #if missing_columns:
        #    print(f"Warning: Missing columns in the DataFrame: {missing_columns}")
        #    return pd.DataFrame()

        def match_row(row, keywords):
            row_str = ' '.join(str(row[col]) for col in columns_to_search if col in row).lower()
            individual_scores = [fuzz.partial_ratio(keyword, row_str) for keyword in keywords]
            combined_keywords = ' '.join(keywords)
            combined_score = fuzz.token_set_ratio(combined_keywords, row_str)
            return all(score >= threshold for score in individual_scores) or combined_score >= threshold

        mask = df.apply(lambda row: match_row(row, keywords), axis=1)
        result_df = df[mask].reset_index(drop=True)

        if 'Year' in result_df.columns:
            result_df['Year'] = pd.to_numeric(result_df['Year'], errors='coerce')
            result_df = result_df.sort_values(by='Year').reset_index(drop=True)

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
            #messagebox.showinfo("Success", "BibTeX info copied to clipboard.")
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

    def save_to_csv(self, csv_file):
        self.df.to_csv(csv_file, index=False)

    def search(self):
        keywords = self.entry_keywords.get().split()
        threshold = int(self.entry_threshold.get())

        if not keywords:
            messagebox.showerror("Error", "Please enter search keywords.")
            return

        self.results = self.fuzzy_search_database(self.df, keywords, threshold)
        self.display_results()

    def display_results(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        if self.results.empty:
            messagebox.showinfo("No Results", "No matching results found.")
            return

        for index, row in self.results.iterrows():
            # Check if 'Year' is valid and convert to integer, otherwise set to 'Unknown'
            try:
                year = int(row['Year']) if pd.notna(row['Year']) and row['Year'] != '' else 'Unknown'
            except ValueError:
                year = 'Unknown'

            # Frame for bibliography information
            frame_biblio = Frame(self.scrollable_frame, pady=5)
            frame_biblio.pack(fill=tk.X, padx=10, pady=5)

            # Construct bibliography text based on the presence of 'Year'
            if year != 'Unknown':
                bibliography_text = f"{year} - {row['Title']} - {row['Author']}"
            else:
                bibliography_text = f"Path: {row['Path']}"

            # Label to display bibliography text with wrapping
            Label(frame_biblio, text=bibliography_text, font=self.title_font, fg="blue", wraplength=1000, justify=tk.LEFT).pack(anchor="w")

            # Frame for buttons
            frame_buttons = Frame(self.scrollable_frame)
            frame_buttons.pack(fill=tk.X, padx=10, pady=5)

            Button(frame_buttons, text="Open PDF", command=lambda p=row['Path']: self.open_pdf(p), font=self.custom_font).pack(side="left", padx=(0, 10))
            Button(frame_buttons, text="Copy BibTeX", command=lambda i=index: self.copy_bibtex(i), font=self.custom_font).pack(side="left", padx=(0, 10))
            Button(frame_buttons, text="Edit Comments", command=lambda i=index: self.open_comments_window(i), font=self.custom_font).pack(side="left", padx=(0, 10))

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
            #messagebox.showinfo("Success", "Database updated successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update database: {e}")
        finally:
            self.hide_running_message()


if __name__ == "__main__":
    root = tk.Tk()
    app = PDFSearchApp(root)
    root.mainloop()
