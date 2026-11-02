"""Check that the tutor is told to stop when it starts going round in circles.

Run with:
    python scripts/admin/check_tool_loops.py

A student asked for a picture of computer architecture and watched "Checked
the FBISE syllabus" five times over three minutes before a word was written.
Each of those is a full round trip to the model, so a loop costs the student
the answer, not just the wait.

Checked here with stand-in messages rather than a real agent, because the rule
is about the shape of a conversation and nothing else. The defensive reading
matters as much as the counting: a guard that crashes the turn it meant to
shorten would be worse than no guard, so every odd message shape is tried.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/shared/core/src"))

from edu_core.tool_loops import (  # noqa: E402
    MAX_SAME_TOOL,
    calls_since_student,
    loop_note,
)

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  -- {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


class Said:
    """A message, shaped the way the agent's history holds one."""

    def __init__(self, type_: str, tool_calls=None):
        self.type = type_
        if tool_calls is not None:
            self.tool_calls = tool_calls


def human(text: str = "") -> Said:
    return Said("human")


def called(tool: str, **args) -> Said:
    return Said("ai", [{"name": tool, "args": args, "id": f"c-{tool}-{len(args)}"}])


SYLLABUS = "find_syllabus_slos"

print("calls are counted only for the question being answered")
history = [
    human(),
    called(SYLLABUS, query="vectors"),
    Said("tool"),
    Said("ai"),
    human(),  # the student asked something new
    called(SYLLABUS, query="computer architecture"),
    Said("tool"),
    called(SYLLABUS, query="von neumann"),
]
calls = calls_since_student(history, SYLLABUS)
check("only this turn's calls are counted", len(calls) == 2, str(calls))
check("the newest is first", calls[0] == {"query": "von neumann"}, str(calls[0]))
check("an earlier turn's identical call is not held against it",
      {"query": "vectors"} not in calls, str(calls))
check("another tool's calls are not counted",
      calls_since_student(history, "search_project_documents") == [], "")

print()
print("the same call twice is answered, not run a third time")
twice = [human(), called(SYLLABUS, query="von neumann"), Said("tool"),
         called(SYLLABUS, query="von neumann")]
note = loop_note(SYLLABUS, calls_since_student(twice, SYLLABUS))
check("there is a note", note is not None)
check("it says the answer is already there", "already called" in (note or ""), note or "")
check("it tells the model to write the answer",
      "Write the student's answer now" in (note or ""), note or "")
check("it names the tool, so the model knows which one", SYLLABUS in (note or ""))

print()
print("a few different searches are allowed - that is narrowing, not looping")
for count in (1, 2, 3):
    narrowing = [human()] + [called(SYLLABUS, query=f"try {i}") for i in range(count)]
    said = loop_note(SYLLABUS, calls_since_student(narrowing, SYLLABUS))
    check(f"{count} different call(s): left alone", said is None, said or "")

print()
print("but a fourth is a loop, and is stopped")
for count in (MAX_SAME_TOOL + 1, 5, 9):
    looping = [human()] + [called(SYLLABUS, query=f"try {i}") for i in range(count)]
    said = loop_note(SYLLABUS, calls_since_student(looping, SYLLABUS))
    check(f"{count} different calls: told to stop", said is not None)
    check(f"{count}: it says how many times", str(count) in (said or ""), said or "")
    check(f"{count}: it allows an honest gap",
          "say plainly if something is missing" in (said or ""), said or "")

# The student's own turn, as it happened
five = [human()] + [called(SYLLABUS, query=f"architecture {i}") for i in range(5)]
check("the five searches the student sat through would now be stopped",
      loop_note(SYLLABUS, calls_since_student(five, SYLLABUS)) is not None)

print()
print("nothing here can crash a turn")
for name, messages in (
    ("no messages", []),
    ("none at all", None),
    ("plain strings", ["hello", "there"]),
    ("objects with no type", [object(), object()]),
    ("tool_calls that is not a list", [Said("ai", "not a list")]),
    ("tool_calls of non-dicts", [Said("ai", ["nope", 7, None])]),
    ("a call with no name", [Said("ai", [{"args": {}}])]),
    ("a call whose args are not a dict", [Said("ai", [{"name": SYLLABUS, "args": "x"}])]),
    ("a call with no args at all", [Said("ai", [{"name": SYLLABUS}])]),
):
    try:
        got = calls_since_student(messages, SYLLABUS)  # type: ignore[arg-type]
        check(f"{name}: read without raising", isinstance(got, list), str(got))
    except Exception as error:  # noqa: BLE001
        check(f"{name}: read without raising", False, f"{type(error).__name__}: {error}")

odd = calls_since_student([Said("ai", [{"name": SYLLABUS, "args": "x"}])], SYLLABUS)
check("a call with unreadable args still counts as a call", len(odd) == 1, str(odd))
check("and is read as empty rather than dropped", odd == [{}], str(odd))

print()
print("a single call is never nagged")
for messages in ([human(), called(SYLLABUS, query="one")], [called(SYLLABUS, query="one")]):
    check("one call, nothing said",
          loop_note(SYLLABUS, calls_since_student(messages, SYLLABUS)) is None)
check("no calls, nothing said", loop_note(SYLLABUS, []) is None)

print()
print("the guard is wired into the agent")
factory = (ROOT / "src/shared/ai/src/edu_ai/chatbot/factory.py").read_text(encoding="utf-8")
check("the middleware exists", "async def stop_repeating_yourself" in factory)
check("it is registered", "stop_repeating_yourself,\n" in factory)
check("it uses the checked rule rather than its own copy",
      "from edu_core.tool_loops import calls_since_student, loop_note" in factory)
check("it adds to the tool's result rather than replacing it",
      'f"{result.content}\\n\\n{note}"' in factory)
check("and it can never take a turn down",
      "with suppress(Exception):" in factory)

print()
print("the picture finder knows the figure drawer exists")
diagram = (ROOT / "src/shared/ai/src/edu_ai/tools/diagram.py").read_text(encoding="utf-8")
check("a failed search points at draw_figure", "draw_figure" in diagram)
check("and only for things that can be drawn",
      "drawn from life" in diagram, "")
check("both failure paths say it", diagram.count("_OR_DRAW") >= 3, str(diagram.count("_OR_DRAW")))

print()
if failures:
    print(f"{len(failures)} failed: " + ", ".join(failures))
    sys.exit(1)
print("all checks passed")
