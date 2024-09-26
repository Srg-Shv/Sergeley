**Description:**

This Python program is a PDF management and search tool tailored for organizing a collection of scientific papers in PDF format. It allows you to:

- **Scan directories** to collect and index PDF files.
- **Extract DOI and BibTeX information** automatically from PDFs.
- **Maintain a searchable database** of your PDF files with metadata.
- **Search** for papers using keywords with fuzzy matching.
- **Open PDFs** directly from the application.
- **Copy and edit BibTeX entries** for easy citation management.
- **Add and edit comments** for each paper.
- **Manage duplicates** based on DOI to keep your collection clean.
- **View recent papers** added or modified in the last 4 weeks.
- **Tag papers** using comments and search papers by tags.
- **External Configuration**: The default directory for scanning is specified in an external `default_directory.txt` file for easy customization.

---

**Instructions to Use the Program:**

**Prerequisites:**

1. **Python 3.x**: Ensure you have Python 3 installed on your system.

2. **Required Python Packages**: Install the following packages if not already installed:

   ```bash
   pip install pandas pdf2doi pyperclip fuzzywuzzy[speedup] python-dateutil
   ```

   - **Note**: The `fuzzywuzzy[speedup]` installation includes the `python-Levenshtein` package for faster processing.
   - **Additional Dependencies for `pdf2doi`**: `pdfminer`, `PyPDF2`, and other dependencies may be required. Install them if prompted.

**Steps to Use the Program:**

1. **Save the Program:**

   - Copy the provided Python code into a file named `pdf_search_app.py`.

2. **Create a `default_directory.txt` File:**

   - In the same directory as your script, create a text file named `default_directory.txt`.
   - In this file, enter the full path to the directory where your PDF files are stored (e.g., `F:\_Papers\2024`).
   - This file allows you to easily change the default scanning directory without modifying the script.

3. **Run the Program:**

   - Open a terminal or command prompt.
   - Navigate to the directory where you saved `pdf_search_app.py`.
   - Run the program using the command:

     ```bash
     python pdf_search_app.py
     ```

4. **Set the Directory to Scan:**

   - In the GUI window that appears, the entry field labeled **"Set Directory to Scan:"** will be pre-filled with the path from the `default_directory.txt` file.
   - You can modify this path manually in the GUI if needed.
   - The directory (and its subdirectories) will be scanned for PDF files.

5. **Update the Database:**

   - Click the **"Update Database"** button.
   - The program will scan the specified directory for PDF files.
   - For each new PDF found, you will be asked if you want to extract DOI information.
     - Click **"Yes"** to extract DOI and BibTeX information using `pdf2doi`.
     - Click **"No"** to skip extraction (you can add/edit BibTeX information later).
   - If duplicates are detected based on DOI, you will be prompted to confirm deletion.

6. **Search for Papers:**

   - In the **"Enter search keywords:"** field, input keywords related to the papers you're searching for.
     - Separate multiple keywords with spaces.
   - In the **"Enter similarity threshold (0-100):"** field, input a number (default is **70**).
     - This sets the sensitivity of the fuzzy search; higher values mean stricter matching.
   - Click the **"Search"** button or press **Enter**.
   - Matching results will be displayed below.

7. **Interact with Search Results:**

   - Each search result will display the paper's title, author, and year (if available).
   - Available actions for each paper:
     - **Open PDF**: Opens the PDF file in your default PDF viewer.
     - **Copy BibTeX**: Copies the BibTeX entry to your clipboard for easy citation.
     - **Edit BibTeX**: Allows you to view and edit the BibTeX information.
     - **Edit Comments**: Add or modify comments and tags for the paper.

8. **View Recent Papers:**

   - Click the **"Show Recent Papers"** button to display papers added or modified in the last 4 weeks.

9. **Tagging and Searching by Tags:**

   - **Adding Tags**:
     - When editing comments for a paper, you can add tags by enclosing them in curly braces `{}`.
     - Example: `This paper discusses deep learning methods. {machine learning} {AI}`
   - **Viewing Tags**:
     - Click the **"Show {Tags}"** button to see a list of all tags used.
   - **Searching by Tag**:
     - In the tags list, double-click a tag to display all papers associated with it.

10. **Remove Duplicates:**

   - The program checks for duplicate PDFs based on DOI during database updates.
   - If

duplicates are found, you'll be asked whether to delete the duplicate files.

11. **Edit BibTeX and Comments:**

    - **Edit BibTeX**:
      - Allows you to correct or update the BibTeX entry for accurate citations.
    - **Edit Comments**:
      - Use this to add personal notes or additional metadata.
      - Include tags within `{}` to categorize papers.

---

**Additional Notes:**

- **Error Handling**:
  - If the program encounters issues (e.g., file not found), it will display error messages.
  - Ensure that all directory paths and file names are correct.

- **Dependencies**:
  - The `pdf2doi` library may require additional system dependencies for PDF parsing.
  - If you encounter issues with DOI extraction, check the `pdf2doi` documentation.

- **Data Storage**:
  - The program stores information in a CSV file named `file_database.csv` in the same directory as the script.
  - This file is updated whenever you update the database or make changes.

- **Exiting the Program**:
  - Close the GUI window to exit the application.
  - All changes are saved automatically upon exit or when actions are performed.

---

**Summary:**

This program streamlines the management of your scientific paper collection by automating the organization and retrieval process. By extracting metadata and providing robust search capabilities, it helps you keep track of your papers, easily find relevant literature, and maintain an organized library for your research needs.

---

**Enjoy managing your scientific papers efficiently!**
