"""Check how a drawn figure is asked for and read back, with no network.

Run with:
    python scripts/admin/check_code_run.py

A student asked for a graph of their own vector question and got ASCII art,
because nothing in the app could draw a figure that did not already exist in
Wikimedia Commons. Figures are now drawn by running real code in Google's
sandbox, which means two things have to be right and neither of them can be
checked by looking at the picture: the rules the model is given, and the
reading of what comes back.

The reading is the dangerous half. Google's own documentation shows camelCase
field names in its REST examples and snake_case in its chat examples, so a
reader that trusted one spelling would come back with no picture, no error,
and nothing to say why. Both spellings are checked here.
"""

import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/shared/core/src"))

from edu_core.code_run import (  # noqa: E402
    FIGURE_RULES,
    SANDBOX_SECONDS,
    CodeRun,
    figure_prompt,
    read_parts,
)

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  -- {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


PNG = b"\x89PNG\r\n\x1a\n" + b"a tiny pretend picture"
ENCODED = base64.b64encode(PNG).decode()


def camel(picture: bool = True) -> list[dict]:
    """A reply shaped the way the REST examples show it."""
    parts: list[dict] = [
        {"text": "Here is the velocity-time graph."},
        {"executableCode": {"language": "PYTHON", "code": "import matplotlib"}},
        {"codeExecutionResult": {"outcome": "OUTCOME_OK", "output": "done\n"}},
    ]
    if picture:
        parts.append({"inlineData": {"mimeType": "image/png", "data": ENCODED}})
    return parts


def snake(picture: bool = True) -> list[dict]:
    """The same reply, spelled the way the chat examples show it."""
    parts: list[dict] = [
        {"text": "Here is the velocity-time graph."},
        {"executable_code": {"language": "PYTHON", "code": "import matplotlib"}},
        {"code_execution_result": {"outcome": "OUTCOME_OK", "output": "done\n"}},
    ]
    if picture:
        parts.append({"inline_data": {"mime_type": "image/png", "data": ENCODED}})
    return parts


print("a reply is read whichever way Google spelled it")
for name, parts in (("camelCase", camel()), ("snake_case", snake())):
    run = read_parts(parts)
    check(f"{name}: the picture comes back", run.pictures == [PNG], str(len(run.pictures)))
    check(f"{name}: the words come back", "velocity-time" in run.text, run.text)
    check(f"{name}: the code it ran comes back", "matplotlib" in run.code, run.code)
    check(f"{name}: the outcome is read", run.outcome == "OUTCOME_OK", run.outcome)
    check(f"{name}: it is not reported as a failure", not run.failed)
    check(f"{name}: it knows it drew something", run.drew_something)

print()
print("a reply with no picture in it is not mistaken for one")
nothing = read_parts(
    [
        {"text": "I cannot draw that."},
        {"codeExecutionResult": {"outcome": "OUTCOME_FAILED", "output": "NameError"}},
    ]
)
check("no picture is reported", not nothing.drew_something)
check("the failure is visible", nothing.failed, nothing.outcome)
check("the sandbox's own message is kept, so the log says why",
      "NameError" in nothing.output, nothing.output)

answered_in_words = read_parts([{"text": "A graph would show a straight line."}])
check("a model that answered in words drew nothing",
      not answered_in_words.drew_something)
check("and that is not called a code failure", not answered_in_words.failed,
      answered_in_words.outcome)

print()
print("a malformed reply does not take the turn down")
for name, parts in (
    ("empty", []),
    ("none", None),
    ("not dicts", ["text", 42, None]),
    ("unknown fields only", [{"somethingNew": {"a": 1}}]),
    ("picture that will not decode", [{"inlineData": {"mimeType": "image/png", "data": "not base64!!"}}]),
    ("picture with no type", [{"inlineData": {"data": ENCODED}}]),
    ("a pdf, which is not a picture", [{"inlineData": {"mimeType": "application/pdf", "data": ENCODED}}]),
):
    try:
        run = read_parts(parts)  # type: ignore[arg-type]
        check(f"{name}: read without raising, and drew nothing", not run.drew_something)
    except Exception as error:  # noqa: BLE001
        check(f"{name}: read without raising", False, f"{type(error).__name__}: {error}")

mixed = read_parts(
    [{"somethingNew": {"a": 1}}, {"inlineData": {"mimeType": "image/png", "data": ENCODED}}]
)
check("a field we do not know about does not lose the picture beside it",
      mixed.pictures == [PNG])

two = read_parts(camel() + [{"inlineData": {"mimeType": "image/png", "data": ENCODED}}])
check("two pictures both come back, newest last", len(two.pictures) == 2, str(len(two.pictures)))

print()
print("an empty run is an empty run, not a failure")
blank = CodeRun()
check("nothing drawn", not blank.drew_something)
check("and nothing failed", not blank.failed)

print()
print("the model is told the things that make a figure usable in an exam")
prompt = figure_prompt(
    "velocity-time graph for a body accelerating from rest",
    subject="Physics",
    given="a = 2 m s^-2 for 5 s, then constant",
)
for rule, why in (
    ("plt.show()", "without it nothing comes back at all"),
    ("SI unit", "an unlabelled axis is worth no marks"),
    ("Never invent", "an invented reading is worse than no figure"),
    ("set_aspect", "angles are a lie without it"),
    ("legend", "more than one series needs one"),
    ("dpi=150", "it is read on a phone"),
    ("arrowheads", "a vector without one is a line"),
):
    check(f"it is told about {rule!r} - {why}", rule in prompt, prompt[:200])

check("it is told the sandbox's time limit", str(SANDBOX_SECONDS) in prompt)
check("it is told it has no internet", "no internet" in prompt)
check("it is sent what to draw", "velocity-time graph" in prompt)
check("the subject reaches it", "Physics" in prompt and "FBISE" in prompt)
check("the student's own numbers reach it", "2 m s^-2" in prompt)
check("and are marked as the only ones allowed",
      "use these exactly, and no others" in prompt)

print()
print("it is told to leave photographs to the search")
for life in ("lung", "leaf section", "drawn from life"):
    check(f"it will not try to plot a {life!r}", life in FIGURE_RULES)

print()
print("a figure can still be asked for with nothing else known")
bare = figure_prompt("a free-body diagram of a block on a slope")
check("no subject and no numbers is still a usable prompt",
      "free-body diagram" in bare and "plt.show()" in bare)
check("and it does not claim numbers it was not given",
      "THE STUDENT'S OWN NUMBERS" not in bare)
check("an empty description still asks for something",
      "figure" in figure_prompt("").lower())

print()
print("the tool is declared in a way Gemini will accept")
# Read rather than import: langchain is not installed where this runs. A dict
# argument becomes a function schema with no properties, Gemini rejects the
# whole declaration, and every turn in the chat fails - not only the ones
# wanting a figure. It is worth a check that costs nothing.
import ast  # noqa: E402

source = (ROOT / "src/shared/ai/src/edu_ai/tools/figure.py").read_text(encoding="utf-8")
tree = ast.parse(source)
drawer = next(
    (
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "draw_figure"
    ),
    None,
)
check("the tool function is there", drawer is not None)
if drawer:
    args = {a.arg: ast.unparse(a.annotation) if a.annotation else "" for a in drawer.args.args}
    check("it takes a description", "description" in args)
    check("it takes the student's own numbers", "given" in args)
    check("it is handed the runtime", "runtime" in args)
    plain = {name: kind for name, kind in args.items() if name != "runtime"}
    check(
        "every argument is a plain string, never a dict or a model",
        all(kind == "str" for kind in plain.values()),
        str(plain),
    )
    description = ast.get_docstring(drawer) or ""
    check("it is documented", bool(description.strip()))

exported: set[str] = set()
for node in ast.walk(tree):
    if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.List):
        continue
    if not any(isinstance(t, ast.Name) and t.id == "tools" for t in node.targets):
        continue
    exported = {e.id for e in node.value.elts if isinstance(e, ast.Name)}

check("it is exported for the agent to pick up", exported == {"draw_figure"}, str(exported))

factory = (ROOT / "src/shared/ai/src/edu_ai/chatbot/factory.py").read_text(encoding="utf-8")
check("and the agent actually registers it",
      "figure_tools" in factory and "*figure_tools," in factory)
check("the picture finder is still registered beside it",
      "*diagram_tools," in factory)

print()
if failures:
    print(f"{len(failures)} failed: " + ", ".join(failures))
    sys.exit(1)
print("all checks passed")
