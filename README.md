# Interview Prep — Azure OpenAI

A Python automation tool for technical interview preparation. It reads questions from a plain-text file, calls **Azure OpenAI** to generate structured Markdown answers, persists every Q&A with token usage in **SQLite**, and exports a self-contained **interactive HTML revision page**.

---

## Features

- Reads questions from `input/InterviewQuestions.txt` — one question per line.
- Sends each question to Azure OpenAI using a configurable system prompt that enforces a consistent Markdown response structure (overview, architecture, diagrams, code examples).
- Stores questions (uppercased, normalised) along with answers and per-call token counts in a local SQLite database.
- Exponential back-off retry logic (up to 5 attempts) for transient API failures.
- Renders all Q&A records into a single dark-themed **accordion HTML page** (`output/Answer.html`) with:
  - Syntax-highlighted code blocks via Prism.js
  - Input / output token counts displayed per question
  - Smooth scroll-to-question on accordion toggle

---

## Tech Stack

| Layer | Library / Tool |
|---|---|
| Language | Python `>=3.12` |
| AI / LLM | [openai](https://pypi.org/project/openai/) — Azure OpenAI client |
| HTML templating | [Jinja2](https://pypi.org/project/Jinja2/) `>=3.1.0` |
| Markdown → HTML | [mistune](https://pypi.org/project/mistune/) `>=3.2.1` |
| Environment config | [python-dotenv](https://pypi.org/project/python-dotenv/) `>=1.2.2` |
| Database | SQLite (Python stdlib) |
| Syntax highlighting | Prism.js 1.29.0 (CDN) |

---

## Project Layout

```text
.
├── main.py                          # Main script — API calls, DB, HTML export
├── pyproject.toml                   # Project metadata and dependencies
├── uv.lock                          # Locked dependency graph (uv)
├── input/
│   ├── InterviewQuestions.txt       # One question per line
│   ├── SystemPromptForQuestion.txt  # System prompt sent to Azure OpenAI
│   └── AnswerTemplate.html          # Jinja2 HTML template for output page
├── Database/
│   └── interviewqa.db               # SQLite database (created at runtime)
└── output/
    └── Answer.html                  # Generated HTML revision page
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

The script runs the following steps sequentially:

| Step | Description |
|---|---|
| S1 | Import all Python modules |
| S2 | Resolve folder and file paths |
| S3 | Validate HTML template and create `output/` folder |
| S4 | Load and validate `.env` credentials |
| S5 | Load questions from `InterviewQuestions.txt` |
| S6 | Load system prompt from `SystemPromptForQuestion.txt` |
| S7 | Open SQLite database connection |
| S8 | Create `interview_qa_table` if it does not exist |
| S9 | Test Azure OpenAI client connectivity |
| S10 | Call Azure OpenAI API for each question (with retry) |
| S11 | Insert each Q&A with token counts into SQLite |
| S12 | Fetch all records from database and close connection |
| S13 | Render `output/Answer.html` from the Jinja2 template |

---

## Output

`output/Answer.html` — a self-contained, dark-themed single-page web app:

- Accordion layout: click a question to expand its answer.
- Each question header shows input and output token counts.
- Code blocks are syntax-highlighted (Prism.js autoloader).
- No external dependencies at runtime — open directly in any browser.

---

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS interview_qa_table (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    question_text    TEXT      NOT NULL DEFAULT 'N/A',
    answer_text      TEXT      NOT NULL DEFAULT 'N/A',
    input_token      INTEGER   NOT NULL DEFAULT 0,
    output_token     INTEGER   NOT NULL DEFAULT 0,
    row_inserted_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    model_name       TEXT               DEFAULT 'N/A'
);
```

- `a) Ask me a question`
- `b) Generate PDF`
- `c) Exit`

On first run after upgrading, if legacy files exist under `input/`, the app copies them to `output/` automatically.

### Ask mode (`a`)

- Enter interview questions continuously.
- Type `exit` or `quit` to stop question entry.
- You will be asked `Any more questions? (y/n):`
  - `y` -> continue asking
  - any other value -> auto-generate PDF and terminate

### PDF mode (`b`)

- Exports all saved questions from SQLite to `output/Interview-Questions.pdf`.
- If no data exists, prints `No content to export.`.

## Data model

The app stores content in `output/interview.db`, table `questions`:

- `id` (auto-increment primary key)
- `question` (corrected question text)
- `answer` (structured model output)
- `prompt_tokens`
- `output_tokens`

The app also performs lightweight schema migration for token columns if an older DB exists.

## Reliability and error handling

- API calls retry up to 5 times with exponential backoff capped at 10 seconds.
- Invalid/empty model payloads are treated as retriable failures.
- Missing token usage is safely stored as `0` to avoid runtime failures.
- Missing required env vars fail fast with a clear `KeyError` at startup.

## PDF formatting details

- A4 layout with page border, footer page number, and readable margins.
- One question per page.
- Token usage printed under each question (`[P-<prompt>, O-<output>]`).
- Unicode punctuation is normalized for reliable Times-font rendering.

## Troubleshooting

- **`KeyError: Missing environment variable...`**
  - Verify `.env` exists in project root and includes all 4 required keys.
- **Retries followed by `All 5 attempts failed`**
  - Check endpoint, key, API version, deployment name, and network access.
- **`No content to export.`**
  - Ask at least one question first, then regenerate PDF.

## Security notes

- Do not commit `.env` (it contains secrets).
- Rotate API keys if they are ever exposed.
