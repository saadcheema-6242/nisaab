> **Superseded.** This describes an earlier version of NISAAB and is no
> longer maintained. The current documentation is
> [docs/handbook](../handbook/README.md), written 9 November 2026.
> This file is kept only so older links still resolve.

# NISAAB — Documentation

**NISAAB** (نصاب, *syllabus*) is an AI tutor for Federal Board (FBISE) FSc students.
Every question it writes, every paper it sets and every answer it marks is tied to a
numbered **SLO** — a Student Learning Outcome from the official FBISE curriculum.

Live: **<https://nisaab.muhammadsaadcheema.com>**

| | |
|---|---|
| **Team** | Muhammad Saad Cheema (development) · Hashir Naveed (UI design) · Fatin Khan Jadoon (presentation) |
| **Supervisor** | Prof. Muhammad Tashfeen Qamar |
| **Institution** | Islamabad Model College for Boys, G-10/4 |
| **Event** | FDE STEM Competition, 29 October 2026 |
| **Cloud** | Google Cloud project `fbise-tutor-2026`, region `asia-south1` (Mumbai) |

---

## Table of contents

| # | Document | What it covers |
|---|---|---|
| 1 | [Overview](01-overview.md) | The problem, what NISAAB does, why SLO grounding is the whole idea |
| 2 | [User guide](02-user-guide.md) | For students and teachers — every screen and what it does |
| 3 | [Architecture](03-architecture.md) | How the pieces fit, and what happens during a request and a job |
| 4 | [Backend](04-backend.md) | FastAPI, the services layer, the database, the job queue |
| 5 | [Frontend](05-frontend.md) | React app, routing, state, the PDF export pipeline |
| 6 | [AI layer](06-ai.md) | The agent, its 28 tools, model roles, and how SLOs reach the prompt |
| 7 | [Cloud and deployment](07-cloud.md) | Google Cloud resources, `deploy.sh`, cost controls |
| 8 | [Curriculum data](08-curriculum-data.md) | The FBISE data NISAAB is built on, and the exam paper patterns |
| 9 | [Operations](09-operations.md) | Running it, verifying it, troubleshooting, known limits |

---

## The system at a glance

Everything below is counted from the source, not estimated.

| | |
|---|---|
| REST endpoints | **93** across 19 routers |
| AI tools the tutor can call | **28** across 8 modules |
| Database tables | **28** models, 41 migrations |
| Web routes | **23** |
| Python / TypeScript files | 171 / 232 |
| SLOs loaded | **1,020** across 41 domains and 100 content areas |
| Subjects | Biology, Chemistry, Computer Science, Mathematics, Physics (XI); Physics (XII) |

### Measured performance

From the end-to-end benchmark run in the cloud on 27 October 2026 (`deploy.sh e2e`,
**52 checks, 52 passed, 0 failed**):

| Operation | Time |
|---|---|
| Half board paper (42 marks) built | 38 s |
| Half board paper marked | 11 s |
| Short paper built / marked | 9 s / 9 s |
| Quiz card generated | 4 s |
| SRQ marked | 6 s |

---

## As one PDF

The whole set is also typeset as **`NISAAB_Documentation.pdf`** — 37 pages, cover,
contents and bookmarks — kept beside the repository folder with the report and the
trifold. The markdown here is the source; regenerate the PDF after editing it:

```bash
python scripts/docs/build_documentation_pdf.py
```

## How to read this

- **A judge or teacher** wants [Overview](01-overview.md) then [User guide](02-user-guide.md).
- **Someone assessing the engineering** wants [Architecture](03-architecture.md),
  then [AI layer](06-ai.md) — that is where the real design decisions live.
- **Whoever maintains this next** wants [Operations](09-operations.md) first, because it
  records what breaks and why.

### A note on the older documents

`docs/` also holds files inherited from the open-source template this project started
from — `ARCHITECTURE.md`, `FEATURES.md`, `BEST_PRACTICES.md`, `AZURE_DEPLOYMENT.md`,
`LOCAL_DEVELOPMENT.md`. They describe the generic EduAgent application and an Azure
deployment that **NISAAB no longer uses**. This folder supersedes them. The planning
documents (`FBISE_FSC_V1_PLAN.md`, `FBISE_MATERIALS_PLAN.md`, and the three `*_PLAN.md`
idea files) are still current as *plans* — they record intent, not what is built.

*Last verified against the source on 27 October 2026.*
