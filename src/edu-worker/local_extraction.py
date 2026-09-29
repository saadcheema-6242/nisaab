"""Local document text extraction, used when Azure Content Understanding is not configured.

Text-based PDFs, DOCX, TXT, MD and HTML are read locally. Scanned PDFs and images
are transcribed by Gemini when ``LLM_PROVIDER`` is ``gemini`` or ``vertex``.
"""

import html
import io
import logging
import re

from docx import Document as DocxDocument
from edu_ai.llm import generate_from_file, supports_file_input
from langchain_core.language_models.chat_models import BaseChatModel
from pypdf import PdfReader

logger = logging.getLogger(__name__)

PAGE_BREAK = "\n\n<!-- PageBreak -->\n\n"
GEMINI_INLINE_LIMIT_BYTES = 18 * 1024 * 1024
MIN_CHARS_PER_TEXT_PAGE = 40
SUMMARY_INPUT_CHARS = 15000
TRANSCRIBE_PROMPT = (
    "Transcribe this document into clean Markdown. Keep headings (#, ##, ###), "
    "lists and tables. Write equations in LaTeX between $ signs. Describe each "
    "diagram in one short italic line. Put the line <!-- PageBreak --> between "
    "pages. Output only the transcription."
)
SUMMARY_PROMPT = (
    "Summarize the following study material in 3-4 sentences for a student. "
    "Mention the main topics it covers.\n\n{content}"
)

IMAGE_MIME_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "jpe": "image/jpeg",
    "webp": "image/webp",
    "heic": "image/heic",
    "heif": "image/heif",
}


class UnsupportedDocumentError(ValueError):
    """Raised when a document cannot be extracted without Content Understanding."""


def extract_document(
    file_content: bytes, file_type: str, llm: BaseChatModel | None
) -> dict:
    """Extract markdown content and a summary from a document.

    Args:
        file_content: Raw file bytes
        file_type: File extension (pdf, docx, txt, ...)
        llm: Chat model used for the summary (optional)

    Returns:
        Dictionary with ``content`` (markdown) and ``summary``
    """
    file_type = (file_type or "").lower()

    if file_type == "pdf":
        content = _extract_pdf(file_content)
    elif file_type == "docx":
        content = _extract_docx(file_content)
    elif file_type in ("txt", "md"):
        content = file_content.decode("utf-8", errors="replace")
    elif file_type == "html":
        content = _extract_html(file_content.decode("utf-8", errors="replace"))
    elif file_type in IMAGE_MIME_TYPES:
        content = _transcribe_with_gemini(file_content, IMAGE_MIME_TYPES[file_type])
    else:
        raise UnsupportedDocumentError(
            f"'.{file_type}' files need Azure Content Understanding. "
            "Supported without it: pdf, docx, txt, md, html and images (with Gemini)."
        )

    content = content.strip()
    if not content:
        raise UnsupportedDocumentError("No text could be extracted from the document.")

    return {"content": content, "summary": _summarize(content, llm)}


def _extract_pdf(file_content: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_content))
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    text_pages = sum(1 for p in pages if len(p) >= MIN_CHARS_PER_TEXT_PAGE)

    # Mostly scanned: transcribe the whole file instead of using the text layer
    if pages and text_pages < len(pages) / 2:
        return _transcribe_with_gemini(file_content, "application/pdf")

    return PAGE_BREAK.join(p for p in pages if p)


def _extract_docx(file_content: bytes) -> str:
    doc = DocxDocument(io.BytesIO(file_content))
    lines: list[str] = []

    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        style = (paragraph.style.name or "").lower() if paragraph.style else ""
        match = re.match(r"heading (\d)", style)
        if match:
            lines.append("#" * min(int(match.group(1)), 3) + " " + text)
        elif style == "title":
            lines.append("# " + text)
        else:
            lines.append(text)

    for table in doc.tables:
        rows = [
            "| " + " | ".join(cell.text.strip() for cell in row.cells) + " |"
            for row in table.rows
        ]
        if rows:
            header_cells = len(table.rows[0].cells)
            rows.insert(1, "|" + " --- |" * header_cells)
            lines.append("\n".join(rows))

    return "\n\n".join(lines)


def _extract_html(markup: str) -> str:
    markup = re.sub(r"(?is)<(script|style).*?</\1>", "", markup)
    text = re.sub(r"(?s)<[^>]+>", "\n", markup)
    text = html.unescape(text)
    return re.sub(r"\n\s*\n+", "\n\n", text)


def _transcribe_with_gemini(file_content: bytes, mime_type: str) -> str:
    if not supports_file_input():
        raise UnsupportedDocumentError(
            "This looks like a scanned document or image. Transcribing it needs "
            "LLM_PROVIDER=gemini or vertex, or Azure Content Understanding."
        )
    if len(file_content) > GEMINI_INLINE_LIMIT_BYTES:
        raise UnsupportedDocumentError(
            "Scanned document is too large to transcribe (limit about 18 MB)."
        )
    return generate_from_file(file_content, mime_type, TRANSCRIBE_PROMPT)


def _summarize(content: str, llm: BaseChatModel | None) -> str:
    fallback = content[:300].strip()
    if llm is None:
        return fallback
    try:
        response = llm.invoke(
            SUMMARY_PROMPT.format(content=content[:SUMMARY_INPUT_CHARS])
        )
        text = response.content if isinstance(response.content, str) else ""
        return text.strip() or fallback
    except Exception as e:
        logger.warning(f"Summary generation failed, using document start instead: {e}")
        return fallback
