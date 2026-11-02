"""Noticing when the tutor is going round in circles, and saying so.

A student asked for a picture of computer architecture and watched "Checked
the FBISE syllabus" five times over three minutes before a word was written.
Every one of those is a full round trip to the model, so a loop does not cost
the student a little time - it costs them the answer.

A model loops because nothing tells it to stop. It searched, the result was
not quite what it hoped for, so it searches again with slightly different
words, and the only thing that ever breaks the cycle is the context running
out. The fix is to say the true thing it is missing: you already have this,
write the answer.

Pure functions of the message list, with no model, no agent and no framework,
so the rule can be checked on its own - which matters, because the alternative
is finding out from a student who waited three minutes.
"""

# How many times the tutor may call one tool for one question. Three allows a
# genuine narrowing - a broad search, a narrower one, a check - and stops well
# short of five.
MAX_SAME_TOOL = 3


def calls_since_student(messages, tool_name: str) -> list[dict]:
    """The arguments of every call to this tool since the student last spoke.

    Newest first, and the call being handled right now is the first entry,
    because the message carrying it is already in the history by the time the
    tool runs.

    Read from the conversation rather than counted in a variable: exact under
    concurrent chats, and nothing has to be added to the agent's state schema.
    Everything is read defensively, since the shape of a message is specific to
    the framework version - a guard that crashes the turn it meant to shorten
    would be worse than no guard at all.
    """
    found: list[dict] = []
    for message in reversed(list(messages or [])):
        if getattr(message, "type", "") == "human":
            break
        for call in getattr(message, "tool_calls", None) or []:
            if isinstance(call, dict) and call.get("name") == tool_name:
                args = call.get("args")
                found.append(args if isinstance(args, dict) else {})
    return found


def loop_note(tool_name: str, calls: list[dict]) -> str | None:
    """What to add to a tool's result, or None when there is nothing to say.

    Two different circles, and they need different things said. An identical
    call is the model forgetting it has the answer; the note points at it. Many
    different calls is the model searching for something that is not there; the
    note tells it to answer with what it has and be honest about the gap.

    The tool's real result is never replaced, only added to. Cutting it off
    would lose information the student might need, and the point is to end the
    loop, not to withhold the answer.
    """
    if len(calls) < 2:
        return None

    if calls[0] in calls[1:]:
        return (
            f"You have already called {tool_name} with exactly these arguments "
            "in this turn, and the answer above is the same one. Do not call it "
            "again. Write the student's answer now with what you have."
        )

    if len(calls) > MAX_SAME_TOOL:
        return (
            f"You have now called {tool_name} {len(calls)} times for this one "
            "question. That is enough looking. Write the student's answer now "
            "with what you have, and say plainly if something is missing."
        )

    return None
