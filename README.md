# Sergeley

**Sergeley** is a Python application designed to help researchers and academics manage and organize their collection of scientific papers (PDF files). It provides a user-friendly interface to search, categorize, and maintain a database of PDFs with rich metadata.

## Features

- **Directory Scanning and Database Updating**:
  - **Set Directory to Scan**: Specify the folder containing your PDF papers.
  - **Update Database**: Scan the directory to find new, moved, or modified PDF files and update the database accordingly.
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
- `concurrent.futures` (included in Python 3)
- `dateutil`
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

3. **Place Your Existing Database (Optional)**:

   - If you have an existing `file_database.csv`, place it in the main project directory.

4. **Run the Application**:

   ```bash
   python main.py
   ```

## Usage

1. **Set Directory to Scan**:

   - In the application, enter the path to the directory containing your PDFs.
   - Click **Update Database** to scan the directory and update the database.

2. **Search for Papers**:

   - Enter keywords in the **Enter search keywords** field.
   - Set the desired similarity threshold (default is 70).
   - Click **Search** to display matching papers.

3. **View Tags**:

   - Click **Show {Tags}** to display a list of all tags.
   - Double-click a tag to view papers associated with it.

4. **View Recent Papers**:

   - **Show Recent Papers**: Displays papers added or modified in the last 4 weeks.
   - **Show just added papers**: Displays papers added or modified in the last 12 hours.

5. **Manage Papers**:

   - **Open PDF**: Opens the selected PDF file.
   - **Move Paper**: Move the paper to a new directory.
   - **Show in Folder**: Opens the file explorer at the paper's location.
   - **Copy BibTeX**: Copies the BibTeX entry to the clipboard.
   - **Edit BibTeX**: Opens a window to edit the BibTeX information.
   - **Edit Comments**: Opens a window to add or edit comments (e.g., `{tag1}`, `{tag2}`).

6. **Update Database**:

   - Regularly update the database after adding new papers to keep it current.

## File Structure

- **main.py**: Entry point of the application.
- **utils.py**: Utility functions for loading directories, databases, and parsing BibTeX fields.
- **database_utils.py**: Functions related to database validation and directory scanning.
- **confirm_dialogs.py**: GUI functions for confirmation dialogs.
- **pdf_search_app.py**: Contains the `PDFSearchApp` class with all GUI-related methods.
- **file_database.csv**: CSV file storing information about your PDF files.
- **default_directory.txt** (optional): Stores the default directory path.

## Notes

- **Default Directory**:

  - The application can load a default directory from `default_directory.txt`. If this file doesn't exist, you can set the directory within the application.

- **Tags**:

  - Tags are enclosed in curly braces `{}` within the comments section of a paper. Use tags to categorize and easily filter papers.

- **Duplicate Detection**:

  - The application detects duplicates based on the DOI extracted from BibTeX entries. It prompts for confirmation before deleting any files.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **pdf2doi**: Used for extracting DOI and metadata from PDF files.
- **fuzzywuzzy**: Used for fuzzy string matching in search functionality.

---

Feel free to customize this description further to suit your repository's needs.
