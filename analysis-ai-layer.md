# AI Layer Analysis — NISAAB

## Overview

NISAAB's AI layer (`edu-ai` package) is a LangChain/LangGraph-based system that provides:
1. A multi-provider LLM abstraction (Vertex AI Gemini, Azure OpenAI, OpenAI, Gemini API)
2. A tool-calling chatbot agent with 11 tools
3. Specialised content generation agents (quiz, flashcard, note, mind map, SRQ, paper)
4. RAG retrieval over student-uploaded documents via pgvector
5. Syllabus lookup over FBISE curriculum data

---

## LLM Provider Abstraction (`llm.py`)

### Multi-Provider Support
The `LLM_PROVIDER` environment variable selects:
- **`vertex`** (production): Gemini on Google Cloud Vertex AI via OpenAI-compatible endpoint
- **`gemini`**: Google Gemini API (AI Studio key) via OpenAI-compatible endpoint
- **`azure`**: Azure OpenAI (GPT-4o default)
- **`openai`**: OpenAI or any compatible endpoint

### Per-Task Model Selection
Four model slots allow different models per workload:
- `LLM_TUTOR_MODEL` — the chatbot conversation
- `LLM_GENERATION_MODEL` — content generation (quizzes, flashcards, etc.)
- `LLM_MARKING_MODEL` — answer marking / moderation
- `LLM_OCR_MODEL` — document OCR via Gemini's native file input

All fall back to `LLM_CHAT_MODEL` if not set. Default is `gemini-3.5-flash`.

### Fallback Chain
`LLM_FALLBACK_MODELS` (comma-separated) builds a chain: on rate limits or server errors, the call moves to the next model. The custom `GeminiChatOpenAI` class handles:
- **Thought signatures**: Gemini 3 returns signatures with tool calls that must be echoed back
- **Streaming fallback**: only before the first chunk (can't switch mid-stream)
- **Retry budget**: `RETRIES_BEFORE_FALLBACK` (2) retries per model before moving on

### Native Gemini API
Three functions bypass the OpenAI-compatible endpoint for Gemini-specific features:
- `generate_from_file()` — PDF/image input (native generateContent)
- `run_code()` — Code execution in Google's sandbox (matplotlib figures)
- `generate_text()` — Short judgement calls (community moderation, 20s timeout)

### Embeddings
- **Vertex AI**: Custom `VertexEmbeddings` class using native `:predict` API (not OpenAI-compatible, which errors)
- Uses `RETRIEVAL_DOCUMENT` / `RETRIEVAL_QUERY` task types for better search quality
- 3072-dimensional vectors matching the pgvector column
- Batch size of 20, exponential backoff on retries

---

## Chatbot Architecture (`chatbot/`)

### ChatbotContext
Carries per-request state:
- `user_id`, `project_id`, `language` (en / ur / ur-Latn)
- `fbise`: FBISE subject context (grade_subject_id, subject name, grade label, curriculum)
- `search`: SearchService for RAG
- `queue`: QueueService for background generation
- `usage`: Rate limiting service
- `allowed_tools` / `web_search`: student's per-message tool choices

### Agent Factory (`factory.py`)
The `make_chatbot()` function builds a LangGraph ReAct agent with:
- **11 tool categories**: RAG, syllabus, web, practice (quiz/flashcards/mind_map/paper), diagram, figure, flashcard, quiz, note, mind_map, study_plan
- **4 middleware**:
  1. `stop_repeating_yourself` — detects tool call loops (e.g. 5x syllabus lookup) and injects a note
  2. `capture_sources_from_rag` — extracts document sources from RAG results for citation
  3. `dynamic_system_prompt` — renders the FBISE-specific system prompt with subject/grade/language
  4. `ensure_sources_in_stream` — carries sources through streaming

### Tool Filtering
- Student can restrict tools per message (UI checkboxes)
- `ALWAYS_AVAILABLE` set: `find_syllabus_slos`, `search_project_documents` (always needed)
- Web search can be toggled off per message

### System Prompt
- Cached by (language, fbise context) for performance
- Dynamic per-message appendix for tool choices and web search state

---

## Tools (11 tool modules)

### Core Retrieval Tools
1. **`search_project_documents`** (RAG) — pgvector similarity search over student uploads
   - Top-5 results, filtered by minimum score (0.45) and relative cut (75% of best)
   - Returns formatted context with source tracking for citations
2. **`find_syllabus_slos`** — TF-IDF-like search over FBISE SLOs
   - Handles SLO codes directly (e.g. `P-11-B-05`)
   - Includes teacher-approved explainer if available from content bank
3. **`search_web`** — Web search (when enabled)

### Practice Tools (return_direct — card shown immediately)
4. **`ask_practice_questions`** — Shows setup card with tappable options before generating
   - Automatically adds "Which part of the syllabus?" from real chapter list with weak SLOs pre-selected
5. **`practice_quiz`** — Interactive MCQ quiz (instant feedback, mastery tracking)
6. **`practice_flashcards`** — Flip-card study (Knew it / Still learning, mastery tracking)
7. **`practice_mind_map`** — Visual zoomable mind map
8. **`practice_paper`** — Full FBISE-style practice paper (MCQ + SRQ + ERQ sections)
   - Lengths: mini (20min), standard (45min), half (90min), board (3hr, 80 marks)

### Content Generation Tools
9. **`generate_note`** — Markdown study notes
10. **`generate_diagram`** / **`generate_figure`** — Diagrams and matplotlib figures via code execution

### Study Planning
11. **`generate_study_plan`** — Study plan based on mastery gaps

---

## Content Generation Agents (`agents/`)

Specialised LangChain agents for each content type:
- **`quiz_agent`** — MCQ generation with cognitive levels and SLO alignment
- **`flashcard_agent`** — Q&A flashcard generation
- **`note_agent`** — Structured notes generation
- **`mind_map_agent`** — Node/edge graph generation for visual maps
- **`srq_agent`** — Short-response question generation with rubrics
- **`bank_agent`** — Pre-generated content bank (explainers, MCQs, SRQs for teacher review)
- **`slo_context`** — Builds SLO context for generation prompts
- **`slo_mind_map`** — SLO-structured mind maps
- **`topic_graph_agent`** — Topic relationship graphs

---

## RAG Pipeline

### Document Processing (Worker)
1. Document uploaded → stored in Cloud Storage → job queued
2. Worker processes: extracts text (Gemini for PDFs/images, local extraction for text)
3. Text chunked into segments
4. Each segment embedded (3072-dim Gemini embeddings) → stored in `document_segments.embedding`

### Query Time
1. Student query → embedded via `RETRIEVAL_QUERY` task type
2. pgvector cosine similarity search (top-5)
3. Score filtering: absolute floor (0.45) + relative cut (75% of best)
4. Context formatted with source tracking
5. Sources captured by middleware for UI citation display

---

## Key Design Decisions

1. **OpenAI-compatible endpoint** for Gemini — allows LangChain's ChatOpenAI base class, only native API for specific features
2. **No external vector DB** — pgvector in Postgres; at this scale (one board, nine subjects) a separate service adds complexity for no gain
3. **Tool call loop detection** — prevents the model from repeating the same tool call (e.g. 5x syllabus lookup) which wasted student time
4. **return_direct practice tools** — practice cards shown immediately without another model call
5. **Fallback chain** — production resilience across multiple Gemini models
6. **Per-task models** — marking uses temperature 0, tutoring allows creativity
7. **Code execution** — for accurate diagrams/figures (matplotlib in Google's sandbox, not model-drawn)
8. **Short timeout for moderation** — 20s; a slow answer is worse than no answer for community posts
