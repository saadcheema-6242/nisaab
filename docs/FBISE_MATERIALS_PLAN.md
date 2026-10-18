# Plan: FBISE official material still worth adding

Written 18 Oct 2026. Every item below was checked by downloading the actual
document, not from the website's description. Topper copies are excluded on the
user's instruction.

## What we already use

| Material | Where it went |
|---|---|
| Assessment Frameworks (50% MCQ pattern, Aug 2026) | 869 Class XI SLOs: code, description, domain, content area, assessment form, cognitive levels |
| The examination pattern inside those AFs | `papers.py` BOARD plan — verified to match exactly: 80 marks, 56 straight MCQs + 6 stimulus sets of 4 at 0.5, 7 SRQs x 4 with internal choice, 2 ERQs x 6 with internal choice (Maths 100 marks) |

## Checked and rejected: the National Curriculum (NCP 2022-23)

The obvious idea was to merge the NCP, because it also lists SLOs and appeared
to add guidance the AF lacked. **It does not.** Compared per SLO:

```
P-11-B-03
  NCP: Derive the equations of motion [For uniform acceleration cases only.
       Derive from the definitions of velocity and acceleration as well as
       graphically]
  AF : Derive the equations of motion [For uniform acceleration cases only.
       Derive from the definitions of velocity and acceleration as well as
       graphically].
```

The AF carries the same bracketed guidance verbatim, and our extraction of it is
cleaner (the NCP text loses subscripts: "V" where the AF has "VH"). Of 193
Physics XI SLOs, 157 match by code and 2 exist only in the NCP.

**Decision: skip the NCP.** Its only unique content is the Grade 9-12 benchmark
and progression structure, which would support prerequisite hints ("you need
Grade 10 circuits first") — a later nice-to-have, not worth the parse now.

## Worth adding

### 1. Command words — the biggest win

`notifications/Guidelines_For_SLOS_Based_Examaiation_2022.pdf` (29 pages)
carries FBISE's official definitions of cognitive levels **and of every command
word, per subject**: Physics pp 4-6, Biology 7-9, Chemistry 10-12, Computer
Science 13-15, Mathematics 16-19.

These are the rules an examiner actually marks against:

- **Define** — "Only a formal statement or equivalent paraphrase is required.
  No examples need to be given."
- **List** — "Requires a number of points, generally each of one word, with no
  elaboration."
- **Calculate** — "A numerical answer is required. Working should be shown,
  especially where two or more steps are involved."
- **State** — "A concise answer with little or no supporting argument."

This fixes our weakest feature. Today `srq_agent` invents its own rubric, so a
"Define" question can be marked as though it needed examples, and a "List"
answer can lose marks for being terse — the opposite of what FBISE says.

**Work**
- Parse to `scripts/seed/data/command-words.json`: `{subject: {word: definition}}`.
  The PDF is a scan with OCR errors ("GOGNITIVE", "lVIention") and its two-column
  table interleaves terms and definitions, so parse with AI help and the same
  safety rule used for the Chemistry AF: every definition must be built from
  words present in the source text. Review before seeding.
- Seed into a `command_words` table keyed by subject.
- Use in:
  - `srq_mark_prompt` — give the examiner the official meaning of the question's
    command word before it builds the rubric.
  - `srq_generate_prompt`, `quiz_slo_prompt`, `stimulus_prompt` — pick a command
    word that matches the SLO's cognitive level, and use FBISE's own vocabulary.
  - `system_prompt_fbise` — let the tutor tell a student what the command word
    demands ("this says Define, so a formal statement is enough").
- Cost: about a day, most of it parsing.

### 2. Periods per SLO, for real domain weighting

The AF SLO table has a "Number of Periods Required" column. **Our parser missed
it almost everywhere**: 7 of 150 Physics SLOs have it, 8 of 22 for Computer
Science, and zero for Chemistry, Biology and Mathematics. The data is sitting in
PDFs we already downloaded.

With it, a paper can follow teaching time instead of spreading evenly. On the
Physics XI SLOs that do carry periods, the split works out as:

```
B Mechanics                 52 periods  ->  32.8 of 80 marks
D Waves                     26 periods  ->  16.4
F Modern Physics            26 periods  ->  16.4
E Electricity and Magnetism 18 periods  ->  11.3
A Measurements               5 periods  ->   3.1
```

**Work**
- Fix the periods column in `parse_af.py` / `extract_af_llm.py`; re-parse all five
  subjects; review the diff.
- `papers.py` `_spread()` — allocate questions by domain periods rather than
  evenly.
- Show it to students: "Mechanics is about a third of the paper."
- Cost: half a day parsing, half a day wiring.

Note: the AF explains what a Table of Specifications is but gives no numeric
per-domain mark table for HSSC-I, so periods are the usable proxy.

### 3. Model question papers as worked examples

Each 50% AF PDF (52 pages for Physics) contains a full official model paper.
Feeding two or three real questions into the generation prompts as examples
would make our questions read like FBISE's rather than like an AI's.

**Work**: extract per subject, store as reference items, use as few-shot examples
in `quiz_slo_prompt`, `srq_generate_prompt` and `stimulus_prompt`. About a day.

## Order, and the honest trade-off

| Priority | Item | Cost |
|---|---|---|
| 1 | Command words | ~1 day |
| 2 | Periods -> domain weighting | ~1 day |
| 3 | Model papers as examples | ~1 day |
| later | NCP benchmarks for prerequisites | 1-2 days |
| later | Topper copies via vision (excluded for now) | 2-3 days |

Against the 29 October competition, these three are worth about three days and
improve answer quality, not the demo's visible surface. Part 2 (Class XII) and
the report, board and demo script are not done. If the competition matters more
than depth, do command words only and leave the rest until after.
