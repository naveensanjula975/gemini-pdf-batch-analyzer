# Gemini PDF Batch Analyzer

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

### 1. Clone and Setup

```powershell
# Clone the repository
git clone <url>
cd gemini-pdf-batch-analyzer

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows PowerShell
# source .venv/bin/activate   # Linux/macOS

# Install dependencies
pip install -e ".[dev]"
```

### 2. Configure

```powershell
# Copy the example environment file
cp .env.example .env

# Edit .env and add your Gemini API key
# Get your API key from: https://aistudio.google.com/apikey
```

### 3. Add PDFs

Place your PDF files in `data/input_pdfs/`

### 4. Run Analysis

```powershell
# Using the CLI
python -m gemini_pdf_analyzer

# Or use the convenience script
.\scripts\run_analysis.ps1

# With options
python -m gemini_pdf_analyzer --input-dir my_pdfs --output-dir results --max-docs 10
```

## 📖 Usage

### Command Line Options

```
python -m gemini_pdf_analyzer [OPTIONS]

Options:
  -i, --input-dir PATH     Directory containing PDF files
  -o, --output-dir PATH    Directory for output files
  -m, --model-name NAME    Gemini model (default: gemini-2.0-flash)
  -n, --max-docs N         Maximum PDFs to process
  -F, --filter PATTERN     Filter filenames (glob syntax, e.g. 'report*.pdf')
  -f, --format FORMAT      Output formats: csv, json, jsonl, excel
  --no-cache               Disable caching, re-analyze all files
  --clear-cache            Clear cached results and exit
  --no-progress            Disable progress bars
  -v, --verbose            Enable verbose logging
  -q, --quiet              Suppress most output
  --version                Show version
  --help                   Show help message
```

### Examples

```powershell
# Process only reports, export to Excel and CSV
python -m gemini_pdf_analyzer --filter "report*.pdf" --format excel csv

# Re-analyze everything (ignore cache)
python -m gemini_pdf_analyzer --no-cache

# Custom paths and verbose output
python -m gemini_pdf_analyzer -i ./reports -o ./analysis -v

# Clear current analysis cache
python -m gemini_pdf_analyzer --clear-cache
```
