"""Draws the report as a PDF with ReportLab. The content comes from report.py."""
import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .readers import clean_text
from .report import APPROVED_NOTE, DRAFT_NOTE, DUPLICATES_NOTE, LEGEND, QUESTIONS_NOTE, WARNINGS_NOTE

BASE = getSampleStyleSheet()
INK = colors.HexColor("#1f2937")
RULE = colors.HexColor("#d1d5db")
HEADER_FILL = colors.HexColor("#f3f4f6")
TITLE = ParagraphStyle("title", parent=BASE["Title"], fontSize=20, leading=25, alignment=0, textColor=INK)
HEADING = ParagraphStyle("heading", parent=BASE["Heading2"], fontSize=13, spaceBefore=14, spaceAfter=6, textColor=INK, keepWithNext=1)
BODY = ParagraphStyle("body", parent=BASE["BodyText"], fontSize=9.5, leading=13, textColor=INK)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=8.5, leading=11)
BOLD_SMALL = ParagraphStyle("bold_small", parent=SMALL, fontName="Helvetica-Bold")
NOTE = ParagraphStyle("note", parent=BODY, fontName="Helvetica-Oblique", textColor=colors.HexColor("#4b5563"))
WARNING = ParagraphStyle("warning", parent=BODY, fontName="Helvetica-Bold", textColor=colors.HexColor("#92400e"))

PAGE_WIDTH = A4[0] - 40 * mm


def text(value, style=BODY):
    """Paragraph reads < and & as markup, so user text must be escaped first."""
    return Paragraph(escape(clean_text(str(value))).replace("\n", "<br/>"), style)


def table(headers, rows, widths):
    data = [[text(header, BOLD_SMALL) for header in headers]]
    data += [[text(cell, SMALL) for cell in row] for row in rows]
    result = Table(data, colWidths=[PAGE_WIDTH * width for width in widths], repeatRows=1)
    result.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_FILL),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return result


def add_table_or_empty(story, headers, rows, widths, empty_message):
    story.append(table(headers, rows, widths) if rows else text(empty_message, NOTE))


def add_stories(story, stories):
    for item in stories:
        story.append(text(f'{item["requirement"]}: {item["story"]}'))
        if item["criteria"]:
            story.append(ListFlowable(
                [ListItem(text(criterion, SMALL)) for criterion in item["criteria"]],
                bulletType="bullet", leftIndent=14,
            ))
        story.append(Spacer(1, 6))


def page_number(canvas, document):
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawRightString(A4[0] - 20 * mm, 12 * mm, f"Page {document.page}")


def render_pdf(report: dict) -> bytes:
    story = [text(report["title"], TITLE), text("Software Requirements Report", HEADING),
             text(f'Generated {report["generated"]}', NOTE)]
    if report["description"]:
        story.append(text(report["description"]))
    story += [Spacer(1, 6), text(LEGEND, NOTE), Spacer(1, 8)]
    story.append(table(["Measure", "Count"], [[key, value] for key, value in report["stats"].items()], [0.7, 0.3]))

    story.append(text("1. Original requirements summary", HEADING))
    for document in report["documents"]:
        story.append(text(f'{document["name"]} ({document["words"]} words)', BOLD_SMALL))
        story += [text(document["excerpt"], SMALL), Spacer(1, 6)]
    if not report["documents"]:
        story.append(text("No source documents.", NOTE))

    story.append(text("2. Structured requirements", HEADING))
    add_table_or_empty(story, ["ID", "Requirement", "Type", "Category", "Status", "Source sentence"],
                       [[r["id"], r["text"], r["type"], r["category"], r["status"], r["source"]]
                        for r in report["requirements"]],
                       [0.09, 0.28, 0.15, 0.15, 0.13, 0.2], "No requirements yet.")

    story.append(text("3. Functional requirements", HEADING))
    add_table_or_empty(story, ["ID", "Requirement", "Status"],
                       [[r["id"], r["text"], r["status"]] for r in report["functional"]],
                       [0.12, 0.63, 0.25], "None.")

    story.append(text("4. Non-functional requirements", HEADING))
    add_table_or_empty(story, ["ID", "Requirement", "Category", "Status"],
                       [[r["id"], r["text"], r["category"], r["status"]] for r in report["non_functional"]],
                       [0.12, 0.5, 0.16, 0.22], "None.")

    story += [text("5. Potential duplicates", HEADING), text(DUPLICATES_NOTE, NOTE), Spacer(1, 4)]
    add_table_or_empty(story, ["Requirement A", "Requirement B", "Score", "Reason for review", "Status"],
                       [[d["a"], d["b"], d["score"], d["reason"], d["status"]] for d in report["duplicates"]],
                       [0.27, 0.27, 0.07, 0.24, 0.15], "No potential duplicates are listed.")

    story += [text("6. Ambiguity and quality warnings", HEADING), text(WARNINGS_NOTE, NOTE), Spacer(1, 4)]
    add_table_or_empty(story, ["Requirement", "Issue", "Details", "Found by", "Status"],
                       [[w["requirement"], w["kind"], w["message"], w["origin"], w["status"]]
                        for w in report["warnings"]],
                       [0.32, 0.15, 0.28, 0.1, 0.15], "No warnings are listed.")

    story += [text("7. Clarification questions", HEADING), text(QUESTIONS_NOTE, NOTE), Spacer(1, 4)]
    add_table_or_empty(story, ["Requirement", "Question"],
                       [[q["requirement"], q["question"]] for q in report["questions"]],
                       [0.15, 0.85], "No questions are listed.")

    story += [text("8. Approved user stories and acceptance criteria", HEADING), text(APPROVED_NOTE, NOTE), Spacer(1, 4)]
    add_stories(story, report["approved_stories"])
    if not report["approved_stories"]:
        story.append(text("No user stories have been approved yet.", NOTE))

    story += [text("9. Unreviewed AI draft user stories", HEADING), text(DRAFT_NOTE, WARNING), Spacer(1, 4)]
    add_stories(story, report["draft_stories"])
    if not report["draft_stories"]:
        story.append(text("No unreviewed drafts.", NOTE))

    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                                 topMargin=18 * mm, bottomMargin=18 * mm, title=report["title"],
                                 author="Automated Requirements Analysis")
    document.build(story, onFirstPage=page_number, onLaterPages=page_number)
    return buffer.getvalue()
