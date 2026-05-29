# Interview Prep CLI (Azure OpenAI)

A production-style command-line tool for AI/ML interview preparation. It accepts free-form questions, asks Azure OpenAI for structured answers, stores each Q&A in SQLite, and exports a polished PDF revision pack.

## What this project does

- Corrects grammar/spelling in each question before storing it.
- Generates interview-ready responses in a consistent format:
  - 3-4 sentence concept explanation
  - 5-10 bullet points
  - practical `Explanation:` scenario
- Tracks token usage (`prompt_tokens`, `output_tokens`) per question.
- Persists data locally in SQLite for repeatable exports.
- Builds an A4 PDF with one question per page, page numbers, and clean formatting.

## Tech stack

- Python `>=3.12`
- [openai](https://pypi.org/project/openai/) (Azure OpenAI client)
- [python-dotenv](https://pypi.org/project/python-dotenv/)
- [fpdf2](https://pypi.org/project/fpdf2/)
- SQLite (built into Python)

## Project layout

```text
.
|-- main.py            # CLI app logic, Azure call, DB, PDF export
|-- pyproject.toml     # dependencies and Python version
|-- uv.lock            # locked dependency graph (uv)
`-- input/             # generated at runtime
    |-- interview.db
    `-- Interview-Questions.pdf
```

## Prerequisites

1. Azure OpenAI resource and deployed chat model.
2. Python 3.12+.
3. `uv` (recommended) or `pip`.

## Setup

### 1) Install dependencies

Using `uv` (recommended):

```bash
uv sync
```

Using `pip`:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2) Configure environment variables

Start from the template:

```bash
cp .env.example .env
```

Create a `.env` file in the project root:

```dotenv
API_ENDPOINT=https://<your-resource-name>.openai.azure.com/
API_KEY=<your-azure-openai-key>
API_VERSION=2024-12-01-preview
CHAT_MODEL_NAME=<your-azure-deployment-name>
```

Variable reference:

- `API_ENDPOINT`: Azure OpenAI endpoint URL.
- `API_KEY`: Azure OpenAI API key.
- `API_VERSION`: Azure OpenAI REST API version.
- `CHAT_MODEL_NAME`: Azure deployment name (not the base model family label).

## Run the application

With `uv`:

```bash
uv run python main.py
```

Without `uv`:

```bash
python3 main.py
```

## CLI workflow

On launch, you see:

- `a) Ask me a question`
- `b) Generate PDF`
- `c) Exit`

### Ask mode (`a`)

- Enter interview questions continuously.
- Type `exit` or `quit` to stop question entry.
- You will be asked `Any more questions? (y/n):`
  - `y` -> continue asking
  - any other value -> auto-generate PDF and terminate

### PDF mode (`b`)

- Exports all saved questions from SQLite to `input/Interview-Questions.pdf`.
- If no data exists, prints `No content to export.`.

## Data model

The app stores content in `input/interview.db`, table `questions`:

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
