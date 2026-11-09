> **Superseded.** This describes an earlier version of NISAAB and is no
> longer maintained. The current documentation is
> [docs/handbook](../handbook/README.md), written 9 November 2026.
> This file is kept only so older links still resolve.

# 10. Data Model

The data layer uses SQLAlchemy 2.0 with typed mapped columns, Alembic for migrations, `psycopg2` as the driver and `pgvector` for vector columns. There are 28 tables.

| Group | Tables |
|---|---|
| Identity | `users`, `student_profiles` |
| Workspaces | `projects`, `subjects`, `grade_subjects` |
| Curriculum | `curriculum_domains`, `slos`, `content_items` |
| Documents | `documents`, `document_segments` |
| Conversation | `chats`, `chat_messages`, `chat_message_parts` |
| Practice | `quizzes`, `quiz_questions`, `flashcard_groups`, `flashcards`, `flashcard_progress`, `notes`, `mind_maps`, `practice_papers`, `srq_questions`, `srq_attempts` |
| Learning record | `practice_records`, `practice_attempts`, `study_plans`, `user_usage` |
| Infrastructure | `jobs` |

## 10.1 Key design points

- **Vector size 3072.** The `document_segments` table stores 3072-dimensional vectors, matching the embedding model.
- **Composite index on `content_items`.** The index on `(grade_subject_id, slo_code, kind)` lets the pre-generated practice for an outcome be fetched in one indexed lookup.
- **Cascade deletion.** Documents and segments are deleted with their owner or project, so a deleted account leaves nothing behind.
- **Review columns.** `content_items` has `review_status`, `reviewed_by`, `reviewed_at`, `review_note` and `source`, so every generated item carries its provenance and approval state.
- **Ownership.** A project belongs to a user. Documents, chats, quizzes, papers and attempts belong to a project.
