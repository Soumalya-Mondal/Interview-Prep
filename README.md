# Interview Prep — Azure OpenAI

A Python automation tool for technical interview preparation. It reads questions from a plain-text file, runs a **two-pass Azure OpenAI pipeline** to first correct each question and then generate a structured Markdown answer, persists everything with token usage in **SQLite**, and exports a self-contained **interactive HTML revision page**.

---

## Features

- Reads questions from `input/InterviewQuestions.txt` — one question per line.
- **Pass 1 — Question correction** (`CorrectQuestionGenerationSystemPrompt.txt`): all questions are sent to Azure OpenAI concurrently (async) to clean and normalise each question into a well-formed technical interview question.
- **Pass 2 — Answer generation** (`QuestionAnswerSystemPrompt.txt`): each corrected question is sent sequentially to Azure OpenAI which returns a structured Markdown response (overview, architecture, diagrams, code examples).
- Cumulative token counts (pass 1 + pass 2) are stored per row in SQLite alongside both the original and corrected question text.
- Renders all Q&A records into a single dark-themed **accordion HTML page** (`output/Answer.html`) with:
  - Syntax-highlighted code blocks via Prism.js
  - Cumulative input / output token counts displayed per question
  - Smooth scroll-to-question on accordion toggle

---

## Tech Stack

| Layer | Library / Tool |
|---|---|
| Language | Python `>=3.12` |
| AI / LLM | [openai](https://pypi.org/project/openai/) `>=2.38.0` — Azure OpenAI client (sync + async) |
| HTML templating | [Jinja2](https://pypi.org/project/Jinja2/) `>=3.1.0` |
| Markdown → HTML | [mistune](https://pypi.org/project/mistune/) `>=3.2.1` |
| Environment config | [python-dotenv](https://pypi.org/project/python-dotenv/) `>=1.2.2` |
| Database | SQLite (Python stdlib) |
| Syntax highlighting | Prism.js 1.29.0 (CDN) |

---

## Project Layout

```text
.
├── main.py                                          # Orchestrates all pipeline steps
├── pyproject.toml                                   # Project metadata and dependencies
├── uv.lock                                          # Locked dependency graph (uv)
├── input/
│   ├── InterviewQuestions.txt                       # One question per line
│   ├── CorrectQuestionGenerationSystemPrompt.txt    # System prompt for question correction (pass 1)
│   ├── QuestionAnswerSystemPrompt.txt               # System prompt for answer generation (pass 2)
│   └── AnswerTemplate.html                          # Jinja2 HTML template for output page
├── supportscripts/
│   ├── credentialcheck.py                           # Loads and validates .env credentials
│   ├── dbtablecreate.py                             # Creates SQLite DB and table
│   ├── questionload.py                              # Reads questions from file → inserts into DB
│   ├── questionprocess.py                           # Pass 1: async question correction via Azure OpenAI
│   ├── questionanswerprocess.py                     # Pass 2: sequential answer generation via Azure OpenAI
│   └── htmlgenerator.py                             # Fetches DB records → renders Answer.html
├── Database/
│   └── interviewqa.db                               # SQLite database (created at runtime)
└── output/
    └── Answer.html                                  # Generated HTML revision page
```

---

## Prerequisites

1. **Azure OpenAI** resource with a deployed chat model.
2. **Python 3.12+**
3. **`uv`** (recommended) or `pip`.

---

## Setup

### 1. Install Dependencies

Using `uv` (recommended):

```bash
uv sync
```

Using `pip`:

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux
pip install -e .
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```dotenv
API_ENDPOINT=https://<your-resource-name>.openai.azure.com/
API_KEY=<your-azure-openai-api-key>
API_VERSION=2024-12-01-preview
CHAT_MODEL_NAME=<your-deployment-name>
```

| Variable | Description |
|---|---|
| `API_ENDPOINT` | Azure OpenAI resource endpoint URL |
| `API_KEY` | Azure OpenAI API key |
| `API_VERSION` | Azure OpenAI REST API version |
| `CHAT_MODEL_NAME` | Deployment name (not the base model label) |

### 3. Add Questions

Edit `input/InterviewQuestions.txt` — one question per line:

```text
What are Python decorators and where have you used them?
Explain Python generators and their benefits.
```

---

## Run

With `uv`:

```bash
uv run python main.py
```

Without `uv`:

```bash
python main.py
```

---

## Execution Pipeline

`main.py` runs the following steps sequentially:

| Step | Function / Module | Description |
|---|---|---|
| S1 | — | Import standard library and third-party modules |
| S2 | — | Append project root to `sys.path` |
| S3 | — | Import `supportscripts` modules |
| S4 | — | Resolve all folder and file paths |
| S5 | `credential_check` | Load `.env` and validate all 4 required environment variables |
| S6 | `db_table_create` | Create `Database/interviewqa.db` and `interview_qa_table` if they don't exist |
| S7 | `question_load` | Read `InterviewQuestions.txt` → insert each question into DB with `row_status = 1` |
| S8 | `question_process` | **Pass 1** — correct all questions concurrently via `AsyncAzureOpenAI`; update DB to `row_status = 2` |
| S9 | `question_answer_process` | **Pass 2** — generate a structured Markdown answer for each corrected question sequentially; update DB to `row_status = 3` |
| S10 | `html_generator` | Fetch all `row_status = 3` records → render `output/Answer.html` via Jinja2 |

---

## Output

`output/Answer.html` — a self-contained, dark-themed single-page web app:

- Accordion layout: click a question to expand its answer.
- Each question header shows cumulative input and output token counts.
- Code blocks are syntax-highlighted (Prism.js autoloader).
- No external dependencies at runtime — open directly in any browser.

---

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS interview_qa_table (
    id                   INTEGER   PRIMARY KEY AUTOINCREMENT,
    row_inserted_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actual_question_text TEXT      NOT NULL DEFAULT 'N/A',
    final_question_text  TEXT      NOT NULL DEFAULT 'N/A',
    answer_text          TEXT      NOT NULL DEFAULT 'N/A',
    input_token          INTEGER   NOT NULL DEFAULT 0,
    output_token         INTEGER   NOT NULL DEFAULT 0,
    model_name           TEXT               DEFAULT 'N/A',
    row_status           INTEGER   NOT NULL DEFAULT 1 CHECK(row_status IN (1, 2, 3))
);
```

| Column | Description |
|---|---|
| `actual_question_text` | Raw question text as read from the input file |
| `final_question_text` | Corrected question text produced by pass 1 |
| `answer_text` | Structured Markdown answer produced by pass 2 |
| `input_token` / `output_token` | Cumulative token counts across both passes |
| `row_status` | `1` = inserted · `2` = question corrected · `3` = answer generated |

---

## Troubleshooting

- **`ERROR - [Main:S5] - Credential Check Failed`**
  — Verify `.env` exists in the project root and contains all four required variables (`API_KEY`, `API_VERSION`, `API_ENDPOINT`, `CHAT_MODEL_NAME`).

- **`ERROR - [Main:S8] - Question Process Failed`**
  — Ensure `input/CorrectQuestionGenerationSystemPrompt.txt` exists and is not empty.

- **`ERROR - [Main:S9] - Question Answer Process Failed`**
  — Ensure `input/QuestionAnswerSystemPrompt.txt` exists and is not empty. Also check that pass 1 completed successfully (`row_status = 2` rows must exist).

- **`No Records Found In Database To Export`**
  — All pipeline steps must complete before HTML generation. Re-run `main.py` after fixing any upstream error.
- **Retries followed by `All 5 attempts failed`**
  - Check endpoint, key, API version, deployment name, and network access.
- **`No content to export.`**
  - Ask at least one question first, then regenerate PDF.

## Security notes

- Do not commit `.env` (it contains secrets).
- Rotate API keys if they are ever exposed.
