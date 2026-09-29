"""Parse the FBISE Computer Science Assessment Framework (NCP 2022-23) into NISAAB's
syllabus format.

Computer Science lists a few broad SLOs, each followed by what students must
understand, know and be able to do. The headline becomes the SLO's first line and
those points follow on their own lines, so the syllabus map shows the headline and
the SLO panel, the tutor and the question writers see everything. Every word comes
from the PDF text; only the layout (page headers, table columns) is removed.

Usage (from the repository root):
    uv run --package edu-worker python scripts/seed/parse_cs_af.py computer-science-xi path/to/af.pdf
Writes scripts/seed/data/<key>.json. Review the output before seeding.
"""

import json
import re
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"

SUBJECTS = {
    "computer-science-xi": {
        "subject": {"code": "CS", "name": "Computer Science"},
        "grade": 11,
        "source_url": "https://www.fbise.edu.pk/ModelPaper/50_percent/Computer_HSSC_I_model_paper_50_percent.pdf",
        # As printed in the AF's Table of Specifications
        "domain_names": {
            "A": "Computer Systems",
            "B": "Computational Thinking and Algorithms",
            "C": "Programming Fundamentals",
            "D": "Data and Analysis",
            "E": "Applications of Computer Science",
            "F": "Impacts of Computing",
            "G": "Digital Literacy",
            "H": "Entrepreneurship in the Digital Age",
        },
        # CS-11-C-06's columns are interleaved in the PDF text: put its form, level and
        # remark words back in the order every other row has
        "text_fixes": [
            (
                r"decompose a problem into Summative Knowledge / Question\(s\) will be\s*\n",
                "decompose a problem into ",
            ),
            (
                r"(Celsius to Fahrenheit conversion etc\.\)\s*\n)(for Theory\s*\nand\s*\nPractical\s*\n"
                r"Based\s*\nAssessment\s*\n)(Understanding/\s*\nApplication\s*\n)(asked in the Annual)",
                r"\1Summative \n\2Knowledge / \n\3Question(s) will be \n\4",
            ),
        ],
    },
}

SLO = re.compile(r"\[SLO\s*([A-Z]{2})\s*-\s*(1[12])\s*-\s*([A-Z])\s*-\s*(\d{1,2})\]")
# The table header repeated on every page, and page numbers
HEADER = re.compile(
    r"Content\s*\n\s*Domain/\s*\n\s*Area\s*\n\s*SLO No\./ Description.*?40 minutes\)\s*\n", re.S
)
PAGE = re.compile(r"Page \d+ of \d+\s*\n")
# Start of a row's form column, e.g. "Summative for Theory and Practical Based Assessment"
FORM = re.compile(
    r"(Summative|Formative)\s+for\s+(Theory(?:\s+and\s+Practical\s+Based\s+Assessment)?"
    r"|Practical(?:\s+Based\s+Assessment)?|PBA)"
)
LEVELS = {"Knowledge": "K", "Understanding": "U", "Application": "A"}
# Words of the remark column ("Question(s) will be asked in the Annual theory paper as well
# as Lab work will be assessed in the Practical Based Assessment"), so wrapped SLO text
# is never mistaken for it
REMARK_WORDS = set(
    "question(s) question s will be not asked in the annual final theory paper examination "
    "as well lab work assessed practical based assessment however it part of".split()
)
BULLETS = "•"
LEAD_IN = re.compile(r"^(Students? will (?:understand|know|be able to)(?: that)?)\s*[.…:]*\s*(.*)$")


def extract_text(pdf: Path) -> str:
    import logging

    import pypdf

    logging.disable(logging.CRITICAL)
    return "\n".join((page.extract_text() or "") for page in pypdf.PdfReader(pdf).pages)


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(f"[{BULLETS}]", " ", text)).strip()


def split_row(body: str) -> tuple[str, str, list[str], int | None]:
    """A row's form, level words, content lines (form columns removed) and periods."""
    match = FORM.search(body)
    if match is None:
        raise ValueError("no form of assessment found")
    question = body.find("Question(s)", match.end())
    levels_text = body[match.end() : question]
    # The remark column continues in short lines, then the periods number (if any)
    lines = body[question:].split("\n")
    consumed, periods = 1, None
    for line in lines[1:]:
        text = line.strip()
        if not text:
            consumed += 1
            continue
        if text.isdigit():
            periods = int(text)
            consumed += 1
            break
        if set(re.findall(r"[a-z()]+", text.lower())) <= REMARK_WORDS:
            consumed += 1
            continue
        break
    rest = "\n".join(lines[consumed:])
    content = (body[: match.start()] + "\n" + rest).split("\n")
    # Drop the next domain's label at the end (e.g. "G: Digital" / "Literacy")
    for index in range(len(content) - 1, max(len(content) - 8, -1), -1):
        if re.match(r"^\s*[A-H]:", content[index]) and all(len(l.strip()) <= 16 for l in content[index:]):
            content = content[:index]
            break
    return match.group(0), levels_text, content, periods


def parse(text: str, config: dict) -> dict:
    for pattern, replacement in config.get("text_fixes", []):
        text, count = re.subn(pattern, replacement, text)
        if count != 1:
            raise SystemExit(f"text fix did not apply exactly once: {pattern[:50]}")
    start = text.index("Details of Content Areas")
    end = min(i for i in (text.find(m, start) for m in ("Note: PBA", "FINAL CONCEPTUAL PATTERN", "Model Question Paper")) if i > 0)
    table = PAGE.sub("", HEADER.sub("\n", text[start:end]))
    markers = list(SLO.finditer(table))
    slos = []
    for index, marker in enumerate(markers):
        prefix, grade, domain, number = marker.groups()
        code = f"{prefix}-{grade}-{domain}-{int(number):02d}"
        stop = markers[index + 1].start() if index + 1 < len(markers) else len(table)
        try:
            form_text, levels_text, content, periods = split_row(table[marker.end() : stop])
        except ValueError as error:
            raise SystemExit(f"{code}: {error}") from error
        form_text = clean(form_text)
        if form_text.startswith("Formative"):
            form = "formative"
        elif "Theory" in form_text:
            form = "summative"  # examined in the theory paper (some also in the practical)
        else:
            form = "practical"
        levels = [abbr for word, abbr in LEVELS.items() if re.search(rf"\b{word}\b", levels_text)]

        # Headline, then "Students will understand / know / be able to" with their points
        headline: list[str] = []
        details: list[list] = []
        for raw in content:
            line = raw.strip()
            if not line:
                continue
            bullet = line[0] in BULLETS
            text_ = clean(line)
            lead = LEAD_IN.match(text_) if not bullet else None
            if lead and headline:
                details.append([lead.group(1) + ":", [lead.group(2)] if lead.group(2) else []])
            elif not details:
                headline.append(text_)
            elif bullet or text_.startswith("o ") or not details[-1][1]:
                details[-1][1].append(text_[2:] if text_.startswith("o ") else text_)
            else:
                details[-1][1][-1] += " " + text_  # a wrapped line continues the point
        description = " ".join(headline).strip()
        for lead, points in details:
            description += "\n" + lead + " " + "; ".join(p.rstrip(";.") for p in points if p) + "."
        slos.append(
            {
                "code": f"{prefix}-{grade}-{domain}-{int(number):02d}",
                "domain": domain,
                "content_area": config["domain_names"][domain],
                "description": description,
                "assessment_form": form,
                "cognitive_levels": levels,
                "periods": periods,
            }
        )

    used = sorted({s["domain"] for s in slos})
    return {
        "subject": config["subject"],
        "grade": config["grade"],
        "scheme": "ISS-2024",
        "curriculum": "NCP 2022-23",
        "source_url": config["source_url"],
        "domains": [{"code": code, "name": config["domain_names"][code]} for code in used],
        "slos": slos,
    }


def main() -> None:
    key, pdf = sys.argv[1], Path(sys.argv[2])
    text = pdf.read_text(encoding="utf-8") if pdf.suffix == ".txt" else extract_text(pdf)
    output = parse(text, SUBJECTS[key])
    out = DATA_DIR / f"{key}.json"
    out.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    forms: dict[str, int] = {}
    for slo in output["slos"]:
        forms[slo["assessment_form"]] = forms.get(slo["assessment_form"], 0) + 1
    print(f"{out.name}: {len(output['slos'])} SLOs in {len(output['domains'])} domains, {forms}")


if __name__ == "__main__":
    main()
