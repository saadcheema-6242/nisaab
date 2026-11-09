> **Superseded.** This describes an earlier version of NISAAB and is no
> longer maintained. The current documentation is
> [docs/handbook](../handbook/README.md), written 9 November 2026.
> This file is kept only so older links still resolve.

# 3. Core Concepts

## 3.1 Student Learning Outcomes and their codes

An SLO is one thing a student must be able to do. Every SLO in an FBISE Assessment Framework has a unique code and some recorded properties.

| Part of the code `P-11-B-05` | Meaning |
|---|---|
| `P` | Physics |
| `11` | Class XI |
| `B` | Domain B (a chapter group, for example Mechanics) |
| `05` | Outcome number 5 in that domain |

| Property | Values | What it tells us |
|---|---|---|
| Form of assessment | Summative, formative, practical | Whether it can be examined in the theory paper, only taught, or assessed in the practical |
| Cognitive level | Knowledge, Understanding, Application | How deep an answer is expected to go |
| Teaching periods | A number | Used to weight the predicted grade |

## 3.2 Retrieval-Augmented Generation

The system does not let the model answer from memory. It first retrieves the exact outcome the question belongs to, then gives that outcome to the model as part of its instructions. The model answers within that scope and names the code.

| Stage | What happens |
|---|---|
| Retrieval | The question is matched against the stored outcomes of the subject using term rarity scoring (section 11.4). A code typed by the student skips the search. |
| Augmentation | The matched outcome, its cognitive level and its exam status are added to the instruction for the model. |
| Generation | The model writes an answer bounded by that outcome and cites the code. |

## 3.3 Grounding, not training

NISAAB keeps the syllabus in a database as readable rows. It does not train or fine-tune a model. This means an answer can be traced to a published document, a change in the FBISE pattern is a data update, and a teacher can approve or reject single items. Section 20 gives the reasoning in full.

## 3.4 The pre-generated content bank

For every examined outcome the system has generated an explanation, five multiple choice questions and one short question ahead of time and stored them with a review state. When a student asks for practice, the bank is used first. The model is asked to write only what is missing.

This is why a numerical quiz takes about 4 seconds, where composing it on demand took about 202 seconds.

## 3.5 Mastery and predicted grade

Every answer updates a mastery score for its outcome. The predicted grade on the IBCC 10-band scale (A++ to U, pass mark 40%) is worked out from the examined outcomes practised so far and shown with a confidence level. Sections 5.7 and 12.4 explain both.
