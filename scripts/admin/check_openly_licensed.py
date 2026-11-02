"""Check the licence rules, without touching the network.

Run with:
    python scripts/admin/check_openly_licensed.py

The rule being guarded is simple and the cost of getting it wrong is not: only
pictures whose licence allows reuse and modification may be used, and each one
must carry its author, its licence and where it came from. Everything else is
refused, including anything whose licence is merely unrecognised.

``scripts/admin/try_media_search.py`` does the live half against Commons.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/shared/core/src"))

from edu_core.openly_licensed import Credit, is_free, parse  # noqa: E402

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  -- {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


print("licences that allow reuse are accepted")
for code in (
    "cc0",
    "cc-by-4.0",
    "cc-by-sa-4.0",
    "cc-by-sa-3.0,2.5,2.0,1.0",
    "pd",
    "PD-USGov-NASA",
    "public domain",
):
    check(f"{code} is free", is_free(code), code)

print()
print("everything else is refused")
for code, why in (
    ("cc-by-nc-4.0", "forbids commercial use"),
    ("cc-by-nc-sa-4.0", "forbids commercial use"),
    ("cc-by-nd-4.0", "forbids modification, and pictures get cropped"),
    ("fair use", "not a licence to republish"),
    ("non-free", "not free"),
    ("", "no licence stated at all"),
    ("some-bespoke-terms", "unrecognised, so not known to be free"),
):
    check(f"{code or '(blank)'} is refused - {why}", not is_free(code), code)

check(
    "a free code with non-commercial terms is still refused",
    not is_free("cc-by-4.0", "This file may not be used commercially"),
)
check(
    "usage terms alone can establish a free licence",
    is_free("", "Public domain"),
)

# Exactly what Commons returned for a real projectile-motion diagram
check(
    "the real reply for a CC BY-SA diagram is accepted",
    is_free("cc-by-sa-4.0", "Creative Commons Attribution-Share Alike 4.0"),
)
check(
    "its prose form alone is also accepted",
    is_free("", "Creative Commons Attribution-Share Alike 4.0"),
)
check(
    "but the NonCommercial prose form is not",
    not is_free("", "Creative Commons Attribution-NonCommercial 4.0"),
)
check(
    "nor the NoDerivatives prose form",
    not is_free("", "Creative Commons Attribution-NoDerivatives 4.0"),
)

print()
print("the credit line names the author, the licence and the source")
credit = Credit(
    author="Jane Example",
    licence="CC BY-SA 4.0",
    licence_url="https://creativecommons.org/licenses/by-sa/4.0",
    source_url="https://commons.wikimedia.org/wiki/File:Projectile.svg",
    title="Projectile motion",
)
line = credit.line()
for part in ("Projectile motion", "Jane Example", "CC BY-SA 4.0", "Wikimedia Commons"):
    check(f"the line carries {part}", part in line, line)
check("it is one line", "\n" not in line, line)
check(
    "an unknown author still produces a usable line",
    "CC BY-SA 4.0" in Credit("", "CC BY-SA 4.0", "", "u").line(),
)
stored = credit.as_dict()
for key in ("author", "licence", "licence_url", "source_url", "source", "line"):
    check(f"'{key}' is stored with the picture", key in stored and stored[key] is not None)

print()
print("a Commons reply is read correctly")


def page(index, title, mime, licence, author="Someone", thumb="https://x/t.png"):
    return {
        "index": index,
        "title": title,
        "imageinfo": [
            {
                "mime": mime,
                "thumburl": thumb,
                "url": "https://x/orig.svg",
                "descriptionurl": "https://commons.wikimedia.org/wiki/" + title,
                "thumbwidth": 1024,
                "thumbheight": 768,
                "extmetadata": {
                    "License": {"value": licence},
                    "LicenseShortName": {"value": licence.upper()},
                    "Artist": {"value": f'<a href="/wiki/User:X">{author}</a>'},
                    "LicenseUrl": {"value": "https://creativecommons.org/x"},
                },
            }
        ],
    }


results = parse(
    {
        "1": page(2, "File:Second.svg", "image/svg+xml", "cc-by-sa-4.0"),
        "2": page(1, "File:First.png", "image/png", "cc0"),
        "3": page(3, "File:Paywalled.jpg", "image/jpeg", "fair use"),
        "4": page(4, "File:Advert.png", "image/png", "cc-by-nc-4.0"),
        "5": page(5, "File:Movie.webm", "video/webm", "cc0"),
    }
)
check("only the freely licensed images come back", len(results) == 2, str(len(results)))
check("best match first", results[0].title == "First", results[0].title)
check("the file extension is dropped from the title", ".png" not in results[0].title)
check("a fair-use file is dropped", all("Paywalled" not in r.title for r in results))
check("a non-commercial file is dropped", all("Advert" not in r.title for r in results))
check("a video is dropped", all("Movie" not in r.title for r in results))
check(
    "the author's HTML is turned into plain text",
    results[0].credit.author == "Someone",
    results[0].credit.author,
)
check(
    "an SVG is taken as the rendered raster, not the SVG itself",
    results[1].image_url.endswith("t.png"),
    results[1].image_url,
)
check("the source links back to the file's page",
      results[0].credit.source_url.startswith("https://commons.wikimedia.org/wiki/"))

print()
print("a reply with nothing usable in it is empty, not a bad picture")
check("no results at all", parse({}) == [])
check(
    "every result unlicensed",
    parse({"1": page(1, "File:A.png", "image/png", "fair use")}) == [],
)
check(
    "a file with no imageinfo is skipped",
    parse({"1": {"index": 1, "title": "File:A.png"}}) == [],
)
check(
    "a file with no usable link is skipped",
    parse(
        {
            "1": {
                "index": 1,
                "title": "File:A.png",
                "imageinfo": [
                    {
                        "mime": "image/png",
                        "extmetadata": {"License": {"value": "cc0"}},
                    }
                ],
            }
        }
    )
    == [],
)

print()
print("we identify ourselves the way Wikimedia's policy demands")
# Nothing here checked the User-Agent, and that is how ten out of ten searches
# came back 403 from Cloud Run with nobody any the wiser. The policy is plain:
# a string that describes the client but gives no way to reach whoever runs it
# is refused. Enforcement got stricter, the string did not change, and the
# tutor quietly stopped being able to show a picture.
from edu_core.openly_licensed import CONTACT, USER_AGENT  # noqa: E402

check("there is a user agent at all", bool(USER_AGENT.strip()))
check("it names the app", "NISAAB" in USER_AGENT, USER_AGENT)
check("it carries a version", "/" in USER_AGENT.split()[0], USER_AGENT)
check(
    "it carries a way to contact us, which is the part that was missing",
    "http" in USER_AGENT or "@" in USER_AGENT,
    USER_AGENT,
)
check("the contact is inside the brackets, where the policy puts it",
      CONTACT in USER_AGENT.split("(", 1)[-1].split(")", 1)[0], USER_AGENT)
check("the contact is not a placeholder",
      not any(bad in CONTACT.lower() for bad in ("example.com", "localhost", "todo", "changeme")),
      CONTACT)
check("it is not one of the generic strings that get refused",
      not any(
          USER_AGENT.lower().startswith(generic)
          for generic in ("python", "httpx", "requests", "mozilla", "curl")
      ),
      USER_AGENT)

print()
print("a refusal says why, so the next one is not guesswork")
source = (ROOT / "src/shared/core/src/edu_core/openly_licensed.py").read_text(
    encoding="utf-8"
)
check("the reply's own text is put into the error", "reply.text" in source)
check("and it is trimmed rather than dumped whole", "[:300]" in source)

print()
if failures:
    print(f"{len(failures)} failed: " + ", ".join(failures))
    sys.exit(1)
print("all checks passed")
