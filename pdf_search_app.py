import os
import tkinter as tk
from tkinter import END, DISABLED, messagebox, Button, Toplevel, Text, Frame, Label, Canvas, Scrollbar, Listbox, filedialog
from tkinter import font as tkfont
import pandas as pd
import threading
import concurrent.futures
import time
import re
import subprocess
import shutil
from datetime import datetime, timedelta
from dateutil.parser import parse
from fuzzywuzzy import fuzz
from pyperclip import copy

from utils import (
    load_database,
    load_default_directory,
    parse_bibtex_field,
    extract_doi,
    generate_safe_filename_from_directory
)
from database_utils import check_database_validity, find_duplicates
from confirm_dialogs import confirm_extraction, confirm_deletion

class PDFSearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sergeley_3.0")
        self.root.geometry("1150x800")

        self.df = pd.DataFrame()
        self.results = pd.DataFrame()
        self.csv_file = None

        self.custom_font = tkfont.Font(family="Helvetica", size=11)
        self.title_font = tkfont.Font(family="Helvetica", size=11, weight="bold")
        self.title_path = tkfont.Font(family="Arial", size=8)

        dir_update_frame = Frame(root)
        dir_update_frame.pack(pady=10)

        self.running_label = tk.Label(root, text="", font=self.custom_font, fg="red")
        self.running_label.pack(pady=2)

        # Load the default directory from the text file
        default_directory = load_default_directory()
        tk.Label(dir_update_frame, text="Set Directory to Scan:", font=self.custom_font).pack()
        self.entry_directory = tk.Entry(dir_update_frame, font=self.custom_font)
        self.entry_directory.pack()
        self.entry_directory.insert(0, default_directory if default_directory else '')

        # Initialize csv_file based on default_directory
        if default_directory:
            self.csv_file = generate_safe_filename_from_directory(default_directory)
            self.df = load_database(self.csv_file)
        else:
            self.df = pd.DataFrame()

        update_button = tk.Button(
            dir_update_frame,
            text="Update Database",
            command=self.run_update_database_task,
            font=self.custom_font
        )
        update_button.pack()

        search_frame = Frame(root)
        search_frame.pack(pady=10)

        # Create a new frame within search_frame to hold the buttons
        button_frame = Frame(search_frame)
        button_frame.pack()

        tag_button = tk.Button(
            button_frame,
            text="Show {Tags}",
            command=self.show_tags,
            font=self.custom_font
        )
        tag_button.pack(side=tk.LEFT, padx=5)

        recent_button = tk.Button(
            button_frame,
            text="Show Recent Papers",
            command=self.show_recent_papers,
            font=self.custom_font
        )
        recent_button.pack(side=tk.LEFT, padx=5)

        very_recent_button = tk.Button(
            button_frame,
            text="Show just added papers",
            command=self.show_very_recent_papers,
            font=self.custom_font
        )
        very_recent_button.pack(side=tk.LEFT, padx=5)

        tk.Label(search_frame, text="Enter search keywords:", font=self.custom_font).pack()
        self.entry_keywords = tk.Entry(search_frame, font=self.custom_font)
        self.entry_keywords.pack()

        tk.Label(search_frame, text="Enter similarity threshold (0-100):", font=self.custom_font).pack()
        self.entry_threshold = tk.Entry(search_frame, font=self.custom_font)
        self.entry_threshold.pack()
        if not self.entry_threshold.get():
            self.entry_threshold.insert(0, "70")

        search_button = tk.Button(
            search_frame,
            text="Search",
            command=self.search,
            font=self.custom_font
        )
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
            self.save_to_csv()
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
            self.save_to_csv()
            messagebox.showinfo("Success", "BibTeX information updated.")
            bibtex_window.destroy()

        bibtex_window = Toplevel(self.root)
        bibtex_window.title("Edit BibTeX")

        text_bibtex = Text(bibtex_window, width=100, height=20, font=self.custom_font)
        text_bibtex.pack()
        text_bibtex.insert(END, bibtex_info if pd.notna(bibtex_info) else "")

        save_button = Button(bibtex_window, text="Save", command=save_bibtex, font=self.custom_font)
        save_button.pack()

    def save_to_csv(self):
        if self.csv_file:
            # Construct the full path to the CSV file
            script_dir = os.path.dirname(os.path.abspath(__file__))
            csv_path = os.path.join(script_dir, self.csv_file)
            self.df.to_csv(csv_path, index=False, encoding='utf-8')
        else:
            # Handle the case where csv_file is not set
            pass


    def search(self):
        keywords = self.entry_keywords.get().split()
        threshold = int(self.entry_threshold.get())

        if not keywords:
            messagebox.showerror("Error", "Please enter search keywords.")
            return

        # Run the search in background
        self.run_task_in_background(self.perform_search, keywords, threshold, task_name='search')

    def perform_search(self, keywords, threshold):
        self.results = self.fuzzy_search_database(self.df, keywords, threshold).copy()

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
            num_lines = (text_width_px // 1040) + 1  # Adjust based on your window width

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

            # Display the path
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
            text_path.insert(tk.END, bibliography_path)
            text_path.config(state=tk.DISABLED)
            text_path.pack(anchor="w", fill='x', expand=True)

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
                text="Show in Folder",
                command=lambda i=index: self.show_file_in_explorer(i),
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

    from tkinter import filedialog  # Add this import at the top of your file

    def prompt_move_paper(self, index):
        # Get the current directory of the selected paper
        current_dir = os.path.dirname(self.results.iloc[index]['Path'])
        
        # Open a directory selection dialog
        destination_folder = filedialog.askdirectory(
            initialdir=current_dir,
            title="Select Destination Folder"
        )

        if destination_folder:
            confirm = messagebox.askyesno(
                "Confirm Move",
                f"Are you sure you want to move the paper to:\n{destination_folder}?"
            )
            if confirm:
                # Run move_file in background
                self.run_task_in_background(self.move_file, index, destination_folder, task_name='move_file')

    def show_file_in_explorer(self, index):
        file_path = self.results.iloc[index]['Path']
        if os.path.exists(file_path):
            subprocess.run(['explorer', '/select,', os.path.normpath(file_path)])
        else:
            messagebox.showerror("File Not Found", f"The file does not exist:\n{file_path}")

    def show_running_message(self):
        self.running_label.config(text="Running...")
        self.root.update_idletasks()

    def hide_running_message(self):
        self.running_label.config(text="")
        self.root.update_idletasks()

    def run_task_in_background(self, task, *args, task_name=None):
        self.background_task_name = task_name
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(task, *args)

        def check_future():
            if future.done():
                try:
                    future.result()
                    self.hide_running_message()
                    self.handle_background_task_result()
                except Exception as e:
                    self.background_task_exception = str(e)
                    self.hide_running_message()
                    self.handle_background_task_result()
            else:
                self.root.after(100, check_future)

        self.show_running_message()
        check_future()

    def handle_background_task_result(self):
        if hasattr(self, 'background_task_exception'):
            messagebox.showerror("Error", f"Failed to perform task: {self.background_task_exception}")
            del self.background_task_exception
        else:
            if self.background_task_name == 'update_database':
                result = self.background_task_result
                messages = result['messages']
                files_requiring_confirmation = result['files_requiring_confirmation']
                duplicates_to_confirm = result['duplicates_to_confirm']

                # Display messages
                messagebox.showinfo("Database Update", "\n".join(messages))

                # Process files requiring extraction
                self.process_doi_extraction_confirmations(files_requiring_confirmation)

                # Process duplicates to confirm deletion
                self.process_duplicate_confirmations(duplicates_to_confirm)

                # Clean up
                del self.background_task_result
            elif self.background_task_name == 'search':
                self.display_results()
            elif self.background_task_name == 'move_file':
                # Refresh the display after moving the file
                self.display_results()
            # Reset background_task_name
            self.background_task_name = None

    def process_duplicate_confirmations(self, duplicates_list):
        self.show_running_message()
        for group in duplicates_list:
            # Skip the first entry and consider the rest as duplicates
            first_entry = group.iloc[0]
            duplicates = group.iloc[1:]

            for idx, item in duplicates.iterrows():
                details = f"Found duplicate:\nName: {item['Name']}\nPath: {item['Path']}"
                response = messagebox.askyesno("Confirm Deletion", details + "\nDo you want to delete this file?")
                if response:
                    # Delete file
                    if os.path.exists(item['Path']):
                        try:
                            os.remove(item['Path'])
                            # Remove from DataFrame
                            self.df = self.df.drop(idx)
                        except OSError as e:
                            messagebox.showerror("Error", f"Failed to delete file: {e}")
        # Save the updated DataFrame
        self.save_to_csv()
        self.hide_running_message()

    def process_doi_extraction_confirmations(self, files):
        self.show_running_message()
        for file_info in files:
            full_path, file_name, extension, size, modified_date = file_info
            if extension == '.pdf':
                should_extract = confirm_extraction(file_name)
                if should_extract:
                    bib_info = extract_doi(full_path)
                    # Update the DataFrame
                    self.df.loc[self.df['Path'] == full_path, 'BibTeX'] = bib_info
        # Save the updated DataFrame
        self.save_to_csv()
        self.hide_running_message()

    def run_update_database_task(self):
        directory_to_scan = self.entry_directory.get()
        if not directory_to_scan:
            messagebox.showerror("Error", "Please set a directory to scan first.")
            return
        # Update csv_file and DataFrame based on the new directory
        self.csv_file = generate_safe_filename_from_directory(directory_to_scan)
        self.df = load_database(self.csv_file)
        self.run_task_in_background(self.update_database, directory_to_scan, task_name='update_database')

    def update_database(self, directory_to_scan):
        try:
            self.csv_file = generate_safe_filename_from_directory(directory_to_scan)
            df, messages, files_requiring_confirmation, duplicates_to_confirm, error_message = check_database_validity(directory_to_scan, self.csv_file)
            if error_message:
                self.background_task_exception = error_message
                return
            self.df = df  # Update DataFrame
            self.background_task_result = {
                'messages': messages,
                'files_requiring_confirmation': files_requiring_confirmation,
                'duplicates_to_confirm': duplicates_to_confirm
            }
        except Exception as e:
            self.background_task_exception = str(e)

    def show_recent_papers(self):
        today = datetime.now()
        four_weeks_ago = today - timedelta(weeks=4)

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
        twelve_hours_ago = today - timedelta(hours=12)

        if 'Modified Date' in self.df.columns:
            def parse_date(date_str):
                try:
                    return parse(date_str)
                except (ValueError, TypeError):
                    return pd.NaT

            self.df['Parsed Modified Date'] = self.df['Modified Date'].apply(parse_date)

            recent_papers = self.df[
                self.df['Parsed Modified Date'].notna() &
                (self.df['Parsed Modified Date'] >= twelve_hours_ago)
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
        file_path = self.results.iloc[index]['Path']
        file_name = os.path.basename(file_path)
        current_folder = os.path.dirname(file_path)

        if not os.path.exists(file_path):
            messagebox.showerror("Error", f"File not found: {file_path}")
            return

        # Normalize paths to absolute paths for accurate comparison
        source_path = os.path.abspath(file_path)
        destination_folder = os.path.abspath(destination_folder)
        new_path = os.path.join(destination_folder, file_name)
        new_path = os.path.abspath(new_path)

        # Check if the source and destination are the same
        if source_path == new_path:
            messagebox.showinfo("Information", "The file is already in the selected folder.")
            return

        self.show_running_message()
        if not os.path.exists(destination_folder):
            os.makedirs(destination_folder)

        try:
            # Move the file to the new location
            shutil.move(source_path, new_path)

            # Update the DataFrame with the new path
            self.df.loc[self.df['Path'] == file_path, 'Path'] = new_path
            self.results.at[index, 'Path'] = new_path  # Update the path in the results DataFrame as well

            # Save the changes to the CSV file
            self.save_to_csv()

            messagebox.showinfo("Success", f"File moved to {destination_folder}.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to move file: {e}")
        finally:
            self.hide_running_message()
