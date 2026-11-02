"""Make the student a study plan, from the chat.

Two ways to ask, and they mean different things:

- a topic ("make me a plan for projectile motion, two weeks, 3 hours a day"),
  which teaches that topic from the syllabus and never looks at the student's
  practice record;
- their weak areas ("plan around what I'm bad at"), which covers everything
  their practice says they are weak at, across the whole syllabus.

Which one is asked rather than guessed. Guessing from whether a topic happened
to be mentioned produced plans that answered a question the student had not
asked - a plan on data science that opened by reporting they had no practice
records, and a plan on "my weak areas" narrowed to one chapter.

Plain typed arguments, not an object: a dict argument becomes a schema with no
properties and Gemini rejects a function declared that way, which would take
down every turn in the chat rather than only the ones wanting a plan.
"""

import json

from edu_core.services.study_plans import StudyPlanService
from langchain.tools import ToolRuntime, tool

from edu_ai.chatbot.context import ChatbotContext


@tool(
    "make_study_plan",
    description=(
        "Write the student a day-by-day study plan and show it in the chat. "
        "Use it when they ask for a plan, a timetable, a revision schedule, or "
        "how to prepare in the time they have left. "
        "\n"
        "Before calling it, you must know which of two plans they want, and "
        "ask in one short question if they have not said: a plan on a topic "
        "they choose, or a plan on the weak areas their practice results show. "
        "Do not decide for them. "
        "\n"
        "mode is 'topic' or 'weak'. "
        "With mode='topic', topic is what to plan around - a chapter, a topic "
        "or an FBISE outcome code - and the plan covers that topic only. It "
        "does not look at their practice results, so never say anything about "
        "their scores or weak areas in a topic plan. "
        "With mode='weak', leave topic empty: the plan covers every outcome "
        "they are weak at, worked out from their own practice results, not "
        "guessed. "
        "\n"
        "days is how long the plan runs; hours_per_day is how long they can "
        "study each day. Ask for whichever of those they have not said, rather "
        "than inventing one. A long plan goes over the same outcomes several "
        "times with harder work, so asking for thirty days gives thirty days. "
        "\n"
        "specifications is anything else they said about how they study, in "
        "their own words - 'only at weekends', 'school until 2pm', 'exams in "
        "three weeks', 'I want more past papers'. Pass it through; do not "
        "tidy it up. "
        "\n"
        "Every step names the outcome it practises and what counts as done, so "
        "do not describe the plan again afterwards - it is shown to them."
    ),
    return_direct=True,
)
async def make_study_plan(
    runtime: ToolRuntime[ChatbotContext],
    mode: str = "",
    topic: str = "",
    days: int = 0,
    hours_per_day: float = 0.0,
    specifications: str = "",
) -> str:
    """Build the plan and hand it back for the chat to show."""
    # Not metered yet. Every other generated thing has its own column on the
    # usage row, and a study plan would need one too plus a migration; counting
    # it as something else would make the student's quota read wrongly. The
    # chat message that asks for it is already counted.
    ctx = runtime.context

    try:
        plan = await StudyPlanService().generate_study_plan(
            user_id=ctx.user_id,
            project_id=ctx.project_id,
            topic=topic.strip() or None,
            days=days or None,
            hours_per_day=hours_per_day or None,
            specifications=specifications.strip() or None,
            mode=mode.strip() or None,
        )
    except Exception as error:  # noqa: BLE001 - a failed plan must not end the chat
        print(f"make_study_plan failed: {type(error).__name__}: {error}")
        return json.dumps(
            {
                "message": (
                    f"The study plan could not be made ({error}). Say so plainly "
                    "and offer to try a smaller topic or a shorter period."
                )
            }
        )

    content = plan.content
    items = content.items if hasattr(content, "items") else []
    if not items:
        return json.dumps(
            {
                "type": "study_plan",
                "study_plan_id": plan.id,
                "message": (
                    "There was nothing to plan: on this scope the student has no "
                    "weak outcomes recorded. Say so, and offer either a plan on "
                    "a topic they name or some practice first so there is "
                    "something to work from."
                ),
            }
        )

    days_used = max(item.day for item in items)
    return json.dumps(
        {
            "type": "study_plan",
            "study_plan_id": plan.id,
            "days": days_used,
            "steps": len(items),
            "minutes": sum(item.minutes for item in items),
            "focus": content.focus_areas[:6],
            "message": (
                f"The plan is now shown in the chat: {len(items)} steps over "
                f"{days_used} days. The student can see it, so do not list it "
                "again - say one short sentence about what it concentrates on."
            ),
        }
    )


tools = [make_study_plan]
