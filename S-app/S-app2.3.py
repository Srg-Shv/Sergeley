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
from tkinter import END, DISABLED, messagebox, Button, Toplevel, Text, Frame, Label, Canvas, Scrollbar, Listbox
from tkinter import font as tkfont
from subprocess import call
from datetime import datetime, timedelta
from dateutil.parser import parse
import concurrent.futures
import threading
import time
import os
import re
import shutil

# Ensure stdout supports UTF-8 encoding
sys.stdout.reconfigure(encoding='utf-8')

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


def scan_directory_parallel(directory, existing_files_info, missing_files_info):
    if not os.path.exists(directory):
        messagebox.showerror("Error", f"The directory '{directory}' does not exist.")
        return [], [], [], 0, 0, 0

    new_data = []
    updated_data = []
    moved_data = []
    new_files_found = 0
    updated_files_found = 0
    moved_files_found = 0

    # Create a mapping from file name to missing file info
    missing_files_name_to_info = {row['Name']: {'old_path': row['Path']} for _, row in missing_files_info.iterrows()}

    def process_file(root, file):
        nonlocal new_files_found, updated_files_found, moved_files_found
        full_path = os.path.join(root, file)
        size = os.path.getsize(full_path)
        modified_date = time.ctime(os.path.getmtime(full_path))
        extension = os.path.splitext(file)[1].lower()

        if extension == '.pdf':
            if full_path not in existing_files_info:
                # Check if file name matches any missing file
                if file in missing_files_name_to_info:
                    # File has been moved
                    old_path = missing_files_name_to_info[file]['old_path']
                    return [old_path, full_path, size, modified_date], 'moved'
                else:
                    # New file
                    if confirm_extraction(file):
                        bib_info = extract_doi(full_path)
                    else:
                        bib_info = ''
                    return [full_path, file, extension, size, modified_date, bib_info, ''], 'new'
            elif size != existing_files_info[full_path]['size'] or modified_date != existing_files_info[full_path]['modified_date']:
                return [full_path, file, extension, size, modified_date], 'updated'

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for root, _, files in os.walk(directory):
            for file in files:
                futures.append(executor.submit(process_file, root, file))

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                data, status = result
                if status == 'new':
                    new_data.append(data)
                    new_files_found += 1
                elif status == 'updated':
                    updated_data.append(data)
                    updated_files_found += 1
                elif status == 'moved':
                    moved_data.append(data)
                    moved_files_found += 1

    return new_data, updated_data, moved_data, new_files_found, updated_files_found, moved_files_found

def check_database_validity(directory, csv_file):
    df = load_database(csv_file)
    existing_files_info = {
        row['Path']: {'size': row['Size'], 'modified_date': row['Modified Date']}
        for _, row in df.iterrows()
    }
    missing_files = [file_path for file_path in existing_files_info if not os.path.exists(file_path)]

    # Collect missing files info but don't remove them yet
    missing_files_info = df[df['Path'].isin(missing_files)].copy()

    messages = []

    # Pass missing_files_info to the scan function
    new_data, updated_data, moved_data, new_files_found, updated_files_found, moved_files_found = scan_directory_parallel(
        directory, existing_files_info, missing_files_info
    )

    if moved_files_found > 0:
        for moved_row in moved_data:
            old_path, new_path, size, modified_date = moved_row
            df.loc[df['Path'] == old_path, ['Path', 'Size', 'Modified Date']] = [new_path, size, modified_date]
        messages.append(f"Database has been updated with {moved_files_found} moved file(s).")
    else:
        messages.append(f"Database has been updated with 0 moved file(s).")

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

    # Now remove any missing files that were not matched
    remaining_missing_files = set(missing_files) - set([row[0] for row in moved_data])
    if remaining_missing_files:
        messages.append(f"Removing {len(remaining_missing_files)} missing file(s) from the database.")
        df = df[~df['Path'].isin(remaining_missing_files)]
    else:
        messages.append("No missing files were removed.")

    df.to_csv(csv_file, index=False, encoding='utf-8')
    messagebox.showinfo("Database Update", "\n".join(messages))
    return df



def remove_duplicates(df, csv_file):
    def extract_doi_from_bibtex(bibtex_str):
        return parse_bibtex_field(bibtex_str, 'DOI')

    df['DOI_extracted'] = df['BibTeX'].apply(extract_doi_from_bibtex)

    df_with_doi = df[df['DOI_extracted'].notna() & df['DOI_extracted'].str.strip().astype(bool)]
    df_without_doi = df[~df.index.isin(df_with_doi.index)]

    duplicates = df_with_doi[df_with_doi.duplicated(subset='DOI_extracted', keep=False)]

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
    df_with_doi = df_with_doi.drop(columns=['DOI_extracted'])

    updated_df = pd.concat([df_with_doi, df_without_doi])
    updated_df.to_csv(csv_file, index=False, encoding='utf-8')

    deleted_files = []
    for file_path in files_to_delete:
        if os.path.exists(file_path):
            os.remove(file_path)
            deleted_files.append(file_path)


class PDFSearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Search")
        self.root.geometry("1150x800")

        self.df = load_database('file_database.csv')
        self.results = pd.DataFrame()

        self.custom_font = tkfont.Font(family="Helvetica", size=11)
        self.title_font = tkfont.Font(family="Helvetica", size=11, weight="bold")
        self.title_path = tkfont.Font(family="Arial", size=8)#, weight="bold")

        dir_update_frame = Frame(root)
        dir_update_frame.pack(pady=10)

        self.running_label = tk.Label(root, text="", font=self.custom_font, fg="red")
        self.running_label.pack(pady=2)########

        tk.Label(dir_update_frame, text="Set Directory to Scan:", font=self.custom_font).pack()
        self.entry_directory = tk.Entry(dir_update_frame, font=self.custom_font)
        self.entry_directory.pack()
        self.entry_directory.insert(0, 'F:\\_Papers\\2024')

        update_button = tk.Button(dir_update_frame, text="Update Database", command=self.run_update_database_task, font=self.custom_font)
        update_button.pack()

        search_frame = Frame(root)
        search_frame.pack(pady=10)

        # Create a new frame within search_frame to hold the buttons
        button_frame = Frame(search_frame)
        button_frame.pack()

        # Adding back the Tags button
        tag_button = tk.Button(button_frame, text="Show {Tags}", command=self.show_tags, font=self.custom_font)
        tag_button.pack(side=tk.LEFT, padx=5)

        recent_button = tk.Button(button_frame, text="Show Recent Papers", command=self.show_recent_papers, font=self.custom_font)
        recent_button.pack(side=tk.LEFT, padx=5)

        very_recent_button = tk.Button(button_frame, text="Show just added papers", command=self.show_very_recent_papers, font=self.custom_font)
        very_recent_button.pack(side=tk.LEFT, padx=5)


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

    def show_tags(self):
        tags = self.extract_tags()
        if not tags:
            messagebox.showinfo("No Tags", "No tags found in the database.")
            return

        # Create a new window to show tags
        tags_window = Toplevel(self.root)
        tags_window.title("Tags")
        tags_window.geometry("200x600")

        # Create a Listbox to show tags
        listbox = Listbox(tags_window, font=self.custom_font)

        for tag in tags:
            listbox.insert(END, tag)

        listbox.pack(fill=tk.BOTH, expand=True)

        # Bind double-click event to the listbox items
        listbox.bind('<Double-1>', lambda event: self.show_papers_with_tag(event, listbox))

    def extract_tags(self):
        """
        Extract tags from the 'Comments' column of the DataFrame.
        Tags are assumed to be enclosed in curly braces {tag}.
        """
        tags = set()
        for comments in self.df['Comments']:
            if pd.notna(comments):
                tags_in_comments = re.findall(r'\{(.*?)\}', comments)
                tags.update(tags_in_comments)
        return sorted(tags)

    def show_papers_with_tag(self, event, listbox):
        selection = listbox.curselection()
        if selection:
            index = selection[0]
            tag = listbox.get(index)
            # Filter the dataframe to show papers with the selected tag
            pattern = r'\{' + re.escape(tag) + r'\}'
            self.results = self.df[self.df['Comments'].str.contains(pattern, na=False, flags=re.IGNORECASE)].copy()
            if self.results.empty:
                messagebox.showinfo("No Results", f"No papers found with tag '{tag}'.")
            else:
                self.display_results()

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
            copy(bib_info)
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

        self.results['Year'] = self.results['BibTeX'].apply(lambda bibtex: parse_bibtex_field(bibtex, 'year'))

        self.results['Year'] = pd.to_numeric(self.results['Year'], errors='coerce')

        self.results = self.results.sort_values(by='Year', ascending=False, na_position='last').reset_index(drop=True)

        default_bg_color = self.root.cget("bg")

        for index, row in self.results.iterrows():
            bibtex_str = row['BibTeX']
            if not isinstance(bibtex_str, str):
                bibtex_str = ''
            elif pd.isna(bibtex_str):
                bibtex_str = ''

            title = parse_bibtex_field(bibtex_str, 'title')
            author = parse_bibtex_field(bibtex_str, 'author')
            year = row['Year']

            if not title:
                title = f"Path: {row['Path']}"

            year = '-' if pd.isna(year) else int(year)

            frame_biblio = Frame(self.scrollable_frame, pady=5)
            frame_biblio.pack(fill=tk.X, padx=10, pady=0, expand=True)

            bibliography_text = f"{year} - {title} - {author}"
            
            # Calculate the total pixel width of the text
            text_width_px = self.title_font.measure(bibliography_text)

            # Calculate the number of lines required
            num_lines = (text_width_px // 1040) + 1  # Add 1 to round up for partial lines

            # Ensure a minimum height of 1 line
            text_height = max(1, num_lines)

            text_biblio = Text(
                frame_biblio,
                font=self.title_font,
                fg="blue",
                bg=default_bg_color,
                wrap='word',
                height=text_height,
                borderwidth=0,
                width=130
            )
            
            text_biblio.insert(tk.END, bibliography_text)
            text_biblio.config(state=tk.DISABLED)
            text_biblio.pack(anchor="w", fill='x', expand=True)
            
            #new (path)
            frame_path = Frame(self.scrollable_frame, pady=5)
            frame_path.pack(fill=tk.X, padx=10, pady=0, expand=True)
            
            bibliography_path = f"{row['Path']}"

            text_path = Text(
                frame_path,
                font=self.title_path,
                fg="black",
                bg=default_bg_color,
                wrap='word',
                height=1,
                borderwidth=0,
                width=130
            )
            text_path.insert(tk.END,  bibliography_path)
            text_path.config(state=tk.DISABLED)
            text_path.pack(anchor="w", fill='x', expand=True)
            #new end  (path)

            frame_buttons = Frame(self.scrollable_frame)
            frame_buttons.pack(fill=tk.X, padx=10, pady=2)

            Button(
                frame_buttons,
                text="Open PDF",
                command=lambda p=row['Path']: self.open_pdf(p),
                font=self.custom_font
            ).pack(side="left", padx=(0, 10))
            Button(
                frame_buttons,
                text="Move Paper",
                command=lambda i=index: self.prompt_move_paper(i),
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

    # New method for prompting move directory input
    def prompt_move_paper(self, index):
        move_window = Toplevel(self.root)
        move_window.title("Move Paper")

        Label(move_window, text=f"The current path is {os.path.dirname(self.results.iloc[index]['Path'])}. Enter the destination folder path:", font=self.custom_font).pack(pady=5)
        entry_folder = tk.Entry(move_window, width=50, font=self.custom_font)
        entry_folder.pack(pady=5)

        def move_paper_action():
            destination_folder = entry_folder.get().strip()
            if destination_folder:
                confirm = messagebox.askyesno(
                    "Confirm Move",
                    f"Are you sure you want to move the paper to:\n{destination_folder}?"
                )
                if confirm:
                    self.move_file(index, destination_folder)
            move_window.destroy()

        Button(move_window, text="Move", command=move_paper_action, font=self.custom_font).pack(pady=5)
  
    def show_running_message(self):
        self.running_label.config(text="Running...")
        self.root.update_idletasks()

    def hide_running_message(self):
        self.running_label.config(text="")
        self.root.update_idletasks()

    def run_task_in_background(self, task, *args):
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(task, *args)

        def check_future():
            if future.done():
                result = future.result()
                self.hide_running_message()
            else:
                self.root.after(100, check_future)

        self.show_running_message()
        threading.Thread(target=check_future).start()

    def run_update_database_task(self):
        directory_to_scan = self.entry_directory.get()
        if not directory_to_scan:
            messagebox.showerror("Error", "Please set a directory to scan first.")
            return
        self.run_task_in_background(self.update_database, directory_to_scan)

    def update_database(self, directory_to_scan):
        try:
            df = check_database_validity(directory_to_scan, 'file_database.csv')
            remove_duplicates(df, 'file_database.csv')
            self.df = load_database('file_database.csv')
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update database: {e}")

    def show_recent_papers(self):
        today = datetime.now()
        four_weeks_ago = today - timedelta(weeks=4)#(weeks=4)

        if 'Modified Date' in self.df.columns:
            def parse_date(date_str):
                try:
                    return parse(date_str)
                except (ValueError, TypeError):
                    return pd.NaT

            self.df['Parsed Modified Date'] = self.df['Modified Date'].apply(parse_date)

            recent_papers = self.df[
                self.df['Parsed Modified Date'].notna() &
                (self.df['Parsed Modified Date'] >= four_weeks_ago)
            ]

            recent_papers = recent_papers.sort_values(by='Parsed Modified Date', ascending=False)

            if recent_papers.empty:
                messagebox.showinfo("No Recent Papers", "No papers added or modified in the last 4 weeks.")
            else:
                self.results = recent_papers.reset_index(drop=True)
                self.display_results()
        else:
            messagebox.showinfo("Error", "'Modified Date' column not found in the database.")
            
    def show_very_recent_papers(self):
        today = datetime.now()
        four_weeks_ago = today - timedelta(hours=12)#(weeks=4)

        if 'Modified Date' in self.df.columns:
            def parse_date(date_str):
                try:
                    return parse(date_str)
                except (ValueError, TypeError):
                    return pd.NaT

            self.df['Parsed Modified Date'] = self.df['Modified Date'].apply(parse_date)

            recent_papers = self.df[
                self.df['Parsed Modified Date'].notna() &
                (self.df['Parsed Modified Date'] >= four_weeks_ago)
            ]

            recent_papers = recent_papers.sort_values(by='Parsed Modified Date', ascending=False)

            if recent_papers.empty:
                messagebox.showinfo("No Just Added Papers", "No papers added or modified in the last 12 hours.")
            else:
                self.results = recent_papers.reset_index(drop=True)
                self.display_results()
        else:
            messagebox.showinfo("Error", "'Modified Date' column not found in the database.")
    
    def move_file(self, index, destination_folder):
        #"""Moves a file from its current path to a specified folder and updates the path in the CSV."""
        file_path = self.results.iloc[index]['Path']
        file_name = os.path.basename(file_path)

        if not os.path.exists(file_path):
            messagebox.showerror("Error", f"File not found: {file_path}")
            return

        if not os.path.exists(destination_folder):
            os.makedirs(destination_folder)

        new_path = os.path.join(destination_folder, file_name)

        try:
            # Move the file to the new location
            shutil.move(file_path, new_path)
            
            # Update the DataFrame with the new path
            self.df.loc[self.df['Path'] == file_path, 'Path'] = new_path
            self.results.at[index, 'Path'] = new_path  # Update the path in the results DataFrame as well
            
            # Save the changes to the CSV file
            self.save_to_csv('file_database.csv')
            
            messagebox.showinfo("Success", f"File moved to {destination_folder}.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to move file: {e}")



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


def confirm_deletion(item):
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


def parse_bibtex_field(bibtex_str, field_name):
    if not isinstance(bibtex_str, str):
        return ''
    pattern = re.compile(rf'{field_name}\s*=\s*\{{(.*?)\}}', re.IGNORECASE | re.DOTALL)
    match = pattern.search(bibtex_str)
    if match:
        return match.group(1).replace('\n', ' ').strip()
    else:
        return ''

if __name__ == "__main__":
    root = tk.Tk()
    app = PDFSearchApp(root)
    root.mainloop()
