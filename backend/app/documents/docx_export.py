"""Writes the report as a Word file with python-docx. The content comes from report.py."""
import io

from docx import Document
from docx.shared import Pt, RGBColor

from .readers import clean_text
from .report import APPROVED_NOTE, DRAFT_NOTE, DUPLICATES_NOTE, LEGEND, QUESTIONS_NOTE, WARNINGS_NOTE


def add_note(document, value, warning=False):
    run = document.add_paragraph().add_run(value)
    run.italic = not warning
    run.bold = warning
    if warning:
        run.font.color.rgb = RGBColor(0x92, 0x40, 0x0E)


def add_table(document, headers, rows, empty_message):
    if not rows:
        add_note(document, empty_message)
        return
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Light Grid Accent 1"
    for cell, header in zip(table.rows[0].cells, headers):
        cell.text = header
    for row in rows:
        for cell, value in zip(table.add_row().cells, row):
            cell.text = clean_text(str(value))
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(9)


def add_stories(document, stories, empty_message):
    if not stories:
        add_note(document, empty_message)
    for item in stories:
        document.add_paragraph(clean_text(f'{item["requirement"]}: {item["story"]}'))
        for criterion in item["criteria"]:
            document.add_paragraph(clean_text(criterion), style="List Bullet")


def render_docx(report: dict) -> bytes:
    document = Document()
    document.styles["Normal"].font.name = "Calibri"
    document.styles["Normal"].font.size = Pt(10.5)

    document.add_heading(clean_text(report["title"]), level=0)
    document.add_paragraph("Software Requirements Report")
    add_note(document, f'Generated {report["generated"]}')
    if report["description"]:
        document.add_paragraph(clean_text(report["description"]))
    add_note(document, LEGEND)
    add_table(document, ["Measure", "Count"], list(report["stats"].items()), "")

    document.add_heading("1. Original requirements summary", level=1)
    for item in report["documents"]:
        document.add_paragraph().add_run(clean_text(f'{item["name"]} ({item["words"]} words)')).bold = True
        document.add_paragraph(clean_text(item["excerpt"]))
    if not report["documents"]:
        add_note(document, "No source documents.")

    document.add_heading("2. Structured requirements", level=1)
    add_table(document, ["ID", "Requirement", "Type", "Category", "Status", "Source sentence"],
              [[r["id"], r["text"], r["type"], r["category"], r["status"], r["source"]]
               for r in report["requirements"]], "No requirements yet.")

    document.add_heading("3. Functional requirements", level=1)
    add_table(document, ["ID", "Requirement", "Status"],
              [[r["id"], r["text"], r["status"]] for r in report["functional"]], "None.")

    document.add_heading("4. Non-functional requirements", level=1)
    add_table(document, ["ID", "Requirement", "Category", "Status"],
              [[r["id"], r["text"], r["category"], r["status"]] for r in report["non_functional"]], "None.")

    document.add_heading("5. Potential duplicates", level=1)
    add_note(document, DUPLICATES_NOTE)
    add_table(document, ["Requirement A", "Requirement B", "Score", "Reason for review", "Status"],
              [[d["a"], d["b"], d["score"], d["reason"], d["status"]] for d in report["duplicates"]],
              "No potential duplicates are listed.")

    document.add_heading("6. Ambiguity and quality warnings", level=1)
    add_note(document, WARNINGS_NOTE)
    add_table(document, ["Requirement", "Issue", "Details", "Found by", "Status"],
              [[w["requirement"], w["kind"], w["message"], w["origin"], w["status"]]
               for w in report["warnings"]], "No warnings are listed.")

    document.add_heading("7. Clarification questions", level=1)
    add_note(document, QUESTIONS_NOTE)
    add_table(document, ["Requirement", "Question"],
              [[q["requirement"], q["question"]] for q in report["questions"]], "No questions are listed.")

    document.add_heading("8. Approved user stories and acceptance criteria", level=1)
    add_note(document, APPROVED_NOTE)
    add_stories(document, report["approved_stories"], "No user stories have been approved yet.")

    document.add_heading("9. Unreviewed AI draft user stories", level=1)
    add_note(document, DRAFT_NOTE, warning=True)
    add_stories(document, report["draft_stories"], "No unreviewed drafts.")

    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()
