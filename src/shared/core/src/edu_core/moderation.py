"""Whether an account is allowed in, and what to tell the person if not.

Three states, and they are genuinely different things:

- not banned, which is almost everyone;
- banned until a date, which is a cooling-off period and ends by itself;
- banned with no end date, which is permanent until an administrator lifts it.

Keeping "until when" as the only field is what makes this safe. A separate
"is banned" flag would eventually disagree with the date - a temporary ban
expires and the flag stays true, and somebody is locked out for good by
accident. Here there is nothing to disagree with: the dates are the state.

Pure functions of the stored values and the current time, so the rules can be
checked without a database, a clock or a web request - including the awkward
ones, like a ban that expired one second ago.
"""

from datetime import datetime, timedelta, timezone

# What an administrator sees in the list
ACTIVE = "active"
TEMPORARY = "temporary"
PERMANENT = "permanent"

# How long the preset suspensions run for
PRESET_DAYS = (1, 7, 30)


def _aware(moment: datetime | None) -> datetime | None:
    """A time that can be compared with any other time here.

    Postgres hands back timezone-aware values and SQLite does not, and
    comparing the two raises. A naive value is read as UTC, which is what
    everything here is stored in.
    """
    if moment is None:
        return None
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment


def is_banned(
    banned_at: datetime | None,
    banned_until: datetime | None,
    now: datetime | None = None,
) -> bool:
    """Whether this account is shut out right now.

    An expired temporary ban is not a ban. It is left in the database on
    purpose - an administrator looking at the account should be able to see
    that it happened and why - but it does not keep anybody out.
    """
    if banned_at is None:
        return False
    until = _aware(banned_until)
    if until is None:
        return True
    moment = _aware(now) or datetime.now(timezone.utc)
    return moment < until


def ban_state(
    banned_at: datetime | None,
    banned_until: datetime | None,
    now: datetime | None = None,
) -> str:
    """How to describe this account: active, temporary or permanent."""
    if not is_banned(banned_at, banned_until, now):
        return ACTIVE
    return PERMANENT if banned_until is None else TEMPORARY


def ban_message(
    banned_until: datetime | None, reason: str | None = None
) -> str:
    """What the person is told when they are turned away.

    Says when it ends, if it ends, because an account that stops working with
    no explanation looks like a broken app and brings a complaint instead of a
    reflection. The reason is included when there is one: being told what you
    did is the only way to not do it again.
    """
    if banned_until is None:
        said = "This account has been suspended."
    else:
        when = _aware(banned_until)
        said = (
            "This account is suspended until "
            f"{when.strftime('%d %B %Y')}."
            if when
            else "This account has been suspended."
        )
    if (reason or "").strip():
        said += f" Reason: {reason.strip()}"
    return said + " Contact your teacher if you think this is a mistake."


def until_from_days(days: int | None, now: datetime | None = None) -> datetime | None:
    """When a suspension of this many days ends, or None for a permanent one.

    Zero and negative are read as permanent rather than as a ban that has
    already expired, which would silently do nothing at all.
    """
    if not days or days <= 0:
        return None
    return (_aware(now) or datetime.now(timezone.utc)) + timedelta(days=days)
