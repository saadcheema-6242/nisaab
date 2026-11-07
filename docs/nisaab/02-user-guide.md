# 2 · User guide

[← Overview](01-overview.md) · [Contents](README.md) · [Next: Architecture →](03-architecture.md)

For students and teachers. No technical knowledge needed.

Open **<https://nisaab.muhammadsaadcheema.com>**

---

## Getting started

### The public site

Before signing in you land on the public site: **Home**, **Features**, **About** and
**Contact**. Home has a playable sample question — you can answer a real SLO-tagged
question without an account.

### Signing up

Sign up with an email and password. Logins are handled by Google Identity Platform, so
NISAAB never stores your password.

### Onboarding — three questions

| Step | Choose |
|---|---|
| **1. Class** | Class XI (HSSC-I) or Class XII (HSSC-II) |
| **2. Group** | Pre-Medical · Pre-Engineering · ICS (Computer Science) |
| **3. Language** | English · Roman Urdu · اردو |

Your group decides which subjects appear. Your language choice decides the language
**explanations** are written in — questions stay in the exam's own language, because
that is what you will sit.

You can change all three later in **Settings**.

---

## The dashboard — "My FSc"

One card per subject in your group. Each card opens that subject's workspace.

## Inside a subject

Three tabs: **Syllabus**, **Study**, **History**.

### Syllabus

The official FBISE curriculum for that subject, as a browsable tree:

```
Domain  →  Content area  →  SLO
```

Each SLO shows its code, its text, and a badge:

| Badge | Meaning |
|---|---|
| **K** | Knowledge — state, define, list |
| **U** | Understanding — explain, describe, distinguish |
| **A** | Application — calculate, apply, predict |

Some SLOs carry more than one badge. From any SLO you can ask for a quiz, flashcards,
a note or a mind map **scoped to just that outcome**.

### Study

Where you work. Start a **New chat** and ask in plain words — English, Roman Urdu or
Urdu. The tutor can:

- Explain a topic at the level the SLO asks for
- **Make a quiz** — multiple choice, with answers and explanations
- **Make flashcards** — for memory work
- **Write a note** — a structured summary
- **Draw a mind map** — for how ideas connect
- **Set a practice paper** — see below
- **Ask you questions** and mark your written answers
- **Search your uploaded documents** and answer from them, with sources
- **Search the web** when something is outside the syllabus

Just ask. "Give me 10 MCQs on vectors", "explain electric flux in Roman Urdu",
"set me a half board paper on Chapter 3" all work.

### Practice papers

This is the part that matches the real exam. Four lengths:

| Length | Physics / Chemistry / Biology / CS | Mathematics | Time |
|---|---|---|---|
| **Mini** | 12 marks | 14 marks | 20 min |
| **Short** | 28 marks | 33 marks | 45 min |
| **Half board** | 42 marks | 56 marks | 90 min |
| **Full board** | **80 marks** | **100 marks** | 180 min |

The full board paper is the exact FBISE shape — for Physics, 80 MCQs at ½ mark, 7 short
questions at 4, and 2 extended at 6. For Mathematics, 64 MCQs at ¾ mark, 7 short at 4,
and 3 extended at 8.

**A shorter paper asks fewer questions. It never changes what a question is worth** — so
a mini paper trains the same mark weights you will meet in the exam hall.

Write your answers in the app and submit. The AI marks the written answers against the
SLO and shows you the marks awarded out of the maximum, with feedback on each.

A full board paper takes about a minute to build. A half board paper took **38 seconds**
in testing.

### History

Everything you have ever made, in one place — quizzes, flashcard sets, papers, mind
maps, notes and study plans. Open any item to see it again, retake it, or download it.

Uploaded documents live in their own section, not in History.

---

## Downloads

Almost everything has a **Download** button, inside the item itself — open a paper and
the button is there, on that paper.

| Item | Formats |
|---|---|
| **Quiz** | PDF with answer key · PDF questions only · *Share as a Google Form* |
| **Flashcards** | PDF printable cards · images as a ZIP · single card as an image |
| **Paper** | PDF to attempt (no answers) · PDF with my answers · PDF with full solutions |
| **Mind map** | PNG · PDF |
| **Note** | PDF |

The paper's three modes are the useful part: print the blank one to attempt on paper,
then come back for the full solutions.

> **Share as a Google Form** creates a real Google Form quiz from your MCQs, copies the
> link, and opens it. Whoever you send it to can answer without signing in and sees
> their score and the explanations on the form itself. This feature needs a one-time
> setup step — see [Operations](09-operations.md).

---

## Uploading your own material

Upload notes, a past paper, or a chapter as PDF or an image. NISAAB extracts the text
(running OCR when it is a scan), splits it into segments and indexes it. After that the
tutor can answer from **your** material and tell you which part it used.

---

## For teachers

### The review queue

At **/review**, teachers listed as reviewers see AI-generated SLO content — explainers,
MCQs and short-response questions — and can approve or reject each item before students
rely on it.

This matters: grounding a question in an SLO controls *what* is asked, not whether the
science is correct. Review is how that gets checked.

### Setting work

Make a quiz on a specific SLO, then **Share as a Google Form** and send the link to a
class. Google marks it and each student sees their own score — nothing has to come back
through NISAAB.

---

## Settings

Change class, group and explanation language at any time. There are daily limits on
chat messages, quiz generations, flashcard generations and document uploads, so one
user cannot exhaust the shared AI budget.

---

[← Overview](01-overview.md) · [Contents](README.md) · [Next: Architecture →](03-architecture.md)
