"""Sharing a quiz or a paper by link, to be read rather than attempted.

A student who has made a good quiz wants to send it to the people sitting
the same paper. Today the only way is a screenshot.

What a share is, and is not:

    It is read-only. The person opening the link sees the quiz or the
    paper as a document. There is no attempt, no marking, no score, and
    nothing is written when they open it. That is the whole reason this
    feature is safe to make public: a route that only reads cannot be
    made to spend money on a model, cannot be used to fill the database,
    and cannot touch anybody's progress.

    It shows the answers. With attempting off the table, a quiz with the
    answers hidden is a list of questions the reader can do nothing with.
    Showing them makes it study material, which is what sharing is for.

    It is revocable. A link is a decision that can be regretted, so every
    share can be withdrawn from the Shares tab, immediately, without
    touching the quiz itself.

The token is the security. There is no sign-in on the public route, so
the only thing standing between an unshared quiz and the world is that
the token cannot be guessed: 32 characters from a 32-letter alphabet is
160 bits, generated with secrets.token_* rather than random.*, which is
seeded predictably and is not for this.

The id is never the token. Using the quiz id would mean every quiz in
the system is one URL away from being public, whether its owner shared
it or not.
"""

import secrets
import string

# Unambiguous when read aloud or copied off a screen: no 0/O, no 1/l/I.
ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
TOKEN_LENGTH = 32

# What may be shared. Only things that are read the same way by a
# stranger as by their owner; a chat is a conversation with somebody's
# own tutor and is deliberately not on this list.
QUIZ = "quiz"
PAPER = "paper"
SHAREABLE = (QUIZ, PAPER)

MAX_TITLE = 200


class ShareError(ValueError):
    """A share cannot be made or read as asked."""


def make_token() -> str:
    """An unguessable token.

    `secrets.choice`, not `random.choice`: the latter draws from a
    Mersenne Twister seeded from the clock, so tokens minted in the same
    moment are related to each other. That is fine for shuffling a quiz
    and useless for keeping one private.
    """
    return "".join(secrets.choice(ALPHABET) for _ in range(TOKEN_LENGTH))


def check_kind(kind: str) -> str:
    """What is being shared."""
    value = (kind or "").strip().lower()
    if value not in SHAREABLE:
        raise ShareError("Only a quiz or a paper can be shared.")
    return value


def check_title(title: str | None) -> str | None:
    """The name shown on the shared page, if one is given."""
    text = (title or "").strip()
    if not text:
        return None
    if len(text) > MAX_TITLE:
        raise ShareError(f"Keep the title under {MAX_TITLE} characters.")
    return text


def is_token_shaped(token: str) -> bool:
    """Whether this could be one of ours.

    Checked before the database is asked, so a public route cannot be
    used to make the server run a query for every string somebody tries.
    """
    if not token or len(token) != TOKEN_LENGTH:
        return False
    return all(c in ALPHABET for c in token)


def is_readable(revoked_at) -> bool:
    """Whether a share may still be opened.

    Revocation is a date rather than a deletion, for the same reason a
    ban and a teacher's approval are: the row is the record that the
    link existed, and somebody asking "did I share that?" deserves an
    answer after they have withdrawn it.
    """
    return revoked_at is None


def share_path(token: str) -> str:
    """Where a share lives. One definition, used by the page and the API."""
    return f"/s/{token}"


def share_url(origin: str, token: str) -> str:
    """The link a student copies.

    The origin is passed in rather than configured here: the same code
    serves localhost, the Firebase domain and the custom domain, and a
    link that always said one of them would be wrong on the other two.
    """
    return f"{(origin or '').rstrip('/')}{share_path(token)}"
