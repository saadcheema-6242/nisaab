"""Generate shared, reviewable content for one SLO: an explainer and MCQs.

SRQs for the bank use ``srq_agent.generate_srq``. Bank content is written in
English (the language of the FSc paper) so one reviewed copy serves everyone.
"""

from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field

from edu_ai.agents.quiz_agent import QuizGenerationResult, _cognitive_level
from edu_ai.agents.slo_context import SloContext, language_name
from edu_ai.latex import clean_latex_deep
from edu_ai.prompts.prompts_utils import render_prompt


class Explainer(BaseModel):
    title: str = Field(..., description="'SLO <code>: <short topic>'")
    content: str = Field(..., description="The explainer in Markdown with LaTeX")


async def generate_explainer(llm: BaseChatModel, slo: SloContext) -> Explainer:
    prompt = render_prompt("slo_explainer_prompt", **slo.prompt_vars())
    result = await llm.with_structured_output(Explainer, method="function_calling").ainvoke(prompt)
    if result is None or not result.content.strip():
        raise ValueError(f"No explainer returned for {slo.code}")
    return Explainer(**clean_latex_deep(result.model_dump()))


async def generate_mcqs(
    llm: BaseChatModel,
    slo: SloContext,
    count: int,
    difficulty: str = "mixed",
    language_code: str = "en",
    instructions: str = "",
) -> list[dict]:
    """MCQs for one SLO (not saved). The bank uses English explanations; practice passes
    the student's language, level and question type."""
    prompt = render_prompt(
        "quiz_slo_prompt",
        **slo.prompt_vars(),
        count=count,
        difficulty=difficulty,
        language_name=language_name(language_code),
        custom_instructions=instructions,
        document_content="(none)",
        format_instructions="",
    )
    result = await llm.with_structured_output(
        QuizGenerationResult, method="function_calling"
    ).ainvoke(prompt)
    if result is None or not result.questions:
        raise ValueError(f"No MCQs returned for {slo.code}")
    return clean_latex_deep([
        {
            "question_text": q.question_text,
            "option_a": q.option_a,
            "option_b": q.option_b,
            "option_c": q.option_c,
            "option_d": q.option_d,
            "correct_option": q.correct_option.strip().lower()[:1],
            "explanation": q.explanation,
            "difficulty_level": q.difficulty_level,
            "cognitive_level": _cognitive_level(q.cognitive_level),
        }
        for q in result.questions
        if q.correct_option.strip().lower()[:1] in ("a", "b", "c", "d")
    ])


class StimulusSet(BaseModel):
    """A scenario with four MCQs that use it (FBISE's new Section A)."""

    scenario: str = Field(..., description="The stimulus: scenario, data or code (Markdown with LaTeX)")
    questions: list[QuizQuestionGenerationResult] = Field(..., description="Exactly 4 MCQs on the stimulus")


async def generate_stimulus_set(
    llm: BaseChatModel, slo: SloContext, language_code: str = "en"
) -> dict:
    """One stimulus-based MCQ set for an SLO: {"scenario", "questions": [4 MCQ payloads]}."""
    prompt = render_prompt(
        "stimulus_prompt", **slo.prompt_vars(), language_name=language_name(language_code)
    )
    result = await llm.with_structured_output(StimulusSet, method="function_calling").ainvoke(prompt)
    if result is None or not result.scenario.strip() or len(result.questions) < 4:
        raise ValueError(f"No stimulus set returned for {slo.code}")
    questions = [
        {
            "question_text": q.question_text,
            "option_a": q.option_a,
            "option_b": q.option_b,
            "option_c": q.option_c,
            "option_d": q.option_d,
            "correct_option": q.correct_option.strip().lower()[:1],
            "explanation": q.explanation,
            "difficulty_level": q.difficulty_level,
            "cognitive_level": _cognitive_level(q.cognitive_level),
        }
        for q in result.questions[:4]
        if q.correct_option.strip().lower()[:1] in ("a", "b", "c", "d")
    ]
    if len(questions) < 4:
        raise ValueError(f"Stimulus set for {slo.code} has fewer than 4 usable MCQs")
    return clean_latex_deep({"scenario": result.scenario, "questions": questions})
