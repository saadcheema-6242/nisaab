"""Keeping contact details out of a room full of other people's children.

NISAAB puts teenagers from schools all over the country in the same room. The
thing that turns a study group into a safeguarding problem is a student
posting a phone number, and the second thing is another student answering it
privately where no teacher can see. So contact details do not go in.

What makes this hard is that the room is full of numbers that are not phone
numbers. A Physics post says 1.6 x 10^-19, a Chemistry one says 0.03 mol,
somebody asks about Chapter 11 and somebody else got 15/20. A filter that
eats those is worse than no filter: students stop using the room, or learn to
work around it, and the real numbers still get through in words.

So the rule is narrow on purpose. A run of digits is only a phone number when
it is long enough to be one AND shaped like one - a Pakistani mobile, an
international number, or something sitting right next to the word "whatsapp".
Everything shorter, and every decimal, is left alone.

Pure functions over a string. No database, no network, no model: the whole
point is that the awkward cases can be checked directly, and they are, in
scripts/admin/check_personal_details.py.
"""

import re

# Platforms a student would be handing over an account on. Matched as whole
# words so "we discussed this on telegram" is not mistaken for a handle, but
# "t.me/someone" is.
PLATFORM_DOMAINS = (
    "facebook.com", "fb.com", "fb.me", "messenger.com",
    "instagram.com", "instagr.am",
    "whatsapp.com", "wa.me", "chat.whatsapp.com",
    "t.me", "telegram.me", "telegram.org",
    "snapchat.com", "tiktok.com", "x.com", "twitter.com",
    "discord.gg", "discord.com", "linkedin.com", "reddit.com",
)

# Words that mean "here is how to reach me". Near digits they lower the bar,
# because "whatsapp 0300" is a contact detail even though the digits alone
# would not qualify.
CONTACT_WORDS = (
    "whatsapp", "whats app", "wtsp", "wattsapp",
    "insta", "instagram", "snapchat", "snap chat", "snapcode",
    "telegram", "tiktok", "discord", "messenger",
    "my number", "my no", "contact me", "contact no", "phone no",
    "call me", "text me", "dm me", "inbox me", "ping me",
    "mobile number", "cell number", "rabta",
)

# Top level domains worth recognising. A fixed list rather than "any dot",
# because "e.g." and "i.e." and "H2O.the next sentence" all contain dots and
# none of them is a link.
TLDS = (
    "com", "net", "org", "io", "co", "me", "app", "dev", "xyz", "info",
    "biz", "tv", "gg", "ly", "be", "pk", "uk", "us", "in", "ae", "sa",
    "edu", "gov", "online", "site", "live", "link", "page", "club",
)

_TLD = "|".join(TLDS)

# A web address, with or without the https:// in front. The TLD must be one
# we know and must be followed by a boundary, so "3.14" and "No.5" are safe.
LINK = re.compile(
    r"\b(?:https?://|www\.)?"
    r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
    r"(?:" + _TLD + r")"
    r"(?:/[^\s]*)?\b",
    re.IGNORECASE,
)

EMAIL = re.compile(
    r"\b[a-z0-9._%+-]+\s*(?:@|\(at\)|\[at\]|\s+at\s+)\s*"
    r"[a-z0-9.-]+\s*(?:\.|\(dot\)|\[dot\]|\s+dot\s+)\s*(?:" + _TLD + r")\b",
    re.IGNORECASE,
)

# A social handle: an @ followed by a name. Not an email (handled above) and
# not an @ in the middle of a word.
HANDLE = re.compile(r"(?:^|[\s(\[])@([a-z0-9._]{3,30})\b", re.IGNORECASE)

# Anything that could be part of how a number is written down.
SEPARATORS = re.compile(r"[\s\-().]+")
# A run of digits once the separators are gone, possibly with a leading +.
DIGIT_RUN = re.compile(r"\+?\d[\d]{6,19}")

# A Pakistani mobile is eleven digits beginning 03, or the same with a country
# code in front. Landlines are not matched: they are rarely personal and the
# shapes collide with ordinary numbers.
PK_MOBILE = re.compile(r"^(?:\+?92|0092)?3\d{9}$|^03\d{9}$")
# An international number: a plus and ten to fifteen digits. The plus is what
# makes it unambiguous, so no length guessing is needed.
INTERNATIONAL = re.compile(r"^\+\d{10,15}$")
# Long enough that nothing in a Physics answer looks like it, used only when a
# contact word is sitting nearby.
NEAR_CONTACT = re.compile(r"^\+?\d{9,15}$")

# People do write numbers with dots: 0300.1234567. But a dot between digits
# is overwhelmingly a decimal point, so a span containing one is only read as
# a phone number when its shape leaves no doubt - a leading 0 on a Pakistani
# mobile, or an explicit country code.
#
# The bare ten-digit mobile form is deliberately NOT accepted here. Pi to
# nine decimal places is 3.141592653, which becomes 3141592653, which matches
# it exactly. A maths room that refuses pi is not a maths room.
DOTTED_PHONE = re.compile(r"^03\d{9}$|^(?:\+92|0092|92)\d{10}$|^\+\d{10,15}$")

# How far from a digit run a contact word still counts as "next to it"
NEARBY = 40


def _folded(text: str) -> str:
    """Lowercased, with the tricks people use to get past filters undone.

    Someone writing "zero three zero zero" is not the problem this solves; it
    catches the common ones, where digits are spelled with lookalike
    characters or an @ is written as (at).
    """
    said = (text or "").lower()
    for wrong, right in (
        ("۰", "0"), ("۱", "1"), ("۲", "2"), ("۳", "3"),
        ("۴", "4"), ("۵", "5"), ("۶", "6"), ("۷", "7"),
        ("۸", "8"), ("۹", "9"),
        ("٠", "0"), ("١", "1"), ("٢", "2"), ("٣", "3"),
        ("٤", "4"), ("٥", "5"), ("٦", "6"), ("٧", "7"),
        ("٨", "8"), ("٩", "9"),
    ):
        said = said.replace(wrong, right)
    return said


def _contact_word_near(said: str, start: int, end: int) -> bool:
    """Whether a "here is how to reach me" word sits beside this span."""
    around = said[max(0, start - NEARBY):min(len(said), end + NEARBY)]
    return any(word in around for word in CONTACT_WORDS)


def find_phone_numbers(text: str) -> list[str]:
    """Runs of digits that are really a way of contacting someone.

    A decimal is not a phone number however long it is, so anything with a
    digit immediately after a dot is skipped before the rest runs. That alone
    saves 1.6 x 10^-19, 6.022, 9.8 and every other constant in the syllabus.
    """
    said = _folded(text)
    found: list[str] = []

    # Walk candidate spans rather than the whole string at once, so the
    # position is known and a nearby contact word can be looked for.
    for match in re.finditer(r"[+\d][\d\s\-().]{6,24}\d", said):
        span = match.group()
        bare = SEPARATORS.sub("", span)
        if not DIGIT_RUN.fullmatch(bare):
            continue

        # A dot between digits usually means a measurement, so the shape has
        # to be unmistakable before it is read as a number to ring.
        if re.search(r"\d\.\d", span):
            if DOTTED_PHONE.match(bare):
                found.append(span.strip())
            continue

        if PK_MOBILE.match(bare) or INTERNATIONAL.match(bare):
            found.append(span.strip())
        elif NEAR_CONTACT.match(bare) and _contact_word_near(
            said, match.start(), match.end()
        ):
            found.append(span.strip())
    return found


def find_emails(text: str) -> list[str]:
    """Email addresses, including the ones written to dodge a filter."""
    return [m.group().strip() for m in EMAIL.finditer(_folded(text))]


def find_links(text: str) -> list[str]:
    """Web addresses. All of them, not only the social ones.

    A room for asking questions does not need links, and allowing some means
    arguing about which - a shortener hides everything, and "my site" is a
    profile page like any other. Blocking the lot is one rule a fifteen year
    old can understand, which a list of exceptions is not.
    """
    said = _folded(text)
    out = []
    for match in LINK.finditer(said):
        hit = match.group().strip(".,;:!?")
        # A version number reads as a domain to any regex, so anything whose
        # labels are all numeric ("2.5.1") is left alone.
        #
        # The scheme has to come off first. With it on, the host of
        # "https://instagram.com/x" is read as "https:", which contains no
        # dot, so the numeric test ran over an empty list - and all() of
        # nothing is True, so every link with a scheme was silently skipped.
        host = hit.split("://")[-1].split("/")[0]
        labels = [part for part in host.split(".")[:-1] if part]
        if labels and all(part.isdigit() for part in labels):
            continue
        out.append(hit)
    return out


def find_handles(text: str) -> list[str]:
    """@usernames, which are social accounts by another name."""
    said = _folded(text)
    # Anything already counted as an email is not also a handle.
    emails = " ".join(find_emails(said))
    return [
        "@" + m.group(1)
        for m in HANDLE.finditer(said)
        if m.group(1) not in emails
    ]


def find_platforms(text: str) -> list[str]:
    """Named social or messaging platforms used as a way to be reached.

    The platform's name on its own is fine: "I saw this on YouTube" is a
    sentence, not a contact detail. It only counts when a handle, a link or a
    number is in the same breath.
    """
    said = _folded(text)
    hits = []
    for domain in PLATFORM_DOMAINS:
        if domain in said:
            hits.append(domain)
    return hits


def find_personal_details(text: str) -> dict[str, list[str]]:
    """Everything found, grouped by what it is. Empty dict means clean."""
    found = {
        "phone": find_phone_numbers(text),
        "email": find_emails(text),
        "link": find_links(text),
        "handle": find_handles(text),
        "platform": find_platforms(text),
    }
    return {kind: hits for kind, hits in found.items() if hits}


# What the student is told. Said once, plainly, naming the kind of thing that
# was spotted but never repeating the value back - a message that echoes the
# number has published it in the error.
REASONS = {
    "phone": "a phone number",
    "email": "an email address",
    "link": "a link",
    "handle": "a social media username",
    "platform": "a social media or messaging account",
}


def refusal_message(found: dict[str, list[str]]) -> str:
    """Why this post was not accepted, in words a student can act on."""
    kinds = [REASONS[kind] for kind in found if kind in REASONS]
    if not kinds:
        return ""
    if len(kinds) == 1:
        what = kinds[0]
    else:
        what = ", ".join(kinds[:-1]) + " and " + kinds[-1]
    return (
        f"This looks like it contains {what}. The class room is public to "
        "everyone in your grade and group, so contact details cannot be "
        "posted here: it keeps you safe and it keeps the help where a "
        "teacher can see it. Ask your question without them."
    )


def is_clean(text: str) -> bool:
    """Whether this may be posted as it stands."""
    return not find_personal_details(text)
