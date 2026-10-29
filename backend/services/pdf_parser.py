import io
import logging

import pypdf

logger = logging.getLogger(__name__)

_PDF_MAGIC = b"%PDF"


class PDFParseError(ValueError):
    pass


def extract_text(pdf_bytes: bytes) -> str:
    """
    Extract plain text from a PDF bytestring.
    Raises PDFParseError if the file is not a valid PDF or yields no text.
    """
    if not pdf_bytes[:4] == _PDF_MAGIC:
        raise PDFParseError(
            "File does not appear to be a valid PDF (missing PDF header). "
            "Please upload a PDF file."
        )

    try:
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    except Exception as exc:
        raise PDFParseError(f"Could not open PDF: {exc}") from exc

    if reader.is_encrypted:
        raise PDFParseError("PDF is password-protected and cannot be parsed")

    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(pages).strip()

    if not text:
        raise PDFParseError(
            "No extractable text found — the PDF may be image-only (scanned). "
            "Please upload a text-based PDF."
        )

    return text
