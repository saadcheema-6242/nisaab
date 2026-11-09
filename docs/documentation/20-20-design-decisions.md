> **Superseded.** This describes an earlier version of NISAAB and is no
> longer maintained. The current documentation is
> [docs/handbook](../handbook/README.md), written 9 November 2026.
> This file is kept only so older links still resolve.

# 20. Design Decisions

| Decision | Alternative | Why we chose this |
|---|---|---|
| Ground the model in the syllabus | Fine-tune a model on the syllabus | Fine-tuning hides knowledge in weights that cannot be inspected or corrected, needs a large labelled set and a full retraining cycle. Grounding keeps the syllabus as readable rows, updated in days, with item-by-item teacher control. |
| PostgreSQL as the job queue | A dedicated broker such as Redis | A broker would scale further, but at this size the database queue removes a whole stateful dependency and keeps job state consistent with the data. |
| Pre-generate practice | Generate on demand | On-demand is simpler but slow and unpredictable. A pre-generated bank is near-instant, predictable in cost and can be reviewed by a teacher. Measured: about 202 seconds down to about 4. |
| Two retrieval methods | Vector search everywhere | Term-rarity scoring suits the small, curated and stable syllabus and is easier to explain. Vector search suits students' unpredictable notes. |
| Pattern held as data | Pattern written into code | A change by FBISE becomes a data update, not a rewrite. |
| Agent with tools | One prompt and one reply | Lets the tutor choose to look up the syllabus, start a quiz or ask a question first, and show results as interactive cards. |
