# The NISAAB handbook

Written 9 November 2026, against the system as it actually runs.

This replaces `docs/documentation/` and `docs/nisaab/`, which described an
earlier version of the product and had drifted: between them they ran to
about 2,900 lines without mentioning weekly sessions, teacher accounts or
the class rooms, and they covered the same ground twice, so a reader could
not tell which was current. One home for prose is worth more than two.

## Who should read what

| You are | Start at | Then |
|---|---|---|
| A judge, teacher or visitor | [1. Overview](01-overview.md) | [8. Features](08-features.md) |
| A developer, new to this | [2. Architecture](02-architecture.md) | [3. Data model](03-data-model.md), [4. Domain logic](04-domain-logic.md) |
| Reviewing the engineering | [13. Design decisions](13-decisions.md) | [4. Domain logic](04-domain-logic.md), [12. Testing](12-testing.md) |
| Running or deploying it | [11. Operations](11-operations.md) | [10. API](10-api.md) |

## Contents

1. [Overview](01-overview.md) — what NISAAB is, who it is for, what is real today
2. [Architecture](02-architecture.md) — the monorepo, the services, how a request flows
3. [Data model](03-data-model.md) — the tables and what they mean
4. [Domain logic](04-domain-logic.md) — mastery, marking, sessions, roles
5. [The AI layer](05-ai-layer.md) — models, retrieval, tools, marking
6. [Curriculum](06-curriculum.md) — how the FBISE syllabus becomes rows
7. [Accounts and access](07-accounts-and-access.md) — students, teachers, administrators
8. [Features](08-features.md) — surface by surface
9. [Frontend](09-frontend.md) — React, Effect, the design system
10. [API](10-api.md) — the routes and what guards them
11. [Operations](11-operations.md) — deploying, migrating, recovering
12. [Testing](12-testing.md) — checkers, the end-to-end suite, what is not covered
13. [Design decisions](13-decisions.md) — why, not what
14. [Limitations and roadmap](14-limitations.md) — what is honestly not finished
15. [Glossary](15-glossary.md) — FBISE and NISAAB vocabulary

## A note on honesty

Several chapters say plainly that something is unfinished, unverified or
known to be wrong. That is deliberate. Documentation that describes the
system you wish you had is worse than none, because the first person it
misleads is the next developer, and the second is you in three months.

Where a number is given it was measured, not estimated. Where something is
untested it says so.
