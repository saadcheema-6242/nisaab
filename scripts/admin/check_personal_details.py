"""Check that contact details are caught and Physics is not.

Run with:
    python scripts/admin/check_personal_details.py

Two ways to get this wrong, and the second is the one that kills the feature.

Too loose and a fifteen year old posts their mobile number to three hundred
strangers. Too tight and the room rejects "1.6 x 10^-19" as a phone number,
students conclude it is broken, and they stop using it - and the real numbers
still get through, written in words.

So the false positives are tested as hard as the true ones. Every string in
the CLEAN list is something a student would genuinely write in an FSc study
room, and every one of them must be allowed through.

No database, no network, no model.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/shared/core/src"))

from edu_core.personal_details import (  # noqa: E402
    find_emails,
    find_handles,
    find_links,
    find_personal_details,
    find_phone_numbers,
    is_clean,
    refusal_message,
)

failures: list[str] = []


def safe(text: str) -> str:
    """Printable on a cp1252 console.

    The Windows terminal cannot encode Arabic-Indic digits, so printing a
    test case killed the run before it could report on the code. The check
    still uses the real string; only the label is folded.
    """
    return text.encode("ascii", "backslashreplace").decode("ascii")


def check(name: str, ok: bool, detail: str = "") -> None:
    line = f"  {'ok  ' if ok else 'FAIL'}  {safe(name)}"
    if detail and not ok:
        line += f"  -- {safe(detail)}"
    print(line)
    if not ok:
        failures.append(safe(name))


def blocked(text: str, kind: str) -> None:
    """Must be refused, and for the stated reason.

    A platform link counts as either "link" or "platform" - instagram.com is
    both, and which one is named first does not matter to the student.
    """
    found = find_personal_details(text)
    ok = kind in found or (kind == "link" and "platform" in found)
    check(f"{kind}: {text[:52]}", ok, f"found {found or 'nothing'}")


def allowed(text: str) -> None:
    found = find_personal_details(text)
    check(f"allowed: {text[:52]}", not found, f"wrongly flagged {found}")


print("Pakistani mobile numbers, however they are written")
for text in (
    "my number is 03001234567",
    "0300-1234567 call me",
    "0300 123 4567",
    "+923001234567",
    "+92 300 1234567",
    "0092 300 1234567",
    "03331234567",
    "whatsapp me on 0321-9876543",
    "(0300) 1234567",
    "0300.1234567",
):
    blocked(text, "phone")

print()
print("other international numbers")
for text in (
    "+447911123456",
    "+1 415 555 0123",
    "+971 50 123 4567",
):
    blocked(text, "phone")

print()
print("a shorter number counts when it is offered as a contact")
blocked("whatsapp 3001234567", "phone")
blocked("my number 300123456", "phone")

print()
print("THE IMPORTANT HALF: things a student really writes, which must pass")
for text in (
    "the charge on an electron is 1.6 x 10^-19 C",
    "Avogadro's number is 6.022 x 10^23",
    "g = 9.8 m/s2",
    "0.03 mol of NaOH",
    "I got 15/20 in the test",
    "see Chapter 11, question 7",
    "the answer is 3.14159",
    "in 1947 Pakistan was founded",
    "FBISE 2022-23 curriculum",
    "Exercise 2.5 problem 12",
    "the value is 299792458 m/s",
    "2.5 x 10^8",
    "temperature rose from 25 to 100 degrees",
    "pH 7.4 is slightly basic",
    "Q3 part b took me 20 minutes",
    "1000000 is ten to the power six",
    "my marks were 85 percent",
    "page 123 has the derivation",
    "H2SO4 + 2NaOH gives Na2SO4 + 2H2O",
    "the half life is 5730 years",
    "250 cm3 of solution",
    "between 1905 and 1915 Einstein published",
    "solve for x: 2x + 3 = 11",
    "at 760 mm Hg and 273 K",
    "Physics XI chapter 4 numerical 16",
):
    allowed(text)

print()
print("a decimal written to many places is still a decimal")
# 3.141592653 becomes 3141592653, which is exactly the shape of a ten digit
# Pakistani mobile. Lifting the decimal guard without care refuses pi.
for text in (
    "pi is 3.141592653",
    "e = 1.602176634 x 10^-19",
    "Avogadro 6.02214076 x 10^23",
    "c = 2.99792458 x 10^8",
    "g = 9.80665 exactly",
):
    allowed(text)
# but a mobile written with dots is still a mobile
blocked("0300.1234567", "phone")
blocked("+92.300.1234567", "phone")

print()
print("the speed of light has nine digits and is not a phone number")
check("299792458 passes on its own", is_clean("c = 299792458 m/s"))
check("but the same digits offered as a contact do not",
      not is_clean("my whatsapp is 299792458"))

print()
print("email addresses, including the ways people dodge a filter")
for text in (
    "mail me at student@example.com",
    "saad (at) gmail (dot) com",
    "saad[at]gmail[dot]com",
    "contact: a.b_c+1@sub.domain.pk",
):
    blocked(text, "email")

print()
print("links")
for text in (
    "https://instagram.com/someone",
    "www.facebook.com/profile",
    "join t.me/somegroup",
    "wa.me/923001234567",
    "see my site at example.com",
    "https://discord.gg/abcd",
    "bit.ly/3xyz",
):
    blocked(text, "link")

print()
print("a version number is not a domain")
for text in ("version 2.5.1 of the app", "Python 3.12 is installed", "see 1.2.3 above"):
    allowed(text)

print()
print("social handles")
blocked("add me @saadcheema", "handle")
blocked("my insta is @study.with.saad", "handle")
check("an email is not also counted as a handle",
      "handle" not in find_personal_details("write to me@example.com"),
      str(find_personal_details("write to me@example.com")))
check("a short @ is not a handle", not find_handles("@ab"))

print()
print("platforms named in passing are fine; offered as contact are not")
allowed("I watched a YouTube video about this")
allowed("we discussed it on telegram in class")
blocked("here is my telegram t.me/saad", "link")

print()
print("Urdu and Arabic digits are read as digits")
blocked("my number is ٠٣٠٠١٢٣٤٥٦٧", "phone")

print()
print("empty and ordinary posts")
for text in ("", "   ", "can someone explain projectile motion?",
             "thanks, that helped a lot", "which chapter is this from"):
    allowed(text)

print()
print("the student is told what happened, and not shown the value again")
said = refusal_message(find_personal_details("call me on 03001234567"))
check("it names the kind of thing", "phone number" in said, said)
check("it does NOT repeat the number back", "03001234567" not in said, said)
check("it says why the rule exists", "safe" in said.lower(), said)
check("it says what to do instead", "without" in said.lower(), said)
check("nothing found means no message", refusal_message({}) == "")

both = refusal_message(find_personal_details("saad@x.com or 03001234567"))
check("two kinds are listed together", "and" in both, both)

print()
print("the finders return what they found, for the record")
check("phone finder returns the text", find_phone_numbers("call 03001234567"))
check("email finder returns the text", find_emails("a@b.com"))
check("link finder returns the text", find_links("go to example.com"))

print()
if failures:
    print(f"{len(failures)} failed:")
    for name in failures:
        print(f"  - {name}")
    sys.exit(1)
print(f"all checks passed")
