"""Fix words that PDF extraction glued together in SLO descriptions ("orquotients").

Gemini proposes corrected spacing; a change is accepted only when the text is
identical apart from whitespace, so FBISE's wording can never be rewritten.

Usage (from the repository root, with an AI provider configured in .env):
    uv run --package edu-worker python scripts/seed/clean_descriptions.py physics-xi
"""

import json
import re
import sys
from pathlib import Path

from edu_ai.llm import GENERATION, create_chat_model
from pydantic import BaseModel, Field

DATA_DIR = Path(__file__).resolve().parent / "data"
BATCH_SIZE = 25

PROMPT = """These SLO descriptions were extracted from a PDF. Some words are glued together
(e.g. "orquotients" should be "or quotients", "ofthermodynamics" should be "of thermodynamics").
Return every description with ONLY the spacing fixed: split glued words and fix doubled spaces.
Do not change, add, remove or reorder any other characters. Keep formulas exactly as they are.

{items}"""


class Fixed(BaseModel):
    code: str
    description: str = Field(description="The description with only whitespace corrected")


class FixedBatch(BaseModel):
    items: list[Fixed]


def letters(text: str) -> str:
    return re.sub(r"\s+", "", text)


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: clean_descriptions.py <subject-key>")
    path = DATA_DIR / f"{sys.argv[1]}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    llm = create_chat_model(task=GENERATION, temperature=0).with_structured_output(
        FixedBatch, method="function_calling"
    )

    slos = data["slos"]
    by_code = {slo["code"]: slo for slo in slos}
    changed = rejected = 0
    for start in range(0, len(slos), BATCH_SIZE):
        batch = slos[start : start + BATCH_SIZE]
        items = "\n".join(f"{s['code']}: {s['description']}" for s in batch)
        result = llm.invoke(PROMPT.format(items=items))
        for fixed in result.items if result else []:
            slo = by_code.get(fixed.code)
            if not slo or fixed.description == slo["description"]:
                continue
            if letters(fixed.description) == letters(slo["description"]):
                print(f"fixed   {slo['code']}: {fixed.description[:90]}")
                slo["description"] = fixed.description
                changed += 1
            else:
                print(f"REJECT  {slo['code']}: change was more than spacing")
                rejected += 1

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{changed} descriptions fixed, {rejected} rejected -> {path}")


if __name__ == "__main__":
    main()
