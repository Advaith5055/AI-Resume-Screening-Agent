# AI Resume Screening Agent

Automated, deterministic resume screening system. Takes a job description and a batch of resumes, scores each candidate across five weighted factors using explicit skill matching and semantic similarity, ranks them, generates grounded explanations, and exports results as CSV/JSON.

**No LLM required.** All scoring, matching, ranking, and explanations run fully offline.

---

## How It Works

```
Job Description + Resumes (PDF / DOCX / TXT)
        │
        ▼
  Document Parsing  →  Structured Extraction  →  Canonical Skill Normalization
        │
        ▼
  Explicit Skill Matching + Semantic Similarity (all-MiniLM-L6-v2)
        │
        ▼
  Deterministic Composite Scoring (0–100)  →  Ranking  →  Grounded Explanations
        │
        ▼
  CSV + JSON Export  /  Interactive Streamlit Dashboard
```

---

## Scoring Formula

| Factor              | Weight | Method |
| :------------------ | -----: | :----- |
| Required Skills     |    40% | Exact match against canonical skill dictionary |
| Preferred Skills    |    20% | Exact match (redistributed to Required if JD has none) |
| Semantic Similarity |    20% | Cosine similarity of sentence embeddings |
| Experience          |    15% | Duration ratio vs. JD minimum |
| Education           |     5% | Degree tier + field-of-study match |

- **Deterministic**: same inputs always produce same scores and rankings.
- **Tie-breaking**: required skill score → semantic similarity → alphabetical name.
- **Explanations are read-only**: generated after scoring, never modify results.

---

## Tech Stack

| Component | Technology |
| :-------- | :--------- |
| Language | Python 3.10+ |
| Data Models | Pydantic v2 |
| PDF Parsing | pypdf |
| DOCX Parsing | python-docx |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`, ~80 MB, local) |
| Similarity | scikit-learn (cosine) |
| Dashboard | Streamlit |
| Testing | pytest (79 tests) |
| Export | pandas, csv, json |

---

## Quick Start

```bash
# 1. Clone and set up
git clone https://github.com/Advaith5055/AI-Resume-Screening-Agent.git
cd AI-Resume-Screening-Agent
python -m venv .venv

# Windows
.\.venv\Scripts\Activate.ps1
# Linux / macOS
# source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run batch screening (CLI)
python -m app.main --job data/job_descriptions/sample_job_description.txt --resumes data/resumes --output outputs

# 4. Run interactive dashboard
streamlit run dashboard.py

# 5. Run tests
python -m pytest
```

### CLI Options

| Option | Description | Default |
| :----- | :---------- | :------ |
| `--job` / `-j` | Job description file (.pdf, .docx, .txt) | `data/job_descriptions/sample_job_description.txt` |
| `--resumes` / `-r` | Directory of candidate resumes | `data/resumes` |
| `--output` / `-o` | Output directory for reports | `outputs` |
| `--top-n` / `-n` | Limit to top N candidates | All |

### Dashboard

`streamlit run dashboard.py` launches a web UI where you can:
- Upload a JD and resumes (or use the built-in sample dataset)
- View ranked candidates with score breakdowns, skill tags, and explanations
- Filter by minimum score
- Download CSV/JSON reports

---

## Example Output

11 sample resumes screened against "Junior AI Research Associate":

```
 1. Priya Sharma    — 91.5/100   [Skills: 100% | Semantic: 73.9% | Exp: 100%]
 2. Marcus Vance    — 79.7/100   [Skills: 100% | Semantic: 65.1% | Exp: 100%]
 3. Rajesh Kumar    — 77.6/100   [Skills: 87.5% | Semantic: 63.2% | Exp: 100%]
 4. David Miller    — 73.0/100   [Skills: 87.5% | Semantic: 64.3% | Exp: 100%]
 5. Alex Chen       — 62.2/100   [Skills: 50.0% | Semantic: 68.4% | Exp: 100%]
 6. Sarah Connor    — 59.7/100   [Skills: 62.5% | Semantic: 60.4% | Exp: 100%]
 7. Elena Rostova   — 52.1/100   [Skills: 75.0% | Semantic: 51.9% | Exp:  50%]
 8. Emily Watson    — 51.9/100   [Skills: 37.5% | Semantic: 62.4% | Exp: 100%]
 9. Aditya Sharma   — 46.5/100   [Skills: 37.5% | Semantic: 69.4% | Exp:  50%]
10. Fatima Mansoor  — 46.3/100   [Skills: 37.5% | Semantic: 51.1% | Exp: 100%]
11. Lucas Silva     — 36.8/100   [Skills: 12.5% | Semantic: 53.3% | Exp: 100%]
```

Each candidate entry in `ranking.csv` / `ranking.json` includes full score breakdowns, matched/missing skills, and a 2–4 sentence grounded explanation.

---

## Project Structure

```
ai-resume-screening-agent/
├── app/
│   ├── config.py                  # Environment config (python-dotenv)
│   ├── main.py                    # CLI entry point
│   ├── parsers/                   # PDF, DOCX, TXT document parsers
│   ├── extractors/                # Rule-based resume + JD extraction
│   │   ├── resume_extractor.py    #   Candidate profile extraction
│   │   └── jd_extractor.py        #   Job description extraction
│   ├── models/                    # Pydantic schemas
│   │   ├── candidate.py           #   Candidate, Education, Experience
│   │   ├── job_description.py     #   JobDescription
│   │   └── ranking.py             #   ScoreBreakdown, MatchResult, RankedCandidate, BatchScreeningResult
│   ├── engine/                    # Screening engine
│   │   ├── embeddings.py          #   SentenceTransformer + mock embedding services
│   │   ├── matcher.py             #   Skill matching + semantic text builders
│   │   ├── scorer.py              #   Multi-factor composite scoring
│   │   ├── ranker.py              #   Deterministic ranking + tie-breaking
│   │   ├── explanation.py         #   Grounded explanation generation (deterministic + optional LLM)
│   │   └── pipeline.py            #   Batch orchestration
│   └── exporters/                 # CSV + JSON report generation
├── dashboard.py                   # Streamlit web UI
├── data/                          # Sample JD + 11 synthetic resumes
├── tests/                         # 79 automated tests
├── outputs/                       # Generated reports (gitignored)
├── requirements.txt
└── .env.example
```

---

## Explanation Layer

Every candidate receives a 2–4 sentence evidence-grounded explanation referencing only structured data (matched skills, missing skills, experience, scores).

- **Default**: Deterministic rule-based templates — no external dependencies.
- **Optional**: Set `LLM_API_BASE` in `.env` to point to a local LLM (e.g., Ollama) for richer phrasing. Falls back to deterministic automatically if unavailable.

---

## Limitations

- Rule-based extraction may miss unconventional resume formats or multi-column layouts.
- Semantic similarity captures contextual alignment but does not replace human judgment.
- Demo data is synthetic; real-world resumes may surface edge cases.
- This is a screening aid, not an autonomous hiring decision-maker.
