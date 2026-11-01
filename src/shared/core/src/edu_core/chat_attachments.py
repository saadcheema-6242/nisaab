"""What a student attaches in the chat, and how long the tutor keeps seeing it.

A picture and a textbook chapter are not the same kind of thing, and treating
them alike is what once made the tutor answer about the wrong image: the
picture was dropped before the tutor saw it, the tutor was told to search the
project's documents instead, and the search handed back the nearest unrelated
file.

So a picture stays with its conversation. It is sent to the tutor again with
every later message, which is what lets a student attach a diagram and then ask
three follow-up questions about it. That costs tokens on every one of those
turns, so only the most recent few are carried.

Pure functions of the message list, with no database, model or storage, so the
rules can be checked on their own.
"""

from edu_core.schemas.chats import FilePartDto

# How many attached pictures ride along with each message. Four covers the way
# a student actually works - a question, a diagram, a page of their notes -
# without a long conversation dragging a growing pile of images behind it.
MAX_CARRIED_PICTURES = 4

# How long a link to an attached file stays valid. Long enough to read a
# conversation without the pictures going blank halfway through; a fresh link
# is made every time the chat is loaded, so it need not outlive that.
ATTACHMENT_LINK_SECONDS = 24 * 60 * 60


def is_picture(part: object) -> bool:
    """Whether this part is an image the tutor can actually look at."""
    return isinstance(part, FilePartDto) and (
        part.file_type or ""
    ).lower().startswith("image/")


def pictures_to_carry(messages: list, limit: int = MAX_CARRIED_PICTURES) -> set[int]:
    """Identities of the most recent attached pictures, up to ``limit``.

    Newest first, because the picture being discussed is the one just sent. A
    conversation that goes past the limit loses its oldest pictures rather than
    its newest, and the text of those messages is untouched either way.
    """
    found: list[int] = []
    for message in reversed(messages):
        for part in reversed(getattr(message, "parts", None) or []):
            if is_picture(part):
                found.append(id(part))
                if len(found) >= limit:
                    return set(found)
    return set(found)
