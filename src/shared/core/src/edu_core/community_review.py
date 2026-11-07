"""Reading a post the way a teacher would, and deciding what to do about it.

The pattern filter catches contact details because those have a shape. Most
of what actually goes wrong in a room of teenagers does not: cruelty aimed at
one person, a threat, somebody asking for exam answers, somebody saying they
want to hurt themselves. No regular expression finds those, and a human
cannot read every post.

So a model reads each one and says what it sees. Three things matter about
how that is wired up:

It never silently deletes. A model that removes posts is a model that will
one day remove a good question and nobody will know why. It flags, the post
stays up, and an administrator decides.

It fails open. If the model is slow, broken or unreachable, the post goes
through unflagged. The alternative is a room that stops working whenever
Vertex has a bad minute, which costs more than the posts it would have
caught.

The exception is distress. A student saying they want to hurt themselves is
not a moderation problem, and hiding their post helps nobody: it is shown,
raised to the top for an adult, and the student is answered gently rather
than warned.

The prompt and the parsing live here, with no network in sight, so what the
model is asked and how its answer is read can both be checked.
"""

import json

# What a post can be flagged as. Ordered by how fast an adult needs to look.
SELF_HARM = "self_harm"
THREAT = "threat"
BULLYING = "bullying"
SEXUAL = "sexual"
HATE = "hate"
CHEATING = "cheating"
CONTACT = "contact"
SPAM = "spam"
CLEAN = "clean"

# How far up the administrator's list each kind goes. Higher is sooner.
SEVERITY = {
    SELF_HARM: 100,
    THREAT: 90,
    SEXUAL: 80,
    HATE: 70,
    BULLYING: 60,
    CHEATING: 40,
    CONTACT: 30,
    SPAM: 20,
    CLEAN: 0,
}

# Kinds the author is warned about. Distress is not among them: warning a
# student who said they are struggling is the worst thing the system could
# do. Cheating gets a word, because most of it is a student who has not
# thought about it rather than one who has.
WARNED = (THREAT, SEXUAL, HATE, BULLYING, CHEATING, CONTACT, SPAM)

# Kinds an adult should see today rather than when they next look.
URGENT = (SELF_HARM, THREAT, SEXUAL)

LABELS = {
    SELF_HARM: "a student who may be in distress",
    THREAT: "a threat",
    BULLYING: "bullying or personal abuse",
    SEXUAL: "sexual content",
    HATE: "hateful content",
    CHEATING: "asking for or sharing exam answers",
    CONTACT: "contact details",
    SPAM: "spam or advertising",
    CLEAN: "nothing of concern",
}


def review_prompt(body: str, room: str) -> str:
    """What the model is asked about one post.

    Written to be read by a model that will otherwise moderate like an
    American content policy: the room is Pakistani teenagers talking about
    their syllabus, and arguing about an answer, being blunt, or writing in
    Urdu are all normal. Over-flagging has a cost that is easy to miss,
    because the flags look like the system working.
    """
    return f"""You are helping a teacher keep an online study room safe.

The room is {room}: Pakistani college students, 16 to 18, studying for their
FBISE FSc examinations. They discuss Physics, Chemistry, Biology, Maths and
Computer Science. They write in English, Urdu, or a mixture, and they are
often blunt with each other.

Read this one post and say whether a teacher needs to look at it.

POST:
\"\"\"{body}\"\"\"

Reply with JSON only, no other text:
{{"finding": "<one label>", "confidence": <0.0 to 1.0>, "why": "<one short sentence>"}}

The labels:
- "self_harm": the writer may be thinking of hurting themselves, or sounds
  genuinely desperate. Exam stress said lightly is not this.
- "threat": threatening to hurt a named person.
- "bullying": attacking or humiliating a particular student.
- "sexual": sexual content.
- "hate": attacking people for their religion, sect, ethnicity or gender.
- "cheating": asking for, offering or sharing live exam paper content.
- "contact": a phone number, email, social media account or link.
- "spam": advertising, selling, or the same thing posted repeatedly.
- "clean": anything else.

Judge it the way a fair teacher would:
- Disagreeing about an answer is not bullying.
- "This chapter is killing me" is exam talk, not self harm.
- Asking for help with homework is not cheating. Asking for the answers to a
  paper being sat right now is.
- Frustration, slang and bluntness are not abuse.
- Urdu and Roman Urdu are normal here, not suspicious.

If you are unsure, answer "clean" with a low confidence. A good question
wrongly flagged costs more than a rude one missed, because students stop
asking."""


def _first_json(text: str) -> dict:
    """The first JSON object in a reply, however it was wrapped.

    Models fence JSON in markdown, add a sentence before it, or both. Looking
    for the braces is more reliable than insisting on clean output, and the
    alternative is a review that fails because of punctuation.
    """
    said = (text or "").strip()
    if not said:
        return {}
    start = said.find("{")
    end = said.rfind("}")
    if start < 0 or end <= start:
        return {}
    try:
        got = json.loads(said[start : end + 1])
    except (ValueError, TypeError):
        return {}
    return got if isinstance(got, dict) else {}


class Review:
    """What the model made of one post."""

    def __init__(self, finding: str, confidence: float, why: str):
        self.finding = finding
        self.confidence = confidence
        self.why = why

    @property
    def severity(self) -> int:
        return SEVERITY.get(self.finding, 0)

    @property
    def is_concerning(self) -> bool:
        return self.finding != CLEAN

    @property
    def is_urgent(self) -> bool:
        return self.finding in URGENT

    @property
    def should_warn(self) -> bool:
        return self.finding in WARNED

    @property
    def label(self) -> str:
        return LABELS.get(self.finding, self.finding)

    def __repr__(self) -> str:
        return f"Review({self.finding}, {self.confidence:.2f})"


# Below this the model is guessing, and a guess is not worth an adult's time
# or a student's warning. Distress is exempt: a possible cry for help is
# worth a false alarm, which is the one place that trade runs the other way.
MIN_CONFIDENCE = 0.6


def read_review(text: str) -> Review:
    """Turn the model's reply into a decision.

    Anything unrecognisable reads as clean. A review that cannot be parsed is
    not evidence of anything, and treating confusion as a finding would flag
    posts because of a malformed response.
    """
    got = _first_json(text)
    finding = str(got.get("finding") or CLEAN).strip().lower()
    if finding not in SEVERITY:
        finding = CLEAN

    try:
        confidence = float(got.get("confidence", 0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = min(1.0, max(0.0, confidence))

    why = str(got.get("why") or "").strip()[:300]

    # Not sure enough to act on, unless it is the one that matters most.
    if finding != CLEAN and finding != SELF_HARM and confidence < MIN_CONFIDENCE:
        return Review(CLEAN, confidence, why)
    return Review(finding, confidence, why)


# What the author is told. Written as a teacher would say it: once, plainly,
# no lecture, and it says what to do next. A warning that reads as a
# punishment makes a teenager argue with it instead of reading it.
WARNINGS = {
    THREAT: (
        "Your post has been reported to a teacher because it reads as a "
        "threat towards someone. Whatever is going on, saying that here is "
        "not the way to deal with it. Talk to your teacher."
    ),
    BULLYING: (
        "Your post has been reported to a teacher. It names or targets "
        "another student in a way that would be hard to read about yourself. "
        "Disagree with the answer, not the person."
    ),
    SEXUAL: (
        "Your post has been reported to a teacher. This room is for your "
        "class and your syllabus, and that is not what it is for."
    ),
    HATE: (
        "Your post has been reported to a teacher. Everyone in this room is "
        "preparing for the same papers, whatever their background."
    ),
    CHEATING: (
        "Your post has been reported to a teacher because it asks for or "
        "shares exam answers. Ask how to solve it instead and you will get "
        "help here, and it will still be there in the examination hall."
    ),
    CONTACT: (
        "Your post contains contact details. This room is open to everyone "
        "in your grade and group, so keep your phone number, email and "
        "social accounts out of it. It keeps you safe."
    ),
    SPAM: (
        "Your post has been reported to a teacher as advertising or spam. "
        "Keep the room for your class and your syllabus."
    ),
}

# Not a warning. The student is not in trouble, and the first thing they read
# should not sound like they are.
SUPPORT = (
    "It sounds like things are heavy right now, and saying so took "
    "something. Please talk to someone today: a parent, your class teacher, "
    "or anyone at home you trust. You do not have to work this out on your "
    "own, and your studies can wait until you have."
)


def message_for(review: Review) -> str:
    """What to send the author, or empty if there is nothing to say."""
    if review.finding == SELF_HARM:
        return SUPPORT
    if review.should_warn:
        return WARNINGS.get(review.finding, "")
    return ""
