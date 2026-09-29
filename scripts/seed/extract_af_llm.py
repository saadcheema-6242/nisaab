"""Extract the SLO table of an FBISE Assessment Framework with AI help, for PDFs whose
table layout the rule-based parser (parse_af.py) cannot follow (e.g. Chemistry XI lists
several SLO codes before their descriptions).

Safety checks, so FBISE's content is copied rather than invented:
- the SLO codes come from the PDF text (regex), per domain; the model must return
  exactly those codes, otherwise the domain is retried and then reported;
- every description must be made of words that appear in that part of the PDF text.
Review the output file before seeding, as with parse_af.py.

Usage (from the repository root, with an AI provider configured in .env):
    uv run --package edu-worker python scripts/seed/extract_af_llm.py chemistry-xi path/to/af.txt
The input is the PDF's extracted text (pypdf), e.g. from parse_af.extract_text.
Writes scripts/seed/data/<subject-key>.json.
"""

import asyncio
import json
import re
import sys
from pathlib import Path

from edu_ai.llm import GENERATION, create_chat_model
from pydantic import BaseModel, Field

DATA_DIR = Path(__file__).resolve().parent / "data"
FBISE_PAGE = "https://www.fbise.edu.pk/curriculum_model_paper.php"

SUBJECTS = {
    "physics-xii": {
        "subject": {"code": "PHY", "name": "Physics"},
        "grade": 12,
        "prefix": "P",
        "table_start": "Details of Content Areas",
        "table_end": "Physics Model Question Paper",
        # As printed in the AF's domain headings (Experimentation Skills codes use N)
        "domain_names": {"B": "Mechanics", "C": "Heat and Thermodynamics", "D": "Waves", "E": "Electricity and Magnetism", "F": "Modern Physics", "G": "Nature of Sciences", "N": "Experimentation Skills"},
    },
    "chemistry-xi": {
        # FBISE prints only domain letters; names summarise each domain's content areas
        "domain_names": {"A": "Nature of Science in Chemistry", "B": "Physical Chemistry", "C": "Inorganic Chemistry", "D": "Environmental Chemistry", "E": "Organic Chemistry", "F": "Energy", "G": "Practical Skills"},
        "subject": {"code": "CHEM", "name": "Chemistry"},
        "grade": 11,
        "prefix": "C",
        "table_start": "Details of Content Areas",
        "table_end": "Model Question Paper",
    },
    "biology-xi": {
        # FBISE prints only domain letters; names summarise each domain's content areas
        "domain_names": {"B": "Evolution and Biodiversity", "C": "Biological Molecules", "D": "Cell Biology", "F": "Bioenergetics", "H": "Reproduction and Genetics", "N": "Ecosystems", "P": "Viruses", "Q": "Plant Physiology", "X": "Practical Skills"},
        "subject": {"code": "BIO", "name": "Biology"},
        "grade": 11,
        "prefix": "B",
        "table_start": "Details of Content Areas",
        "table_end": "Model Question Paper",
    },
    "mathematics-xi": {
        "subject": {"code": "MATH", "name": "Mathematics"},
        "grade": 11,
        "prefix": "M",
        "table_start": "Details of Content Area",
        "table_end": "Model Question Paper Mathematics",
        # PDF text drops the 1 in the square root of -1
        "text_fixes": {"√− .": "√−1.", "√−  .": "√−1."},
    },
}

MAX_CHUNK = 14_000


class ExtractedSlo(BaseModel):
    code: str = Field(..., description="SLO code exactly as listed, e.g. C-11-B-03")
    description: str = Field(..., description="The SLO description, copied word for word from the text")
    content_area: str = Field(..., description="The content area (topic) the SLO belongs to")
    cognitive_levels: list[str] = Field(..., description="K, U and/or A from the Cognitive Level column")
    assessment_form: str = Field(
        ...,
        description="summative, formative, or practical ('Summative for PBA' or practical/lab work)",
    )


class ExtractedDomain(BaseModel):
    domain_code: str = Field(..., description="Domain letter, e.g. B")
    domain_name: str = Field(..., description="Domain name as written in the table, e.g. Atomic Structure")
    slos: list[ExtractedSlo]


PROMPT = """Below is text extracted from the SLO table of the FBISE Assessment Framework for {subject} Grade {grade}.
The PDF text is messy: table columns are interleaved, and sometimes several SLO codes are listed first and
their descriptions follow in the same order.

Extract every SLO of domain {domain}. The codes in this part of the table are, in order:
{codes}

For each code return:
- description: copied word for word from the text (only join words broken across lines; do not reword,
  shorten or add anything; leave out the remarks column, e.g. "Question(s) will not be asked...")
  and include any note in square brackets that follows the description, e.g. "[This will include ...]",
  because it is part of the SLO
- content_area: the topic name from the Content Area column
- cognitive_levels: from the Cognitive Level column (Knowledge=K, Understanding=U, Application=A)
- assessment_form: "summative" if Summative, "formative" if Formative, "practical" if "Summative for PBA"
Also give the domain name.

Return exactly the listed codes, each once.

TEXT:
{text}
"""

CODE = re.compile(r"SLO\s*:?\s*([A-Z]{1,2})\s*-\s*(\d{2})\s*-\s*([A-Z])\s*-\s*(\d{1,3})")
LEVELS = {"K", "U", "A"}
FORMS = {"summative", "formative", "practical"}


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def table_text(text: str, config: dict) -> str:
    start = text.find(config["table_start"])
    start = start if start >= 0 else 0
    end = text.find(config["table_end"], start + 1)
    return text[start : end if end > 0 else len(text)]


def domain_chunks(table: str) -> list[tuple[str, list[str], str]]:
    """Split the table into (domain, codes in order, text) chunks at domain changes."""
    markers = list(CODE.finditer(table))
    chunks: list[tuple[str, list[str], str]] = []
    start = 0
    current: str | None = None
    codes: list[str] = []
    for index, marker in enumerate(markers):
        code = f"{marker.group(1)}-{marker.group(2)}-{marker.group(3)}-{int(marker.group(4)):02d}"
        domain = marker.group(3)
        if current is None:
            current = domain
        if domain != current:
            # A domain starts at the text before its first code (domain/content area names)
            cut = table.rfind("\n", 0, marker.start())
            chunks.append((current, codes, table[start:cut]))
            start, current, codes = cut, domain, []
        if code not in codes:
            codes.append(code)
    if current is not None:
        chunks.append((current, codes, table[start:]))

    # Very long domains are split into groups of codes. Each group gets the text from a
    # little before its first code to well past the next group's first code, because
    # descriptions can follow a block of codes.
    result = []
    for domain, domain_codes, text in chunks:
        if len(text) <= MAX_CHUNK:
            result.append((domain, domain_codes, text))
            continue
        positions = {}
        for marker in CODE.finditer(text):
            code = f"{marker.group(1)}-{marker.group(2)}-{marker.group(3)}-{int(marker.group(4)):02d}"
            positions.setdefault(code, marker.start())
        pieces = -(-len(text) // MAX_CHUNK)
        size = -(-len(domain_codes) // pieces)
        for i in range(0, len(domain_codes), size):
            group = domain_codes[i : i + size]
            begin = max(0, positions.get(group[0], 0) - 1500) if i else 0
            following = domain_codes[i + size] if i + size < len(domain_codes) else None
            end = positions.get(following, len(text)) + 3000 if following else len(text)
            result.append((domain, group, text[begin:end]))
    return result


PBA = r"(?:PBA|Practical\s+Based\s+Assessment(?:\s*\(PBA\))?)"
ROW_FORM = re.compile(
    rf"\b(Summative|Formative)\b(?:\s+for\s+(theory\s+and\s+{PBA}|theory|{PBA}))?", re.IGNORECASE
)
LEVEL_WORDS = {"Knowledge": "K", "Understanding": "U", "Application": "A"}


def row_facts(table: str) -> dict[str, tuple[str, list[str]]]:
    """Assessment form and K/U/A levels from each SLO's own row, where unambiguous.

    A row is the text from an SLO code to the next code. Rows that belong to a block
    of codes listed before their descriptions have no form, or several, and are skipped.
    """
    markers = list(CODE.finditer(table))
    facts: dict[str, tuple[str, list[str]]] = {}
    for index, marker in enumerate(markers):
        code = f"{marker.group(1)}-{marker.group(2)}-{marker.group(3)}-{int(marker.group(4)):02d}"
        end = markers[index + 1].start() if index + 1 < len(markers) else len(table)
        row = table[marker.end() : end]
        forms = list(ROW_FORM.finditer(row))
        if len(forms) != 1 or code in facts:
            continue
        kind, qualifier = forms[0].group(1).lower(), (forms[0].group(2) or "").lower()
        # "Summative for theory (and PBA)" is examined in the theory paper; "Summative for
        # PBA" only in the practical; "Formative (for PBA)" is never examined
        if kind == "formative":
            form = "formative"
        elif qualifier and not qualifier.startswith("theory"):
            form = "practical"
        else:
            form = "summative"
        after = row[forms[0].end() :]
        levels = [
            abbr
            for word, abbr in LEVEL_WORDS.items()
            if re.search(rf"\b{word}\b", after, re.IGNORECASE)
        ]
        facts[code] = (form, levels)
    return facts


def check(slo: ExtractedSlo, source_words: set[str]) -> str | None:
    desc = words(slo.description)
    if not desc:
        return "empty description"
    unknown = [w for w in desc if w not in source_words]
    if len(unknown) > max(1, len(desc) // 10):
        return f"words not in the PDF text: {' '.join(unknown[:6])}"
    if slo.assessment_form not in FORMS:
        return f"unknown assessment form {slo.assessment_form}"
    return None


async def extract_chunk(llm, config: dict, domain: str, codes: list[str], text: str) -> ExtractedDomain | None:
    prompt = PROMPT.format(
        subject=config["subject"]["name"],
        grade=config["grade"],
        domain=domain,
        codes="\n".join(codes),
        text=text,
    )
    source_words = set(words(text))
    for attempt in range(2):
        result = await llm.with_structured_output(ExtractedDomain, method="function_calling").ainvoke(prompt)
        if result is None:
            continue
        got = [s.code.strip().upper() for s in result.slos]
        problems = []
        if sorted(set(got)) != sorted(codes):
            missing = sorted(set(codes) - set(got))
            extra = sorted(set(got) - set(codes))
            problems.append(f"missing {missing} extra {extra}")
        for slo in result.slos:
            # Models sometimes write line breaks as a literal backslash-n
            slo.description = re.sub(r"\s+", " ", slo.description.replace("\\n", " ")).strip()
            slo.content_area = re.sub(r"\s+", " ", slo.content_area.replace("\\n", " ")).strip()
            slo.code = slo.code.strip().upper()
            slo.assessment_form = slo.assessment_form.strip().lower()
            slo.cognitive_levels = sorted(
                {lvl.strip().upper()[:1] for lvl in slo.cognitive_levels} & LEVELS, key="KUA".index
            )
            if problem := check(slo, source_words):
                problems.append(f"{slo.code}: {problem}")
        if not problems:
            return result
        print(f"  domain {domain} attempt {attempt + 1}: {'; '.join(problems)[:500]}")
    return result


async def main() -> None:
    if len(sys.argv) != 3 or sys.argv[1] not in SUBJECTS:
        sys.exit(f"Usage: extract_af_llm.py <{'|'.join(SUBJECTS)}> <af.txt>")
    key, source = sys.argv[1], Path(sys.argv[2])
    config = SUBJECTS[key]
    table = table_text(source.read_text(encoding="utf-8"), config)
    chunks = domain_chunks(table)
    print(f"{sum(len(c) for _, c, _ in chunks)} SLO codes in {len(chunks)} chunks")

    llm = create_chat_model(task=GENERATION, temperature=0)
    results = await asyncio.gather(
        *(extract_chunk(llm, config, domain, codes, text) for domain, codes, text in chunks)
    )

    domains: dict[str, str] = {}
    slos: dict[str, dict] = {}
    problems = 0
    for (domain, codes, text), result in zip(chunks, results):
        if result is None:
            print(f"FAILED domain {domain}: no result")
            problems += 1
            continue
        domains.setdefault(domain, config.get("domain_names", {}).get(domain) or result.domain_name.strip())
        source_words = set(words(text))
        for slo in result.slos:
            if slo.code not in codes or slo.code in slos:
                continue
            if problem := check(slo, source_words):
                print(f"SKIPPED {slo.code}: {problem}")
                problems += 1
                continue
            for wrong, right in config.get("text_fixes", {}).items():
                slo.description = slo.description.replace(wrong, right)
            slos[slo.code] = {
                "code": slo.code,
                "domain": slo.code.split("-")[2],
                "content_area": slo.content_area.strip(),
                "description": re.sub(r"\s+", " ", slo.description).strip(),
                "assessment_form": slo.assessment_form,
                "cognitive_levels": slo.cognitive_levels,
                "periods": None,
            }
        for code in codes:
            if code not in slos:
                print(f"MISSING {code}")
                problems += 1

    # Where an SLO's own row states its assessment type unambiguously, the PDF text
    # wins over the model (it confused "Summative for theory" with PBA)
    overridden = 0
    for code, (form, levels) in row_facts(table).items():
        if code in slos and (slos[code]["assessment_form"], slos[code]["cognitive_levels"]) != (form, levels or slos[code]["cognitive_levels"]):
            slos[code]["assessment_form"] = form
            slos[code]["cognitive_levels"] = levels or slos[code]["cognitive_levels"]
            overridden += 1
    print(f"{overridden} assessment forms/levels taken from the PDF rows instead of the model")

    ordered = sorted(slos.values(), key=lambda s: (s["domain"], int(s["code"].split("-")[3]), s["code"]))
    output = {
        "subject": config["subject"],
        "grade": config["grade"],
        "scheme": "ISS-2024",
        "curriculum": "NCP 2022-23",
        "source_url": FBISE_PAGE,
        "domains": [{"code": code, "name": domains[code]} for code in sorted(domains)],
        "slos": ordered,
    }
    out = DATA_DIR / f"{key}.json"
    out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    forms: dict[str, int] = {}
    for slo in ordered:
        forms[slo["assessment_form"]] = forms.get(slo["assessment_form"], 0) + 1
    print(f"{len(ordered)} SLOs -> {out}; by form {forms}; {problems} problem(s)")
    print("domains:", {d["code"]: d["name"] for d in output["domains"]})


if __name__ == "__main__":
    asyncio.run(main())
