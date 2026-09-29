"""Mind maps whose structure comes from the FBISE syllabus.

- A domain map (e.g. "Mechanics") is built straight from the SLO tree: domain →
  content areas → SLOs. No AI, so it is instant and always matches FBISE.
- A topic map (e.g. "vector product") has one branch per matching SLO; the AI only
  fills in 3-5 key points per branch.

Both return map_data in the format the mind map viewer reads: nodes and edges,
where node data carries label, content and (for SLO branches) slo_code and form.
"""

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field

from edu_ai.agents.slo_context import GRADE_LABELS, language_name
from edu_ai.latex import clean_latex_deep
from edu_ai.prompts.prompts_utils import render_prompt


class MapPoint(BaseModel):
    label: str = Field(..., description="At most 8 words; may contain a short $formula$")
    detail: str = Field(..., description="1-3 sentences explaining the point")


class MapBranch(BaseModel):
    slo_code: str = Field(..., description="The SLO code this branch covers")
    title: str = Field(..., description="Short branch title, at most 5 words")
    points: list[MapPoint] = Field(..., description="3-5 key points")


class SloMindMap(BaseModel):
    title: str = Field(..., description="Title of the whole map, at most 6 words")
    summary: str = Field(..., description="One-sentence summary")
    branches: list[MapBranch]


class _Builder:
    def __init__(self) -> None:
        self.nodes: list[dict] = []
        self.edges: list[dict] = []

    def add(self, label: str, parent: str | None = None, **data) -> str:
        node_id = f"n{len(self.nodes)}"
        self.nodes.append(
            {"id": node_id, "position": {"x": 0, "y": 0}, "data": {"label": label, **data}}
        )
        if parent:
            self.edges.append({"id": f"e{len(self.edges)}", "source": parent, "target": node_id})
        return node_id

    def map_data(self) -> dict:
        return {"nodes": self.nodes, "edges": self.edges}


def short(text: str, words: int = 9) -> str:
    parts = text.split()
    return " ".join(parts[:words]) + ("…" if len(parts) > words else "")


def domain_map(subject: str, grade: int, domain: dict, slos: list[dict]) -> tuple[str, str, dict]:
    """Domain → content areas → SLOs, straight from the syllabus.

    domain: {code, name}; slos: [{code, description, content_area, assessment_form}] in order.
    """
    builder = _Builder()
    title = f"{domain['name']} ({subject} {GRADE_LABELS.get(grade, grade)})"
    root = builder.add(domain["name"], content=f"Domain {domain['code']} of the FBISE {subject} syllabus")
    areas: dict[str, str] = {}
    for slo in slos:
        area = slo.get("content_area") or domain["name"]
        if area not in areas:
            areas[area] = builder.add(area, root)
        builder.add(
            f"{slo['code']}: {short(slo['description'])}",
            areas[area],
            content=slo["description"],
            slo_code=slo["code"],
            form=slo["assessment_form"],
        )
    description = f"{len(slos)} SLOs in {len(areas)} topics, from the FBISE Assessment Framework"
    return title, description, builder.map_data()


async def topic_map(
    llm: BaseChatModel,
    topic: str,
    subject: str,
    grade: int,
    slos: list[dict],
    language_code: str,
    detail: str = "standard",
    include: list[str] | None = None,
    notes: str | None = None,
) -> tuple[str, str, dict]:
    """One branch per SLO; the AI writes each branch's key points.

    detail: "quick" (2-3 points per SLO), "standard" (3-5) or "detailed" (5-7);
    include: what the student wants in the points, e.g. formulas, derivations, exam tips.
    """
    points = {"quick": "2 to 3", "detailed": "5 to 7"}.get(detail, "3 to 5")
    prompt = render_prompt(
        "mind_map_slo_prompt",
        topic=topic,
        subject=subject,
        grade_label=GRADE_LABELS.get(grade, f"Grade {grade}"),
        slos=slos,
        language_name=language_name(language_code),
        points=points,
        include=", ".join(include or []),
        notes=(notes or "").strip()[:300],
    )
    result = await llm.with_structured_output(SloMindMap, method="function_calling").ainvoke(prompt)
    if result is None or not result.branches:
        raise ValueError("The AI returned no mind map")
    result = SloMindMap(**clean_latex_deep(result.model_dump()))

    by_code = {slo["code"]: slo for slo in slos}
    builder = _Builder()
    root = builder.add(result.title, content=result.summary)
    for branch in result.branches:
        slo = by_code.get(branch.slo_code.strip().upper())
        branch_id = builder.add(
            branch.title,
            root,
            content=slo["description"] if slo else None,
            slo_code=slo["code"] if slo else None,
            form=slo["assessment_form"] if slo else None,
        )
        for point in branch.points:
            builder.add(point.label, branch_id, content=point.detail)
    return result.title, result.summary, builder.map_data()
