> **Superseded.** This describes an earlier version of NISAAB and is no
> longer maintained. The current documentation is
> [docs/handbook](../handbook/README.md), written 9 November 2026.
> This file is kept only so older links still resolve.

# 12. Domain Logic

## 12.1 Examination paper pattern

| Section | Content | Marks |
|---|---|---:|
| A | 56 straight multiple choice questions plus 6 stimulus sets of 4 questions each | 40 |
| B | 7 short questions of 4 marks, with internal choice | 28 |
| C | 2 extended questions of 6 marks, with internal choice | 12 |
| **Total** | Mathematics uses its own blueprint and is out of 100 | **80** |

The structure is declared as data per length and subject. A change in the FBISE pattern is a change to this table, not to the program logic.

```python
BOARD = {
    'board': {
        'default': {'mcq': 56, 'stimulus': 6, 'mcq_marks': 0.5, 'srq': 7,
                    'srq_marks': 4, 'erq': 2, 'erq_marks': 6, 'minutes': 180},
        'MATH':    {'mcq': 40, 'stimulus': 6, 'mcq_marks': 0.75, 'srq': 7,
                    'srq_marks': 4, 'erq': 3, 'erq_marks': 8, 'minutes': 180},
    },
    'half': { ... },
}
```

## 12.2 How a paper is built

1. Multiple choice questions are drawn from the bank, one per outcome before any outcome is used twice.
2. Stimulus sets are reused from the bank or generated and saved back for later papers.
3. Short and extended questions are generated in pairs, so each one carries an internal choice.
4. Outcomes are spread across domains by taking the domains in turn.
5. Generation runs at the same time under a semaphore.
6. A board paper is built by the worker. The request returns at once with the paper in a "preparing" state and the interface polls until it is ready.

## 12.3 Marking

A written answer is marked against a scheme of points, each worth whole marks. Each point is judged separately and the total is added up in code, not by the model, with the model set to temperature 0 for consistency. Only the answered part of a choice pair counts. If a student answers both, the better one is taken, and section and total marks are computed so that a choice pair counts once. For Computer Science the marking prompt also judges whether the submitted code would run under Python 3. Marks are shown as **AI-estimated** because they have not yet been compared with teacher marking.

## 12.4 Mastery estimation

Mastery per outcome is an exponentially weighted accuracy. It was chosen because it is easy to explain to a student and a teacher.

```
weight   = min(1, max(1 / attempts, 0.3) x factor)
mastery += weight x (score - mastery)

factor = 1.0 for marked work; 0.5 for flashcards, which the student rates
score  = 1 or 0 for right or wrong; the fraction of marks for written answers
The first answer sets the starting point.
```

The floor of 0.3 means recent practice always moves the estimate, so a student who has improved is not held down by old mistakes.

## 12.5 Predicted grade

The predicted grade is worked out from the examined outcomes practised so far, weighted by their teaching periods, and reported on the IBCC 10-band scale. It is shown with a confidence level based on how much of the syllabus has been attempted. When the estimate rests on too little practice, the interface says so plainly.
