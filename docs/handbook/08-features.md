# 8. Features

Surface by surface, as a student meets them.

## Landing

Dark page, a constellation of the 869 Part 1 outcomes, a chalk diagram
that draws itself, Urdu in the subheading, and a playable question so a
visitor can try the product before signing up. Honours
`prefers-reduced-motion`: with it on, nothing animates.

## Onboarding

First: student or teacher. A student then picks year, group and
explanation language (English, Roman Urdu, اردو) and gets their subject
projects. A teacher gives subjects and years and goes to the waiting
page. An administrator skips the question and picks a starting cohort.

## My FSc — the student dashboard

The subject workspaces, one card each, with the SLO count when the
syllabus map is loaded for that subject. Below: a progress summary, and
the student's own projects for material outside the nine subjects.

## The tutor

A chat per project. It retrieves from the syllabus and from the student's
uploaded documents, explains in their chosen language, and can build
things mid-conversation: a quiz, a flashcard set, a mind map, a note, a
study plan, or a practice run. Those appear as cards in the thread, not
as walls of text.

Diagrams and figures are generated where a picture is the explanation.
Maths renders through KaTeX.

## Syllabus map

The board's domains and outcomes for a subject and year, with the
student's mastery against each. This is the view that makes "what have I
actually not done yet" answerable.

## Practice and mastery

Questions tied to specific SLOs. Each answer updates the mastery estimate
for that outcome (chapter 4). Flashcards are self-graded and count for
half as much.

## Written answers (SRQ)

The student writes a real answer. It is marked point by point against a
scheme, with the total computed in code. For Computer Science the marking
also judges whether the code would run.

Marks are labelled **AI-estimated** throughout.

## Practice papers

A full paper to the FBISE blueprint — 30% Knowledge, 50% Understanding,
20% Application — with stimulus sets and (a)-or-(b) choice pairs handled
properly: only the answered part counts, and answering both takes the
better one.

## Progress

Four tabs:

- **Mastery** per outcome and per domain
- **Cognitive levels**, each shown against what the paper weights it,
  because 60% on Application and 60% on Understanding are not the same
  problem
- **Weekly trend**, a line that draws itself left to right, with the
  current week's point drawn larger
- **Activity**, a calendar of the last twelve weeks

The gaps in the calendar are deliberate. A chart of only the days a
student worked is a trophy cabinet; the empty squares are what say, with
no nagging, that last week went quiet.

An outcome never attempted is **not counted as a weakness**. It is not
counted at all.

## Class rooms

One room per (grade, group) — six in total. Posts, replies, polls, image
attachments.

Posts containing phone numbers or email addresses are refused: teenagers
exchanging contact details in a public room is the risk this product most
needs to avoid creating. Reports go to the admin moderation queue.

Administrators post as **Admin**, and can read any room.

## Weekly sessions

Live classes with a teacher, arranged by an administrator.

A session is for a **subject and year**, so Physics XI is one class and
Pre-Medical, Pre-Engineering and ICS students all join it.

A student is given the join link **fifteen minutes before the start** and
not before — withheld by the server, not hidden by the page. A teacher
has it the whole time.

## My classes — the teacher dashboard

The next class, large, with the link; the rest of the week below. When
nothing is timetabled it says so, and says whose job that is, rather than
showing an empty page that reads as a broken app.

## Admin dashboard

Accounts, Teachers, Sessions, Moderation. Chapter 7.

## Review content

For reviewers: approve or reject generated SLO content item by item, with
a note. Students never see rejected items; approved quizzes carry a
**Teacher-checked** badge.

## Usage limits

Per day, per account, from `config.py`:

| Limit | Default |
|---|---|
| Chat messages | 100 |
| Quiz generations | 30 |
| Flashcard generations | 20 |
| Document uploads | 10 |
| Class room posts | 40 |

Next: [9. Frontend](09-frontend.md)
