"""Reads text from TXT, PDF and DOCX files."""
import io
import re


class UnsupportedDocument(Exception):
    """The file cannot be read. The message explains why, for the user."""


def clean_text(text: str) -> str:
    """Normalise line endings and remove control characters that break documents."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\f", "\n\n")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text.strip()


def read_txt(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return content.decode("cp1252", errors="replace")


def read_pdf(content: bytes) -> str:
    import fitz  # PyMuPDF
    try:
        with fitz.open(stream=content, filetype="pdf") as pdf:
            return "\n\n".join(page.get_text() for page in pdf)
    except Exception as error:
        raise UnsupportedDocument("This PDF could not be read. It may be damaged or password protected.") from error


def read_docx(content: bytes) -> str:
    from docx import Document
    try:
        document = Document(io.BytesIO(content))
    except Exception as error:
        raise UnsupportedDocument("This DOCX file could not be read. It may be damaged.") from error
    lines = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            lines.extend(cell.text for cell in row.cells)
    return "\n\n".join(line for line in lines if line.strip())


READERS = {"txt": read_txt, "pdf": read_pdf, "docx": read_docx}


def read_document(filename: str, content: bytes) -> str:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in READERS:
        raise UnsupportedDocument("Please upload a TXT, PDF or DOCX file.")
    text = clean_text(READERS[extension](content))
    if not text:
        message = "No text was found in this file."
        if extension == "pdf":
            message += " It may be a scanned image, and scanned PDFs are not supported."
        raise UnsupportedDocument(message)
    return text
