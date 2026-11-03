"""Who shares a room, what they are called in it, and what may be posted.

A room is a grade and a group together. Pre-Medical XI and Pre-Engineering XI
sit different papers, so they are different rooms, and there is no
all-of-NISAAB room: a question about Biology helps nobody studying Computer
Science.

The rule that matters most here is the quiet one. A student's email is not
theirs to give to a room full of strangers, so a post never carries one - only
a name, or the part before the @ if that is all there is. Getting that wrong
would not raise an error or look broken; it would just publish a few hundred
teenagers' email addresses to their classmates. So it lives here, with no
database or framework around it, where it can be checked.
"""

# What each group is called where a student can see it
GROUP_NAMES = {
    "PRE_MED": "Pre-Medical",
    "PRE_ENG": "Pre-Engineering",
    "ICS": "ICS",
}
GRADE_NAMES = {11: "XI", 12: "XII"}

# The longest a post may be. Long enough for a worked question, short enough
# that the room stays readable on a phone.
MAX_BODY = 2000
# How many top-level posts come back at once
PAGE_SIZE = 50
# Replies shown under each post. One level only: a thread a student can
# follow, not a tree nobody reads to the bottom of.
MAX_REPLIES = 20

# Shown when there is nothing usable to call someone. Never "Unknown" or a
# blank: a post with no visible author reads as broken.
SOMEONE = "A student"


def room_name(grade: int, group_code: str) -> str:
    """What to call this room, e.g. "Pre-Medical XI"."""
    group = GROUP_NAMES.get(group_code) or group_code or "FSc"
    return f"{group} {GRADE_NAMES.get(grade) or grade}"


def display_name(name: str | None, email: str | None) -> str:
    """Who wrote a post, as the rest of the class should see them.

    The name they gave, or failing that the part of their email before the @ -
    never the address itself. A room is other students, not people they chose
    to hand their email to.
    """
    if (name or "").strip():
        return (name or "").strip()
    local = (email or "").split("@")[0].strip()
    return local or SOMEONE


def check_body(body: str | None) -> str:
    """The post as it will be stored, or a ValueError saying why not."""
    said = (body or "").strip()
    if not said:
        raise ValueError("A post cannot be empty")
    if len(said) > MAX_BODY:
        raise ValueError(f"A post can be at most {MAX_BODY} characters")
    return said
