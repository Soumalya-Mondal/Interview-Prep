import json
import os
import sqlite3
import shutil
import sys
import time
from dotenv import load_dotenv
from fpdf import FPDF
from openai import AzureOpenAI

load_dotenv()


def _get_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    raise KeyError(f"Missing environment variable. Tried: {', '.join(names)}")


client = AzureOpenAI(
    azure_endpoint=_get_env("API_ENDPOINT"),
    api_key=_get_env("API_KEY"),
    api_version=_get_env("API_VERSION"),
)

DEPLOYMENT = _get_env("CHAT_MODEL_NAME")
OUTPUT_DIR = "output"
LEGACY_DIR = "input"
DB_FILE  = os.path.join(OUTPUT_DIR, "interview.db")
PDF_FILE = os.path.join(OUTPUT_DIR, "Interview-Questions.pdf")
os.makedirs(OUTPUT_DIR, exist_ok=True)


SYSTEM_PROMPT = """I am preparing for an interview and the role is AI/ML Engineer with 4-5 years of experience. I will ask questions that may contain spelling mistakes or grammatical errors.
First, correct the question if needed, then answer it as follows:
- Start with 3-4 clear and concise sentences describing the concept in depth.
- Then provide between 5 and 10 bullet points (as many as needed) covering key details, facts, use cases, and important distinctions.
- After ALL bullet points, add a section starting with "Explanation:" that gives a practical example or scenario to reinforce the concept.

You MUST respond only with a valid JSON object in exactly this format (include 5-10 bullet points as appropriate):
{
  "corrected_question": "<grammatically correct version of the user's question>",
  "answer": "<3-4 line description>\\n\\n• <point 1>\\n• <point 2>\\n• <point 3>\\n• <point 4>\\n• <point 5>\\n• <point 6>\\n• <point 7>\\n• <point 8>\\n\\nExplanation:\\n<practical example or scenario>"
}

No extra text, no markdown, no code fences — just the raw JSON object."""


MAX_RETRIES = 5
MAX_WAIT   = 10  # seconds


def ask(question: str) -> tuple[str, str, int, int]:
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=DEPLOYMENT,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": question},
                ],
            )
            if not response.choices:
                raise ValueError("No choices in response")

            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty content in response")

            data = json.loads(content)
            corrected = data.get("corrected_question", question)
            answer = data.get("answer", "")
            if not answer:
                raise ValueError("Empty answer in response")
            usage = response.usage
            prompt_tokens = usage.prompt_tokens if usage and usage.prompt_tokens is not None else 0
            output_tokens = usage.completion_tokens if usage and usage.completion_tokens is not None else 0
            return corrected, answer, prompt_tokens, output_tokens
        except Exception as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                wait = min(2 ** (attempt - 1), MAX_WAIT)  # 1, 2, 4, 8, 10 ...
                print(f"[Retry {attempt}/{MAX_RETRIES}] Error: {exc}. Retrying in {wait}s...")
                time.sleep(wait)

    print(f"\nAll {MAX_RETRIES} attempts failed: {last_error}")
    sys.exit(1)


def migrate_legacy_files() -> None:
    legacy_db = os.path.join(LEGACY_DIR, "interview.db")
    legacy_pdf = os.path.join(LEGACY_DIR, "Interview-Questions.pdf")

    if not os.path.exists(DB_FILE) and os.path.exists(legacy_db):
        shutil.copy2(legacy_db, DB_FILE)
        print(f"Migrated database to '{DB_FILE}'")

    if not os.path.exists(PDF_FILE) and os.path.exists(legacy_pdf):
        shutil.copy2(legacy_pdf, PDF_FILE)
        print(f"Copied existing PDF to '{PDF_FILE}'")


def init_db() -> None:
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                question      TEXT    NOT NULL,
                answer        TEXT    NOT NULL,
                prompt_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0
            )
        """)
        # Migrate existing DB: add token columns if they don't exist yet
        for col in ("prompt_tokens", "output_tokens"):
            try:
                conn.execute(f"ALTER TABLE questions ADD COLUMN {col} INTEGER NOT NULL DEFAULT 0")
            except sqlite3.OperationalError:
                pass  # column already exists


def save_to_db(question: str, answer: str, prompt_tokens: int, output_tokens: int) -> None:
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "INSERT INTO questions (question, answer, prompt_tokens, output_tokens) VALUES (?, ?, ?, ?)",
            (question, answer, prompt_tokens, output_tokens),
        )


def get_next_question_number() -> int:
    with sqlite3.connect(DB_FILE) as conn:
        row = conn.execute("SELECT COUNT(*) FROM questions").fetchone()
    return row[0] + 1


def _to_latin1(text: str) -> str:
    """Replace common non-Latin-1 characters so core Times font renders them."""
    table = str.maketrans({
        "\u2018": "'",  "\u2019": "'",   # curly single quotes
        "\u201c": '"',  "\u201d": '"',   # curly double quotes
        "\u2013": "-",  "\u2014": "--",  # en / em dash
        "\u2026": "...",                  # ellipsis
        "\u2022": "-",                    # bullet (fallback)
        "\u00b7": "-",                    # middle dot
    })
    return text.translate(table).encode("latin-1", errors="replace").decode("latin-1")


def generate_pdf() -> None:
    with sqlite3.connect(DB_FILE) as conn:
        rows = conn.execute(
            "SELECT id, question, answer, prompt_tokens, output_tokens FROM questions ORDER BY id"
        ).fetchall()

    if not rows:
        print("No content to export.")
        return

    # Remove stale PDF before regenerating
    if os.path.exists(PDF_FILE):
        os.remove(PDF_FILE)

    MARGIN = 12   # 1.2 cm content margin
    BORDER = 8    # 0.8 cm page border
    FOOTER_H = 12  # space reserved for footer

    class PDF(FPDF):
        def header(self):
            self.set_draw_color(0, 0, 0)
            self.set_line_width(0.5)
            # Border box: 0.8 cm from every edge on A4 (210 x 297 mm)
            self.rect(BORDER, BORDER, 210 - 2 * BORDER, 297 - 2 * BORDER)

        def footer(self):
            self.set_y(-(FOOTER_H + BORDER))
            self.set_font("Times", "", 9)
            self.set_text_color(80, 80, 80)
            self.cell(0, 10, f"Page-{self.page_no()}", align="C")
            self.set_text_color(0, 0, 0)

    pdf = PDF(format="A4")
    pdf.set_margins(MARGIN, MARGIN, MARGIN)
    pdf.set_auto_page_break(auto=True, margin=MARGIN + FOOTER_H)

    for q_id, question, answer, prompt_tokens, output_tokens in rows:
        # Each question starts on its own page
        pdf.add_page()

        # Question (bold 14pt)
        pdf.set_x(MARGIN)
        pdf.set_font("Times", "B", 14)
        pdf.multi_cell(0, 8, _to_latin1(f"Q{q_id}: {question}"))

        # Token info (regular 8pt)
        pdf.set_x(MARGIN)
        pdf.set_font("Times", "", 8)
        pdf.cell(0, 5, f"[P-{prompt_tokens}, O-{output_tokens}]", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        # Answer label
        pdf.set_x(MARGIN)
        pdf.set_font("Times", "B", 12)
        pdf.cell(0, 7, "Answer:", new_x="LMARGIN", new_y="NEXT")

        # Answer body — render line by line
        for line in answer.split("\n"):
            if not line.strip():
                pdf.ln(3)
            elif line.startswith("\u2022"):
                pdf.set_x(MARGIN)
                pdf.set_font("Times", "", 12)
                pdf.multi_cell(0, 6, _to_latin1("  - " + line[1:].lstrip()))
            else:
                pdf.set_x(MARGIN)
                pdf.set_font("Times", "", 12)
                pdf.multi_cell(0, 6, _to_latin1(line))

    pdf.output(PDF_FILE)
    print(f"\nPDF saved as '{PDF_FILE}'")


def show_menu() -> str:
    print("\n----- Interview Prep -----")
    print("a) Ask me a question")
    print("b) Generate PDF")
    print("c) Exit")
    print("--------------------------")
    while True:
        choice = input("Choose (a/b/c): ").strip().lower()
        if choice in {"a", "b", "c"}:
            return choice
        print("Invalid choice. Please enter a, b, or c.")


def main():
    migrate_legacy_files()
    init_db()
    while True:
        choice = show_menu()

        if choice == "a":
            print("\nType 'exit' or 'quit' when done.\n")
            while True:
                question = input("Question: ").strip()
                if not question:
                    continue
                if question.lower() in {"exit", "quit"}:
                    more = input("Any more questions? (y/n): ").strip().lower()
                    if more != "y":
                        generate_pdf()
                        return
                    continue
                corrected, answer, prompt_tokens, output_tokens = ask(question)
                print(f"AI: {answer}\n")
                save_to_db(corrected, answer, prompt_tokens, output_tokens)

        elif choice == "b":
            generate_pdf()

        elif choice == "c":
            break


if __name__ == "__main__":
    main()
