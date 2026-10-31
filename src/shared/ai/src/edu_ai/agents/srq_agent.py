"""Short-response questions (SRQs): generate one for an SLO, and mark a written answer.

Marking follows FBISE practice: the examiner awards marks per rubric point, so the
model judges each point separately and the total is added up in code (clamped to
each point's marks), never taken from the model.
"""

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field

from edu_ai.agents.slo_context import SloContext, language_name
from edu_ai.latex import clean_latex_deep
from edu_ai.prompts.prompts_utils import render_prompt


class RubricPoint(BaseModel):
    point: str = Field(..., description="What the answer must contain for this mark, e.g. 'States R = v^2 sin2θ / g'")
    marks: int = Field(..., description="Marks for this point, usually 1")


class GeneratedSrq(BaseModel):
    question: str = Field(..., description="The SRQ text, with LaTeX in $...$ for maths")
    marks: int = Field(..., description="Total marks, 3 or 4")
    model_answer: str = Field(..., description="A full-marks answer as a strong student would write it")
    rubric: list[RubricPoint] = Field(..., description="Marking points; their marks add up to the total")
    cognitive_level: str = Field(..., description="K, U or A")


class PointMark(BaseModel):
    point: str = Field(..., description="The rubric point, copied exactly")
    awarded: float = Field(..., description="Marks awarded for this point (0, 0.5 or up to its marks)")
    comment: str = Field(..., description="One short sentence: what the student wrote or missed for this point")


class SrqMarking(BaseModel):
    points: list[PointMark] = Field(..., description="One entry per rubric point, in order")
    feedback: str = Field(..., description="Two or three sentences: what was good and how to get full marks")


async def generate_srq(
    llm: BaseChatModel,
    slo: SloContext,
    language_code: str,
    long: bool = False,
    marks: int | None = None,
    parts: bool = True,
    level: str | None = None,
) -> GeneratedSrq:
    """A short question (SRQ, 3-4 marks) or, with long=True, an extended one (ERQ, 6 marks).

    marks asks for an exact total (e.g. 4 for Section B of the new FBISE paper, 6 or 8
    for Section C) and parts=False for one straight question without (a) and (b).

    level (K, U or A) asks for a cognitive level. A paper decides its levels in
    advance to hit the framework's weighting, so without this the model picks
    the level itself and the paper ends up almost entirely application.
    """
    prompt = render_prompt(
        "srq_generate_prompt",
        **slo.prompt_vars(),
        language_name=language_name(language_code),
        long=long,
        marks=marks,
        parts=parts,
        level=level,
    )
    for attempt in range(2):
        result = await llm.with_structured_output(GeneratedSrq, method="function_calling").ainvoke(prompt)
        if result is None:
            raise ValueError("The AI returned no question")
        result = GeneratedSrq(**clean_latex_deep(result.model_dump()))
        # Whole-mark points only, and a total that matches the rubric the examiner uses
        result.rubric = [p for p in result.rubric if p.marks >= 1 and p.point.strip()]
        if not result.rubric:
            raise ValueError("The AI returned no usable marking rubric")
        result.marks = sum(p.marks for p in result.rubric)
        if marks is None or result.marks == marks or attempt == 1:
            break
    if marks is not None and result.marks > marks:
        # Keep the first points that make up the asked total
        kept, total = [], 0
        for point in result.rubric:
            if total + point.marks <= marks:
                kept.append(point)
                total += point.marks
        result.rubric, result.marks = kept, total
    return result


async def mark_srq(
    llm: BaseChatModel,
    *,
    question: str,
    marks: int,
    rubric: list[dict],
    model_answer: str,
    answer: str,
    slo: SloContext | None,
    language_code: str,
) -> tuple[float, dict]:
    """Return (awarded marks, result) where result has points, feedback and missing points."""
    prompt = render_prompt(
        "srq_mark_prompt",
        question=question,
        marks=marks,
        rubric=rubric,
        model_answer=model_answer,
        answer=answer,
        slo=slo.model_dump() if slo else None,
        language_name=language_name(language_code),
    )
    marking = await llm.with_structured_output(SrqMarking, method="function_calling").ainvoke(prompt)
    if marking is None:
        raise ValueError("The AI returned no marking")
    marking = SrqMarking(**clean_latex_deep(marking.model_dump()))

    points = []
    for index, item in enumerate(rubric):
        judged = marking.points[index] if index < len(marking.points) else None
        available = float(item.get("marks", 1))
        awarded = min(max(judged.awarded, 0.0), available) if judged else 0.0
        points.append(
            {
                "point": item.get("point", ""),
                "marks": available,
                "awarded": round(awarded * 2) / 2,  # FBISE awards whole or half marks
                "comment": judged.comment if judged else "",
            }
        )
    total = min(sum(p["awarded"] for p in points), float(marks))
    missing = [p["point"] for p in points if p["awarded"] < p["marks"]]
    return total, {"points": points, "feedback": marking.feedback, "missing": missing}
