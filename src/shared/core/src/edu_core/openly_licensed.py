"""Find a diagram that someone has actually given permission to use.

An image model cannot draw a correct labelled diagram: it cannot spell, and a
confidently wrong diagram in an exam question is worse than none. The pictures
that are both correct and labelled already exist - in Wikimedia Commons,
OpenStax, PhET and NASA - and are published under licences that allow reuse.

Two rules, enforced here in code rather than asked of a model:

1. Only openly licensed sources are searched, and only free licences are
   accepted. A licence that forbids commercial use or forbids modification is
   rejected along with everything unlicensed, because this is a product and
   because a picture gets cropped and scaled on its way into a paper.
2. Every picture carries its licence, its author and where it came from, and
   that travels with it - into the app, the PDF and the Google Form. Crediting
   is a condition of these licences, not a courtesy.

Wikimedia Commons is searched first and is the only backend here: it holds the
science diagrams, and its API returns the licence as a machine-readable field
rather than as prose someone has to read. The others are worth adding, but
each needs its own licence handling and none is as broad.
"""

import html
import os
import re
from dataclasses import dataclass

import httpx

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
# Commons renders every file, SVG included, to a PNG thumbnail at a width we
# ask for. Taking the thumbnail rather than the original means one predictable
# raster format everywhere - a Google Form will not render an SVG, and the PDF
# export rasterises anyway.
THUMB_WIDTH = 1024
TIMEOUT = 20.0
# Identify ourselves, as Wikimedia's User-Agent policy requires. The contact
# is not decoration: a string that merely describes the client, with no way to
# reach whoever runs it, is refused with a 403 and no explanation beyond the
# status. Every search from Cloud Run came back 403 - ten out of ten - until
# this carried a URL.
#
# Settable, because the right contact is wherever this is actually deployed,
# and a stale address is worse than none. The default is the real domain
# rather than a Cloud Run URL: the edu-web service that used to serve the
# site is gone, and a contact URL that 404s is the stale address this
# warns about - it reads as a client with no owner, which is what the 403
# was for.
CONTACT = os.getenv("MEDIA_SEARCH_CONTACT", "https://nisaab.muhammadsaadcheema.com")
USER_AGENT = f"NISAAB/1.0 ({CONTACT}; FBISE FSc study app) httpx"

# Licences that allow reuse in a product. Commons reports these in a machine
# readable field, so this is a comparison and not an interpretation.
# The machine code ("cc-by-sa-4.0") is the reliable field. The prose form
# ("Creative Commons Attribution-Share Alike 4.0") is accepted too, for the
# files that carry only that - the forbidden list below still applies to it,
# and NonCommercial and NoDerivatives both appear there.
FREE_PREFIXES = (
    "cc0",
    "cc-by",
    "pd",
    "publicdomain",
    "public domain",
    "creative commons attribution",
)
# Rejected even though they are Creative Commons: NC forbids commercial use,
# and this is a product; ND forbids derivative works, and a picture is cropped
# and scaled on its way into a paper.
#
# The prose is checked as well as the code, and either one is enough to refuse.
# A file can carry a free licence code and a usage note that contradicts it,
# and where they disagree the restrictive one is the one to believe.
FORBIDDEN_PARTS = (
    "-nc",
    "-nd",
    "nonfree",
    "non-free",
    "fair use",
    "fairuse",
    "noncommercial",
    "non-commercial",
    "not be used commercial",
    "no commercial",
    "noderiv",
    "nonderivative",
    "non-derivative",
    "no derivative",
    "all rights reserved",
)

USABLE_TYPES = ("image/png", "image/jpeg", "image/svg+xml", "image/gif", "image/webp")


@dataclass(frozen=True)
class Credit:
    """Who made a picture, under what licence, and where it came from.

    Stored with the picture and shown wherever the picture is shown. Without
    all three the licence is not satisfied, so there is no partial version of
    this.
    """

    author: str
    licence: str
    licence_url: str
    source_url: str
    source: str = "Wikimedia Commons"
    title: str = ""

    def line(self) -> str:
        """One line of attribution, as it should appear under the picture."""
        parts = [self.title.strip(), self.author.strip()]
        who = " - ".join(p for p in parts if p)
        return f"{who} ({self.licence}), via {self.source}" if who else (
            f"{self.licence}, via {self.source}"
        )

    def as_dict(self) -> dict:
        return {
            "author": self.author,
            "licence": self.licence,
            "licence_url": self.licence_url,
            "source_url": self.source_url,
            "source": self.source,
            "title": self.title,
            "line": self.line(),
        }


@dataclass(frozen=True)
class Found:
    """One usable picture, with everything needed to show and credit it."""

    title: str
    image_url: str
    credit: Credit
    width: int = 0
    height: int = 0
    mime: str = ""


class SearchError(RuntimeError):
    """The search could not be done."""


def _text(value: str) -> str:
    """Commons returns author and credit as HTML; this is the readable text."""
    without_tags = re.sub(r"<[^>]+>", " ", value or "")
    return " ".join(html.unescape(without_tags).split())[:200]


def is_free(licence_code: str, usage_terms: str = "") -> bool:
    """Whether a licence allows reuse in a product, including modification.

    Decided from the machine-readable code where there is one. Anything not
    recognised is refused: an unknown licence is not an open licence, and the
    cost of being wrong here is republishing someone's work without the right
    to do so.
    """
    code = (licence_code or "").strip().lower()
    terms = (usage_terms or "").strip().lower()
    if not code and not terms:
        return False
    haystack = f"{code} {terms}"
    if any(bad in haystack for bad in FORBIDDEN_PARTS):
        return False
    return code.startswith(FREE_PREFIXES) or terms.startswith(FREE_PREFIXES)


def _credit_from(meta: dict, page_url: str, title: str) -> Credit | None:
    """Read the licence block Commons returns, or None if it is not usable."""
    def field(name: str) -> str:
        entry = meta.get(name) or {}
        return _text(entry.get("value", "")) if isinstance(entry, dict) else ""

    licence_code = field("License")
    usage_terms = field("UsageTerms")
    if not is_free(licence_code, usage_terms):
        return None

    short = field("LicenseShortName") or usage_terms or licence_code
    author = field("Artist") or field("Credit") or "Unknown author"
    licence_url = ""
    raw_url = meta.get("LicenseUrl") or {}
    if isinstance(raw_url, dict):
        licence_url = (raw_url.get("value") or "").strip()

    return Credit(
        author=author,
        licence=short,
        licence_url=licence_url,
        source_url=page_url,
        title=title,
    )


def _usable(info: dict) -> bool:
    mime = (info.get("mime") or "").lower()
    return mime in USABLE_TYPES


def search(query: str, limit: int = 6, timeout: float = TIMEOUT) -> list[Found]:
    """Pictures from Wikimedia Commons that may be reused, best match first.

    Only files whose licence passes ``is_free`` are returned, so an empty list
    means nothing usable was found - not that nothing was found.

    Raises:
        SearchError: If Commons could not be reached or refused the request.
    """
    wanted = " ".join((query or "").split())
    if not wanted:
        return []

    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": wanted,
        # Namespace 6 is File:, so pages about files rather than articles
        "gsrnamespace": "6",
        "gsrlimit": str(max(1, min(limit * 3, 30))),
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|mime|size",
        "iiurlwidth": str(THUMB_WIDTH),
    }
    try:
        with httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT}) as client:
            reply = client.get(COMMONS_API, params=params)
    except httpx.HTTPError as error:
        raise SearchError(f"Wikimedia Commons could not be reached: {error}") from error
    if reply.status_code != 200:
        # Carry Wikimedia's own words. A bare 403 cost a day of guessing at
        # firewalls and cloud IP ranges when the reply itself says which rule
        # was broken - the policy is enforced with an explanation, and throwing
        # it away was the real mistake.
        said = " ".join((reply.text or "").split())[:300]
        raise SearchError(
            f"Wikimedia Commons refused the search ({reply.status_code})"
            + (f": {said}" if said else "")
        )

    pages = (reply.json().get("query") or {}).get("pages") or {}
    return parse(pages, limit)


def parse(pages: dict, limit: int = 6) -> list[Found]:
    """Turn the Commons reply into usable results. Separate so it can be tested."""
    out: list[Found] = []
    # Commons returns the best match first via the index it puts on each page
    ordered = sorted(pages.values(), key=lambda page: page.get("index", 999))
    for page in ordered:
        infos = page.get("imageinfo") or []
        if not infos:
            continue
        info = infos[0]
        if not _usable(info):
            continue
        credit = _credit_from(
            info.get("extmetadata") or {},
            info.get("descriptionurl") or "",
            _title(page.get("title", "")),
        )
        if credit is None:
            continue
        # thumburl is the rendered raster; url is the original, which may be SVG
        image_url = info.get("thumburl") or info.get("url") or ""
        if not image_url:
            continue
        out.append(
            Found(
                title=credit.title,
                image_url=image_url,
                credit=credit,
                width=int(info.get("thumbwidth") or info.get("width") or 0),
                height=int(info.get("thumbheight") or info.get("height") or 0),
                mime=info.get("mime") or "",
            )
        )
        if len(out) >= limit:
            break
    return out


def _title(page_title: str) -> str:
    """'File:Projectile motion.svg' reads better as 'Projectile motion'."""
    name = re.sub(r"^File:", "", page_title or "").strip()
    return re.sub(r"\.(svg|png|jpe?g|gif|webp)$", "", name, flags=re.I)


def fetch(url: str, timeout: float = TIMEOUT) -> bytes:
    """Download a picture that search returned.

    Taken into our own storage rather than linked: a link to someone else's
    server breaks when they move the file, and a question that loses its
    diagram months later is worse than one that never had it. Copying is what
    these licences permit, provided the credit travels with it.
    """
    try:
        with httpx.Client(
            timeout=timeout, headers={"User-Agent": USER_AGENT}, follow_redirects=True
        ) as client:
            reply = client.get(url)
    except httpx.HTTPError as error:
        raise SearchError(f"The picture could not be downloaded: {error}") from error
    if reply.status_code != 200 or not reply.content:
        raise SearchError(f"The picture could not be downloaded ({reply.status_code})")
    return reply.content
