> **Superseded.** This describes an earlier version of NISAAB and is no
> longer maintained. The current documentation is
> [docs/handbook](../handbook/README.md), written 9 November 2026.
> This file is kept only so older links still resolve.

# 8 · Curriculum data

[← Cloud](07-cloud.md) · [Contents](README.md) · [Next: Operations →](09-operations.md)

The FBISE data NISAAB is built on, and the exam shapes it reproduces. Every number
here was counted from `scripts/seed/data/` on 27 October 2026.

---

## What is loaded

**1,020 SLOs across 41 domains and 100 content areas.** Curriculum: **NCP 2022-23**.
Sourced from FBISE's own published model papers and curriculum pages.

| Subject | Code | Class | Domains | SLOs |
|---|---|---|---:|---:|
| Chemistry | `CHEM` | XI | 7 | **329** |
| Biology | `BIO` | XI | 9 | **246** |
| Physics | `PHY` | XI | 7 | **193** |
| Physics | `PHY` | XII | 7 | **151** |
| Mathematics | `MATH` | XI | 3 | **79** |
| Computer Science | `CS` | XI | 8 | **22** |
| | | | **41** | **1,020** |

### Reconciling with the public site and the report

The live site and the project report quote **869 SLOs across 34 domains**. That is not a
contradiction — it is **Class XI only**, which is what both describe ("the whole FSc Part 1
syllabus"). Physics XII was added afterwards:

| Scope | SLOs | Domains | Content areas | Examinable |
|---|---:|---:|---:|---:|
| Class XI (FSc Part 1) | 869 | 34 | 83 | 611 |
| Class XII (Physics only) | 151 | 7 | 17 | 114 |
| **Loaded in total** | **1,020** | **41** | **100** | **725** |

Quote whichever figure matches the claim being made, and say which it is.

### Where it is thin — stated plainly

- **Computer Science has 22 SLOs.** Chemistry has 329. CS coverage is a fraction of the
  others and should be treated as partial.
- **Class XII exists for Physics only.** The other five subjects are Class XI.
- Mathematics has only 3 domains, which reflects how FBISE groups it rather than a gap.

These are known and recorded rather than smoothed over. Adding a subject is a JSON file
plus `deploy.sh seed`.

---

## How an SLO is classified

Every SLO carries two classifications that drive generation.

### Cognitive level

| Code | Level | Count |
|---|---|---:|
| `U` | Understanding | 654 |
| `A` | Application | 314 |
| `K` | Knowledge | 203 |

These sum to more than 1,020 because **one SLO may carry more than one level**. The
level is passed into the prompt, so an `A`-level SLO yields a question that requires
applying the idea rather than restating it. See [AI layer](06-ai.md#grounding-how-an-slo-reaches-the-prompt).

### Assessment form

| Form | Count | Meaning |
|---|---:|---|
| `summative` | 725 | Examinable in the board paper |
| `formative` | 265 | Assessed during teaching |
| `practical` | 30 | Laboratory work |

Only `summative` SLOs are eligible for board-paper generation. That single filter is
what stops a practice paper asking about something the real paper cannot.

### Two classification oddities

Both come from the FBISE documents as published, not from a processing error:

- **Five Biology SLOs that read as theory are marked `practical`.**
- **Physics Domain N — 27 practical-skills SLOs — is marked `formative`.**

Neither breaks anything; both are worth knowing if the counts ever look surprising.

---

## The FBISE paper pattern

Under NCP 2022-23 the paper is **50% MCQs, 50% descriptive**.

### What one question is worth

```python
QUESTION_MARKS = {
    "default": {"mcq": 0.5,  "srq": 4, "erq": 6},
    "MATH":    {"mcq": 0.75, "srq": 4, "erq": 8},
}
```

Mathematics genuinely differs — ¾ of a mark per MCQ and 8 per extended question. This
was **confirmed against FBISE's published papers**, because assuming one pattern across
all subjects would have produced papers with the wrong totals.

### Every shape NISAAB can build

All totals below are computed from the code, not quoted.

| Paper | Subject | MCQs | SRQs | ERQs | Time | **Total** |
|---|---|---:|---:|---:|---:|---:|
| **Full board** | Sciences / CS | 80 | 7 | 2 | 180 min | **80** |
| **Full board** | Mathematics | 64 | 7 | 3 | 180 min | **100** |
| Half board | Sciences / CS | 40 | 4 | 1 | 90 min | 42 |
| Half board | Mathematics | 32 | 4 | 2 | 90 min | 56 |
| Short | Sciences / CS | 12 | 4 | 1 | 45 min | 28 |
| Short | Mathematics | 12 | 4 | 1 | 45 min | 33 |
| Mini | Sciences / CS | 8 | 2 | 0 | 20 min | 12 |
| Mini | Mathematics | 8 | 2 | 0 | 20 min | 14 |

The two full board rows are the real thing:

- **Sciences / CS** — 80 × 0.5 + 7 × 4 + 2 × 6 = **80 marks**
- **Mathematics** — 64 × 0.75 + 7 × 4 + 3 × 8 = **100 marks**

### Stimulus sets

A board paper's MCQs are not all standalone. The science paper is **56 individual MCQs
plus 6 stimulus sets of 4** (`STIMULUS_SIZE = 4`) — a passage, diagram or data table
followed by four questions on it. 56 + 24 = 80.

### The rule that makes short papers worth doing

> **A shorter paper asks fewer questions. It never changes what a question is worth.**

So a mini paper is 12 marks, not a tidy 10 or 20. A student practising on it meets the
same ½-mark MCQ and 4-mark SRQ they will meet in the exam hall.

This was a bug once: mini papers used invented values of 1 and 3 marks. Consolidating
every weight into `QUESTION_MARKS` fixed it, and the fix was checked across 5 subjects ×
4 lengths.

---

## Adding a subject

1. Write `scripts/seed/data/<subject>-<grade>.json` with `subject`, `grade`, `scheme`,
   `curriculum`, `source_url`, `domains` and `slos`.
2. Each SLO needs its code, description, domain, content area, `cognitive_levels` and
   `assessment_form`.
3. ```bash
   bash deploy/gcp/deploy.sh seed
   ```

Seeding is idempotent — re-running updates rather than duplicating.

---

[← Cloud](07-cloud.md) · [Contents](README.md) · [Next: Operations →](09-operations.md)
