import os
import time
import concurrent.futures
import pandas as pd
import re
from utils import load_database, parse_bibtex_field
from datetime import datetime

def scan_directory_parallel(directory, existing_files_info, missing_files_info):
    """
    Scans the given directory in parallel to identify new, updated, and moved files.
    Adds 'Date Added' and 'Last Used Time' columns to new files.
    """
    if not os.path.exists(directory):
        # Handle directory not existing
        return [], [], [], 0, 0, 0, [], f"The directory '{directory}' does not exist."

    new_data = []
    updated_data = []
    moved_data = []
    new_files_found = 0
    updated_files_found = 0
    moved_files_found = 0
    files_requiring_confirmation = []

    # Map file names to missing file information
    missing_files_name_to_info = {row['Name']: {'old_path': row['Path']} for _, row in missing_files_info.iterrows()}

    def process_file(root, file):
        """
        Processes an individual file and determines if it is new, updated, or moved.
        """
        nonlocal new_files_found, updated_files_found, moved_files_found
        full_path = os.path.join(root, file)
        size = os.path.getsize(full_path)
        modified_date = time.ctime(os.path.getmtime(full_path))
        extension = os.path.splitext(file)[1].lower()

        if extension in ['.pdf', '.djvu']:
            if full_path not in existing_files_info:
                # Check if the file matches a missing file
                if file in missing_files_name_to_info:
                    # File has been moved
                    old_path = missing_files_name_to_info[file]['old_path']
                    return [old_path, full_path, size, modified_date], 'moved'
                else:
                    # New file
                    bibtex_info = '' if extension == '.djvu' else None  # None indicates DOI extraction required
                    if extension == '.pdf':
                        files_requiring_confirmation.append((full_path, file, extension, size, modified_date))
                    # Add current timestamp as 'Date Added'
                    date_added = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    return [full_path, file, extension, size, modified_date, bibtex_info, '', None, date_added], 'new'
            elif size != existing_files_info[full_path]['size'] or modified_date != existing_files_info[full_path]['modified_date']:
                # File has been updated
                return [full_path, file, extension, size, modified_date], 'updated'

    # Use a ThreadPoolExecutor to process files in parallel
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

    return new_data, updated_data, moved_data, new_files_found, updated_files_found, moved_files_found, files_requiring_confirmation, None
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
    error_message = None  # Initialize error_message as None

    # **Here's where the 'if not' operator is used**
    if not os.path.exists(directory):
        error_message = f"The directory '{directory}' does not exist."
        # Return None for all other return values since the directory is invalid
        return None, None, None, None, error_message

    # Pass missing_files_info to the scan function
    result = scan_directory_parallel(directory, existing_files_info, missing_files_info)

    new_data, updated_data, moved_data, new_files_found, updated_files_found, moved_files_found, files_requiring_confirmation, scan_error_message = result

    # If there was an error during scanning (should not happen in this setup)
    if scan_error_message:
        error_message = scan_error_message
        return None, None, None, None, error_message

    if moved_files_found > 0:
        for moved_row in moved_data:
            old_path, new_path, size, modified_date = moved_row
            df.loc[df['Path'] == old_path, ['Path', 'Size', 'Modified Date']] = [new_path, size, modified_date]
        messages.append(f"Database has been updated with {moved_files_found} moved file(s).")
    else:
        messages.append(f"Database has been updated with 0 moved file(s).")

    if new_files_found > 0:
        columns = ['Path', 'Name', 'Extension', 'Size', 'Modified Date', 'BibTeX', 'Comments', 'Last Used Time', 'Date Added']
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

    save_to_csv(df, csv_file)

    # Collect duplicates to confirm deletion (we'll handle this in the main thread)
    duplicates_to_confirm = find_duplicates(df)

    # Return the DataFrame, messages, files requiring confirmation, duplicates to confirm, and error_message
    return df, messages, files_requiring_confirmation, duplicates_to_confirm, error_message

def find_duplicates(df):
    def extract_doi_from_bibtex(bibtex_str):
        return parse_bibtex_field(bibtex_str, 'DOI')

    # Extract DOIs into a new column
    df['DOI_extracted'] = df['BibTeX'].apply(extract_doi_from_bibtex)

    # Exclude entries where 'DOI_extracted' is empty or contains only whitespace
    df_non_empty_doi = df[df['DOI_extracted'].str.strip() != '']

    # Identify duplicates among entries with non-empty DOIs
    duplicates = df_non_empty_doi[df_non_empty_doi.duplicated(subset='DOI_extracted', keep=False)]

    # Group duplicates by DOI
    grouped_duplicates = [group for _, group in duplicates.groupby('DOI_extracted')]

    # Drop the temporary 'DOI_extracted' column
    df.drop(columns=['DOI_extracted'], inplace=True)

    return grouped_duplicates


def update_last_used_time(df, file_path, csv_file):
    """
    Update the 'Last Used Time' column for a given file in the DataFrame.
    """
    current_time = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    df.loc[df['Path'] == file_path, 'Last Used Time'] = current_time
    
    save_to_csv(df, csv_file)
    
    
def save_to_csv(df, csv_file):
    """
    Save the given DataFrame to the specified CSV file.

    Parameters:
    df (pd.DataFrame): The DataFrame to save.
    csv_file (str): The relative path to the CSV file.

    Returns:
    str: The full path to the saved CSV file.
    """
    # Construct the full path to the CSV file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, csv_file)

    # Save the DataFrame to the CSV file
    df.to_csv(csv_path, index=False, encoding='utf-8')

    return csv_path
