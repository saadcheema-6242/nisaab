"""Check the sharing rules without a database.

Run with:
    python scripts/admin/check_sharing.py

A share is the first thing in NISAAB that anyone can open without signing
in, so the question this file exists to ask is: can somebody reach a quiz
that was never shared? Everything below is arranged around that.
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src/shared/core/src"))

from edu_core.sharing import (  # noqa: E402
    ALPHABET,
    TOKEN_LENGTH,
    ShareError,
    check_kind,
    check_title,
    is_readable,
    is_token_shaped,
    make_token,
    share_path,
    share_url,
)

passed = failed = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    if ok:
        passed += 1
        print(f"  ok    {label}")
    else:
        failed += 1
        print(f"  FAIL  {label}" + (f" - {detail}" if detail else ""))


print("tokens cannot be guessed")
tokens = [make_token() for _ in range(500)]
check("every token is the stated length", all(len(t) == TOKEN_LENGTH for t in tokens))
check("every character is from the alphabet",
      all(set(t) <= set(ALPHABET) for t in tokens))
check("500 tokens, no two the same", len(set(tokens)) == 500,
      "a collision here means one student opening another's share")
# 31 characters is not a typo if ALPHABET changes; assert the entropy instead.
import math  # noqa: E402

bits = TOKEN_LENGTH * math.log2(len(ALPHABET))
check("at least 128 bits of entropy", bits >= 128, f"{bits:.0f} bits")
check("the alphabet has no look-alike characters",
      not (set("01lIO") & set(ALPHABET)),
      "a token read off a screen must not be ambiguous")

print()
print("a token is checked for shape before the database is asked")
check("a real token passes", is_token_shaped(make_token()))
check("the empty string is refused", not is_token_shaped(""))
check("a short string is refused", not is_token_shaped("abc"))
check("the right length but wrong letters is refused",
      not is_token_shaped("A" * TOKEN_LENGTH),
      "uppercase is not in the alphabet")
check("a token with a look-alike is refused",
      not is_token_shaped("0" * TOKEN_LENGTH))
check("SQL in the token is refused, not escaped",
      not is_token_shaped("' OR 1=1 --" + "a" * 21))
check("a path traversal is refused",
      not is_token_shaped("../" + "a" * 29))

print()
print("only a quiz or a paper may be shared")
check("a quiz may", check_kind("quiz") == "quiz")
check("a paper may", check_kind("paper") == "paper")
check("case and spacing do not matter", check_kind("  QUIZ ") == "quiz")
for bad in ("chat", "document", "note", "flashcards", "mind_map", "", "user"):
    try:
        check_kind(bad)
        check(f"{bad or '(empty)'} may not", False, "it was accepted")
    except ShareError:
        check(f"{bad or '(empty)'} may not", True)

print()
print("a revoked share stops opening")
check("a live share opens", is_readable(None))
import datetime  # noqa: E402

check("a revoked one does not",
      not is_readable(datetime.datetime(2026, 11, 9, tzinfo=datetime.timezone.utc)),
      "revoking must take effect, not merely be recorded")

print()
print("the title")
check("an ordinary title is kept", check_title(" Physics XI quiz ") == "Physics XI quiz")
check("an empty title becomes nothing", check_title("   ") is None)
check("no title is nothing", check_title(None) is None)
try:
    check_title("x" * 500)
    check("an absurd title is refused", False, "it was accepted")
except ShareError:
    check("an absurd title is refused", True)

print()
print("the link")
tok = make_token()
check("the path is built from the token", share_path(tok) == f"/s/{tok}")
check("the url joins cleanly",
      share_url("https://nisaab.example.com", tok)
      == f"https://nisaab.example.com/s/{tok}")
check("a trailing slash on the origin does not double up",
      share_url("https://nisaab.example.com/", tok)
      == f"https://nisaab.example.com/s/{tok}",
      "two slashes would 404 on some hosts")

print()
print(f"{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
