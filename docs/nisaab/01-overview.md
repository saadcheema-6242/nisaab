# 1 · Overview

[← Contents](README.md) · [Next: User guide →](02-user-guide.md)

---

## The problem

An FSc student preparing for the Federal Board exam has three things to work with: a
textbook, a pile of past papers, and a guidebook. None of them tells them the one thing
that actually decides their marks — **which specific learning outcome a question is
testing, and whether they can do it.**

Two further problems make this worse:

1. **The paper pattern changed.** Under the NCP 2022-23 curriculum, FBISE moved to a
   50% MCQ / 50% descriptive scheme. Past papers printed before that change drill a
   format the student will not sit.
2. **"Practice" is undirected.** A student who fails a question on electric flux does
   not know whether the gap is the definition, the formula, or applying it to a new
   case — so they re-read the whole chapter, which is the slowest possible fix.

Generic AI tutors do not solve this. Ask one for "a Physics test" and it produces
plausible physics — not *Federal Board, Class XI, Domain C, 4 marks, application-level*
physics. The output looks right and trains the wrong thing.

## What NISAAB does

NISAAB is built around the **SLO** — the numbered Student Learning Outcome that FBISE
publishes for every topic. 1,020 of them are loaded into the database, each carrying
its domain, content area, cognitive level and assessment form.

Every piece of content NISAAB produces is generated **from an SLO, and labelled with
it**. That single decision is what separates this from a chatbot:

- A quiz question is not "a question about moments" — it is a question against
  **SLO-level** text, tagged **K**, **U** or **A**.
- A practice paper is not "20 questions" — it is the **exact FBISE shape** for that
  subject, with the real marks per question.
- A wrong answer does not produce "study harder" — it points at the SLO that was missed.

### Why that matters for marks

Because the SLO carries a **cognitive level**, the student can see the shape of their
own weakness rather than just a score:

| Level | Code | What it asks |
|---|---|---|
| Knowledge | **K** | State, define, list, recall |
| Understanding | **U** | Explain, describe, distinguish, interpret |
| Application | **A** | Calculate, apply, derive, predict in a new situation |

A student scoring well on K and poorly on A has a *specific* problem with a *specific*
fix. That is information neither a textbook nor a past paper gives them.

## What is actually built

Not a prototype, and not slideware — a deployed application on Google Cloud that a
student can sign into right now.

| Capability | State |
|---|---|
| SLO-grounded chat tutor with 28 tools | Working |
| Quizzes, flashcards, notes, mind maps — all SLO-scoped | Working |
| Full FBISE board papers, half papers, short papers | Working, marks verified |
| AI marking of short and extended responses | Working |
| Document upload with OCR, then RAG over it | Working |
| PDF export of every artefact, in three modes for papers | Working |
| Practice history as a browsable library | Working |
| Teacher review queue for generated content | Working |
| Share a quiz as a Google Form | Working — needs re-authorising weekly until Google verifies the app, see [Operations](09-operations.md) |

## The honest limits

Documentation that only lists strengths is marketing. These are real:

- **Coverage is uneven.** Chemistry XI has 329 SLOs loaded; Computer Science XI has 22.
  Class XII exists for Physics only. See [Curriculum data](08-curriculum-data.md).
- **A handful of SLOs are classified oddly** in the source data — five Biology SLOs that
  read as theory are marked `practical`, and Physics Domain N's 27 practical-skills SLOs
  are marked `formative`. These come from the FBISE documents as published.
- **The AI can still be wrong.** Grounding a question in an SLO constrains *what* is
  asked, not whether the physics is right. The teacher review queue exists for exactly
  this reason, and generated content is reviewable rather than presumed correct.
- **It is not a replacement for a teacher.** It is a way to practise the right thing
  between lessons.

---

[← Contents](README.md) · [Next: User guide →](02-user-guide.md)
