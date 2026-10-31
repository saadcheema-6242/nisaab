"""Draw the NISAAB system architecture diagram.

Run with:
    python scripts/docs/build_architecture_diagram.py

Needs a package the services do not, so install it just for this:
    uv pip install pymupdf

Writes two files into docs/nisaab/assets/ - a vector PDF, which the
documentation PDF places on its own landscape page, and a PNG for the DOCX and
for GitHub, which cannot render the PDF.

The numbers in the header are counted from the source, so re-run this whenever
they move: 93 endpoints, 28 agent tools, 7 job types, 1,020 SLOs.
"""

import pathlib
import sys

import pymupdf

REPO = pathlib.Path(__file__).resolve().parents[2]      # edu-agent/
OUTDIR = REPO / "docs" / "documentation" / "assets"
LOGO = REPO.parent / "brand" / "nisaab-mark-light.png"

W, H = 1120.0, 706.0

GREEN = (0x1F / 255, 0x6B / 255, 0x4A / 255)
SOFT = (0x2E / 255, 0x8B / 255, 0x6F / 255)
TINT = (0xE7 / 255, 0xF1 / 255, 0xEB / 255)
PALE = (0xF5 / 255, 0xF8 / 255, 0xF6 / 255)
INK = (0.13, 0.15, 0.14)
GREY = (0.45, 0.47, 0.46)
LINE = (0.78, 0.84, 0.80)
AMBER = (0xB4 / 255, 0x7E / 255, 0x16 / 255)

REG = "C:/Windows/Fonts/segoeui.ttf"
BOLD = "C:/Windows/Fonts/segoeuib.ttf"
MONO = "C:/Windows/Fonts/consola.ttf"

FREG = pymupdf.Font(fontfile=REG)
FBOLD = pymupdf.Font(fontfile=BOLD)

page: pymupdf.Page


def text(x, y, body, size=8.4, font=REG, colour=INK, centre_in=None):
    if centre_in is not None:
        metric = FBOLD if font == BOLD else FREG
        x = centre_in - metric.text_length(body, size) / 2
    page.insert_text((x, y), body, fontname="f" + str(abs(hash(font)) % 97),
                     fontfile=font, fontsize=size, color=colour)


def box(x0, y0, x1, y1, title, lines, accent=GREEN, fill=(1, 1, 1)):
    rect = pymupdf.Rect(x0, y0, x1, y1)
    page.draw_rect(rect, color=LINE, fill=fill, width=0.8, radius=0.04)
    page.draw_rect(pymupdf.Rect(x0, y0 + 3, x0 + 3.4, y1 - 3), color=None, fill=accent)
    text(x0 + 14, y0 + 19, title, size=10, font=BOLD, colour=accent)
    y = y0 + 34
    for line in lines:
        text(x0 + 14, y, line, size=8.2, colour=GREY)
        y += 12.4


def lane(y0, y1, label):
    page.draw_rect(pymupdf.Rect(28, y0, W - 28, y1), color=None, fill=PALE, radius=0.03)
    words = label.split(" ")
    y = (y0 + y1) / 2 - (len(words) - 1) * 6
    for word in words:
        text(44, y, word, size=7.6, font=BOLD, colour=SOFT)
        y += 12


def arrow(x0, y0, x1, y1, label=None, colour=SOFT, dashed=False,
          label_side="right", label_at=0.5):
    kwargs = {"color": colour, "width": 1.1}
    if dashed:
        kwargs["dashes"] = "[2 2] 0"
    page.draw_line(pymupdf.Point(x0, y0), pymupdf.Point(x1, y1), **kwargs)
    # arrowhead
    import math
    angle = math.atan2(y1 - y0, x1 - x0)
    size = 5.0
    for turn in (2.6, -2.6):
        page.draw_line(
            pymupdf.Point(x1, y1),
            pymupdf.Point(x1 + size * math.cos(angle + turn),
                          y1 + size * math.sin(angle + turn)),
            color=colour, width=1.1)
    if label:
        # label_at slides the caption along the line, to dodge a neighbour
        mx, my = x0 + (x1 - x0) * label_at, y0 + (y1 - y0) * label_at
        width = FREG.text_length(label, 7.4)
        if abs(x1 - x0) < abs(y1 - y0):           # vertical
            lx = mx + 7 if label_side == "right" else mx - 7 - width
            ly = my + 3
        else:                                      # horizontal
            lx, ly = mx - width / 2, my - 6
        page.draw_rect(pymupdf.Rect(lx - 3, ly - 8, lx + width + 3, ly + 3),
                       color=None, fill=(1, 1, 1))
        text(lx, ly, label, size=7.4, colour=colour)


def main() -> int:
    global page
    doc = pymupdf.open()
    page = doc.new_page(width=W, height=H)
    page.draw_rect(pymupdf.Rect(0, 0, W, H), color=None, fill=(1, 1, 1))

    # ---------------------------------------------------------------- header
    page.insert_image(pymupdf.Rect(30, 24, 74, 68), filename=str(LOGO),
                      keep_proportion=True)
    text(88, 48, "NISAAB — System Architecture", size=20, font=BOLD, colour=GREEN)
    text(88, 64, "Everything runs in one Google Cloud project: fbise-tutor-2026, "
                 "region asia-south1 (Mumbai)", size=9, colour=GREY)

    for i, (value, label) in enumerate(
        [("93", "REST endpoints"), ("28", "agent tools"),
         ("7", "job types"), ("1,020", "SLOs loaded")]
    ):
        cx = 790 + i * 82
        text(0, 48, value, size=17, font=BOLD, colour=GREEN, centre_in=cx)
        text(0, 62, label, size=7, colour=GREY, centre_in=cx)

    page.draw_line(pymupdf.Point(28, 82), pymupdf.Point(W - 28, 82),
                   color=TINT, width=1.6)

    # ------------------------------------------------------------ lane bands
    lane(96, 168, "WHO USES IT")
    lane(186, 262, "IN THE BROWSER")
    lane(280, 414, "THE APPLICATION")
    lane(432, 526, "DATA AND AI")

    # ------------------------------------------------------------- the boxes
    box(140, 106, 420, 158, "Student · Class XI or XII",
        ["Asks, practises, sits papers, downloads PDFs",
         "English · Roman Urdu · Urdu"])
    box(448, 106, 728, 158, "Subject teacher · reviewer",
        ["Opens the review queue and approves or",
         "rejects generated content, per outcome"])

    box(140, 196, 560, 252, "edu-web · Cloud Run",
        ["React 19 · TypeScript · Vite · TanStack Router · Effect Atom",
         "nginx serves the built app; 23 routes, public site and dashboard"])
    box(760, 196, 1070, 252, "Google Identity Platform",
        ["Email and password sign-in. Every request",
         "carries a signed ID token."], accent=SOFT)

    # Wide gaps between these three: the arrow labels have to sit in them
    box(140, 292, 430, 404, "edu-api · FastAPI",
        ["93 endpoints across 19 routers",
         "Verifies the token, loads the student's",
         "profile (class, group, language) and",
         "enforces daily limits. Business rules live",
         "in the services layer, never in the router."])
    box(500, 292, 790, 404, "LangGraph agent",
        ["create_agent · 28 tools · 8 modules",
         "Three middleware: a prompt rebuilt per",
         "student, a guard around every tool call,",
         "a check on the reply before it is sent.",
         "Practice tools end the turn."])
    box(860, 292, 1070, 404, "edu-worker · Cloud Run",
        ["7 job types",
         "Quizzes, flashcards, notes,",
         "mind maps, papers, OCR.",
         "5 AI calls at once, 90 s each.",
         "Scales to zero."], accent=AMBER)

    # Cloud SQL sits under the API, Vertex under the agent, Storage under the
    # worker, so most of the arrows below are short and vertical
    box(140, 442, 470, 516, "Cloud SQL — PostgreSQL 16 + pgvector",
        ["28 tables · 41 migrations · the jobs queue is a table here",
         "Document embeddings are stored alongside, so there is",
         "no separate vector database"])
    box(492, 442, 790, 516, "Vertex AI — Gemini",
        ["4 roles: tutor · generation · marking · OCR",
         "gemini-3.5-flash, falling back to flash-lite",
         "then gemini-2.5-flash on overload"])
    box(812, 442, 1070, 516, "Cloud Storage",
        ["Uploaded notes, past papers, scans.",
         "Scans are read by the OCR model, split",
         "into segments and embedded."])

    # ----------------------------------------------------------- the arrows
    arrow(260, 158, 260, 196, "opens")
    arrow(520, 158, 520, 196, "reviews")
    arrow(300, 252, 300, 292, "HTTPS + signed token")
    arrow(830, 252, 400, 292, "verifies the token", dashed=True)

    # Labels live in the 70pt gaps between the boxes, so they cover no text
    arrow(430, 328, 500, 328, "asks")
    arrow(500, 368, 430, 368, "answers")
    arrow(790, 348, 860, 348, "queues")

    # The long diagonals go down first, so the short vertical labels - whose
    # white backing plates would otherwise be struck through - sit on top
    arrow(900, 404, 430, 442, "claims jobs", dashed=True, label_at=0.76)
    arrow(880, 404, 700, 442, "generation", label_at=0.42)
    arrow(285, 404, 285, 442, "reads and writes")
    arrow(645, 404, 645, 442, "prompt + tools")
    arrow(960, 404, 960, 442, "documents")

    # -------------------------------------------------- the two request paths
    page.draw_rect(pymupdf.Rect(28, 544, W - 28, 656), color=None, fill=GREEN,
                   radius=0.02)
    text(48, 568, "TWO PATHS THROUGH THE SYSTEM", size=9.6, font=BOLD,
         colour=(1, 1, 1))
    page.draw_line(pymupdf.Point(560, 586), pymupdf.Point(560, 640),
                   color=(0.35, 0.58, 0.48), width=0.8)

    pale = (0.75, 0.89, 0.82)
    text(48, 596, "A   The tutor replies — synchronous, streamed", size=9,
         font=BOLD, colour=(0.84, 0.95, 0.89))
    text(48, 614, "Words have to appear as they are written, so nothing is queued.",
         size=8.2, colour=pale)
    text(48, 627, "The agent may call tools mid-turn — look up an SLO, search the",
         size=8.2, colour=pale)
    text(48, 640, "student's documents, make a quiz — then the answer streams back.",
         size=8.2, colour=pale)

    text(592, 596, "B   Something gets made — asynchronous, queued", size=9,
         font=BOLD, colour=(0.84, 0.95, 0.89))
    text(592, 614, "A paper takes seconds to minutes, so the request returns at once",
         size=8.2, colour=pale)
    text(592, 627, "and the browser polls. FOR UPDATE SKIP LOCKED lets two workers",
         size=8.2, colour=pale)
    text(592, 640, "share one queue safely; a 9-minute cap fails a stuck build.",
         size=8.2, colour=pale)

    # ------------------------------------------------------------- footnote
    text(28, 684, "FBISE 2026 paper pattern · Sciences and CS: 80 MCQ × ½ + 7 SRQ × 4 "
                  "+ 2 ERQ × 6 = 80 marks   ·   Mathematics: 64 × ¾ + 7 × 4 + 3 × 8 "
                  "= 100 marks", size=7.6, colour=GREY)
    note = "Not an official FBISE product"
    text(W - 28 - FREG.text_length(note, 7.6), 684, note, size=7.6, colour=GREY)

    OUTDIR.mkdir(parents=True, exist_ok=True)
    pdf = OUTDIR / "nisaab-architecture.pdf"
    png = OUTDIR / "nisaab-architecture.png"
    # Without this the full Segoe UI and Consolas sets are embedded, ~1 MB
    doc.subset_fonts()
    doc.save(pdf, deflate=True, garbage=4)
    page.get_pixmap(dpi=200).save(png)
    print(f"wrote {pdf}")
    print(f"wrote {png}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
