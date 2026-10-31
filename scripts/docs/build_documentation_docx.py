"""Build NISAAB_Documentation.docx from docs/nisaab/*.md.

Run with:
    python scripts/docs/build_documentation_docx.py

Needs two packages that the services do not, so install them just for this:
    uv pip install python-docx markdown-it-py

Same content and title page as the PDF; this is the editable copy. The
markdown under docs/nisaab/ stays the source for both, so a change there is made
once and both documents are rebuilt from it.

The contents page is a real Word field rather than a frozen list, so it renumbers
itself after an edit - Word offers to update it when the file is opened.
"""

import pathlib
import re
import sys

from docx import Document
from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from markdown_it import MarkdownIt

REPO = pathlib.Path(__file__).resolve().parents[2]
DOCS = REPO / "docs" / "documentation"
LOGO = REPO.parent / "brand" / "nisaab-mark-light.png"
OUT = REPO.parent / "docs" / "NISAAB_Documentation.docx"

GREEN = RGBColor(0x1F, 0x6B, 0x4A)
SOFT = RGBColor(0x2E, 0x8B, 0x6F)
INK = RGBColor(0x22, 0x25, 0x1F)
GREY = RGBColor(0x73, 0x78, 0x75)
TINT = "E7F1EB"
CODE_BG = "F4F7F5"

DETAILS = [
    ("Project", "NISAAB, the SLO-grounded AI tutor for Federal Board FSc students"),
    ("Version", "1.0"),
    ("Date", "25 October 2026"),
    ("Project team", "Muhammad Saad Cheema, Muhammad Hashir Naveed, Fatin Khan Jadoon"),
    ("Prepared by", "Muhammad Hashir Naveed, on behalf of the project team"),
    ("Supervisor", "Prof. Mr. Tashfeen Qamar"),
    ("Institution", "Islamabad Model College for Boys G-10/4, Islamabad"),
    ("Competition", "FDE STEM Competition, Group C, 29 October 2026, IMCB F-8/4"),
    ("Working model", "edu-web-yvi5hrqfda-el.a.run.app"),
]

NAV = re.compile(r"^\s*(\[←|\*\*?\[?←)|^\s*\[Contents\]")
LINK = re.compile(r"\[([^\]]+)\]\((?!https?:)[^)]+\)")
# A figure is too wide for a portrait column, so it is lifted out of the text
# and given a landscape page of its own rather than shrunk into the flow.
FIGURE = re.compile(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", re.M)


# --------------------------------------------------------------- docx plumbing

def shade(element, fill: str) -> None:
    """Give a paragraph or table cell a background colour."""
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), fill)
    element.append(shd)


def field(paragraph, instruction: str, placeholder: str) -> None:
    """Insert a Word field - a value Word works out, not one written in."""
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = placeholder
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for node in (begin, instr, separate, text, end):
        run._r.append(node)


def setup_styles(doc: Document) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = "Segoe UI"
    normal.font.size = Pt(10)
    normal.font.color.rgb = INK
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15
    # East-Asian font name has to be set separately or Word substitutes its own
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Segoe UI")

    for name, size, colour, before in (
        ("Heading 1", 20, GREEN, 18),
        ("Heading 2", 14, GREEN, 14),
        ("Heading 3", 11.5, SOFT, 11),
        ("Heading 4", 10.5, INK, 9),
    ):
        style = doc.styles[name]
        style.font.name = "Segoe UI"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = colour
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(4)
        style.paragraph_format.keep_with_next = True

    for section in doc.sections:
        # Word's default template is US Letter; the PDF is A4, and so is every
        # printer this will meet
        section.page_width = Inches(8.27)
        section.page_height = Inches(11.69)
        section.top_margin = Inches(0.9)
        section.bottom_margin = Inches(0.9)
        section.left_margin = Inches(0.95)
        section.right_margin = Inches(0.95)
        footer = section.footer.paragraphs[0]
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        footer.add_run("NISAAB Project Documentation  |  Page ")
        field(footer, "PAGE", "1")
        for run in footer.runs:
            run.font.size = Pt(8.5)
            run.font.color.rgb = GREY
            run.font.name = "Segoe UI"


# ------------------------------------------------------------------ title page

def title_page(doc: Document) -> None:
    gap = doc.add_paragraph()
    gap.paragraph_format.space_after = Pt(0)

    if LOGO.exists():
        picture = doc.add_paragraph()
        picture.alignment = WD_ALIGN_PARAGRAPH.CENTER
        picture.add_run().add_picture(str(LOGO), width=Inches(1.15))
        picture.paragraph_format.space_after = Pt(14)

    # Word shapes Arabic itself, so the plain string is right here - unlike the
    # PDF, which needs presentation forms because PyMuPDF does no shaping
    for text, size, bold, colour, after in (
        ("NISAAB", 34, True, GREEN, 2),
        ("نصاب", 20, False, SOFT, 10),
        ("PROJECT DOCUMENTATION", 15, True, INK, 3),
        ("User guide, technical reference and operations manual", 11.5, False, GREY, 26),
    ):
        paragraph = doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = paragraph.add_run(text)
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = colour
        run.font.name = "Segoe UI"
        paragraph.paragraph_format.space_after = Pt(after)

    table = doc.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for cell, label in zip(table.rows[0].cells, ("Detail", "Information")):
        shade(cell._tc.get_or_add_tcPr(), TINT)
        run = cell.paragraphs[0].add_run(label)
        run.font.bold = True
        run.font.size = Pt(9.5)
        run.font.color.rgb = GREEN
        run.font.name = "Segoe UI"

    for label, value in DETAILS:
        cells = table.add_row().cells
        left = cells[0].paragraphs[0].add_run(label)
        left.font.bold = True
        left.font.size = Pt(9.5)
        left.font.name = "Segoe UI"
        right = cells[1].paragraphs[0].add_run(value)
        right.font.size = Pt(9.5)
        right.font.name = "Segoe UI"

    for row in table.rows:
        row.cells[0].width = Inches(1.7)
        row.cells[1].width = Inches(4.6)

    note = doc.add_paragraph()
    note.paragraph_format.space_before = Pt(16)
    run = note.add_run(
        "NISAAB is a student project. It is aligned with the FBISE National "
        "Curriculum 2022-23 and is not an official FBISE product."
    )
    run.font.size = Pt(8.5)
    run.font.color.rgb = GREY
    run.font.name = "Segoe UI"

    doc.add_page_break()


def contents_page(doc: Document) -> None:
    heading = doc.add_paragraph()
    run = heading.add_run("Contents")
    run.font.size = Pt(20)
    run.font.bold = True
    run.font.color.rgb = GREEN
    run.font.name = "Segoe UI"
    heading.paragraph_format.space_after = Pt(10)

    hint = doc.add_paragraph()
    hint_run = hint.add_run(
        "If the list below is empty, right-click it and choose Update Field."
    )
    hint_run.font.size = Pt(8.5)
    hint_run.font.italic = True
    hint_run.font.color.rgb = GREY
    hint_run.font.name = "Segoe UI"

    field(doc.add_paragraph(), 'TOC \\o "1-3" \\h \\z \\u', "Contents go here.")
    doc.add_page_break()


# -------------------------------------------------------------- markdown → docx

def add_inline(paragraph, token, bold=False, italic=False) -> None:
    """Walk one inline token, keeping bold, italic and code formatting."""
    for child in token.children or []:
        if child.type == "text":
            run = paragraph.add_run(child.content)
        elif child.type == "code_inline":
            run = paragraph.add_run(child.content)
            run.font.name = "Consolas"
            run.font.size = Pt(8.8)
            run.font.color.rgb = GREEN
        elif child.type == "strong_open":
            bold = True
            continue
        elif child.type == "strong_close":
            bold = False
            continue
        elif child.type in ("em_open",):
            italic = True
            continue
        elif child.type in ("em_close",):
            italic = False
            continue
        elif child.type == "softbreak":
            paragraph.add_run(" ")
            continue
        elif child.type in ("link_open", "link_close", "s_open", "s_close"):
            continue
        else:
            continue
        run.font.bold = bold or run.font.bold
        run.font.italic = italic or run.font.italic


def add_code(doc: Document, text: str) -> None:
    paragraph = doc.add_paragraph()
    shade(paragraph._p.get_or_add_pPr(), CODE_BG)
    fmt = paragraph.paragraph_format
    fmt.space_before = Pt(4)
    fmt.space_after = Pt(8)
    fmt.left_indent = Inches(0.12)
    fmt.line_spacing = 1.0
    lines = text.rstrip("\n").split("\n")
    for index, line in enumerate(lines):
        if index:
            paragraph.add_run().add_break()
        run = paragraph.add_run(line)
        run.font.name = "Consolas"
        run.font.size = Pt(7.8)


def add_table(doc: Document, rows: list[list]) -> None:
    if not rows:
        return
    table = doc.add_table(rows=0, cols=len(rows[0]))
    table.style = "Table Grid"
    for index, cells in enumerate(rows):
        row = table.add_row().cells
        for cell, token in zip(row, cells):
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(2)
            if token is not None:
                add_inline(paragraph, token)
            for run in paragraph.runs:
                run.font.size = Pt(8.8)
                if index == 0:
                    run.font.bold = True
                    run.font.color.rgb = GREEN
            if index == 0:
                shade(cell._tc.get_or_add_tcPr(), TINT)


def render(doc: Document, tokens: list) -> None:
    i = 0
    list_depth = 0
    ordered = False
    while i < len(tokens):
        token = tokens[i]

        if token.type == "heading_open":
            level = int(token.tag[1])
            paragraph = doc.add_paragraph(style=f"Heading {min(level, 4)}")
            add_inline(paragraph, tokens[i + 1])
            i += 3
            continue

        if token.type == "paragraph_open":
            if list_depth:
                paragraph = doc.add_paragraph(
                    style="List Number" if ordered else "List Bullet"
                )
            else:
                paragraph = doc.add_paragraph()
            add_inline(paragraph, tokens[i + 1])
            i += 3
            continue

        if token.type == "fence":
            add_code(doc, token.content)
            i += 1
            continue

        if token.type in ("bullet_list_open", "ordered_list_open"):
            list_depth += 1
            ordered = token.type == "ordered_list_open"
            i += 1
            continue

        if token.type in ("bullet_list_close", "ordered_list_close"):
            list_depth = max(0, list_depth - 1)
            i += 1
            continue

        if token.type == "table_open":
            rows: list[list] = []
            current: list = []
            depth = 0
            j = i
            while j < len(tokens):
                inner = tokens[j]
                if inner.type == "table_close":
                    break
                if inner.type in ("tr_open",):
                    current = []
                elif inner.type in ("th_open", "td_open"):
                    nxt = tokens[j + 1]
                    current.append(nxt if nxt.type == "inline" else None)
                elif inner.type == "tr_close":
                    rows.append(current)
                j += 1
                depth += 1
            add_table(doc, rows)
            i = j + 1
            continue

        if token.type == "blockquote_open":
            j = i + 1
            while j < len(tokens) and tokens[j].type != "blockquote_close":
                if tokens[j].type == "inline":
                    paragraph = doc.add_paragraph()
                    shade(paragraph._p.get_or_add_pPr(), CODE_BG)
                    paragraph.paragraph_format.left_indent = Inches(0.15)
                    add_inline(paragraph, tokens[j])
                j += 1
            i = j + 1
            continue

        i += 1


def landscape_figure(doc: Document, image: pathlib.Path, caption: str) -> None:
    """Put one wide figure on a landscape page, then turn the page back."""
    wide = doc.add_section(WD_SECTION.NEW_PAGE)
    wide.orientation = WD_ORIENT.LANDSCAPE
    wide.page_width, wide.page_height = wide.page_height, wide.page_width
    wide.left_margin = wide.right_margin = Inches(0.6)
    wide.top_margin = wide.bottom_margin = Inches(0.6)

    picture = doc.add_paragraph()
    picture.alignment = WD_ALIGN_PARAGRAPH.CENTER
    picture.add_run().add_picture(str(image), width=Inches(9.6))

    note = doc.add_paragraph()
    run = note.add_run(caption)
    run.font.size = Pt(8.5)
    run.font.color.rgb = GREY
    run.font.name = "Segoe UI"

    back = doc.add_section(WD_SECTION.NEW_PAGE)
    back.orientation = WD_ORIENT.PORTRAIT
    back.page_width, back.page_height = back.page_height, back.page_width
    back.left_margin = back.right_margin = Inches(0.95)
    back.top_margin = back.bottom_margin = Inches(0.9)


def load(path: pathlib.Path) -> tuple[str, list[pathlib.Path]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    text = "\n".join(ln for ln in lines if not NAV.match(ln))
    figures = [(path.parent / m.group(2), m.group(1)) for m in FIGURE.finditer(text)]
    text = FIGURE.sub("", text)
    text = LINK.sub(r"\1", text)
    text = text.replace("(نصاب, *syllabus*)", "(*nisaab* — syllabus)")
    text = re.sub(r"اردو", "Urdu", text)
    text = re.sub(r"^\*Last verified.*\*$", "", text, flags=re.M)
    return text.strip(), figures


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    files = sorted(p for p in DOCS.glob("*.md") if p.name != "README.md")
    index = DOCS / "README.md"
    chapters = ([index] if index.exists() else []) + files
    if not chapters:
        raise SystemExit(f"no markdown found in {DOCS}")

    doc = Document()
    setup_styles(doc)
    title_page(doc)
    contents_page(doc)

    md = MarkdownIt("commonmark").enable("table").enable("strikethrough")
    for index, path in enumerate(chapters):
        if index:
            doc.add_page_break()
        text, figures = load(path)
        for figure, alt in figures:
            if not figure.exists():
                raise SystemExit(
                    f"missing figure: {figure} — run the figure scripts first."
                )
            landscape_figure(doc, figure, alt)
        render(doc, md.parse(text))

    doc.core_properties.title = "NISAAB — Project Documentation"
    doc.core_properties.author = (
        "Muhammad Saad Cheema, Muhammad Hashir Naveed, Fatin Khan Jadoon"
    )
    doc.core_properties.subject = (
        "User guide, technical reference and operations manual — "
        "FDE STEM Competition, Group C, 29 October 2026"
    )

    doc.save(OUT)
    print(f"wrote {OUT}  ({OUT.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
