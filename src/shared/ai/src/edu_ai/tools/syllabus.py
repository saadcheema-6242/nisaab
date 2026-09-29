"""FBISE syllabus lookup for the tutor: find the SLOs that match a topic."""

import asyncio
import math
import re
from functools import lru_cache

from edu_ai.chatbot.context import ChatbotContext
from edu_db.models import ContentItem, CurriculumDomain, Slo
from edu_db.session import get_session_factory
from langchain.tools import tool
from langgraph.prebuilt import ToolRuntime

FORMS = {
    "summative": "examined in the annual paper",
    "formative": "classroom only, not examined",
    "practical": "practical exam only",
}
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "in", "is",
    "it", "of", "on", "or", "the", "to", "what", "when", "which", "why", "with",
}
CODE = re.compile(r"\b([A-Z]{1,3}-\d{2}-[A-Z]-\d{1,2}|[A-Z]-\d{1,2})\b", re.IGNORECASE)


@lru_cache(maxsize=32)
def _load_slos(grade_subject_id: str) -> tuple[dict, ...]:
    """SLOs of one grade subject (they only change when the curriculum is re-seeded)."""
    with get_session_factory()() as db:
        rows = (
            db.query(Slo, CurriculumDomain.name)
            .join(CurriculumDomain, Slo.domain_id == CurriculumDomain.id)
            .filter(Slo.grade_subject_id == grade_subject_id)
            .order_by(Slo.sort_order)
            .all()
        )
        return tuple(
            {
                "code": slo.code,
                "domain": domain,
                "content_area": slo.content_area or "",
                "description": slo.description,
                "assessment_form": slo.assessment_form,
                "cognitive_levels": list(slo.cognitive_levels or []),
            }
            for slo, domain in rows
        )


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS}


def _matches(word: str, words: set[str]) -> float:
    if word in words:
        return 1.0
    # projectile / projectiles, derive / derivation
    if len(word) >= 5 and any(w.startswith(word[:5]) for w in words):
        return 0.5
    return 0.0


def search_slos(grade_subject_id: str, query: str, limit: int = 5) -> list[dict]:
    """Rank the SLOs of a grade subject against a query.

    Each query word counts by how rare it is in the syllabus (so "projectile"
    matters more than "effect"), and an SLO must cover at least half of the
    query's weight to be returned.
    """
    slos = _load_slos(grade_subject_id)
    codes = [c.upper() for c in CODE.findall(query)]
    exact = [
        slo
        for slo in slos
        if any(slo["code"].upper() == c or slo["code"].upper().endswith("-" + c) for c in codes)
    ]
    if exact:
        return exact[:limit]

    words = _words(CODE.sub(" ", query))
    if not words:
        return []
    texts = [
        _words(f"{slo['description']} {slo['content_area']} {slo['domain']}") for slo in slos
    ]
    weights = {
        word: math.log((len(slos) + 1) / (sum(1 for t in texts if _matches(word, t)) + 1)) + 1
        for word in words
    }
    total = sum(weights.values())
    scored = []
    for slo, text in zip(slos, texts):
        score = sum(weight * _matches(word, text) for word, weight in weights.items())
        if score >= total / 2:
            scored.append((score, slo))
    scored.sort(key=lambda pair: -pair[0])
    return [slo for _, slo in scored[:limit]]


def resolve_slos(
    grade_subject_id: str, topic: str, chosen: list[str] | None = None, limit: int = 6
) -> list[str]:
    """The SLO codes the student chose (e.g. "P-11-B-02: Describe ..." or "B-02"), or
    else the best syllabus match for the topic. Unknown codes are dropped."""
    known = [slo["code"] for slo in _load_slos(grade_subject_id)]
    codes: list[str] = []
    for text in chosen or []:
        for found in CODE.findall(text or ""):
            found = found.upper()
            match = next(
                (c for c in known if c.upper() == found or c.upper().endswith("-" + found)), None
            )
            if match and match not in codes:
                codes.append(match)
    if codes:
        return codes[:limit]
    matches = search_slos(grade_subject_id, topic, limit=1)
    return [matches[0]["code"]] if matches else []


def slo_choices(grade_subject_id: str, topic: str, limit: int = 5) -> list[dict]:
    """The SLOs a topic covers, for a "which part?" question: the best matches plus the
    other SLOs of the best match's content area. [{code, description, domain, content_area}]"""
    slos = _load_slos(grade_subject_id)
    matches = search_slos(grade_subject_id, topic, limit=limit)
    if not matches:
        return []
    chosen = [m["code"] for m in matches]
    area = matches[0]["content_area"]
    for slo in slos:
        if len(chosen) >= limit:
            break
        if slo["content_area"] == area and slo["code"] not in chosen:
            chosen.append(slo["code"])
    order = {slo["code"]: i for i, slo in enumerate(slos)}
    by_code = {slo["code"]: slo for slo in slos}
    return [by_code[code] for code in sorted(chosen, key=lambda c: order[c])]


def approved_explainer(grade_subject_id: str, slo_code: str) -> str | None:
    """A teacher-approved explainer for the SLO, if there is one."""
    with get_session_factory()() as db:
        item = (
            db.query(ContentItem)
            .filter(
                ContentItem.grade_subject_id == grade_subject_id,
                ContentItem.slo_code == slo_code,
                ContentItem.kind == "explainer",
                ContentItem.review_status == "approved",
            )
            .first()
        )
        return item.payload.get("content") if item else None


@tool(
    "find_syllabus_slos",
    description=(
        "Find the FBISE syllabus learning outcomes (SLOs) of the student's subject that "
        "match a topic, e.g. 'projectile range' or 'P-11-B-05'. Use English physics/chemistry/"
        "biology/maths keywords. Use it to cite the exact SLO code and to check whether a topic "
        "is in the FSc syllabus and whether it is examined."
    ),
)
async def find_syllabus_slos(query: str, runtime: ToolRuntime[ChatbotContext]) -> str:
    """Return matching SLOs as text for the tutor."""
    fbise = runtime.context.fbise
    if not fbise or not fbise.has_slos:
        return "No FBISE SLO list is available for this workspace yet."

    matches = await asyncio.to_thread(search_slos, fbise.grade_subject_id, query)
    if not matches:
        return (
            f"No {fbise.subject} {fbise.grade_label} SLO matches '{query}'. "
            "The topic may be outside this year's FSc syllabus; try other keywords once."
        )
    lines = []
    for slo in matches:
        area = slo["content_area"] or slo["domain"]
        levels = "/".join(slo["cognitive_levels"]) or "-"
        form = FORMS.get(slo["assessment_form"], slo["assessment_form"])
        lines.append(
            f"- SLO {slo['code']} ({area}; {form}; level {levels}): {slo['description'][:600]}"
        )
    result = f"Matching {fbise.subject} {fbise.grade_label} SLOs:\n" + "\n".join(lines)
    explainer = await asyncio.to_thread(
        approved_explainer, fbise.grade_subject_id, matches[0]["code"]
    )
    if explainer:
        result += (
            f"\n\nTeacher-reviewed explainer for SLO {matches[0]['code']} "
            f"(prefer its facts and notation):\n{explainer[:2500]}"
        )
    return result


tools = [find_syllabus_slos]
