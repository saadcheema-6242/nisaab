# 13. Design decisions

The chapter worth reading. Anyone can read the code and see *what* it
does; none of this is recoverable from it.

Each entry: the decision, why, and what it costs.

---

## The syllabus is rows, not a fine-tuned model

**Why.** Three things follow that otherwise could not. An explanation can
be traced to a published outcome. A change to the FBISE pattern is a data
edit, not a retraining run. And a teacher can approve or reject a single
generated item — you cannot approve one fact inside a fine-tuned model.

**Cost.** Someone has to parse the board's PDFs and keep the rows right.
That work is real and it is in `scripts/seed/`.

---

## Rules live in modules that cannot touch the database

**Why.** So they can be checked by a script that runs in two seconds with
no Postgres, no pgvector and no API key. A suite that needs a database
container is a suite nobody runs before pushing, and rules that are never
checked are rules that quietly stop holding.

**Cost.** An extra indirection: the service reads rows, the pure module
decides, the service writes. Slightly more code than putting the
arithmetic inline.

**Evidence it was right.** 22 checkers that a developer actually runs,
including 62 assertions on session rules and 40 on roles.

---

## Mastery is computed, never stored

**Why.** A stored figure and the records it came from are two sources of
truth, and they drift the first time a record is corrected or deleted.

**Cost.** Recomputation on read. At this data size it does not matter.

---

## Mastery has a weight floor

`MIN_WEIGHT = 0.3`.

**Why.** With a pure `1/attempts` decay, a student who has answered an
outcome thirty times can no longer demonstrate that they have learned it;
the estimate is frozen by its own history. A floor keeps recent evidence
able to move the number.

**Cost.** The estimate is slightly noisier late on. That is the right
trade for a learner: the point is to reflect what they know *now*.

---

## An unattempted outcome is not a weakness

**Why.** Honesty. Counting "never tried" as "cannot do" would make every
new student look hopeless and make the number useless as a guide to what
to revise.

**Cost.** The headline figure covers only what has been practised, which
has to be explained on the page. It is.

---

## Approval is a date, not a boolean

`users.teacher_approved_at`, nullable, with `teacher_approved_by`.

**Why.** The dates are the whole state. A boolean beside a timestamp
drifts the first time one is written without the other. The ban state on
the same table already worked this way.

**Cost.** Every check is `is not None` rather than a flag, and both
halves — role *and* date — must be read together. `roles.py` exists to
make sure they always are.

---

## "Who can teach" is never filtered on the role alone

**Why.** This is the one that would actually hurt someone. Anybody can
tick "I am a teacher" at signup. Listing teachers by `role == 'teacher'`
looks correct, reads correctly, and quietly offers every stranger who
ticked the box as assignable to a class of real children.

**Cost.** None worth mentioning. `can_teach()` is three lines and
`ClassSessionService.create()` re-checks it server-side even though the
dropdown already filtered.

---

## Administrators are an environment variable, not a column

`ADMIN_EMAILS`.

**Why.** There is no privilege-escalation path through the database. No
bug in a profile update, no row in a seed file, no compromised account
can make someone an administrator. Changing the list requires deploy
access, which is a different and stronger thing than application access.

**Cost.** Real. Making someone an administrator needs a redeploy, not a
click, and the list is invisible from inside the app. For a product with
one or two administrators this is the right side of the trade; at fifty
it would not be.

---

## An administrator is all three roles, not a fourth

**Why.** A fourth kind of account means a fourth set of paths through
every screen, each one untested. Making the administrator a student of
every cohort and also a teacher means they travel the same code the
students do — so if it breaks for them it was already broken.

**Cost.** Their cohort has to be *unpinned* in several places (the room
switcher, the unfiltered timetable), each a small special case.

---

## A session belongs to a subject, not a group

**Why.** All three FSc groups study Physics. Scheduling per group would
have produced three identical Physics classes a week, and nothing in the
system to notice. Deriving attendance from the subject means one class,
one teacher, one link.

**Cost.** "Who can attend" is computed rather than stored, so it cannot
be overridden for a one-off.

---

## The join link is withheld by the server

**Why.** Sending the link and hiding it in the page puts it in the
network tab for anyone who opens dev tools. The fifteen-minute window is
only a window if the link genuinely is not there.

**Cost.** The page cannot show a disabled "Join" button with a real
target. It shows the time instead, which is more useful anyway.

---

## Hiding a link is not access control

`surfaceFor()` is read by both the sidebar and the route guard.

**Why.** A hidden link still has a URL. A guard without a matching
sidebar is a dead end users are invited to walk into. Both need the same
answer, so both read the same function; two copies of a rule is how they
come to disagree.

**Cost.** The rule must live somewhere neutral — `lib/surface.ts` — and
be imported by both.

---

## 404 rather than 403 on admin routes

**Why.** 403 confirms the endpoint exists and that the caller is simply
the wrong person. 404 tells a curious student nothing.

**Cost.** Slightly more confusing to debug if you forget. The log still
says what happened.

---

## Marks are added up in code, not by the model

**Why.** Models are good at judgement and bad at arithmetic. Each scheme
point is judged separately at temperature 0; the total is Python.

**Cost.** More calls per answer. Worth it: a marking total that is
occasionally wrong is worse than no marking at all.

---

## One cloud provider

**Why.** Cloud Run, Cloud SQL, Cloud Storage, Identity Platform and
Vertex all in `asia-south1` means one bill, one IAM model, one region,
one place to look when something breaks, and the lowest latency available
to Pakistan. For a two-person project, operational surface is the scarce
resource.

**Cost.** Lock-in, and no second opinion when a region has a bad day.

---

## Self-hosted fonts

**Why.** The product is demonstrated at an exhibition where the network
may be poor. A blocked font request means a flash of fallback type at
exactly the moment a judge forms a view. Variable weights keep it to one
file per family.

**Cost.** ~130 KB of woff2 in the bundle, and updates are manual.

---

## Motion is skipped under prefers-reduced-motion

**Why.** Standard accessibility, but also concrete here: the machine the
product is demonstrated from has Reduced Motion switched on, so the still
path is the one most likely to be seen. It has to be the good one.

**Cost.** Every animated component needs both paths written and checked.

Next: [14. Limitations and roadmap](14-limitations.md)
