# NISAAB · نصاب

**An AI tutor for FBISE FSc students, built on the board's own syllabus.**

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/React-19-blue.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.124+-green.svg)](https://fastapi.tiangolo.com/)
[![Google Cloud](https://img.shields.io/badge/Google%20Cloud-Cloud%20Run%20%2B%20Vertex-4285F4.svg)](https://cloud.google.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Live: <https://nisaab.muhammadsaadcheema.com>**

---

NISAAB is an AI tutor for Pakistani students sitting the FBISE
Intermediate examination — FSc Pre-Medical, Pre-Engineering and ICS.

It is not a chatbot with a syllabus pasted into the prompt. **The FBISE
curriculum is in the database as rows**: every Student Learning Outcome
the board publishes, under its domain, under its subject, under its
year — 869 of them for Part 1. Teaching, questions, marking and progress
all hang off those rows.

That one decision is the product:

- an answer traces back to a published outcome, not a model's
  recollection
- a change to the board's pattern is a data update, not a retraining run
- a teacher can approve or reject a single generated item
- progress is measured against the same outcomes the real paper is

NISAAB explains in **English, Roman Urdu or اردو**, at the student's
choice.

## What it does

**For a student** — a tutor that retrieves from the syllabus and from
their own uploads; quizzes, flashcards, mind maps, notes and study plans
generated mid-conversation; SLO practice with mastery tracking; written
answers marked point by point against a scheme; full practice papers to
the FBISE blueprint (30% Knowledge, 50% Understanding, 20% Application);
a progress page showing mastery, cognitive levels, a weekly trend and an
activity calendar; and a class room shared with their own year and
group.

**For a teacher** — a dashboard of the classes they are taking, with the
meeting link available the whole time.

**For an administrator** — accounts, the teacher approval queue, the
weekly timetable, and the moderation queue.

Weekly sessions are arranged **by subject**, so one Physics XI class
serves Pre-Medical, Pre-Engineering and ICS students together.

## Stack

| | |
|---|---|
| API | FastAPI, Python 3.12, uv workspace |
| Worker | Background generation and document processing |
| Web | React 19, Vite, TanStack Router, Effect, Tailwind v4 |
| Database | PostgreSQL + pgvector (Cloud SQL) |
| Models | Gemini on Vertex AI |
| Auth | Google Identity Platform |
| Hosting | Cloud Run + Firebase Hosting, `asia-south1` |

Retrieval runs in Postgres with pgvector — no separate vector service.
At one board, two years and nine subjects, a dedicated vector database
would be another system to run for no gain.

## Documentation

**→ [The NISAAB handbook](docs/handbook/README.md)**

Fifteen chapters, written against the system as it actually runs. If you
read one, read **[13. Design
decisions](docs/handbook/13-decisions.md)** — the reasoning behind the
choices, which is the part you cannot recover from the code.

[14. Limitations](docs/handbook/14-limitations.md) says plainly what is
unfinished and unverified.

`docs/documentation/` and `docs/nisaab/` are superseded and kept only so
old links resolve.

## Running it locally

```bash
python -m uv sync

# API, on port 8010
cd src/edu-api && python -m uv run uvicorn main:app --reload --port 8010

# Web, on port 3000
cd src/edu-web && pnpm install && pnpm dev
```

Needs PostgreSQL with pgvector and a model key. See
[11. Operations](docs/handbook/11-operations.md).

The fastest way to check nothing is broken needs neither — the 22
offline checkers run in seconds with no database and no key:

```bash
python scripts/admin/check_roles.py
python scripts/admin/check_weekly_session.py
```

That is possible because the domain rules live in modules that import no
database. [12. Testing](docs/handbook/12-testing.md) explains why that
matters more than it sounds.

## Deploying

One script, every step re-runnable:

```bash
deploy/gcp/deploy.sh          # everything, first time
deploy/gcp/deploy.sh deploy   # API and worker
deploy/gcp/deploy.sh web      # the site
deploy/gcp/deploy.sh e2e      # 244 end-to-end checks, in the cloud
```

## Tests

| Layer | What |
|---|---|
| 22 offline checkers | Domain rules, no database needed |
| 244 end-to-end checks | Real database, real models, in the cloud |
| 58 Vitest tests | Frontend guards, routing, marking display |

## Status

Complete and live for **FSc Part 1** across all five subjects. Part 2
has Physics only. Attendance and email reminders are not built. AI
marking is labelled **AI-estimated** and has not been compared against
examiner marking — see
[14. Limitations](docs/handbook/14-limitations.md).

**NISAAB is not an official FBISE product.** Every page says so.

## Credits

Built on [EduAgent](https://github.com/StudentTraineeCenter/edu-agent)
by the Student Trainee Center, MIT licensed. NISAAB is a substantial
rework: the FBISE curriculum model, SLO-based mastery and progress,
FBISE paper generation and marking, class rooms, weekly sessions,
teacher accounts and the Google Cloud deployment are new.

MIT. See [LICENSE](LICENSE).
