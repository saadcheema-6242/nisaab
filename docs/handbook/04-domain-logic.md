# 4. Domain logic

Everything here lives in `src/shared/core/src/edu_core/` as a module with
**no database import**. Values in, values out. Chapter 12 shows what that
buys.

## Mastery — `mastery.py`

How well a student knows one SLO, as a number between 0 and 1.

It is an **exponentially weighted** accuracy: recent answers count for
more than old ones, but never so much that one bad morning erases a
term's work.

```python
def advance(attempts, mastery, score, factor=1.0) -> tuple[int, float]:
    attempts += 1
    weight = 1.0 if attempts == 1 else min(1.0, max(1 / attempts, MIN_WEIGHT) * factor)
    return attempts, mastery + weight * (score - mastery)
```

- The first answer sets the estimate outright; there is nothing to
  average against.
- After that the weight decays as `1/attempts`, so early answers move it
  a lot and later ones refine it.
- `MIN_WEIGHT = 0.3` stops the decay. Without a floor, a student who has
  answered an outcome thirty times could no longer show that they had
  learned it.
- `SELF_RATED_WEIGHT = 0.5` halves the weight of a flashcard the student
  graded themselves, because that is a weaker signal than a marked
  question.

`estimate()` is a fold over `advance()`. **One definition of the step**,
used by both. That is not tidiness: a bug in October came from the step
being written twice, once in the estimator and once in the trend, and the
two disagreeing — 0.882 where the answer was 1.0. Chapter 12 explains why
the checker missed it.

## Progress over time — `progress_trend.py`

Weekly mastery, for the graph on the Progress page.

The subtlety is that a week's figure is the **mean of per-outcome
estimates**, not one estimate over all answers pooled together. Pooling
lets a student who drilled one easy outcome forty times look like a
student who knows the subject.

State is therefore kept per SLO and averaged at each week boundary.

Weeks are Pakistan weeks: `PAKISTAN_OFFSET_HOURS = 5`, exported from this
module and imported elsewhere rather than copied, so a UTC-midnight
answer lands in the day the student actually sat down.

## Marking — `grading.py`, `answer_check.py`

A written answer is marked against a **points scheme**, each point worth
whole marks. Each point is judged separately by the model at temperature
0, and **the total is added up in code**, not by the model. Models are
poor at arithmetic and good at judgement; this gives each the job it is
suited to.

For an (a)-or-(b) choice pair, only the answered part counts. If a
student answers both, the better one is taken, and the pair counts once
toward the section and paper totals.

For Computer Science the prompt also judges whether submitted code would
run under Python 3.

Marks are presented as **AI-estimated** everywhere. See chapter 14.

## The FBISE paper — `paper_blueprint.py`

A generated practice paper follows the board's own weighting:

| Level | Share of the paper |
|---|---|
| Knowledge | 30% |
| Understanding | 50% |
| Application | 20% |

This is also why the Progress page shows mastery *against paper weight*.
Sixty percent on Application and sixty percent on Understanding are not
the same problem, and only the weighting tells a student which to revise
first.

## Weekly sessions — `weekly_session.py`

Rules for a live class.

**`check_link`** accepts only `https` to a known meeting host
(`meet.google.com`, `zoom.us`, `teams.microsoft.com`, `teams.live.com`,
`webex.com`). It reads `parsed.hostname`, which matters: a link like
`https://meet.google.com@evil.example/x` has `meet.google.com` as
*credentials*, not as the host, and a naive substring check would accept
it.

**`JOIN_OPENS_MINUTES = 15`** — a student is given the link fifteen
minutes before the start and not before. The server withholds it; the
page never receives it. Hiding a link in the markup puts it in the
network tab for anyone who looks.

A teacher gets the link the whole time: they have to be in the room
before the students are.

**`groups_for(subject)`** derives which groups may attend from the
subject, so one Physics class serves Pre-Medical, Pre-Engineering and
ICS.

## Roles — `roles.py`

```python
def is_approved_teacher(role, approved_at) -> bool:
    return role == TEACHER and approved_at is not None
```

Both halves. The role says what they asked to be; the date says an
administrator agreed. **Anything that reads one without the other is a
hole** — and the specific hole this module exists to prevent is listing
"who can teach" by role alone, which quietly offers every stranger who
ticked a box at signup as assignable to a real class.

`needs_onboarding()` returns where an account must go before it can use
the app: `/onboarding`, `/awaiting-approval`, or nothing. One function,
so the question is answered the same way by the API and the router.

## Class room rules — `community_rules.py`, `personal_details.py`, `moderation.py`

Posts are scoped to the author's own (grade, group) and that scoping is
server-side; the client cannot ask for another room.

`personal_details.py` refuses posts containing phone numbers, email
addresses and similar — teenagers sharing contact details in a public
room is the risk this product most needs to not create. Physics notation
that looks like a phone number is deliberately allowed; the end-to-end
suite checks both directions.

Next: [5. The AI layer](05-ai-layer.md)
