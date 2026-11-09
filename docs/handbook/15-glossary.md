# 15. Glossary

## FBISE and Pakistani schooling

**FBISE** — Federal Board of Intermediate and Secondary Education, the
examination board NISAAB is built against.

**Intermediate / FSc** — the two years after matriculation, years 11 and
12. "FSc" is the science stream.

**Part 1 / Part 2** — year 11 and year 12. NISAAB's curriculum data is
complete for Part 1; Part 2 has Physics only.

**Group** — the subject combination a student takes:

| Group | Subjects |
|---|---|
| Pre-Medical | Physics, Chemistry, Biology |
| Pre-Engineering | Physics, Chemistry, Mathematics |
| ICS | Physics, Mathematics, Computer Science |

**SLO** — Student Learning Outcome. One statement of something a student
should be able to do, published by the board with a code and a cognitive
level. The row everything in NISAAB hangs off.

**Domain** — the board's grouping of SLOs within a subject and year;
roughly a chapter.

**Cognitive level** — Knowledge, Understanding or Application. The paper
weights them 30 / 50 / 20.

**Assessment framework** — the board's published document setting out
outcomes, weights and paper structure. `scripts/seed/` parses it.

**SRQ** — Short Response Question. A written answer, marked against a
points scheme.

**Stimulus set** — several questions sharing one passage, diagram or
data table.

**Choice pair** — an (a)-or-(b) question. Only the answered part counts;
answering both takes the better one.

## NISAAB

**نصاب (nisaab)** — Urdu for "syllabus" or "curriculum".

**Mastery** — an exponentially weighted estimate, 0 to 1, of how well a
student knows one SLO. Computed, never stored.

**Attempt / practice record** — one answer to one SLO.

**Project** — a workspace. One per subject, plus any the student makes
for their own material.

**Class room** — the discussion room for one (grade, group). Six exist
and are never created; a post simply carries the pair.

**Weekly session** — a live class with a teacher, for a subject and
year, arranged by an administrator.

**Join window** — the fifteen minutes before a session when the server
will give a student the meeting link.

**Surface** — which part of the app an account is for: student, teacher
or admin. `lib/surface.ts`.

**Approved teacher** — role `teacher` *and* `teacher_approved_at` set.
Both halves; one without the other is not a teacher.

**Content item** — pre-generated SLO content awaiting review.

**Teacher-checked** — the badge on content a reviewer approved.

**AI-estimated** — the label on every mark produced by the model, which
stays until marking is compared against a real examiner.

## Technical

**Pure module** — a file in `edu_core` with no database import. Values
in, values out, checkable offline.

**Checker** — a script in `scripts/admin/` that asserts the rules
without a database.

**Atom** — a unit of server state in the frontend, read as a `Result`.

**Result** — `Initial`, `Success` or `Failure`. Never a half-filled
object.

**`send_to`** — the field on `/teachers/me` saying where an account must
go before it can use the app: `/onboarding`, `/awaiting-approval`, or
nothing.
