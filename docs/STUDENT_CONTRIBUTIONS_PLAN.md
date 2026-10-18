# Plan: student-contributed material

Written 18 Oct 2026. The idea: students upload their own notes and agree to
share them, so the shared knowledge grows with material written by Pakistani
students for Pakistani exams — the kind of local method and example a general
model does not have.

## What consent does and does not settle

Asking the student to agree is the right instinct, and it settles the first
problem. It does not settle the other two.

| Problem | Does consent fix it? |
|---|---|
| **Privacy** — another student's notes carry their name, their teacher's comments | **Mostly yes.** An explicit, specific agreement is a fair basis, with the limits below |
| **Copyright** — a student uploads the NBF textbook and ticks "share" | **No.** They cannot grant a right they do not hold. The tick is worthless here |
| **Quality** — wrong notes, or a joke file, now answer everyone's questions | **No.** Consent says nothing about whether the content is correct |

Two further limits on the privacy side: FSc students are 16-18, so consent from
a minor is weaker than consent from an adult and may need a parent or the
college behind it; and a student's notes may contain other people's information,
which the student cannot consent away on their behalf.

So the design needs three gates, not one: **consent, a rights declaration, and
review.**

## The shape I would build

Do not share whole documents. Share the useful piece, tied to an SLO, through
the bank that already exists.

```
Student uploads a file            -> private library (works today)
Student offers part of it         -> consent + rights declaration
AI extracts a candidate item      -> tied to one SLO, kind = explainer / mcq / srq
Item enters the bank as a draft   -> source = "student_contributed"
Reviewer approves or rejects      -> existing review page
Approved only                     -> served to other students, labelled
```

This fits what is already there. `ContentItem` already carries `review_status`
(draft / approved / rejected), `review_note`, `reviewed_by`, `reviewed_at` and
`source`; `routers/review.py` already gates reviewers by email; and
`features/review/review-page.tsx` is already the queue. Nothing new is needed
for the hard part.

Sharing extracted items rather than raw files also narrows the copyright
exposure: a student's own worked method for a numerical is theirs to give, in a
way that a scanned textbook chapter never is.

## Work

### 1. Database (small)

- `content_items.contributed_by` — the student's user id, nullable.
- `content_items.source` — allow `"student_contributed"`.
- `documents.share_status` — `private` (default) / `offered` / `withdrawn`.
- `documents.rights_declared_at` — when they made the declaration.

### 2. "My materials" section

A real place for a student's own files, not buried inside each subject:

- Everything they have uploaded, with its subject.
- Plain wording: "Only you can see these."
- Delete at any time.
- Per document, an **Offer to the shared bank** action.

### 3. The offer flow

When a student offers a document, they see one screen, in their own language,
with two separate ticks — not one lumped agreement:

- "This is my own work, or I am allowed to share it." (rights)
- "Other students may be shown material based on this, after a teacher checks
  it." (consent)

Then: which subject and topic it covers, and an optional note to the reviewer.
They can withdraw at any time, which pulls any unapproved items and stops
further use of approved ones.

### 4. Extraction

A worker job reads the offered document and proposes bank items against matching
SLOs — an explainer, MCQs, or a worked short answer. Each is saved as a draft
with `source="student_contributed"` and `contributed_by`.

The student's name is never attached to what other students see; the credit line
is "shared by a student, checked by a teacher".

### 5. Review

The existing page, with three additions: show that the item is
student-contributed, show the reviewer the source passage it came from, and
allow reject-with-reason (including "appears to be from a textbook").

### 6. How it is used and labelled

Approved student items join the bank and are used like any other, with one
difference: the tutor says where it came from. "From the FBISE syllabus" and
"from reviewed student notes" must never look the same to a student.

Keep official FBISE content ranked above contributed content when both match.

## Risks to keep in view

- **Nothing goes live unreviewed.** Without the gate this feature becomes a way
  to publish pirated textbooks through our account.
- **Review is a real cost.** Every contribution needs a human. Without a
  teacher signed up, do not turn the feature on; the offer queue just grows.
- **Say it plainly to judges.** "Students may contribute, a teacher approves,
  and answers show which is which" is a strong answer. "Students upload and the
  AI learns from everything" invites exactly the questions we would not want.

## Timing

This is roughly 3-4 days: a day for the section and the offer flow, a day for
extraction, a day for review changes and labelling, and a day to test.

The competition is 29 October, eleven days away, and Part 2 (Class XII), the
report, the board and the demo script are all still to do. **Build this after
the competition.** It is, though, an excellent thing to describe on the board
as the next step: it shows the project has a path to growing beyond what one
student can build.
