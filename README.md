
# Bulk Certificate Generator

A web application that generates certificates in bulk from Excel or CSV files and allows users to download individual certificates or all certificates as a ZIP file.

## Features

- Upload recipient details using Excel or CSV files
- Generate PDF certificates in bulk
- Download individual certificates
- Download all generated certificates as a ZIP file
- Dashboard built with HTML, CSS, and JavaScript
- FastAPI backend
- SQLite database

## Technologies Used

- Python
- FastAPI
- SQLite
- HTML
- CSS
- JavaScript
- Pandas
- ReportLab

## Installation

1. Clone this repository.
2. Open the project folder in a terminal.
3. Create a virtual environment:

   ```bash
   python -m venv .venv
   ```

4. Activate it on Windows:

   ```bash
   .venv\Scripts\activate
   ```

5. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

6. Start the application:

   ```bash
   python -m uvicorn app.main:app --reload
   ```

7. Open http://127.0.0.1:8000/ in your browser.

## Project Status

Developed as a Python web application for bulk PDF certificate generation.
