# Sergeley (2.9)

**Sergeley** is a Python application designed to help researchers and academics manage and organize their collection of scientific papers (PDF files). It provides a user-friendly interface to search, categorize, and maintain a database of PDFs with rich metadata.

## New Feature: Directory-Based Databases

- **Multiple Databases Support**:
  - The application now automatically creates and manages separate databases for different directories.
  - The CSV database filename is generated based on the directory path (e.g., scanning `F:\Papers` creates `file_database_Papers.csv`).
  - Easily switch between different collections by changing the directory in the application.

## Features

- **Directory Scanning and Database Updating**:
  - **Set Directory to Scan**: Specify the folder containing your PDF papers.
  - **Update Database**: Scan the directory to find new, moved, or modified PDF files and update the corresponding database.
  - **Automatic BibTeX Extraction**: Optionally extract DOI from new PDFs to fetch and store BibTeX entries.

- **Search Functionality**:
  - **Fuzzy Search**: Search papers using keywords with a customizable similarity threshold (0-100).
  - **Tag Filtering**: View and search papers based on custom tags enclosed in `{}` within the comments.
  - **Recent Papers**:
    - **Show Recent Papers**: Display papers added or modified in the last 4 weeks.
    - **Show Just Added Papers**: Display papers added or modified in the last 12 hours.

- **Paper Management**:
  - **Open PDF**: Open the selected PDF file directly from the application.
  - **Move Paper**: Move a paper to a different directory and update its path in the database.
  - **Show in Folder**: Open the file explorer to the location of the selected PDF.

- **Metadata Editing**:
  - **Copy BibTeX**: Copy the BibTeX entry of a paper to the clipboard.
  - **Edit BibTeX**: Modify the BibTeX information stored for a paper.
  - **Edit Comments**: Add or edit comments for a paper to include notes or tags.

- **Duplicate Detection**:
  - **Find Duplicates**: Automatically detect duplicate papers based on DOI and confirm deletion.

## Getting Started

### Prerequisites

- **Python 3.x**

### Required Python Packages

- `pandas`
- `pdf2doi`
- `pyperclip`
- `fuzzywuzzy`
- `python-dateutil`
- `tkinter` (usually included with Python)
- Additional standard libraries: `os`, `sys`, `re`, `shutil`, `subprocess`, `time`, `datetime`, `random`, `string`, `json`, `threading`

### Installation

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/yourusername/PDFSearchApp.git
   cd PDFSearchApp
   ```

2. **Install Dependencies**:

   ```bash
   pip install pandas pdf2doi pyperclip fuzzywuzzy python-dateutil
   ```

3. **Run the Application**:

   ```bash
   python main.py
   ```

## Usage

1. **Set Directory to Scan**:

   - In the application, enter the path to the directory containing your PDFs.
   - The application will create or load a database specific to that directory.

2. **Update Database**:

   - Click **Update Database** to scan the directory and update the database.
   - The database file is named based on the directory (e.g., `file_database__Papers_General.csv`).

3. **Switch Between Databases**:

   - To work with different collections, change the directory path in the application.
   - The application will automatically switch to the corresponding database.

4. **Search and Manage Papers**:

   - Use the search functionality, tag filtering, and recent papers features as before.
   - All features operate within the context of the currently selected directory/database.

## File Structure

- **main.py**: Entry point of the application.
- **utils.py**: Utility functions for loading directories, databases, and parsing BibTeX fields.
- **database_utils.py**: Functions related to database validation and directory scanning.
- **confirm_dialogs.py**: GUI functions for confirmation dialogs.
- **pdf_search_app.py**: Contains the `PDFSearchApp` class with all GUI-related methods.
- **file_database_<sanitized_directory_path>.csv**: CSV files storing information about your PDF files for each directory.
- **default_directory.txt** (optional): Stores the default directory path.

## Notes

- **Directory-Based Databases**:

  - The application creates a separate database for each directory scanned.
  - CSV filenames are generated by sanitizing the directory path.
  - This allows for organized management of different collections of papers.

- **Default Directory**:

  - The application can load a default directory from `default_directory.txt`.
  - If this file doesn't exist, you can set the directory within the application.

- **Tags**:

  - Tags are enclosed in curly braces `{}` within the comments section of a paper.
  - Use tags to categorize and easily filter papers.

- **Duplicate Detection**:

  - The application detects duplicates based on the DOI extracted from BibTeX entries.
  - It prompts for confirmation before deleting any files.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **pdf2doi**: Used for extracting DOI and metadata from PDF files.
- **fuzzywuzzy**: Used for fuzzy string matching in search functionality.

---

Feel free to customize this description further to suit your repository's needs.
