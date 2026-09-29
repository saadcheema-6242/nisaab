"""Parse an FBISE Assessment Framework PDF into a reviewed-ready SLO JSON file.

FBISE publishes one Assessment Framework (AF) per subject and grade. Its SLO table
lists every Student Learning Outcome with a code (e.g. P-11-B-05), description,
form of assessment (summative = examined, formative = classroom only, "Summative for
PBA" = practical exam) and cognitive level (Knowledge / Understanding / Application).

The PDF text wraps table cells across lines and pages, so the parser works per SLO
entry: it takes the text between one "[SLO: ...]" marker and the next, removes the
table's fixed vocabulary (form, cognitive level, remarks, page headers) and keeps
the rest as the description. Subject specifics (domain names, content areas from
the AF's Table of Specifications, known typos in the PDF) live in SUBJECTS below.

Usage (from the repository root):
    uv run --package edu-worker python scripts/seed/parse_af.py physics-xi path/to/af.pdf
Writes scripts/seed/data/<subject-key>.json. Review the file before seeding.
"""

import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader

DATA_DIR = Path(__file__).resolve().parent / "data"

SUBJECTS = {
    "physics-xi": {
        "subject": {"code": "PHY", "name": "Physics"},
        "grade": 11,
        "scheme": "ISS-2024",
        "curriculum": "NCP 2022-23",
        "source_url": (
            "https://www.fbise.edu.pk/ModelPaper/2025/Assessment%20Frameworks/HSSC-I/"
            "Final%20Assessment%20Framework%20Model%20Question%20Paper%20Physics%20HSSC-I.pdf"
        ),
        # The SLO table ends with notes, followed by the model question paper
        "table_end": "Note: In the Assessment Framework",
        "domains": {
            "A": "Measurements",
            "B": "Mechanics",
            "C": "Heat and Thermodynamics",
            "D": "Waves",
            "E": "Electricity and Magnetism",
            "F": "Modern Physics",
            "N": "Experimentation Skills",
        },
        # From the AF's Table of Specifications: content area -> SLO number ranges
        "content_areas": {
            "A": [("Measurements", [(1, 7)])],
            "B": [
                ("Vectors", [(1, 2)]),
                ("Translatory motion", [(3, 6), (11, 13)]),
                ("Rotational and circular motion", [(7, 10), (14, 21)]),
                ("Deformation of solids", [(22, 28)]),
                ("Work and kinetic energy", [(29, 32)]),
                ("Fluid dynamics", [(33, 44)]),
            ],
            "C": [("Heat and thermodynamics", [(1, 99)])],
            "D": [("Waves", [(1, 99)])],
            "E": [("Electrostatics", [(1, 9)]), ("Electricity", [(10, 27)]), ("Magnetism", [(28, 99)])],
            "F": [("Relativity", [(1, 8)]), ("Particle physics", [(9, 99)])],
            "N": [("Experimentation skills", [(1, 99)])],
        },
        # Typos in the published PDF: code as printed -> correct code
        "code_fixes": {"P-12-C-01": "P-11-C-01", "P-110-N-18": "P-11-N-18"},
        # Rows whose form/level columns the PDF printed on a neighbouring row
        "overrides": {"P-11-B-05": {"assessment_form": "summative", "cognitive_levels": ["A"]}},
        # Stray characters in the PDF text: wrong -> right
        "text_fixes": {"calculate for Ja projectile": "calculate for a projectile"},
    },
}

# The opening bracket is missing for a few SLOs in the PDFs (e.g. "SLO: P-11-E-07]")
SLO_MARKER = re.compile(
    r"\[?\s*SLO\s*:?\s*([A-Z]{1,3})\s*-\s*(\d{2,3})\s*-\s*([A-Z])\s*-\s*(\d{1,2})\s*\]"
)
FORM = re.compile(r"\b(Summative|Formative)\b(\s+for\s+PBA)?")
COGNITIVE = {"Knowledge": "K", "Understanding": "U", "Application": "A"}
PERIODS = re.compile(r"\b(\d{1,2})\s*periods?\b", re.IGNORECASE)
NOISE = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"Page \d+ of \d+",
        r"NCP SLOs Description Form of\s+Assessment\s+Cognitive\s+Level\s+Remarks\s+Number of\s+Periods\s*Required\s+\(1 period\s*=\s*40 minutes\)",
        # The remarks column; its two halves can wrap around description text
        r"Question(\(s\))?\s+will\s+(not\s+)?be\s+asked\s+in",
        r"\b(final|annual)\s+examination\.?",
        r",?\s*however,?\s*it\s+will be part of Lab work\.?",
        r",?\s*however,?\s*it\b",
        r"will be part of Lab work\.?",
        r"Domain\s*:?\s*[A-Z]\s*:?\s*[A-Za-z ,&]+?\s+\d{1,2}\s*periods",
        r"Domain\s*:\s*[A-Z]\s+[A-Za-z ,&]+?(?=\s+Question|\s*$)",
        r"National Curriculum of Pakistan 2022-2023",
        r"Assessment Framework \w+ Grade-[XIV]+ \(HSSC-I+\)",
        r"Details of Content Areas/ SLOs",
    ]
]


def extract_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    # Words run together across the PDF's line breaks ("orquotients", "ofthermodynamics")
    return text.replace(" - ", " – ").strip(" -–")


def content_area(config: dict, domain: str, number: int) -> str:
    for name, ranges in config["content_areas"].get(domain, []):
        if any(low <= number <= high for low, high in ranges):
            return name
    return config["domains"].get(domain, domain)


def parse(text: str, config: dict) -> list[dict]:
    end = text.find(config["table_end"])
    table = text[: end if end > 0 else len(text)]
    markers = list(SLO_MARKER.finditer(table))
    entries: dict[str, dict] = {}

    for index, marker in enumerate(markers):
        code = "-".join(marker.groups()[:3]) + f"-{int(marker.group(4)):02d}"
        code = config["code_fixes"].get(code, code)
        # Codes are kept as FBISE prints them (e.g. Physics XI Domain E uses P-09-E-..),
        # so they match FBISE's model-paper alignment tables
        if code.split("-")[2] not in config["domains"]:
            continue
        chunk_end = markers[index + 1].start() if index + 1 < len(markers) else len(table)
        chunk = table[marker.end() : chunk_end]
        for pattern in NOISE:
            chunk = pattern.sub(" ", chunk)

        form_match = FORM.search(chunk)
        head = chunk[: form_match.start()] if form_match else chunk
        tail = chunk[form_match.end() :] if form_match else ""

        cognitive = sorted(
            {abbr for word, abbr in COGNITIVE.items() if re.search(rf"\b{word}\b", tail)},
            key="KUA".index,
        )
        periods_match = PERIODS.search(tail) or PERIODS.search(head)
        rest = tail
        for word in COGNITIVE:
            rest = re.sub(rf"\b{word}\b", " ", rest)
        rest = PERIODS.sub(" ", re.sub(r"[+]", " ", rest))
        head = PERIODS.sub(" ", head)
        # Description text that wrapped past the form/level columns
        continuation = clean(rest)
        description = clean(head)
        if continuation and re.search(r"[a-z]{3}", continuation):
            description = f"{description} {continuation}".strip()

        if form_match is None:
            form = "unknown"
        elif form_match.group(1) == "Formative":
            # "Formative for PBA": lab work that is never examined
            form = "formative"
        elif form_match.group(2):
            form = "practical"  # "Summative for PBA": assessed in the practical exam
        else:
            form = "summative"

        domain = code.split("-")[2]
        number = int(code.split("-")[3])
        entry = {
            "code": code,
            "domain": domain,
            "content_area": content_area(config, domain, number),
            "description": description,
            "assessment_form": form,
            "cognitive_levels": cognitive,
            "periods": int(periods_match.group(1)) if periods_match else None,
        }
        if code in entries:
            # Listed twice in the PDF: keep one entry, merge cognitive levels
            previous = entries[code]
            merged = sorted(set(previous["cognitive_levels"]) | set(cognitive), key="KUA".index)
            entry = {**previous, "cognitive_levels": merged}
        entries[code] = entry

    for entry in entries.values():
        for wrong, right in config.get("text_fixes", {}).items():
            entry["description"] = entry["description"].replace(wrong, right)

    for code, fields in config.get("overrides", {}).items():
        if code in entries:
            entries[code].update(fields)

    blank = [code for code, entry in entries.items() if not entry["description"]]
    for code in blank:
        print(f"skipped {code}: blank row in the published PDF")
        del entries[code]

    return sorted(entries.values(), key=lambda e: (e["domain"], int(e["code"].split("-")[3])))


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[1] not in SUBJECTS:
        sys.exit(f"Usage: parse_af.py <{'|'.join(SUBJECTS)}> <assessment-framework.pdf>")
    key, pdf_path = sys.argv[1], Path(sys.argv[2])
    config = SUBJECTS[key]
    slos = parse(extract_text(pdf_path), config)

    output = {
        "subject": config["subject"],
        "grade": config["grade"],
        "scheme": config["scheme"],
        "curriculum": config["curriculum"],
        "source_url": config["source_url"],
        "domains": [
            {"code": code, "name": name} for code, name in config["domains"].items()
        ],
        "slos": slos,
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_DIR / f"{key}.json"
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    forms = {}
    for slo in slos:
        forms[slo["assessment_form"]] = forms.get(slo["assessment_form"], 0) + 1
    print(f"{len(slos)} SLOs -> {out_path}")
    print("by form:", forms)
    print("by domain:", {d: sum(1 for s in slos if s["domain"] == d) for d in config["domains"]})
    missing_levels = [s["code"] for s in slos if not s["cognitive_levels"]]
    if missing_levels:
        print("no cognitive level found:", missing_levels)


if __name__ == "__main__":
    main()
