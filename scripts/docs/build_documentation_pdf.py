"""Build NISAAB_Documentation.pdf from docs/nisaab/*.md.

Run with:
    python scripts/docs/build_documentation_pdf.py

Needs two packages that the services do not, so install them just for this:
    uv pip install pymupdf markdown-it-py

The PDF lands in the docs/ folder beside the repository, with the report.
Re-run it after editing anything under docs/nisaab/ - the markdown is the
source, this file is only the typesetting.

Body text is Segoe UI, which carries the Greek, the maths and the Arabic; code
blocks are Consolas, which carries the box-drawing characters the architecture
diagrams are made of. Neither font has every one on its own, which is why they
are split that way rather than by taste.
"""

import io
import pathlib
import re
import shutil
import sys
import tempfile

import pymupdf
from markdown_it import MarkdownIt

REPO = pathlib.Path(__file__).resolve().parents[2]   # edu-agent/
ROOT = REPO.parent                                   # the folder holding it
DOCS = REPO / "docs" / "documentation"
LOGO = ROOT / "brand" / "nisaab-mark-light.png"
OUT = ROOT / "docs" / "NISAAB_Documentation.pdf"
WORK = pathlib.Path(
    sys.argv[1] if len(sys.argv) > 1 else tempfile.gettempdir()
) / "nisaab-pdf-fonts"

GREEN = (0x1F / 255, 0x6B / 255, 0x4A / 255)
SOFT = (0x2E / 255, 0x8B / 255, 0x6F / 255)
TINT = (0xE7 / 255, 0xF1 / 255, 0xEB / 255)
INK = (0.13, 0.15, 0.14)
GREY = (0.45, 0.47, 0.46)

W, H = 595.276, 841.89
MEDIA = pymupdf.Rect(0, 0, W, H)
LEFT, RIGHT, TOP, BOTTOM = 58, 58, 74, 62
CONTENT = pymupdf.Rect(LEFT, TOP, W - RIGHT, H - BOTTOM)

FONTS = {
    "segoeui.ttf": "C:/Windows/Fonts/segoeui.ttf",
    "segoeuib.ttf": "C:/Windows/Fonts/segoeuib.ttf",
    "segoeuii.ttf": "C:/Windows/Fonts/segoeuii.ttf",
    "consola.ttf": "C:/Windows/Fonts/consola.ttf",
    "consolab.ttf": "C:/Windows/Fonts/consolab.ttf",
}

CSS = """
@font-face {font-family: body; src: url(segoeui.ttf);}
@font-face {font-family: body; font-weight: bold; src: url(segoeuib.ttf);}
@font-face {font-family: body; font-style: italic; src: url(segoeuii.ttf);}
@font-face {font-family: mono; src: url(consola.ttf);}
@font-face {font-family: mono; font-weight: bold; src: url(consolab.ttf);}

body { font-family: body; font-size: 9.6px; color: #22251F; line-height: 1.5; }
p { margin-top: 0; margin-bottom: 7px; }

h1 { font-family: body; font-size: 20px; font-weight: bold; color: #1F6B4A;
     margin-top: 0; margin-bottom: 3px; }
h2 { font-family: body; font-size: 13.5px; font-weight: bold; color: #1F6B4A;
     margin-top: 15px; margin-bottom: 5px; }
h3 { font-family: body; font-size: 11px; font-weight: bold; color: #2E8B6F;
     margin-top: 12px; margin-bottom: 3px; }
h4 { font-family: body; font-size: 9.8px; font-weight: bold; color: #22251F;
     margin-top: 9px; margin-bottom: 2px; }

ul, ol { margin-top: 0; margin-bottom: 7px; }
li { margin-bottom: 2.5px; }

code { font-family: mono; font-size: 8.6px; color: #1F6B4A; }
pre { font-family: mono; font-size: 7.9px; color: #22251F;
      background-color: #F4F7F5; padding: 7px; margin-top: 2px; margin-bottom: 9px;
      line-height: 1.32; }
pre code { font-size: 7.9px; color: #22251F; }

table { width: 100%; margin-top: 3px; margin-bottom: 10px; font-size: 8.8px; }
th { font-family: body; font-weight: bold; background-color: #E7F1EB; color: #1F6B4A;
     text-align: left; padding: 4px; border-bottom: 1px solid #1F6B4A; }
td { padding: 4px; border-bottom: 0.5px solid #DCE4DF; vertical-align: top; }

blockquote { background-color: #F4F7F5; padding: 7px; margin-top: 3px;
             margin-bottom: 9px; color: #22251F; }
blockquote p { margin-bottom: 0; }
hr { margin-top: 9px; margin-bottom: 9px; }
a { color: #1F6B4A; }
strong { font-weight: bold; }
"""

# Lines that only exist so the files can be browsed on GitHub
NAV = re.compile(r"^\s*(\[←|\*\*?\[?←)|^\s*\[Contents\]|^\s*\[←.*Contents.*\]")
LINK = re.compile(r"\[([^\]]+)\]\((?!https?:)[^)]+\)")
LASTVERIFIED = re.compile(r"^\*Last verified.*\*$", re.M)
# A figure is too wide for a portrait column, so it is lifted out of the text
# and given a landscape page of its own rather than shrunk into the flow.
FIGURE = re.compile(r"^!\[[^\]]*\]\(([^)]+)\)\s*$", re.M)


def load(path: pathlib.Path) -> tuple[str, str, list[pathlib.Path]]:
    """Return (chapter title, markdown, figures) with navigation stripped."""
    lines = path.read_text(encoding="utf-8").splitlines()
    kept = [ln for ln in lines if not NAV.match(ln)]
    text = "\n".join(kept)

    figures = [
        (path.parent / match.group(1)).with_suffix(".pdf")
        for match in FIGURE.finditer(text)
    ]
    text = FIGURE.sub("", text)

    # Internal cross-references become plain words: there is nowhere to click
    text = LINK.sub(r"\1", text)
    # Arabic needs right-to-left shaping, which this renderer does not do
    text = text.replace("(نصاب, *syllabus*)", "(*nisaab* — syllabus)")
    text = text.replace("· اردو", "· Urdu")
    text = re.sub(r"اردو", "Urdu", text)
    text = LASTVERIFIED.sub("", text)

    title = "NISAAB"
    for ln in kept:
        if ln.startswith("# "):
            title = ln[2:].strip()
            break
    return title, text.strip(), figures


def prepare_fonts() -> pymupdf.Archive:
    WORK.mkdir(parents=True, exist_ok=True)
    for name, source in FONTS.items():
        target = WORK / name
        if not target.exists():
            shutil.copyfile(source, target)
    return pymupdf.Archive(WORK)


def body_pdf(chapters: list[tuple[str, str]], arch) -> tuple[bytes, list[str]]:
    """Render every chapter; return the PDF and which chapter each page holds."""
    md = MarkdownIt("commonmark").enable("table").enable("strikethrough")
    buf = io.BytesIO()
    writer = pymupdf.DocumentWriter(buf)
    owner: list[str] = []

    for title, text, _figures in chapters:
        html = f"<body>{md.render(text)}</body>"
        story = pymupdf.Story(html=html, user_css=CSS, archive=arch, em=12)
        more = True
        while more:
            device = writer.begin_page(MEDIA)
            more, _ = story.place(CONTENT)
            story.draw(device)
            writer.end_page()
            owner.append(title)

    writer.close()
    return buf.getvalue(), owner


# The document-control table on the title page. Each value is a list of lines,
# so a long one wraps where it reads best rather than wherever it happens to fit.
# "nisaab" in Arabic. PyMuPDF does no right-to-left shaping, so the letters
# are given as presentation forms in visual order - checked by eye against
# the plain string, which renders disconnected and backwards.
NISAAB_ARABIC = "ﺏﺎﺼﻧ"

DETAILS = [
    ("Project", ["NISAAB, the SLO-grounded AI tutor for",
                 "Federal Board FSc students"]),
    ("Version", ["1.0"]),
    ("Date", ["25 October 2026"]),
    ("Project team", ["Muhammad Saad Cheema, Muhammad Hashir Naveed,",
                      "Fatin Khan Jadoon"]),
    ("Prepared by", ["Muhammad Hashir Naveed, on behalf of the project team"]),
    ("Supervisor", ["Prof. Mr. Tashfeen Qamar"]),
    ("Institution", ["Islamabad Model College for Boys G-10/4, Islamabad"]),
    ("Competition", ["FDE STEM Competition, Group C,",
                     "29 October 2026, IMCB F-8/4"]),
    ("Working model", ["nisaab.muhammadsaadcheema.com"]),
]


def draw_cover(page) -> None:
    band = pymupdf.Rect(0, 0, W, 398)
    page.draw_rect(band, color=None, fill=GREEN)
    page.draw_rect(pymupdf.Rect(0, 398, W, 405), color=None, fill=SOFT)

    # The mark is green on green, so it needs a white badge to read at all
    size, pad = 76, 11
    badge = pymupdf.Rect((W - size) / 2 - pad, 74 - pad,
                         (W + size) / 2 + pad, 74 + size + pad)
    page.draw_rect(badge, color=None, fill=(1, 1, 1), radius=0.26)
    page.insert_image(
        pymupdf.Rect((W - size) / 2, 74, (W + size) / 2, 74 + size),
        filename=str(LOGO), keep_proportion=True,
    )

    # A 40pt line needs more than 40pt of box: Segoe UI's line height is ~1.4em
    dropped = page.insert_textbox(
        pymupdf.Rect(0, 196, W, 268), "NISAAB",
        fontname="segb", fontfile=FONTS["segoeuib.ttf"],
        fontsize=40, color=(1, 1, 1), align=pymupdf.TEXT_ALIGN_CENTER,
    )
    if dropped < 0:
        raise SystemExit(f"cover title did not fit (overflow {dropped})")

    page.insert_textbox(
        pymupdf.Rect(0, 242, W, 278), NISAAB_ARABIC,
        fontname="seg", fontfile=FONTS["segoeui.ttf"],
        fontsize=21, color=(0.84, 0.95, 0.89), align=pymupdf.TEXT_ALIGN_CENTER,
    )

    page.insert_textbox(
        pymupdf.Rect(0, 286, W, 314), "PROJECT DOCUMENTATION",
        fontname="segb", fontfile=FONTS["segoeuib.ttf"],
        fontsize=15, color=(1, 1, 1), align=pymupdf.TEXT_ALIGN_CENTER,
    )
    page.insert_textbox(
        pymupdf.Rect(0, 318, W, 346),
        "User guide, technical reference and operations manual",
        fontname="seg", fontfile=FONTS["segoeui.ttf"],
        fontsize=12, color=(0.84, 0.93, 0.89), align=pymupdf.TEXT_ALIGN_CENTER,
    )
    page.insert_textbox(
        pymupdf.Rect(70, 352, W - 70, 392),
        "An AI tutor grounded in the official FBISE curriculum — every question, "
        "paper and mark tied to a numbered learning outcome.",
        fontname="segi", fontfile=FONTS["segoeuii.ttf"],
        fontsize=10, color=(0.76, 0.88, 0.83),
        align=pymupdf.TEXT_ALIGN_CENTER, lineheight=1.45,
    )

    # The document-control table: Detail | Information
    label_x, value_x = LEFT, LEFT + 126
    top = 452
    head = pymupdf.Rect(LEFT, top, W - RIGHT, top + 25)
    page.draw_rect(head, color=None, fill=TINT)
    page.insert_text((label_x + 8, top + 17), "Detail", fontname="segb",
                     fontfile=FONTS["segoeuib.ttf"], fontsize=9.6, color=GREEN)
    page.insert_text((value_x + 8, top + 17), "Information", fontname="segb",
                     fontfile=FONTS["segoeuib.ttf"], fontsize=9.6, color=GREEN)

    y = top + 25
    for label, lines in DETAILS:
        height = 20 + 13 * (len(lines) - 1)
        page.insert_text((label_x + 8, y + 14), label, fontname="segb",
                         fontfile=FONTS["segoeuib.ttf"], fontsize=9.2, color=INK)
        for i, line in enumerate(lines):
            page.insert_text((value_x + 8, y + 14 + i * 13), line, fontname="seg",
                             fontfile=FONTS["segoeui.ttf"], fontsize=9.6, color=INK)
        y += height
        page.draw_line(pymupdf.Point(LEFT, y), pymupdf.Point(W - RIGHT, y),
                       color=(0.87, 0.90, 0.88), width=0.5)

    page.draw_rect(pymupdf.Rect(LEFT, top, W - RIGHT, y),
                   color=(0.80, 0.86, 0.82), width=0.6, fill=None)
    page.draw_line(pymupdf.Point(value_x, top), pymupdf.Point(value_x, y),
                   color=(0.87, 0.90, 0.88), width=0.5)

    page.insert_text((LEFT, y + 26),
                     "NISAAB is a student project. It is aligned with the FBISE National "
                     "Curriculum 2022-23 and is not an official FBISE product.",
                     fontname="seg", fontfile=FONTS["segoeui.ttf"],
                     fontsize=8.4, color=GREY)


def draw_contents(page, entries: list[tuple[str, int]]) -> None:
    page.insert_text((LEFT, 96), "Contents", fontname="segb",
                     fontfile=FONTS["segoeuib.ttf"], fontsize=24, color=GREEN)
    page.draw_line(pymupdf.Point(LEFT, 112), pymupdf.Point(LEFT + 54, 112),
                   color=SOFT, width=2.4)

    y = 152
    for title, page_number in entries:
        clean = title.replace("·", "").strip()
        number, _, rest = clean.partition(" ")
        if number.isdigit():
            page.insert_text((LEFT, y), number, fontname="segb",
                             fontfile=FONTS["segoeuib.ttf"], fontsize=10.5, color=SOFT)
            label = rest.strip()
        else:
            label = clean
        page.insert_text((LEFT + 26, y), label, fontname="seg",
                         fontfile=FONTS["segoeui.ttf"], fontsize=11.5, color=INK)
        page.insert_text((W - RIGHT - 16, y), str(page_number), fontname="seg",
                         fontfile=FONTS["segoeui.ttf"], fontsize=10.5, color=GREY)
        page.draw_line(pymupdf.Point(LEFT + 26, y + 4.5),
                       pymupdf.Point(W - RIGHT - 22, y + 4.5),
                       color=(0.88, 0.90, 0.89), width=0.5, dashes="[1 3] 0")
        y += 29


def stamp(page, chapter: str, number: int) -> None:
    page.draw_line(pymupdf.Point(LEFT, 52), pymupdf.Point(W - RIGHT, 52),
                   color=TINT, width=0.9)
    page.insert_text((LEFT, 46), "NISAAB — Project Documentation",
                     fontname="seg", fontfile=FONTS["segoeui.ttf"],
                     fontsize=7.6, color=GREY)
    width = pymupdf.Font(fontfile=FONTS["segoeui.ttf"]).text_length(chapter, 7.6)
    page.insert_text((W - RIGHT - width, 46), chapter, fontname="seg",
                     fontfile=FONTS["segoeui.ttf"], fontsize=7.6, color=SOFT)
    page.insert_textbox(
        pymupdf.Rect(0, H - 44, W, H - 26),
        f"NISAAB Project Documentation  |  Page {number}",
        fontname="seg", fontfile=FONTS["segoeui.ttf"],
        fontsize=8.2, color=GREY, align=pymupdf.TEXT_ALIGN_CENTER)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in DOCS.glob("*.md") if p.name != "README.md")
    index = DOCS / "README.md"
    chapters = ([load(index)] if index.exists() else []) + [load(p) for p in files]
    if not chapters:
        raise SystemExit(f"no markdown found in {DOCS}")

    arch = prepare_fonts()
    raw, owner = body_pdf(chapters, arch)

    body = pymupdf.open("pdf", raw)
    out = pymupdf.open()
    out.new_page(width=W, height=H)   # cover
    out.new_page(width=W, height=H)   # contents
    out.insert_pdf(body)

    # Each figure gets a landscape page in front of the chapter it belongs to,
    # inserted back to front so the earlier indexes stay valid
    figure_pages: set[int] = set()
    for title, _text, figures in reversed(chapters):
        for figure in reversed(figures):
            if not figure.exists():
                raise SystemExit(f"missing figure: {figure}\nRun build_architecture_diagram.py first.")
            at = 2 + owner.index(title)
            page = out.new_page(pno=at, width=H, height=W)   # A4 landscape
            with pymupdf.open(figure) as source:
                page.show_pdf_page(
                    pymupdf.Rect(26, 24, H - 26, W - 46), source, 0, keep_proportion=True
                )
            caption = f"Figure — {title.split('·')[-1].strip()}"
            page.insert_text((26, W - 26), caption, fontname="seg",
                             fontfile=FONTS["segoeui.ttf"], fontsize=8.4, color=GREY)
            owner.insert(owner.index(title), title)
            figure_pages.add(at)

    # Drawn only now: insert_pdf invalidates any Page object taken before it
    draw_cover(out[0])

    # Body page i is the printed page i + 3 (cover, contents, then the body)
    starts: list[tuple[str, int]] = []
    for i, title in enumerate(owner):
        if not starts or starts[-1][0] != title:
            starts.append((title, i + 3))
    draw_contents(out[1], starts)

    for i, title in enumerate(owner):
        if i + 2 not in figure_pages:        # the landscape pages carry no header
            stamp(out[i + 2], title, i + 3)

    out.set_metadata({
        "title": "NISAAB — Project Documentation",
        "author": "Muhammad Saad Cheema, Muhammad Hashir Naveed, Fatin Khan Jadoon",
        "subject": "User guide, technical reference and operations manual — FDE STEM Competition, Group C, 29 October 2026",
        "keywords": "NISAAB, FBISE, FSc, AI tutor, SLO, Google Cloud",
    })

    toc = [[1, title.replace("·", "").strip(), page] for title, page in starts]
    out.set_toc(toc)
    out.subset_fonts()
    out.save(OUT, deflate=True, garbage=4)
    out.close()
    body.close()

    print(f"wrote {OUT}  ({OUT.stat().st_size / 1024:.0f} KB, {len(owner) + 2} pages)")
    for title, page in starts:
        print(f"  p{page:>3}  {title}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
