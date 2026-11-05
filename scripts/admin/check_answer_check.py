"""Check that a question agrees with itself before a student sees it.

Run with:
    python scripts/admin/check_answer_check.py

A teacher sat one of our quizzes, chose the option the explanation itself
calls correct, and was marked wrong. The marking was fine. The question was
not: the model had written four options, picked a letter, and written an
explanation concluding something else, and nothing compared the two.

That is the worst thing this product can do. A student told their right answer
is wrong does not decide the app is broken - they decide they misunderstood,
and change their mind about something they had correct.

The danger in the fix is the opposite one: a checker too eager to call a
question contradictory would throw away good ones. So both directions are
checked here, and the cases where the answer simply cannot be read out of the
explanation must come back as "do not know", never as "wrong".
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/shared/core/src"))

from edu_core.answer_check import (  # noqa: E402
    disagrees,
    distinguishing,
    implied_letter,
    keep_sound,
    letter_of,
    numbers_in,
)

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  -- {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


class Q:
    """A generated question, shaped the way the model returns one."""

    def __init__(self, a, b, c, d, correct, explanation, text="A question"):
        self.option_a, self.option_b, self.option_c, self.option_d = a, b, c, d
        self.correct_option = correct
        self.explanation = explanation
        self.question_text = text


ANGLES = {"a": "30 degrees", "b": "45 degrees", "c": "60 degrees", "d": "90 degrees"}
HEIGHTS = {"a": "10.2 m", "b": "14.4 m", "c": "20.4 m", "d": "40.8 m"}

print("the case a teacher actually hit")
# The explanation concludes 45 degrees; the key says 30.
wrong_key = Q(*ANGLES.values(), "a",
              "For maximum range the projectile must be launched at 45 degrees, "
              "because sin(2x) is largest when 2x is 90.")
check("the contradiction is caught", disagrees(wrong_key.correct_option, ANGLES, wrong_key.explanation))
check("and the explanation's own answer is identified",
      implied_letter(ANGLES, wrong_key.explanation) == "b",
      str(implied_letter(ANGLES, wrong_key.explanation)))

right_key = Q(*ANGLES.values(), "b", wrong_key.explanation)
check("the same question with the right key is kept",
      not disagrees(right_key.correct_option, ANGLES, right_key.explanation))

print()
print("a numerical question, where the options differ only by value")
worked = ("Using h = v^2 sin^2(x) / 2g with v = 20 m/s, x = 45 degrees and "
          "g = 9.8 m/s^2 gives h = 10.2 m.")
check("the computed value picks its option", implied_letter(HEIGHTS, worked) == "a",
      str(implied_letter(HEIGHTS, worked)))
check("a key pointing elsewhere is caught", disagrees("c", HEIGHTS, worked))
check("the matching key is accepted", not disagrees("a", HEIGHTS, worked))
check("numbers from the question itself do not confuse it",
      implied_letter(HEIGHTS, worked) == "a",
      "20 and 9.8 are in the working but are not options")

print()
print("an explanation that rules an option out is not choosing it")
ruled_out = ("The answer is 45 degrees. It is not 30 degrees, which is a "
             "common mistake, and 90 degrees would give no range at all.")
check("only the asserted value counts", implied_letter(ANGLES, ruled_out) == "b",
      str(implied_letter(ANGLES, ruled_out)))
check("a question like this is kept", not disagrees("b", ANGLES, ruled_out))
check("and its key is still checked", disagrees("a", ANGLES, ruled_out))

print()
print("when the answer cannot be read, the question is left alone")
for name, options, explanation in (
    ("wordy options", {"a": "It increases", "b": "It decreases",
                       "c": "It stays the same", "d": "It reverses"},
     "The velocity falls as the ball rises, because gravity opposes the motion."),
    ("no explanation", ANGLES, ""),
    ("explanation names nothing", HEIGHTS, "Apply the standard formula carefully."),
    ("two options named", ANGLES, "Both 30 degrees and 60 degrees give the same range."),
    ("every option shares the number", {"a": "5 m", "b": "5 s", "c": "5 kg", "d": "5 N"},
     "The answer is 5."),
):
    check(f"{name}: no verdict", implied_letter(options, explanation) is None,
          str(implied_letter(options, explanation)))
    check(f"{name}: so the question survives", not disagrees("a", options, explanation))

print()
print("a key that is not a letter at all is refused")
for bad in (None, "", "e", "1", "option b", "   "):
    check(f"{bad!r} is not a usable key", letter_of(bad) is None, str(letter_of(bad)))
for bad in (None, "", "e", "1"):
    check(f"{bad!r} drops the question", disagrees(bad, ANGLES, "The answer is 45 degrees."))
check("a valid letter in capitals is fine", letter_of("B") == "b")
check("a letter with a bracket is fine", letter_of("b)") == "b")

print()
print("numbers are read the way a student reads them")
check("a decimal is kept", numbers_in("10.2 m") == {"10.2"})
check("trailing zeros do not make a new answer", numbers_in("45.0") == numbers_in("45"))
check("a unit alone has no number", numbers_in("metres per second") == set())
check("several numbers are all found", numbers_in("v = 20, g = 9.8") == {"20", "9.8"})
check("a negative value keeps its sign", "-5" in numbers_in("the change is -5 J"))

print()
print("only what tells the options apart is used")
marks = distinguishing({"a": "5 m", "b": "5 s", "c": "10 m", "d": "20 m"})
check("a value shared by two options is ignored", marks["a"] == set() and marks["b"] == set(),
      f"{marks['a']} {marks['b']}")
check("a value unique to one option is kept", marks["c"] == {"10"} and marks["d"] == {"20"})

print()
print("sorting a batch keeps the good and drops the bad")
good_one = Q(*HEIGHTS.values(), "a", worked)
bad_one = Q(*ANGLES.values(), "d", "The correct answer is 45 degrees.")
unclear = Q("It rises", "It falls", "It stops", "It reverses", "b",
            "Gravity slows the ball on the way up.")
keep, drop = keep_sound([good_one, bad_one, unclear])
check("the sound question is kept", good_one in keep)
check("the unclear one is kept too", unclear in keep)
check("only the contradiction is dropped", drop == [bad_one], str(len(drop)))
check("nothing is lost or duplicated", len(keep) + len(drop) == 3)
check("an empty batch is fine", keep_sound([]) == ([], []))

print()
print("the generator actually uses it")
agent = (ROOT / "src/shared/ai/src/edu_ai/agents/quiz_agent.py").read_text(encoding="utf-8")
check("quiz generation filters its questions", "keep_sound(kept)" in agent)
check("and says which ones it dropped", "self-contradicting" in agent)
check("it runs after the duplicate filter, on what survives",
      agent.index("distinct_by_text(result.questions)") < agent.index("keep_sound(kept)"))

print()
if failures:
    print(f"{len(failures)} failed: " + ", ".join(failures))
    sys.exit(1)
print("all checks passed")
