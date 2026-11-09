# 6. Curriculum

## The groups

FBISE Intermediate has three groups, and they overlap:

| Group | Subjects |
|---|---|
| Pre-Medical | Physics, Chemistry, Biology |
| Pre-Engineering | Physics, Chemistry, Mathematics |
| ICS | Physics, Mathematics, Computer Science |

`GROUP_SUBJECTS` in `edu_core/group_change.py` is the single statement of
this, and a surprising amount follows from it.

All three groups study **Physics**. Pre-Medical and Pre-Engineering share
**Chemistry**. Pre-Engineering and ICS share **Mathematics**. So a
Physics session is one class for the whole year group, and
`weekly_session.groups_for("PHY")` returns all three. Scheduling by group
instead of by subject would have produced three identical Physics classes
a week and no way to notice.

It also decides what a student sees: their projects, their syllabus map,
their timetable and their class room are all derived from
(grade, group).

## From the board's documents to rows

The board publishes its scheme in PDFs. `scripts/seed/` turns them into
JSON and then into rows:

| File | Job |
|---|---|
| `parse_af.py`, `parse_cs_af.py` | Parse the published assessment framework |
| `extract_af_llm.py` | Model-assisted extraction where parsing is not enough |
| `clean_descriptions.py` | Tidy the text |
| `seed_curriculum.py` | Load JSON into `subjects`, `grade_subjects`, `curriculum_domains`, `slos` |

The checked-in JSON under `scripts/seed/data/` is the source of truth for
what is loaded:

```
biology-xi.json  chemistry-xi.json  computer-science-xi.json
mathematics-xi.json  physics-xi.json  physics-xii.json
```

So: **FSc Part 1 is complete across all five subjects. Part 2 is Physics
only.** The landing page's "869 learning outcomes" is the Part 1 count.

Loading is a deploy command:

```bash
deploy/gcp/deploy.sh seed
```

Re-runnable. It updates rather than duplicating.

## Why rows and not a fine-tuned model

The three reasons, stated once here and again in chapter 13:

1. **Traceability.** Every explanation can be tied to a published
   outcome. A student or a teacher can ask "where does this come from"
   and get an answer.
2. **Change.** FBISE revises its pattern. That is an afternoon editing
   JSON and re-running `seed`, not a retraining run and a re-evaluation.
3. **Review.** A teacher can approve or reject a single generated item
   (`content_items`, chapter 8). You cannot approve one fact inside a
   fine-tuned model.

## Pre-generated content

`deploy/gcp/deploy.sh content --subject PHY --grade 11 --domains B`
generates explainers, MCQs and SRQs per SLO into `content_items`, where a
reviewer can approve or reject them.

The point is latency and quality at once: a student gets a reviewed
explanation immediately rather than waiting for a model, and anything
reviewed carries a "Teacher-checked" badge.

**The first full review of the bank has not been done.** Chapter 14.

Next: [7. Accounts and access](07-accounts-and-access.md)
