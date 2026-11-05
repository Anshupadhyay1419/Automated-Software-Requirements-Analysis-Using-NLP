"""File reading and report export tests, using real PDF and DOCX files."""
import io

import fitz
import pytest
from docx import Document as WordDocument

from app.documents.docx_export import render_docx
from app.documents.pdf_export import render_pdf
from app.documents.readers import UnsupportedDocument, clean_text, read_document


def make_pdf(text):
    pdf = fitz.open()
    if text:
        pdf.new_page().insert_text((72, 72), text)
    else:
        pdf.new_page()
    return pdf.tobytes()


def make_docx(text):
    document = WordDocument()
    document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_read_txt_with_bom_and_windows_lines():
    assert read_document("a.txt", "﻿Users log in.\r\nAdmins export.".encode()) == "Users log in.\nAdmins export."


def test_read_txt_in_older_encoding():
    assert "café" in read_document("a.txt", "The café app.".encode("cp1252"))


def test_read_pdf():
    assert "Users can log in" in read_document("a.PDF", make_pdf("Users can log in."))


def test_read_docx():
    assert read_document("a.docx", make_docx("Users can log in.")) == "Users can log in."


@pytest.mark.parametrize("name, content, message", [
    ("a.doc", b"old", "TXT, PDF or DOCX"),
    ("a.pdf", b"not a pdf", "could not be read"),
    ("a.docx", b"not a docx", "could not be read"),
    ("a.txt", b"   ", "No text"),
])
def test_bad_files_give_a_clear_error(name, content, message):
    with pytest.raises(UnsupportedDocument, match=message):
        read_document(name, content)


def test_scanned_pdf_gives_a_clear_error():
    with pytest.raises(UnsupportedDocument, match="scanned"):
        read_document("a.pdf", make_pdf(""))


def test_control_characters_are_removed():
    assert clean_text("a\x00b\x07c") == "abc"


REPORT = {
    "title": "Shop <App> & Co", "description": "Test", "generated": "1 January 2026, 10:00",
    "stats": {"Active requirements": 1},
    "documents": [{"name": "brief.txt", "words": 3, "excerpt": "Users log in."}],
    "requirements": [{"id": "REQ-1", "text": "Users can log in when x < 5 & y > 2.", "req_type": "functional",
                      "type": "Functional", "category": "-", "status": "Approved", "source": "Users log in."}],
    "functional": [{"id": "REQ-1", "text": "Users can log in when x < 5 & y > 2.", "status": "Approved"}],
    "non_functional": [],
    "duplicates": [{"a": "REQ-1: A", "b": "REQ-2: B", "score": "0.91", "reason": "Close", "status": "Unreviewed AI suggestion"}],
    "warnings": [{"requirement": "REQ-1: A", "kind": "Vague expression", "message": "Vague.", "origin": "Rule", "status": "Unreviewed AI suggestion"}],
    "questions": [{"requirement": "REQ-1", "question": "What target?"}],
    "approved_stories": [{"requirement": "REQ-1", "story": "As a user, I want to log in, so that I can work.", "criteria": ["A user can log in."], "status": "accepted"}],
    "draft_stories": [{"requirement": "REQ-2", "story": "As a user, I want to log out, so that I am safe.", "criteria": ["A user can log out."], "status": "pending"}],
}


def pdf_text(content):
    with fitz.open(stream=content, filetype="pdf") as pdf:
        return " ".join(" ".join(page.get_text().split()) for page in pdf)


def docx_text(content):
    document = WordDocument(io.BytesIO(content))
    parts = [paragraph.text for paragraph in document.paragraphs]
    parts += [cell.text for table in document.tables for row in table.rows for cell in row.cells]
    return " ".join(" ".join(parts).split())


@pytest.mark.parametrize("render, read", [(render_pdf, pdf_text), (render_docx, docx_text)])
def test_report_contains_every_section_and_special_characters(render, read):
    text = read(render(REPORT))
    for expected in ["Shop <App> & Co", "Original requirements summary", "Structured requirements",
                     "Functional requirements", "Non-functional requirements", "Potential duplicates",
                     "quality warnings", "Clarification questions", "What target?",
                     "Approved user stories", "I want to log in", "NOT APPROVED", "I want to log out",
                     "x < 5 & y > 2", "The client did not state them"]:
        assert expected in text


@pytest.mark.parametrize("render, read", [(render_pdf, pdf_text), (render_docx, docx_text)])
def test_empty_report_still_renders(render, read):
    empty = {**REPORT, "documents": [], "requirements": [], "functional": [], "duplicates": [],
             "warnings": [], "questions": [], "approved_stories": [], "draft_stories": []}
    assert "No user stories have been approved yet" in read(render(empty))
