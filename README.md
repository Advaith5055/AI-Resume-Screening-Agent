# AI Resume Screening Agent

An automated, explainable resume screening system built for the Junior AI Research Associate selection challenge. The agent screens batches of candidate resumes against job descriptions, computes grounded relevance scores, produces explainable evaluation summaries, and exports ranked candidate lists in CSV and JSON formats.

---

## Current Architecture

The project is structured into modular, decoupled packages designed for clean extension:

```text
ai-resume-screening-agent/
├── .env.example              # Environment variables template
├── .gitignore                # Git ignore rules for Python, IDEs, and data artifacts
├── README.md                 # Project documentation and quickstart guide
├── requirements.txt          # Core dependencies
├── app/
│   ├── __init__.py           # Package version definition
│   ├── config.py             # Configuration loaded via python-dotenv & os.environ
│   ├── main.py               # Application entrypoint
│   ├── parsers/              # Document parsers (PDF, DOCX, base interfaces)
│   ├── extractors/           # Information extraction for resumes and job descriptions
│   ├── models/               # Pydantic schemas for candidates, JDs, and rankings
│   ├── engine/               # Matching, scoring, and ranking engine
│   └── exporters/            # CSV and JSON report exporters
├── data/
│   ├── job_descriptions/     # Directory for input job descriptions
│   └── resumes/              # Directory for input candidate resumes (10+)
├── outputs/                  # Exported rankings and evaluation summaries
└── tests/
    ├── __init__.py
    ├── conftest.py           # Shared test fixtures
    └── test_main.py          # Smoke tests
```

---

## Setup & Getting Started

### 1. Prerequisites
- Python 3.10+ installed on your system.

### 2. Create and Activate a Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to create your local `.env`:
```bash
cp .env.example .env
```
*(On Windows PowerShell, use `Copy-Item .env.example .env`)*

---

## Running the Application

To execute the entry point:
```bash
python -m app.main
```

### Running Tests
To run the automated smoke tests with pytest:
```bash
pytest
```
