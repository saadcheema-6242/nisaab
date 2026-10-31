"""Draw Figure 2 (the agent loop) and Figure 3 (the curriculum pipeline).

Run with:
    python scripts/docs/build_figures.py

Needs a package the services do not, so install it just for this:
    uv pip install pymupdf

Figure 1 is the system architecture and has its own script,
build_architecture_diagram.py. All three write a vector PDF and a PNG into
docs/documentation/assets/ - the PDF for the documentation PDF, the PNG for the
DOCX and for GitHub.

Both are drawn wide, because the documents place a figure on a landscape page.
"""

import math
import pathlib
import sys

import pymupdf

REPO = pathlib.Path(__file__).resolve().parents[2]      # edu-agent/
OUTDIR = REPO / "docs" / "documentation" / "assets"

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
FREG = pymupdf.Font(fontfile=REG)
FBOLD = pymupdf.Font(fontfile=BOLD)


class Sheet:
    """One figure: a page, plus the few drawing helpers both figures need."""

    def __init__(self, width: float, height: float):
        self.doc = pymupdf.open()
        self.page = self.doc.new_page(width=width, height=height)
        self.w, self.h = width, height
        self.page.draw_rect(pymupdf.Rect(0, 0, width, height), color=None, fill=(1, 1, 1))

    def text(self, x, y, body, size=8.4, font=REG, colour=INK, centre_in=None):
        if centre_in is not None:
            metric = FBOLD if font == BOLD else FREG
            x = centre_in - metric.text_length(body, size) / 2
        self.page.insert_text((x, y), body, fontname="f" + str(abs(hash(font)) % 97),
                              fontfile=font, fontsize=size, color=colour)

    def box(self, x0, y0, x1, y1, title, lines=(), accent=GREEN, fill=(1, 1, 1),
            centred=False):
        self.page.draw_rect(pymupdf.Rect(x0, y0, x1, y1), color=LINE, fill=fill,
                            width=0.9, radius=0.05)
        self.page.draw_rect(pymupdf.Rect(x0, y0 + 3, x0 + 3.4, y1 - 3),
                            color=None, fill=accent)
        mid = (x0 + x1) / 2
        if centred:
            self.text(0, y0 + 20, title, size=10, font=BOLD, colour=accent, centre_in=mid)
            y = y0 + 35
            for line in lines:
                self.text(0, y, line, size=8.2, colour=GREY, centre_in=mid)
                y += 12.4
        else:
            self.text(x0 + 14, y0 + 20, title, size=10, font=BOLD, colour=accent)
            y = y0 + 35
            for line in lines:
                self.text(x0 + 14, y, line, size=8.2, colour=GREY)
                y += 12.4

    def arrow(self, x0, y0, x1, y1, label=None, colour=SOFT, dashed=False,
              label_at=0.5, above=True):
        kwargs = {"color": colour, "width": 1.2}
        if dashed:
            kwargs["dashes"] = "[2 2] 0"
        self.page.draw_line(pymupdf.Point(x0, y0), pymupdf.Point(x1, y1), **kwargs)
        angle = math.atan2(y1 - y0, x1 - x0)
        for turn in (2.6, -2.6):
            self.page.draw_line(
                pymupdf.Point(x1, y1),
                pymupdf.Point(x1 + 5.4 * math.cos(angle + turn),
                              y1 + 5.4 * math.sin(angle + turn)),
                color=colour, width=1.2)
        if label:
            mx = x0 + (x1 - x0) * label_at
            my = y0 + (y1 - y0) * label_at
            width = FREG.text_length(label, 7.6)
            lx, ly = mx - width / 2, my - 7 if above else my + 13
            self.page.draw_rect(pymupdf.Rect(lx - 3, ly - 8, lx + width + 3, ly + 3),
                                color=None, fill=(1, 1, 1))
            self.text(lx, ly, label, size=7.6, colour=colour)

    def elbow(self, points, label=None, colour=SOFT):
        """A right-angled connector through a list of points, arrow at the end."""
        for (x0, y0), (x1, y1) in zip(points, points[1:-1]):
            self.page.draw_line(pymupdf.Point(x0, y0), pymupdf.Point(x1, y1),
                                color=colour, width=1.2)
        (x0, y0), (x1, y1) = points[-2], points[-1]
        self.arrow(x0, y0, x1, y1, colour=colour)
        if label:
            mx = (points[0][0] + points[-1][0]) / 2
            my = points[1][1]
            width = FREG.text_length(label, 7.6)
            self.page.draw_rect(pymupdf.Rect(mx - width / 2 - 3, my - 8,
                                             mx + width / 2 + 3, my + 3),
                                color=None, fill=(1, 1, 1))
            self.text(mx - width / 2, my, label, size=7.6, colour=colour)

    def header(self, title, subtitle):
        self.text(30, 36, title, size=16, font=BOLD, colour=GREEN)
        self.text(30, 52, subtitle, size=8.8, colour=GREY)
        self.page.draw_line(pymupdf.Point(30, 64), pymupdf.Point(self.w - 30, 64),
                            color=TINT, width=1.4)

    def save(self, stem):
        OUTDIR.mkdir(parents=True, exist_ok=True)
        pdf, png = OUTDIR / f"{stem}.pdf", OUTDIR / f"{stem}.png"
        self.doc.subset_fonts()
        self.doc.save(pdf, deflate=True, garbage=4)
        self.page.get_pixmap(dpi=200).save(png)
        print(f"wrote {pdf.name} and {png.name}")


def agent_loop() -> None:
    s = Sheet(1000.0, 500.0)
    s.header("The agent loop",
             "LangGraph runs the agent as a graph with a typed state. The tool node returns "
             "to the model node, so the agent may call several tools before it answers.")

    # The top row is the path of one turn; the loop hangs below the model node
    s.box(28, 150, 166, 250, "Student's message", ["In English, Urdu", "or Roman Urdu"],
          centred=True)
    s.box(196, 150, 356, 250, "@dynamic_prompt", ["Builds the system prompt",
                                                  "for this student and",
                                                  "subject. Cached."],
          accent=SOFT, fill=PALE)
    s.box(386, 150, 546, 250, "Model node", ["Gemini on Vertex AI.", "Answer now, or",
                                             "call a tool?"])
    s.box(606, 150, 766, 250, "@after_model", ["Makes sure captured", "sources reach the",
                                               "streamed update."], accent=SOFT, fill=PALE)
    s.box(796, 150, 942, 250, "The answer", ["Streams to the", "browser as text",
                                             "or a card"], centred=True)

    s.box(28, 320, 166, 430, "Typed context", ["user, language,", "subject, grade,",
                                               "project, services"], accent=SOFT, centred=True)
    s.box(386, 320, 546, 430, "Tool node", ["28 tools, 8 modules.", "@wrap_tool_call wraps",
                                            "every execution."], accent=AMBER)
    s.box(606, 320, 766, 430, "return_direct", ["The five practice tools", "end the turn here, so",
                                                "the card is shown."], accent=AMBER, fill=PALE)

    s.arrow(166, 200, 196, 200)
    s.arrow(356, 200, 386, 200)
    s.arrow(546, 200, 606, 200, "no more tools")
    s.arrow(766, 200, 796, 200)

    # Two parallel vertical arrows between the model and the tools: that is the loop
    s.arrow(446, 250, 446, 320, "calls a tool", above=False, label_at=0.52)
    s.arrow(492, 320, 492, 250, "result returns", label_at=0.48)

    s.arrow(166, 370, 386, 240, "travels with every step", dashed=True, label_at=0.42)
    s.arrow(546, 375, 606, 375, "practice")
    s.elbow([(766, 375), (869, 375), (869, 250)])

    s.text(30, 466, "The loop is the point: the model chooses which tool to call and in what "
                    "order. The application code never fixes that sequence.",
           size=8.4, colour=GREY)
    s.save("nisaab-agent-loop")


def pipeline() -> None:
    s = Sheet(1120.0, 420.0)
    s.header("The curriculum data pipeline",
             "The seven stages used for every subject, from FBISE's published PDF to a tested "
             "deployment.")

    stages = [
        ("01", "Obtain", ["The official Assessment", "Framework from the", "FBISE website"]),
        ("02", "Extract", ["Text taken out page", "by page"]),
        ("03", "Parse", ["Code, description, form", "of assessment, cognitive", "level"]),
        ("04", "Verify", ["Checked against FBISE's", "newest 50% MCQ", "documents"]),
        ("05", "Load", ["Seeded by subject,", "grade and domain.", "Idempotent"]),
        ("06", "Generate", ["Practice written ahead", "for every examined", "outcome"]),
        ("07", "Test", ["52 end-to-end checks", "against the live", "deployment"]),
    ]

    width, gap = 136.0, 14.0
    left = 30.0
    for i, (number, name, lines) in enumerate(stages):
        x0 = left + i * (width + gap)
        x1 = x0 + width
        s.page.draw_rect(pymupdf.Rect(x0, 100, x1, 126), color=None, fill=GREEN,
                         radius=0.08)
        s.text(0, 118, f"{number}  {name}", size=9.6, font=BOLD, colour=(1, 1, 1),
               centre_in=(x0 + x1) / 2)
        s.page.draw_rect(pymupdf.Rect(x0, 126, x1, 212), color=LINE, fill=(1, 1, 1),
                         width=0.9)
        y = 146
        for line in lines:
            s.text(0, y, line, size=7.8, colour=GREY, centre_in=(x0 + x1) / 2)
            y += 11.6
        if i < len(stages) - 1:
            s.arrow(x1 + 1, 156, x1 + gap - 1, 156)

    s.page.draw_rect(pymupdf.Rect(30, 246, 560, 352), color=None, fill=PALE, radius=0.03)
    s.text(46, 270, "Stage 03 needs three parsers", size=9.6, font=BOLD, colour=GREEN)
    for i, line in enumerate([
        "Rule-based — Physics, Biology, Mathematics. Reads to the next code.",
        "AI-assisted — Chemistry, whose table lists codes before descriptions.",
        "    Every returned word is checked against the source, or rejected.",
        "Nested-list — Computer Science, where outcomes carry sub-lists.",
    ]):
        s.text(46, 292 + i * 14, line, size=8.2, colour=INK if i != 2 else GREY)

    s.page.draw_rect(pymupdf.Rect(584, 246, 1090, 352), color=None, fill=TINT, radius=0.03)
    s.text(600, 270, "What stage 04 found", size=9.6, font=BOLD, colour=GREEN)
    for i, line in enumerate([
        "Chemistry had been revised: one outcome added, thirteen moved",
        "to practical assessment only.",
        "Physics, Biology and Mathematics already matched.",
        "Computer Science was missing from the earlier work and was added.",
    ]):
        s.text(600, 292 + i * 14, line, size=8.2, colour=INK)

    s.text(30, 386, "Not an official FBISE product. The frameworks are FBISE's own published "
                    "documents; NISAAB reproduces their wording and never invents it.",
           size=7.8, colour=GREY)
    s.save("nisaab-pipeline")


def main() -> int:
    agent_loop()
    pipeline()
    return 0


if __name__ == "__main__":
    sys.exit(main())
