# EduAgent → FBISE FSc Tutor: V1 Customization Plan

> Scope of V1: **FBISE (Federal Board, Islamabad) — FSc only**, i.e. HSSC Grades XI & XII for the
> **Pre-Medical** (Physics, Chemistry, Biology) and **Pre-Engineering** (Physics, Chemistry, Mathematics) groups.
>
> Research date: September 2026. Every FBISE fact below is taken from FBISE's own documents or reported
> news, and the source is listed at the end. Rules have changed more than once in 2024–2026, so the items marked **(verify)**
> must be checked against the latest FBISE notification before launch.
>
> Deployment: **everything on Google Cloud** (decided 25 Sept 2026): Cloud Run + Vertex AI Gemini + Cloud SQL (Postgres +
> pgvector) + Cloud Storage + Identity Platform logins, paid by the $300 trial credit. Live since 25 Sept (§5.7,
> `deploy/gcp/README.md`). **Judging demo: Sunday 5 October 2026**; the demo build plan is §7.1.

---

## 1. Executive summary

EduAgent today is a **general** "upload your documents → chat / quiz / flashcards / study plan" app.
FBISE FSc students have a very specific target: the **SLO-based FBISE annual exam**, which has a published
structure (sections, marks, cognitive levels) and a published list of what can be examined (the
**summative SLOs** in each subject's Assessment Framework).

The customization is therefore not mainly about prompts. It is about adding a **curriculum layer**
(Board → Group → Grade → Subject → Domain → SLO) and making every feature use it:

| Today (generic) | V1 (FBISE FSc) |
|---|---|
| Student creates empty projects and uploads their own files | Student picks **group + grade + exam scheme** during onboarding; subject workspaces are created automatically and come preloaded with a vetted FBISE corpus |
| Quiz = 4-option MCQ only | FBISE question types: **MCQ, stimulus/scenario MCQ sets, SRQ (short response) and ERQ (extended response)**, each tagged with **SLO + cognitive level (K/U/A)** |
| "Topic" = first 100 characters of the question text | Performance tracked **per SLO and per domain** → real weak-area detection |
| Generic study plan | **Exam-date-aware revision plan** over the *summative* SLOs, weighted by the Table of Specifications |
| No exam simulation | **Mock papers** that follow the official paper blueprint (Section A/B/C, OR-choices, timings), with AI marking of written answers against a rubric |
| No notion of grades | **Predicted grade** on the new 10-band FBISE/IBCC scale (pass mark 40%) |
| Generic tutor prompt | FBISE tutor: stays inside the syllabus, cites SLO codes, explains in English / Urdu / Roman Urdu, renders equations properly |

The rest of this document gives the research, the gap analysis against the current code, the
target design, the file-by-file work plan, the content pipeline, the timeline and the risks.

---

## 2. Research findings: how FBISE FSc works (as of Sept 2026)

### 2.1 Scheme of studies and groups

- **Inclusive Scheme of Studies 2024** (FBISE notification 27 Mar 2025):
  - In force for **HSSC-I from academic session 2025** and **HSSC-II from session 2026**.
  - Students who started under the **Scheme of Studies 2006** stay on it until certification, including
    compartment and improvement attempts. **So during 2026–2027 both schemes exist side by side for Grade XII.**
  - HSSC total: **1200 marks**.
  - Elective science subjects: **80% theory + 20% practical** (80 + 20 = 100 per grade). Mathematics has no practical.
  - Compulsory subjects: Urdu 100+100, English 100+100, Islamiat 50 (XI), Translation of Holy Quran 50+50, Pakistan Studies 50 (XII).
  - Academic session for XI–XII starts in the **first week of August**, with about 110 (5-day week) or 150 (6-day week) working days.
- **Elective groups relevant to FSc:**
  - **Medical group:** Physics (Th+Pr), Chemistry (Th+Pr), Biology (Th+Pr)
  - **Engineering group:** Physics (Th+Pr), Chemistry (Th+Pr), Mathematics
  - (Out of scope for V1: General Science/Computer Science group (ICS), Humanities, Allied Health.)

### 2.2 Curriculum and assessment: SLO-based, not textbook-based

- FBISE uses the **National Curriculum of Pakistan (NCP) 2022-23**. Papers are **set from the SLOs, not from a textbook**.
  Several publishers print approved textbooks (e.g. National Book Foundation, Cantab Publisher, New College Publications).
  **Product consequence:** the backbone must be the SLO list, not a single book.
- Each subject has an official **Assessment Framework (AF)** containing:
  - Every SLO with a **stable code**, e.g. `P-11-B-05` (Physics, Grade 11, Domain B, SLO 05), `C-11-B-01`, `B-11-B-01`, `M-11-A-01`, `P-12-B-01`.
  - **Form of assessment**: *Summative* (can be examined) or *Formative* (taught in class but **not** examined). Some are summative for the practical (PBA) only.
  - **Cognitive level**: Knowledge (K), Understanding (U), Application (A).
  - **Periods required** (1 period = 40 minutes). This is a good proxy for how much weight and study time a topic needs.
  - A **model question paper** plus an **alignment table** that maps every question part to its SLO(s), cognitive level and marks.
  - A **Table of Specifications (ToS)**. The target cognitive mix is **30% K / 50% U / 20% A (±5%)**.
    Paired "OR" alternatives must test **different SLOs** at the **same difficulty**.
- **Domains (from the AFs I parsed):**
  - Physics XI: A Measurements, B Mechanics, C Heat & Thermodynamics, D Waves, E Electricity & Magnetism, F Modern Physics, N Experimentation Skills
  - Physics XII: B Mechanics, C Heat & Thermodynamics, D Waves, E Electricity & Magnetism, F Modern Physics, G Nature of Science, H Experimentation Skills
  - Chemistry XI: A Nature of Science in Chemistry, B (Atomic Structure, Chemical Bonding, Stoichiometry, States of Matter, Energetics, Kinetics, Equilibrium …), C …
  - Mathematics XI: A Numbers & Algebra, B Geometry, C Information Handling
  - Biology XI: domain/content-area table per unit
- **Size of the SLO lists** (unique SLO codes found in the Grade XI AFs):
  Physics about 190, Chemistry about 330, Biology about 245, Mathematics about 75.
  Roughly 70–80% are summative. **Grades XI + XII across the 4 subjects come to roughly 1,500–1,800 SLOs.**
  This is a manageable, finite dataset to seed and review by hand.

### 2.3 Paper patterns (IMPORTANT: two are live)

**Pattern 1: "Classic SLO pattern" (Inclusive Scheme 2024, AFs published 2025)**

| Subject | Section A (MCQ) | Section B (SRQ) | Section C (ERQ) | Theory total | Time (B+C) |
|---|---|---|---|---|---|
| Physics / Chemistry / Biology XI | 17 MCQs × 1 = 17, 25 min | 13 × 3 = 39 (each with an OR) | 4 × 6 = 24 (each with an OR) | 80 (+20 practical) | 2 h 35 min |
| Physics XII (2024 scheme) | 17 | B+C = 63 | | 80 (+20) | 2 h 45 min |
| Physics XII (2006 scheme) | 17 | B+C = 68 | | 85 (+15) | 2 h 45 min |
| Mathematics XI | 20 MCQs = 20, 25 min | 12 × 4 = 48 | 32 | 100 | 2 h 35 min |

**Pattern 2: "50% MCQs & 50% Descriptive" (FBISE Notification No. 1-10/FBISE/RES/242, 7 Aug 2026; approved by the Board of Governors 28 Jul 2026)**

- Applies to **Physics, Chemistry, Biology, Mathematics and Computer Science** at SSC and HSSC.
- For Physics, Chemistry, Biology and Computer Science (80-mark theory paper):
  - **Section A:** **80 MCQs × 0.5 = 40 marks**, **1 h 40 min**. **56 straight MCQs** plus **24 MCQs grouped under 6 stimuli/scenarios** (a passage, diagram or data followed by about 4 MCQs).
  - **Section B:** **7 SRQs × 4 = 28**, each with an internal choice, no sub-parts.
  - **Section C:** **2 ERQs × 6 = 12**, each with an internal choice. Sub-parts are allowed if they test the same concept.
  - Only summative SLOs of NCP 2022-23; the ToS keeps domain coverage balanced.
- Mathematics: reported as 64 MCQs = 48 marks out of 100. **(verify)**
- **Rollout:**
  - Phase 1: fresh HSSC-I students in the Second Annual Exam 2026.
  - Phase 2: HSSC-I and those HSSC-II students at First Annual 2027.
  - Phase 3: all HSSC-II students by First Annual 2028.

**Product consequence:** the exam pattern must be **data, not code**. Store paper *blueprints* in a table so each
student sees the pattern for their own cohort, and adding the next change is a data edit.

### 2.4 Grading (IBCC policy, FBISE)

- New **10-band scale**:
  - **HSSC-I:** from the **2026** annual exams.
  - **HSSC-II:** from **2027**. Full adoption across boards is expected by 2028.
- **Pass mark raised from 33% to 40%.** Results are issued as grades and GPA rather than raw marks.

| % | Grade | Descriptor |
|---|---|---|
| 96–100 | A++ | Extraordinary |
| 91–95 | A+ | Exceptional |
| 86–90 | A | Outstanding |
| 81–85 | B++ | Excellent |
| 76–80 | B+ | Very Good |
| 71–75 | B | Good |
| 61–70 | C+ | Fairly Good |
| 51–60 | C | Above Average |
| 40–50 | D | Emerging |
| < 40 | U | Ungraded / fail |

The **grade-point value of each band was not in any source I could access. (verify with IBCC)** Until it is confirmed, store the table as configuration.

### 2.5 What this means for the product

1. **SLO-tagged content** is the single most valuable asset. FBISE itself tags every model-paper question with its SLO.
2. Students need practice with **written answers** (SRQ/ERQ make up 50–80% of the marks), not only MCQs.
3. The **stimulus-MCQ** format is new for 2026–27. Very few resources prepare students for it, which makes it a differentiator.
4. Students must be kept away from **formative-only SLOs** (not examined) when revising for the exam.
5. The 2006 and 2024 schemes, and the classic and 50/50 patterns, **overlap for 2 years**. The student profile must record which cohort the student belongs to.

---

## 3. Current codebase: what we keep, and the gaps

### 3.1 What we can reuse almost unchanged

- **Monorepo structure**: `edu-api` (FastAPI), `edu-worker` (queue processor), `shared/{db,core,ai,queue}`, `edu-web` (React + TanStack). This is clean and extensible.
- **RAG pipeline**: document reader → markdown → header- and page-aware chunking → embeddings → pgvector
  ([document.py](../src/edu-worker/processors/document.py), [search.py](../src/shared/core/src/edu_core/services/search.py)).
- **LangGraph/LangChain tool-calling tutor** with middleware and source capture ([factory.py](../src/shared/ai/src/edu_ai/chatbot/factory.py)).
- **Async generation via queue** for quizzes, flashcards, notes and mind maps (worker processors + registry).
- **Jinja2 prompt templates** ([prompts/](../src/shared/ai/src/edu_ai/prompts/)), so prompt customization is cheap.
- **Usage limits** (`UserUsage` table plus the service): useful for a freemium tier.
- **Alembic** migrations, and the Google Cloud platform built in Sept 2026 (§5.7): Vertex AI, Cloud SQL, Cloud Storage, logins, jobs queue, deploy scripts.

### 3.2 Gaps and problems found in the code

| # | Finding | Where | Why it matters for FBISE |
|---|---|---|---|
| G1 | **"Topic" of a practice record is just the first 100 characters of the question text** | [quiz-detail-state.ts:227](../src/edu-web/src/data-acess/quiz-detail-state.ts:227), [flashcard-detail-state.ts:393](../src/edu-web/src/features/flashcard/state/flashcard-detail-state.ts:393), [models.py:388](../src/shared/db/src/edu_db/models.py:388) | Weak-topic analysis in [study_plans.py:144](../src/shared/core/src/edu_core/services/study_plans.py:144) groups by *each question* separately, so the "< 70% success" logic never finds real weak areas. **Must be replaced by SLO/domain IDs.** |
| G2 | No curriculum model: there are no subjects, grades, SLOs or blueprints | [models.py](../src/shared/db/src/edu_db/models.py) | Everything in V1 depends on this layer. |
| G3 | Quiz supports only 4-option MCQs | [models.py:312](../src/shared/db/src/edu_db/models.py:312) `QuizQuestion`, [quiz_agent.py:14](../src/shared/ai/src/edu_ai/agents/quiz_agent.py:14) | FBISE needs SRQ, ERQ, stimulus sets, marks, SLO tags, cognitive level and a rubric. |
| G4 | Content is **per user and per project** only | `Document.project_id`, `SearchService.search_documents` filters by project documents | FBISE needs a **shared, curated corpus** (SLOs, model papers, vetted notes) that every student's workspace can search, without re-uploading and re-embedding it for each user. |
| G5 | The tutor prompt is generic and search returns short snippets | [system_prompt.jinja2](../src/shared/ai/src/edu_ai/prompts/system_prompt.jinja2), [rag.py:21](../src/shared/ai/src/edu_ai/tools/rag.py:21) (`top_k=5`), [search.py:177](../src/shared/core/src/edu_core/services/search.py:177) (keeps 500 characters × 3 chunks per document) | Answers have no syllabus boundary, no SLO references and no FBISE marking style. The truncation can cut derivations and worked examples in half. |
| G6 | Language list has no Urdu, and the default language is Czech (`cs`) | [upsert-project-dialog.tsx:61](../src/edu-web/src/features/project/components/upsert-project-dialog.tsx:61) | Pakistani students need English, and ideally Urdu or Roman-Urdu explanations. |
| G8 | No math or chemistry rendering pipeline was confirmed (streamdown is used; KaTeX/mhchem not verified) | [package.json](../src/edu-web/package.json) | Physics, Chemistry and Maths content is formula-heavy. |
| G9 | Embeddings are fixed at `Vector(3072)` (text-embedding-3-large) | [models.py:125](../src/shared/db/src/edu_db/models.py:125) | Fine, but it fixes the model choice and the storage cost. Decide before seeding the corpus. |
| G10 | The quiz tool says "count 10-30"; the generator has no blueprint concept | [tools/quiz.py:38](../src/shared/ai/src/edu_ai/tools/quiz.py:38) | Mock papers need exact counts per section and cognitive level. |
| G11 | The document reader keeps text only: **figures and diagrams are dropped** | [local_extraction.py](../src/edu-worker/local_extraction.py) | Circuit diagrams, biology diagrams and graphs matter in FSc, and stimulus MCQs depend on them. |
| G12 | Document chunk metadata only stores `id` and `document_id` | `PGVectorStore(... metadata_columns=["id","document_id"])` | You cannot filter retrieval by subject, grade or SLO. |

---

## 4. V1 product definition

### 4.1 Target users

- **Primary:** FBISE FSc students, Grade XI or XII, Pre-Medical or Pre-Engineering, in Islamabad, federal areas or overseas FBISE schools. Most use mobile, often on limited bandwidth.
- **Secondary (read-only in V1):** teachers and parents who view progress. Full teacher tools come in V2.

### 4.2 Core user journeys (V1)

1. **Onboarding (about 60 seconds):** name → Grade (XI/XII) → Group (Pre-Med/Pre-Eng) → Scheme (2024 inclusive or 2006) →
   Exam pattern (auto-suggested from grade and year: classic or 50/50) → Exam session (Annual 1 / Annual 2, year) →
   explanation language (English / Urdu / Roman Urdu).
   → The system creates **3 subject workspaces** (e.g. Physics XI, Chemistry XI, Biology XI) preloaded with the FBISE corpus.
2. **Syllabus map:** per subject, a Domain → SLO tree with mastery colours. Formative SLOs are greyed out and labelled "not examined".
   Tapping an SLO opens: explanation, a short practice set, flashcards and past model-paper questions.
3. **Ask the tutor:** chat that retrieves from the curated corpus plus the student's own uploads. It stays inside the FSc syllabus, shows the SLO code(s) it answered from, and explains in the chosen language with properly rendered formulas.
4. **Practice by SLO or domain:** MCQs, stimulus sets, SRQs and ERQs. Written answers are marked by AI against a rubric, with FBISE-style feedback ("You earned 2/3: definition correct, missing the unit").
5. **Mock paper:** a timed, full or half paper built from the student's blueprint, with Section A timed separately exactly like the exam. The result shows marks, the **predicted grade band**, and an SLO-wise breakdown.
6. **Study plan:** countdown to the exam date. It schedules the remaining summative SLOs, weighted by (a) ToS or periods weight, (b) mastery gap, (c) cognitive level. It updates as mastery changes.
7. **Progress dashboard:** mastery per subject, domain and SLO; mock-paper trend; predicted grade.

### 4.3 Explicitly out of scope for V1

- ICS / General Science / Humanities groups; SSC (Matric); other boards (BISE Punjab etc.). The design is board-agnostic, so these are data additions later.
- English, Urdu, Islamiat, Tarjuma-tul-Quran and Pakistan Studies (compulsory subjects). **Candidate for V1.1.**
- Practical Based Assessment (PBA) simulations. V1 has only a PBA checklist and viva-style flashcards.
- Handwritten-answer photo marking (V1.5; see §9).
- MDCAT/ECAT prep (V2; it shares much of the FSc content).
- Payments. V1 is free with usage limits; add JazzCash/Easypaisa in V2.

---

## 5. Target design

### 5.1 Curriculum layer (new tables, `shared/db`)

```text
board            (id, code='FBISE', name)
program          (id, board_id, code='HSSC', name)
study_scheme     (id, program_id, code='ISS-2024'|'SOS-2006', effective_from_session, notes)
group_           (id, program_id, code='PRE_MED'|'PRE_ENG', name)
subject          (id, code='PHY'|'CHEM'|'BIO'|'MATH', name, has_practical bool)
group_subject    (group_id, subject_id)
grade_subject    (id, subject_id, grade=11|12, scheme_id, curriculum='NCP-2022-23',
                  theory_marks, practical_marks)
domain           (id, grade_subject_id, code='A'..'N', name, sort_order)
content_area     (id, domain_id, name, sort_order)                 -- e.g. "Vectors", "Fluid Dynamics"
slo              (id, content_area_id, code='P-11-B-05' UNIQUE, description,
                  assessment_form: 'summative'|'formative'|'summative_pba',
                  cognitive_levels: text[] ('K','U','A'),
                  periods int NULL, remarks text, source_doc_url, version)
paper_blueprint  (id, grade_subject_id, pattern_code='CLASSIC_2025'|'MCQ50_2026',
                  effective_from_exam, effective_to_exam NULL,
                  total_theory_marks, spec jsonb)                   -- sections, counts, marks, timing, OR-rules, K/U/A targets
grading_scale    (id, code='IBCC_2026', effective_from, bands jsonb) -- the 10-band table
```

Example `paper_blueprint.spec` for **Physics XI, MCQ50_2026**:

```json
{
  "sections": [
    {"id": "A", "title": "MCQs", "time_min": 100, "items": [
      {"type": "mcq", "count": 56, "marks_each": 0.5},
      {"type": "stimulus_set", "count": 6, "mcq_per_set": 4, "marks_each": 0.5}
    ]},
    {"id": "B", "title": "SRQs", "items": [{"type": "srq", "count": 7, "marks_each": 4, "internal_choice": true}]},
    {"id": "C", "title": "ERQs", "items": [{"type": "erq", "count": 2, "marks_each": 6, "internal_choice": true}]}
  ],
  "cognitive_mix": {"K": 0.30, "U": 0.50, "A": 0.20, "tolerance": 0.05},
  "rules": ["alternatives_must_differ_in_slo", "alternatives_same_difficulty", "summative_slos_only"]
}
```

### 5.2 Student profile and workspaces

- New table `student_profile` (user_id PK, grade, group_id, scheme_id, exam_pattern_code, exam_session, exam_year,
  explanation_language, school/city optional, onboarding_completed_at).
- **Keep `Project` as the "subject workspace"** (least disruption). Add nullable columns to `projects`:
  `grade_subject_id`, `kind` ('subject_workspace' | 'custom'). Onboarding creates one workspace per subject.
  Students can still create custom projects for their own notes.
- `language_code` stays on `Project`. Add `ur` and `ur-Latn` (Roman Urdu) and default to `en`.

### 5.3 Shared corpus ("Library") + retrieval

- New table `library_document` (like `Document` but global): `grade_subject_id`, `kind`
  ('slo_explainer' | 'model_paper' | 'marking_scheme' | 'reference_notes' | 'practical_guide'), `source`, `license`, `status`.
- Its segments go into the **same `document_segments` table** with extra columns:
  `library_document_id` (nullable), `grade_subject_id`, `domain_code`, `slo_codes text[]`, `page_number`, `content_kind`.
  Add these to `metadata_columns` in `PGVectorStore.create` so retrieval can filter on them.
- `SearchService.search_documents` gets a new signature:
  `search(query, *, project_id, grade_subject_id, slo_codes=None, include_library=True, top_k=8)`.
  The filter is `(document_id IN project_docs) OR (grade_subject_id = X AND library_document_id IS NOT NULL)`.
- Improve retrieval quality:
  - **Hybrid search**: pgvector plus Postgres full-text on `content`, merged with reciprocal-rank fusion (RRF). SLO codes and formula names match much better lexically.
  - **SLO boosting**: if the query maps to an SLO (via an embedding match on `slo.description`), filter or boost segments carrying that SLO.
  - Return **full chunks** (up to about 1,500 characters) instead of 3 × 500-character snippets; the current truncation breaks derivations.

### 5.4 Question bank (replaces or extends `quizzes`)

```text
question          (id, grade_subject_id, type: 'mcq'|'stimulus_mcq'|'srq'|'erq',
                   stem_md, options jsonb NULL, correct_option NULL,
                   answer_md, rubric jsonb NULL,            -- marking points for SRQ/ERQ
                   marks numeric, cognitive_level 'K'|'U'|'A', difficulty 1..5,
                   stimulus_id NULL, figure_urls text[],
                   source: 'fbise_model_paper'|'ai_generated'|'teacher'|'past_paper',
                   review_status: 'draft'|'ai_checked'|'sme_approved'|'rejected',
                   created_by, created_at)
question_slo      (question_id, slo_id, is_primary)          -- many-to-many
stimulus          (id, grade_subject_id, body_md, figure_urls, source)
assessment        (id, user_id, project_id, kind 'practice'|'mock_paper'|'slo_drill',
                   blueprint_id NULL, started_at, submitted_at, time_limit_s, score, max_score)
assessment_item   (id, assessment_id, question_id, section, position, chosen_alternative)
response          (id, assessment_item_id, answer_text / selected_option / image_url,
                   awarded_marks, feedback_md, graded_by 'auto'|'ai'|'teacher', grader_meta jsonb)
slo_mastery       (user_id, slo_id, attempts, correct_weighted, mastery 0..1, last_seen_at, next_review_at)
```

- **Migration path:** keep the existing `Quiz`/`QuizQuestion` working (the UI depends on it) and add `slo_codes`, `cognitive_level` and `marks` to `quiz_questions` in phase 1.
  Build the new `question`/`assessment` tables for mock papers in phase 2. Later, migrate quizzes to become `assessment(kind='practice')`.
- **`practice_records.topic` → `slo_id` + `domain_code`.** This fixes G1. Keep `topic` for display only.
- **Mastery model (V1, simple and explainable):** an exponentially weighted accuracy per SLO, weighting K/U/A as 1/1.5/2 and
  normalising partial marks for SRQ/ERQ. A spaced-repetition due date (`next_review_at`) uses SM-2-lite.
  (The repo removed an earlier spaced-repetition implementation; bring it back scoped to SLOs.)

### 5.5 AI components (shared/ai)

| Component | What it does | Changes |
|---|---|---|
| **FBISE Tutor (chat)** | Explains within the syllabus, cites SLOs, handles English/Urdu/Roman Urdu | New `system_prompt_fbise.jinja2` with the student's grade, group, subject and scheme; tools get `grade_subject_id`; new tools `get_slo(code)`, `list_weak_slos()`, `start_slo_drill(slo_code)` |
| **Question generator** | Generates MCQ/stimulus/SRQ/ERQ **for a given SLO and cognitive level**, following FBISE style | New `question_agent.py` + `question_prompt.jinja2`; output schema includes `slo_codes`, `cognitive_level`, `marks`, `rubric` |
| **Question validator** | Second pass that checks the correct answer, a single correct option, distractor quality, SLO alignment, and that the question is inside the summative scope | New `question_validator_agent.py`; low-confidence questions go to the review queue |
| **Paper assembler** | Deterministic (not an LLM): fills a `paper_blueprint` from the bank using ToS constraints (domain coverage, K/U/A mix, OR-pairs on different SLOs, same difficulty) and generates only the missing items | New `edu_core/services/paper_assembly.py` (a constraint or greedy solver) |
| **Answer marker** | Marks SRQ/ERQ text against the rubric: marks per point, feedback, "how to write it for full marks" | New `marking_agent.py` with structured output `{points:[{rubric_point, awarded, evidence}], total, feedback}`. Use temperature 0; calibrate on SME-marked samples |
| **Study-plan agent** | Uses **SLO mastery + exam date + blueprint weights** instead of question-text topics | Rewrite `StudyPlanService.generate_study_plan` input; deterministic scheduling plus LLM wording only |
| **Topic graph / mind map** | Build from the SLO tree (deterministic) instead of LLM-guessing topics from the full text | `TopicGraphAgent` reads domain → content area → SLO from the DB |

Prompt rules to encode (FBISE tutor):
- Stay within FSc and NCP 2022-23 scope. If the question is outside the syllabus, say so briefly, then answer at a basic level.
- Prefer the **summative SLO wording**, and show "SLO P-11-B-05" chips (rendered as UI links, not raw text).
- Use FBISE answer style for SRQs (definition → formula → units → short justification) and ERQs (derivation steps, labelled diagram description, final boxed result).
- Use SI units, significant figures, and KaTeX `$...$` for maths. Use mhchem `\ce{}` for chemistry.
- **Language modes:**
  - `en`: English.
  - `ur`: Urdu script, with scientific terms kept in English in brackets.
  - `ur-Latn`: Roman Urdu, which is how many students actually type.
  - Always keep formulas and technical terms in English, because the exam is answered in English for these subjects.
- Socratic mode for practice, direct mode for "explain".

### 5.6 Frontend (edu-web)

- **Onboarding wizard** (new route) → creates the profile and workspaces.
- **Home = "My FSc" dashboard**: subjects, exam countdown, today's plan, predicted grade, weak SLOs.
- **Syllabus explorer**: Domain → Content area → SLO tree with mastery chips; an "Examined / Not examined" filter.
- **Practice player**: extend the quiz player for stimulus sets (the passage or figure stays pinned while its MCQs are answered), SRQ/ERQ text input,
  marks display, rubric feedback, and a "Show model answer" button.
- **Mock paper mode**: Section A timer (25 min or 1 h 40 min by pattern) that locks when time runs out (it is collected separately in the real exam), then B/C with an OR-choice selector.
- **Math rendering**: add `katex`, `remark-math`, `rehype-katex` and `mhchem` to the markdown renderer used by chat, notes and questions.
- **Language**: an explanation-language switcher. UI copy can stay in English for V1, but choose RTL-safe components for Urdu message bubbles (`dir="auto"`).
- **Mobile-first pass**: most users are on Android phones. Lazy-load heavy components (mind map canvas, PDF preview) and keep network payloads small.
- Replace Czech defaults, and brand as FBISE FSc (logo, colours, copy).

### 5.7 Platform (in place on Google Cloud)

The platform work is finished and live (Sept 2026). Everything runs in the Google Cloud project `fbise-tutor-2026`
(region `asia-south1`, Mumbai), paid by the $300 trial credit. Details and commands: `deploy/gcp/README.md`.

```text
Students (browser, mostly Android)
  ├─► Cloud Run: edu-web (React app) ──► Identity Platform (email + password sign-in)
  └─► Cloud Run: edu-api (FastAPI) ──► Vertex AI Gemini (tutor, generation, marking, embeddings)
                 │   └─► Cloud Storage (uploaded documents, extracted text)
                 ▼
     Cloud SQL: Postgres 16 + pgvector (all data, including the jobs queue)
                 ▲
Cloud Scheduler ─ every minute ─► Cloud Run: edu-worker (private; document processing and generation jobs)
Cloud Run jobs: edu-migrate (database migrations), edu-e2e (end-to-end check)
```

| Area | What is in place |
|---|---|
| AI | Vertex AI Gemini, with a model per task (`LLM_TUTOR_MODEL`, `LLM_GENERATION_MODEL`, `LLM_MARKING_MODEL`, `LLM_OCR_MODEL`) and automatic fallback to other models on quota or server errors. Embeddings: `gemini-embedding-001` (3072 dims) through Vertex's native API |
| Generation | Structured output through function calling, so LaTeX formulas survive intact |
| Documents | PDF, Word, text, Markdown and HTML read in the worker; scanned PDFs and photos transcribed by Gemini |
| Jobs | Postgres `jobs` table with retries (3 attempts) and stale-job recovery; worker scales to zero and is woken every minute, or runs always-on for demos |
| Security | Login tokens verified against Google's keys; worker is private; database password only in Secret Manager; storage bucket private with short-lived signed preview URLs |
| Operations | `deploy/gcp/deploy.sh setup / deploy / migrate / e2e`; budget alerts at about $50, $150 and $250 |

Current models: `gemini-3.5-flash` for tutor, generation, marking and scanned files; fallbacks
`gemini-3.5-flash-lite`, `gemini-2.5-flash`. Model names are configuration in `deploy/gcp/deploy.env`.

**Cost controls** (still to apply as features land):
- Cache SLO explainers: generate once per SLO and serve to everyone, not per student.
- Keep question-bank reuse high: assemble from the bank first and generate only the gaps.
- Per-feature daily limits (reuse `UserUsage`; add `answer_markings_today`).
- Log token usage per feature, and store AI-marking decisions for audit and calibration.

---

## 6. Content pipeline (the real moat)

### 6.1 Sources

| Source | Use | Licensing note |
|---|---|---|
| FBISE Assessment Frameworks (XI & XII, 4 subjects, both schemes) | **SLO seed data** (codes, text, summative/formative, K/U/A, periods) + ToS + model papers + SLO alignment | Public FBISE documents. Attribute them and keep a link to the source. |
| FBISE model papers + marking schemes/solutions | Seed questions with **official SLO tags** and rubrics; few-shot examples for generators and the marker | Public; attribute. |
| FBISE past papers (annual 1 & 2) | Past-paper practice, style calibration, frequency analysis | Generally reproduced publicly; confirm FBISE's terms. |
| Textbooks (NBF, Cantab, New College) | **Do not bulk-ingest** without permission. Students may upload their own copy into their workspace (private, per-user). | Copyrighted. Approach NBF for a licence. |
| Original content written or checked by subject experts (SLO explainers, notes, questions) | The main curated corpus | Owned by you. |

### 6.2 Pipeline steps

1. **Download** the AF PDFs from `fbise.edu.pk/curriculum_model_paper.php`: Physics, Chemistry, Biology and Maths for XI (2024 scheme) and XII (2006 and 2024 schemes), including the 50/50 versions.
   (Tested: `pypdf` extracts the SLO tables as text. For example, `phy11.pdf` gives 193 unique SLO codes. Tables wrap across lines, so a parsing pass is needed.)
2. **Parse → structured JSON** with a script (`scripts/seed/parse_af.py`):
   - Regex for `SLO: ?[A-Z]+-\d\d-[A-Z]-\d+`.
   - An LLM "table repair" pass to join wrapped cells into `{code, description, form, cognitive_levels, periods, domain, content_area}`.
   - Validation: unique codes, domain letters match, every code has a form.
3. **Human review** by 1 subject expert per subject (about 1–2 days each) in a simple review UI or a spreadsheet export.
4. **Seed** with `alembic` data migrations or a `seed` CLI: boards, groups, subjects, schemes, domains, SLOs, blueprints (from §2.3) and the grading scale (§2.4).
5. **Model-paper questions → question bank**. Use the alignment tables (question → SLO → K/U/A → marks), which FBISE already publishes, so tagging is nearly free. Source = `fbise_model_paper`.
6. **Generate an SLO explainer per summative SLO** (about 1,200 across the 4 subjects × 2 grades): definition, key equations, a worked example, common mistakes, and 2 MCQs + 1 SRQ.
   Run an AI check, then expert approval, then publish into the Library (embedded, tagged with its SLO).
7. **Bank growth target for launch:** at least 15 MCQs, 3 SRQs and 1 ERQ per summative SLO, plus 6 or more stimulus sets per domain. All must be `ai_checked` or better; the mock-paper assembler uses only `sme_approved` or `fbise_model_paper` items.

---

## 7. Work plan

### 7.1 Demo build: 26 September – 5 October 2026 (judging demo on Sunday 5 October)

**Goal:** on the live Google Cloud app, show the FBISE specialization end to end for **Physics XI**: a student signs up,
picks their group, sees the official FBISE syllabus, practises by SLO, asks the FBISE tutor (including in Roman Urdu),
gets a written answer marked like an examiner, and sees their weak SLOs and predicted grade.

**Scope rules**
- Full content for **Physics XI** only. Other Pre-Med / Pre-Eng subjects (Chemistry, Biology, Maths XI) appear as workspaces with their
  SLO lists if the parser output is clean, otherwise marked "coming soon".
- Reuse existing tables and screens wherever possible (quizzes, flashcards, chat); the full question bank (§5.4) comes after the demo.
- Every milestone is deployed to Google Cloud and checked with the cloud end-to-end job.

**Progress (26 Sep)**
- D1 built: onboarding wizard (class → group → explanation language), `student_profiles`, subject workspaces
  (`projects.kind`, `projects.grade_subject_id`), "My FSc" dashboard, FSc profile in Settings, placeholder name "FSc Tutor"
  (`VITE_APP_TITLE`), FBISE notice, English / Roman Urdu / Urdu options (Czech default removed).
- D2 built: curriculum tables, Physics XI parsed from the official AF (193 SLOs: A 7, B 44, C 23, D 21, E 43, F 28, N 27;
  150 summative, 43 not examined, including 27 "Formative for PBA" lab-work SLOs), spacing cleaned with a whitespace-only AI pass, seeded by the `edu-seed` job on
  every deploy; syllabus map with search, filters, mastery colours and an SLO panel. Chemistry, Biology and Maths show "coming soon".
- D3 built: "Practise 10 MCQs" and "Flashcards" per SLO (SLO text and cognitive level in the prompt, items tagged with the SLO
  code and K/U/A level), practice answers tagged with the SLO on the server, mastery per SLO on the map.
  Fixed an upstream bug: the Generate dialog called the API with an empty quiz/flashcard/note ID.
- D4 built: FBISE tutor prompt for subject workspaces (FSc scope, SLO citations, FBISE answer style, English / Urdu /
  Roman Urdu with formulas in English); `find_syllabus_slos` tool (rarity-weighted keyword search over the subject's SLOs,
  plus the teacher-approved explainer of the best match); KaTeX (`$...$`, `\(...\)`, `\[...\]`) and `\ce{}` in chat, notes,
  quizzes and flashcards. Tested: "projectile ki range kaise nikalte hain?" → Roman Urdu answer, formula, SLO P-11-B-05.
- D5 built: SRQs per SLO (`srq_questions`, `srq_attempts`), generated and marked inside the API request (no queue wait):
  whole-mark rubric, marks per point judged by the model at temperature 0 and added up in code, feedback in the student's
  language, model answer; partial marks feed mastery (`practice_records.score`). Tested: a half-right answer got 1.5/3
  with the arithmetic slip and missing unit named, in about 2 seconds.
- D6 built: `GET /api/v1/progress` and a "My progress" dashboard section: predicted IBCC grade band from practised examined
  SLOs weighted by teaching periods, with coverage and confidence; mastery by domain; "Needs work" and "Start with" SLOs
  that open the SLO panel. Daily limits raised for the demo (100 chat messages, 30 quizzes/SRQs) and configurable.
- Physics XII (151 SLOs, 2024 scheme), Chemistry XI (328 SLOs), Biology XI (246) and Maths XI (79) extracted from their AFs with `scripts/seed/extract_af_llm.py`
  (AI-assisted, but every code must match the codes found in the PDF text and every description must use only words from
  that text; assessment type and K/U/A are read from each SLO's own PDF row wherever that row is unambiguous); the
  Chemistry and Biology AFs print only domain letters, so those domain names summarise their content areas. To be spot-checked by
  subject teachers after the demo.
- Fixes after first user testing (26 Sep): cold-start "Transport error" (one warm API instance, CPU boost, client retries,
  CORS-safe 500s, race-safe first login); broken formulas in AI content (doubled LaTeX backslashes and formulas without
  `$...$`): repaired on display (`lib/math.ts`, tested), cleaned before saving (`edu_ai/latex.py`), prompts tightened, and
  16 stored rows fixed with `deploy.sh script scripts/content/fix_latex.py`.
- Chat upgrade after student testing (agreed order: quick fixes → quiz in chat → flashcards in chat → SLO mind map in
  chat → PDF/PNG export → mini paper with typed answers → DOCX/PPTX):
  - Quick fixes (done): friendly tool status lines with an Open button, no internal IDs, no duplicate typed-out
    quizzes, clean copying, dead attach/search/model buttons removed.
  - Quiz in chat (done, cloud-tested): `practice_quiz` tool finds the SLO, uses teacher bank questions when there
    are enough, otherwise generates on the spot; answered inside the chat with instant feedback; attempts stored in
    `practice_attempts` and counted for mastery; "Ask tutor about my mistakes".
  - Flashcards in chat (done, cloud-tested): `practice_flashcards`, flip cards, "Knew it" counts half weight for mastery.
  - SLO mind maps in chat (done, cloud-tested): `practice_mind_map`; domain maps straight from the SLO tree (instant),
    topic maps with one branch per SLO; viewer with formulas, SLO colours, zoom, node details with Explain / Practise.
  - Export (done): Download menu on quiz, flashcard, mind map and note pages and chat cards: quiz PDF (with or without
    answer key), printable flashcard PDF (8 per A4, backs mirrored), share images per card (1080 px, ZIP), mind map
    PNG/PDF, note PDF. Drawn in the browser, so formulas and Urdu match the screen.
  - Mini paper (done, cloud-tested): `practice_papers`; Mini (8 MCQs + 2 SRQs, 20 min) or Standard (12 MCQs +
    4 SRQs + 1 ERQ, 45 min) for the whole syllabus or a domain; exam page with timer, autosave and auto-submit;
    written answers marked in parallel; results with IBCC band per paper; from the chat (`practice_paper`) or the
    "Practice paper" button on the syllabus map.
  - Fixes from student testing (27 Sep): quiz card no longer shows twice (tool parts stream with a stable ID) and no
    longer disappears when the chat is reopened (chat reloads fresh); practice tools end the turn on the card
    (`return_direct`, one model call fewer, no long duplicate text) and the chat history keeps a short note of each
    card; every retry is saved as a numbered attempt ("Attempt 2"), shown in the quiz card, the full quiz page (which
    now saves attempts too) and a new History tab; mind maps can be deleted; the chat has one scroll area (KaTeX's
    hidden MathML copies had escaped it and added blank space) and the input stays on screen.
  - Questions before practice (27 Sep): when a request leaves important choices open, the tutor first shows a
    card of 3–5 tappable questions (`ask_practice_questions`): the server adds "Which part of the syllabus?" from
    the real SLOs with weak ones pre-ticked, and the AI writes 2–4 questions for the topic (question type, level,
    count, purpose; for flashcards the focus; for mind maps detail and what to include; for papers the length).
    Specific requests, retries ("ek aur") and "you decide" skip the card. The answers become practice settings
    (`slo_codes`, `style`, `level`, `focus`, `detail`, `include`, `notes`; `edu_core/practice_options.py`):
    matching teacher-bank questions first, the rest written by the AI in parallel per SLO.
  - After the demo: DOCX/PPTX export.
- Cloud end-to-end job (26 Sep): all 10 stages pass on Google Cloud, including onboarding, the 193-SLO map, the Roman
  Urdu tutor citing P-11-B-05 with formulas, SLO quiz → mastery, SRQ marked in 4 s, and a predicted grade.
- D7 built and deployed: shared content bank (`content_items`: explainer, 5 MCQs and 1 SRQ per examined SLO,
  draft → approved / rejected); `deploy.sh content --subject PHY --grade 11 --domains B` generated all 150 examined
  Physics XI SLOs (1,050 drafts: Mechanics 287, other domains 763). Practice uses bank items first (instant,
  teacher-approved first, never rejected ones) and falls back to AI generation; explainers show in the SLO panel and
  ground the tutor once approved; "Review content" page for teachers listed in `REVIEWER_EMAILS` (needs the Physics
  reviewer's email). Demo script: `docs/DEMO_SCRIPT.md`.

#### D1. Branding and onboarding (26–27 Sep)
- App name, logo, colours and landing-page copy; footer notice "Aligned with FBISE NCP 2022-23; not an official FBISE product".
- Database: `student_profile` (user, grade, group, explanation language, onboarding time); `projects.grade_subject_id` and `projects.kind`.
- API: `GET/PUT /api/v1/profile`, `POST /api/v1/onboarding` (creates the subject workspaces).
- Web: 3-step onboarding after the first sign-in (grade → group → explanation language); dashboard lists the subject workspaces.
- Language options: English, Urdu, Roman Urdu; default English (fixes G6).
- **Done when:** a new student signs up, completes onboarding, and sees Physics XI, Chemistry XI and Biology XI (Pre-Med) or Physics XI, Chemistry XI and Maths XI (Pre-Eng).

#### D2. SLO curriculum and syllabus map (26–28 Sep)
- Database (a subset of §5.1): `subject`, `grade_subject`, `domain`, `slo` (code, description, summative/formative, K/U/A, periods, content area).
- `scripts/seed/parse_af.py`: parse the official Physics XI Assessment Framework PDF (≈190 SLO codes, 7 domains) into reviewed JSON; seed it with a Cloud Run job (`deploy.sh seed`).
- API: `GET /api/v1/curriculum/grade-subjects/{id}/tree` (domains → SLOs, with the student's mastery).
- Web: syllabus map per workspace (domain sections, SLO rows with code, text, K/U/A chips, "not examined" badge, mastery colour);
  SLO panel with **Explain**, **Practise** and **Flashcards** buttons.
- **Done when:** the Physics XI map matches the FBISE PDF (domains, SLO codes, summative/formative).

#### D3. Practice by SLO and mastery (28–29 Sep)
- Quizzes and flashcards generated **for one SLO** (the SLO text and cognitive level go into the prompt); every generated item is tagged with its SLO code.
- `quiz_questions.slo_code`, `flashcards.slo_code`, `practice_records.slo_code`; the web app sends the SLO code instead of the first 100 characters of the question (**fixes G1**).
- Mastery per SLO computed from practice records (weighted by K/U/A), shown on the syllabus map and dashboard.
- **Done when:** answering questions for an SLO changes its colour on the syllabus map.

#### D4. FBISE tutor (28–29 Sep)
- New tutor prompt (§5.5 rules): stays inside FSc/NCP 2022-23, cites SLO codes, FBISE answer style, English / Urdu / Roman Urdu modes
  (formulas and technical terms stay in English).
- Shared **Physics XI library**: the official AF text and generated SLO explainers, searchable from every Physics XI workspace
  alongside the student's own uploads (minimal version of §5.3; fixes G4). Search returns full chunks instead of 500-character snippets (G5).
- Formula rendering (KaTeX; mhchem for chemistry) in chat, notes and questions (G8).
- **Done when:** "projectile ki range kaise nikalte hain?" gets a Roman-Urdu answer with the formula rendered and SLO P-11-B-05 cited.

#### D5. Written-answer marking, SRQ (30 Sep – 1 Oct)
- SRQ items stored with the quiz questions: question type, marks, model answer and a marking rubric (points).
- Marking agent (temperature 0, structured output): marks per rubric point, total, what was missing, model answer.
- API: `POST .../questions/{id}/mark`; web: answer box, "Submit for marking", result with marks and feedback, labelled "AI-estimated marks".
- **Done when:** a typed answer to a 3-mark SRQ comes back in about 10 seconds with marks and the specific points missed.

#### D6. Dashboard and predicted grade (1 Oct)
- Per-subject and per-domain mastery, the 5 weakest SLOs with "Practise" links, and a **predicted grade band** on the new IBCC scale
  (from mastery weighted by SLO periods), with a clear "estimate" label.
- **Done when:** the numbers move after a practice session.

#### D7. Demo content and review (1–2 Oct)
- Pre-generate for Physics XI: an explainer for every summative SLO, 5 MCQs and 1 SRQ per SLO (Mechanics domain first, then the rest as budget allows).
- A Physics teacher reviews the Mechanics content (1–2 hours); flagged items are fixed or removed.
- **Feature freeze: 2 Oct night.**

#### Hardening and demo (3–5 Oct)
- 3 Oct: rehearsal with the demo script, bug fixes only, cloud end-to-end job, on-demand database backup, recorded backup video of the full demo.
- 4 Oct: demo mode (`WORKER_ALWAYS_ON=true`, `API_MIN_INSTANCES=1`), final check of demo accounts.
- 5 Oct: demo. Switch demo mode off afterwards.

| Date | Milestone | Deploy |
|---|---|---|
| 26–27 Sep | D1 onboarding and branding; D2 curriculum tables, parser, seed | 27 Sep |
| 28–29 Sep | D2 syllabus map; D3 practice by SLO and mastery; D4 FBISE tutor | 29 Sep |
| 30 Sep – 1 Oct | D5 SRQ marking; D6 dashboard | 1 Oct |
| 1–2 Oct | D7 content generation and teacher review | 2 Oct (feature freeze) |
| 3 Oct | Rehearsal, fixes, backup video | final deploy |
| 4 Oct | Demo mode | settings only |
| **5 Oct** | **Demo** | — |

**If time runs short** (cut in this order): D6 predicted grade → a simple mastery summary; D5 → a fixed set of prepared SRQs;
other subjects' SLO lists → "coming soon". D1–D4 are the core of the demo and are not cut.

**Needed from the team**
- App name and any logo/colours: **by 27 Sep**.
- A Physics teacher (or strong FSc student) for 1–2 hours of content review: **1–2 Oct**.
- 1–2 demo accounts created on the live app, and who presents: **by 3 Oct**.

### 7.2 After the demo: from demo to public V1

The demo build delivers the core of Phases 1–2 for Physics XI. What remains, in order:

**Phase 1: Curriculum for all FSc subjects**
- [ ] Remaining curriculum tables (§5.1): boards, programs, schemes (2006 and 2024), groups, paper blueprints, grading scale.
- [ ] Parse, review and seed the Chemistry, Biology and Maths XI and all Grade XII Assessment Frameworks (both schemes for XII).
- [ ] Onboarding extended to scheme, exam pattern (classic or 50/50) and exam session.

**Phase 2: Library and tutor at full strength**
- [ ] `library_document` with tags and figure extraction (G11); segment metadata for subject/grade/SLO filtering (G12).
- [ ] Hybrid search (vector + full text with rank fusion) and SLO boosting.
- [ ] Tutor tools `get_slo`, `list_weak_slos`, `start_slo_drill`; SLO chips in chat sources.
- [ ] SLO explainers and question bank for every subject, reviewed by subject experts.

**Phase 3: Exam practice**
- [ ] Question bank tables (§5.4): `question`, `stimulus`, `assessment`, `assessment_item`, `response`, `slo_mastery`.
- [ ] Question generator and validator agents; ERQ marking; marker calibration (200+ expert-marked answers per subject).
- [ ] Stimulus MCQ sets, paper assembler from blueprints, **timed mock papers** with section timers and OR choices.

**Phase 4: Study plan and launch**
- [ ] Study-plan rewrite: deterministic schedule over summative SLOs weighted by mastery gap, exam countdown.
- [ ] Usage limits per feature, analytics, load test before exam season, error monitoring.
- [ ] Account-switch data move scripted and tested (Cloud SQL export/import, bucket copy, Identity Platform users) before the trial ends.
- [ ] Closed beta with 50–100 FBISE students from 2–3 Islamabad colleges; then public launch.

**Timeline:** about 10–12 weeks after the demo to a public V1, aiming for the beta before the First Annual HSSC exams
(usually April–May; check FBISE's date sheet).

---

## 8. Quality, evaluation, and safety

- **Golden sets per subject:**
  - 100 tutor questions with expert reference answers.
  - 200 marked SRQ/ERQ answers.
  - 300 MCQs with known keys.
  Run them in CI (nightly) on every prompt or model change.
- **Metrics:**
  - Tutor: groundedness (claims supported by retrieved chunks) and the in-syllabus rate.
  - Generated MCQs: key accuracy, single-correct-answer rate, SLO-alignment agreement with experts.
  - Marking: marker MAE.
  - Learning outcome: mastery gain per week.
- **Human-in-the-loop:** mock papers use only approved or official items. AI-generated practice items are labelled, and a "Report an issue" button feeds the review queue.
- **Academic integrity:** position the product as practice and tutoring, not exam-answer generation. There is no live-exam feature.
- **Minors' data:** many users are 16–18. Collect minimal PII and get parental consent where required.
  Don't expose student data to teachers without the student linking them. Review Pakistan's data-protection requirements before launch.
- **Brand and legal:** "Aligned with FBISE NCP 2022-23 SLOs". Do **not** use the FBISE logo or imply official endorsement.

---

## 9. Roadmap after V1

- **V1.1:** compulsory subjects (English, Urdu, Islamiat, Pakistan Studies, Tarjuma-tul-Quran) with Urdu-script UI.
- **V1.5:** **handwritten answer photo → marking** (vision model: OCR plus rubric marking), because FBISE answers are handwritten. PBA practical viva bot.
- **V2:**
  - Teacher and school dashboards (assign SLO drills, class mastery heatmaps).
  - ICS and SSC (Matric) groups.
  - MDCAT/ECAT bridge (reuse the Physics, Chemistry and Biology SLO banks).
  - Other boards (BISE Punjab, Sindh, KPK). The curriculum layer is board-agnostic; add `board` rows and blueprints.
- **V2+:** JazzCash/Easypaisa subscriptions, offline mode (PWA) for low connectivity, WhatsApp tutor channel.

---

## 10. Risks and open questions

| Risk / question | Mitigation |
|---|---|
| FBISE changes the pattern again (it already changed in 2025 and 2026) | Blueprints and grading are **data**; add a new row, not a code change. Watch the FBISE notifications page. |
| Grade-point values for the new bands are unconfirmed | Keep them configurable; show the band, and hide GPA until confirmed. |
| Mathematics 50/50 structure details (64 MCQs / 48 marks) are unconfirmed | Parse the official `Maths_HSSC_I_model_paper_50_percent.pdf` before seeding. |
| AI marking disagrees with human examiners | Calibration set, conservative scoring, "estimated" label, show the rubric points, allow disputes. |
| Hallucinated or incorrect generated questions | Validator agent + expert approval for mock papers + user reports. |
| Textbook copyright | Don't ingest publisher books into the shared corpus; allow only private user uploads; pursue an NBF licence. |
| LLM cost per student | Cache SLO content globally, reuse the bank, cheaper models for validation and marking, usage limits. |
| Urdu / Roman Urdu quality | Evaluate candidate models on a Roman-Urdu physics Q&A set before choosing. |
| Two schemes (2006 vs 2024) at Grade XII until 2027 | `study_scheme` on the profile; seed both XII AFs (FBISE publishes both). |
| Free-trial credit expires (90 days, about mid/late December) or runs out | Budget alerts; upgrade to a paid billing account before the trial ends; the account-switch data move is scripted and tested beforehand (§7.2). |
| Cloud SQL smallest tier (few connections, shared CPU) | Small connection pools, API capped at 2 instances; move up a tier before the beta. Daily backups are on. |
| AI quota or outage during the judging demo | Paid Vertex quota, per-task fallback chain, demo content pre-generated, a recorded backup video. |
| Demo-day cold starts or slow jobs | Demo mode on 4–5 Oct (worker always on, one API instance kept warm). |
| Schedule risk: 9 days for the demo build | Fixed cut order (§7.1); D1–D4 first; feature freeze on 2 Oct. |
| Student data on a free AI tier | Production uses paid Vertex AI (no training on data). The free AI Studio key is only for local development with sample content. |

**Decided:** everything on Google Cloud (Cloud Run, Vertex AI Gemini, Cloud SQL, Cloud Storage, Identity Platform); Gemini models as in §5.7;
judging demo on 5 Oct 2026 with the §7.1 scope.

**Decisions still needed from you:**
1. **App name** (and any logo/colours), by 27 Sep.
2. Is Urdu-script explanation needed for the demo, or is English + Roman Urdu enough?
3. V1 after the demo: FSc Pre-Med + Pre-Eng only, or add Computer Science (ICS)?
4. Subject experts for review: a Physics reviewer for 1–2 Oct now, and reviewers for the other subjects after the demo.
5. Target public launch date relative to the exam calendar.

---

## Sources

- FBISE, *Curriculum > Model Question Paper with Assessment Frameworks*: https://www.fbise.edu.pk/curriculum_model_paper.php
- FBISE, *Implementation of Inclusive Scheme of Studies 2024* (No.0-5/FBISE/RES/CC/362, 27 Mar 2025), inside https://www.fbise.edu.pk/Syllabus/Scheme-of-Studies.pdf
- FBISE, *Assessment Framework Physics Grade XI, NCP 2022-23* (2025): https://www.fbise.edu.pk/ModelPaper/2025/Assessment%20Frameworks/HSSC-I/Final%20Assessment%20Framework%20Model%20Question%20Paper%20Physics%20HSSC-I.pdf
- FBISE, *AF Physics XI, 50% MCQs & 50% Descriptive*: https://www.fbise.edu.pk/ModelPaper/50_percent/Physics_HSSC_I_model_paper_50_percent.pdf
- FBISE AFs for Chemistry, Biology, Mathematics, Computer Science XI and Physics XII (2006 and 2024 schemes), all linked from the curriculum page above
- FBISE, *HSSC-I Scheme of Studies & Syllabus*: https://www.fbise.edu.pk/syllabusHSSC-I.php
- FBISE, *Detail of Textbook of HSSC Level*: https://www.fbise.edu.pk/notifications/hssc/Detail%20of%20Textbook%20of%20HSSC%20Level.PDF
- APP, *Federal Board announces implementation of national curriculum from academic year 2024*: https://www.app.com.pk/national/federal-board-announces-implementation-of-national-curriculum-from-academic-year-2024/
- ProPakistani, *FBISE Introduces New Exam Pattern for Five Subjects* (15 Aug 2026): https://propakistani.pk/2026/08/15/fbise-introduces-new-exam-pattern-for-five-subjects/
- ResultChecker, *FBISE New Examination Pattern (50% MCQs/50% Descriptive)*: https://resultchecker.com.pk/fbise-new-examination-pattern-2027-announced/
- Dawn, *'Passing marks' raised as federal board revises grading system*: https://www.dawn.com/news/1947346
- The Nation, *FBISE introduces new grading system for SSC and HSSC* (9 Oct 2025): https://www.nation.com.pk/09-Oct-2025/fbise-introduces-new-grading-system-ssc-hssc
- IBCC, *New Grading System of SSC & HSSC – FAQs*: https://ibcc.edu.pk/faqs/new-grading-system-of-ssc-hssc-faqs/
- Nearpeer, *Federal Board New Paper Pattern 2026-27*: https://nearpeer.org/blog/General/federal-board-new-paper-pattern-2026-2027
- Google, *Gemini API billing* (trial credit excluded from the Gemini API since March 2026): https://ai.google.dev/gemini-api/docs/billing
- Klymentiev, *Gemini Free Credits 2026: Why the $300 Trial No Longer Works* (trial still covers Vertex AI): https://klymentiev.com/blog/gemini-free-credits
- Google Cloud, *Free Trial FAQs*: https://cloud.google.com/signup-faqs
- Google Cloud, *OpenAI compatibility on Vertex AI*: https://docs.cloud.google.com/vertex-ai/generative-ai/docs/start/openai
