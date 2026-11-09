# 1. Overview

## What NISAAB is

NISAAB (نصاب, "syllabus") is an AI tutor for Pakistani students sitting
the FBISE Intermediate examination — FSc Pre-Medical, Pre-Engineering and
ICS, years 11 and 12.

It is not a chatbot with a syllabus pasted into the prompt. The FBISE
curriculum is held in the database as rows: every Student Learning
Outcome (SLO) the board publishes, under its domain, under its subject,
under its year. Teaching, questions, marking and progress all hang off
those rows.

That one decision is what the rest of the product is built on. It means:

- an answer can be traced back to a published outcome, not to a model's
  recollection;
- when FBISE changes the pattern, that is a data update, not a retraining
  run;
- a student's progress is measured against the same outcomes the real
  paper is measured against.

## Who it is for

A student in Islamabad or Rawalpindi studying for FSc, usually on a
phone, often on a slow connection, frequently more comfortable reading an
explanation in Roman Urdu or Urdu than in English. NISAAB explains in
English, Roman Urdu or اردو, at the student's choice.

Teachers take weekly live sessions. An administrator arranges the
timetable and decides who is allowed to teach.

## What is real today

Everything below runs in production at
<https://nisaab.muhammadsaadcheema.com>.

| Area | State |
|---|---|
| Syllabus map, 869 SLOs for FSc Part 1 | Live |
| Tutor chat with retrieval over the syllabus | Live |
| Quizzes, flashcards, mind maps, notes, study plans | Live |
| SLO practice and mastery tracking | Live |
| Written-answer (SRQ) marking against a points scheme | Live, marks shown as AI-estimated |
| Practice papers to the FBISE blueprint | Live |
| Progress: mastery, cognitive levels, weekly trend, activity | Live |
| Class rooms (community), with moderation | Live |
| Weekly sessions, teacher accounts, admin approval | Live |
| Admin dashboard | Live |
| Attendance | Not built |
| Email reminders | Not built |

Part 2 (year 12) curriculum data is not loaded. The product is complete
for Part 1.

## What it is not

- **Not an official FBISE product.** Every page carries that notice.
- **Not a marking authority.** Written answers are marked by a model
  against a points scheme and labelled AI-estimated. They have not been
  compared against real examiner marking, and chapter 14 says so again.
- **Not a replacement for a teacher.** The weekly sessions exist because
  a person in front of a class is the thing the software is arranged
  around, not a feature bolted onto it.

## Status and dates

- FBISE STEM exhibition: **13 November 2026**
- This handbook: written **9 November 2026**
- Deployed on Google Cloud, project `fbise-tutor-2026`, region
  `asia-south1`

Next: [2. Architecture](02-architecture.md)
