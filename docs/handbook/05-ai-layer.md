# 5. The AI layer

`src/shared/ai/src/edu_ai/`.

## Models

Production runs **Gemini on Vertex AI**, in `asia-south1`.

`llm.py` can also speak to the Gemini API directly (AI Studio key) and to
OpenAI, both through the OpenAI-compatible endpoint. That is not
hedging — it is what makes a local developer able to work without a GCP
project.

Models are set **per task**, falling back to `LLM_CHAT_MODEL`:

| Variable | Used for |
|---|---|
| `LLM_TUTOR_MODEL` | The conversation with the student |
| `LLM_GENERATION_MODEL` | Quizzes, flashcards, mind maps, plans |
| `LLM_MARKING_MODEL` | Marking written answers |
| `LLM_OCR_MODEL` | Reading uploaded images and scans |

Separate knobs because the jobs are not alike. Marking wants determinism
and runs at temperature 0. Tutoring wants warmth. Generation runs on the
worker where latency does not matter, so it can afford a better model
than the chat path.

`LLM_FALLBACK_MODELS` lists models to try when the first is rate-limited
or unavailable. On exhibition day that is the difference between a demo
and an apology.

## Retrieval

Documents are chunked into `document_segments`, embedded, and stored in
Postgres with pgvector. Syllabus content is embedded the same way.

Retrieval is scoped to the student's own project and to their grade and
group. A Pre-Medical student asking about cell division does not get ICS
material, because the SLO rows carry the cohort and the query is filtered
before the vectors are compared.

## Tools

The tutor is an agent with tools, in `edu_ai/tools/`:

| Tool | What it does |
|---|---|
| `rag.py` | Looks up syllabus and document context |
| `quiz.py` | Builds a quiz, in the chat |
| `flashcard.py` | Builds a flashcard set |
| `mind_map.py` | Builds a mind map from the syllabus |
| `note.py` | Writes a note |
| `study_plan.py` | Builds a plan to a date |
| `practice.py` | Starts SLO practice |
| `diagram.py`, `figure.py` | Diagrams and figures |

`edu_core/tool_loops.py` holds the rules about how many times a tool may
be called and when a loop should be cut off — a pure module, checked
offline, because a runaway tool loop costs real money.

## Agents

`edu_ai/agents/` holds the non-conversational generators: `quiz_agent`,
`flashcard_agent`, `mind_map_agent`, `note_agent`, `srq_agent`,
`bank_agent` (pre-generated reviewable content), `topic_graph_agent`, and
`slo_context` / `slo_mind_map` which assemble syllabus context for them.

These run on the worker, not in the request.

## What the model is never trusted with

A deliberate list, because it is the difference between a tutor and a
toy:

- **Arithmetic on marks.** Each point is judged, the sum is computed in
  Python.
- **What the syllabus says.** It comes from `slos`, a row from the
  board's published document, not from recall.
- **Whether a student has mastered something.** That is
  `edu_core.mastery`, a formula.
- **Whether a post breaks the rules.** The model advises; the refusal
  rules in `edu_core` decide, and `personal_details.py` is regex, not
  judgement.

No model is fine-tuned. Chapter 13 explains why.

Next: [6. Curriculum](06-curriculum.md)
