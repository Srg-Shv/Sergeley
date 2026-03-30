import os
import time
import pandas as pd
import re
from datetime import datetime
from utils import load_database, parse_bibtex_field

def scan_directory_fast(directory, existing_files_info, missing_files_name_to_info):
    """
    Scans the directory using os.scandir (which is 5-10x faster than os.walk + threads 
    because it caches file stats at the OS level).
    """
    new_data = []
    updated_data =[]
    moved_data = []
    files_requiring_confirmation =[]

    def _scan(dir_path):
        try:
            with os.scandir(dir_path) as it:
                for entry in it:
                    if entry.is_dir(follow_symlinks=False):
                        _scan(entry.path)
                    elif entry.is_file(follow_symlinks=False):
                        ext = os.path.splitext(entry.name)[1].lower()
                        if ext in ['.pdf', '.djvu']:
                            # entry.stat() is cached, making this incredibly fast
                            stat = entry.stat()
                            size = stat.st_size
                            modified_date = time.ctime(stat.st_mtime)
                            full_path = entry.path
                            file_name = entry.name

                            if full_path not in existing_files_info:
                                if file_name in missing_files_name_to_info:
                                    # File has been moved
                                    old_path = missing_files_name_to_info[file_name]['old_path']
                                    moved_data.append({
                                        'OldPath': old_path, 'Path': full_path, 
                                        'Size': size, 'Modified Date': modified_date
                                    })
                                else:
                                    # New file
                                    bibtex_info = '' if ext == '.djvu' else None
                                    if ext == '.pdf':
                                        files_requiring_confirmation.append((full_path, file_name, ext, size, modified_date))
                                    
                                    date_added = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                    
                                    # OPTIMIZATION: Align exactly with the new schema!
                                    new_data.append({
                                        'Path': full_path, 'Name': file_name, 'Size': size,
                                        'Modified Date': modified_date, 'BibTeX': bibtex_info,
                                        'Comments': '', 'Last Used Time': None, 'Date Added': date_added,
                                        'Title': pd.NA, 'Author': pd.NA, 'Year': pd.NA
                                    })
                            else:
                                # Check if updated
                                if size != existing_files_info[full_path]['size'] or modified_date != existing_files_info[full_path]['modified_date']:
                                    updated_data.append({
                                        'Path': full_path, 'Size': size, 'Modified Date': modified_date
                                    })
        except PermissionError:
            pass # Skip folders we don't have permission to read

    _scan(directory)
    return new_data, updated_data, moved_data, files_requiring_confirmation


def check_database_validity(directory, csv_file):
    if not os.path.exists(directory):
        return None, None, None, None, f"The directory '{directory}' does not exist."

    df = load_database(csv_file)
    
    existing_files_info = {
        row['Path']: {'size': row['Size'], 'modified_date': row['Modified Date']}
        for _, row in df.iterrows()
    }
    
    missing_files =[file_path for file_path in existing_files_info if not os.path.exists(file_path)]
    missing_files_info = df[df['Path'].isin(missing_files)].copy()
    missing_files_name_to_info = {row['Name']: {'old_path': row['Path']} for _, row in missing_files_info.iterrows()}

    # Run the lightning-fast scanner
    new_data, updated_data, moved_data, files_requiring_confirmation = scan_directory_fast(
        directory, existing_files_info, missing_files_name_to_info
    )

    messages =[]

    # --- OPTIMIZATION: Vectorized Updates (No more slow loops!) ---
    
    if moved_data:
        moved_df = pd.DataFrame(moved_data)
        # Create fast lookup dictionaries
        path_mapping = dict(zip(moved_df['OldPath'], moved_df['Path']))
        size_mapping = dict(zip(moved_df['OldPath'], moved_df['Size']))
        mod_mapping = dict(zip(moved_df['OldPath'], moved_df['Modified Date']))

        # Apply updates instantly using .map()
        mask = df['Path'].isin(path_mapping.keys())
        df.loc[mask, 'Size'] = df.loc[mask, 'Path'].map(size_mapping)
        df.loc[mask, 'Modified Date'] = df.loc[mask, 'Path'].map(mod_mapping)
        df.loc[mask, 'Path'] = df.loc[mask, 'Path'].map(path_mapping)

        messages.append(f"Database has been updated with {len(moved_data)} moved file(s).")
    else:
        messages.append("Database has been updated with 0 moved file(s).")

    if new_data:
        new_df = pd.DataFrame(new_data)
        df = pd.concat([df, new_df], ignore_index=True)
        messages.append(f"Database has been updated with {len(new_data)} new file(s).")
    else:
        messages.append("Database has been updated with 0 new file(s).")

    if updated_data:
        updated_df = pd.DataFrame(updated_data)
        # Instant bulk update using index alignment
        df.set_index('Path', inplace=True)
        updated_df.set_index('Path', inplace=True)
        df.update(updated_df)
        df.reset_index(inplace=True)
        messages.append(f"Database has been updated with {len(updated_data)} modified file(s).")
    else:
        messages.append("Database has been updated with 0 modified file(s).")

    # Remove missing files that weren't moved
    moved_old_paths = set(d['OldPath'] for d in moved_data)
    remaining_missing_files = set(missing_files) - moved_old_paths
    
    if remaining_missing_files:
        messages.append(f"Removing {len(remaining_missing_files)} missing file(s) from the database.")
        df = df[~df['Path'].isin(remaining_missing_files)]
    else:
        messages.append("No missing files were removed.")

    save_to_csv(df, csv_file)

    # Collect duplicates
    duplicates_to_confirm = find_duplicates(df)

    return df, messages, files_requiring_confirmation, duplicates_to_confirm, None


def find_duplicates(df):
    """
    Finds duplicates based on Name, Size, and DOI.
    """
    duplicate_groups =[]
    processed_paths = set()

    def add_groups(grouped):
        for _, group in grouped:
            # Filter out files we already flagged in a previous check
            group = group[~group['Path'].isin(processed_paths)]
            if len(group) > 1:
                duplicate_groups.append(group)
                processed_paths.update(group['Path'].tolist())

    # 1. Exact File Name Match (Fastest)
    add_groups(df[df.duplicated(subset='Name', keep=False)].groupby('Name'))

    # 2. Exact File Size Match (Ignore files < 1KB to prevent false positives)
    df_size = df[df['Size'] > 1000]
    add_groups(df_size[df_size.duplicated(subset='Size', keep=False)].groupby('Size'))

    # 3. Exact DOI Match (Deepest)
    # Safely extract DOIs, ignoring empty or missing BibTeX entries
    if 'BibTeX' in df.columns:
        extracted_dois = df['BibTeX'].astype(str).str.extract(r'doi\s*=\s*\{([^}]+)\}', flags=re.IGNORECASE)[0].str.strip()
        valid_dois = extracted_dois.notna() & (extracted_dois != '')
        
        df_dois = df[valid_dois].copy()
        df_dois['DOI_extracted'] = extracted_dois[valid_dois]
        
        add_groups(df_dois[df_dois.duplicated(subset='DOI_extracted', keep=False)].groupby('DOI_extracted'))

    return duplicate_groups


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
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(script_dir, csv_file)

    df.to_csv(csv_path, index=False, encoding='utf-8')

    return csv_path
