# 3. Data model

PostgreSQL, SQLAlchemy models in `src/shared/db/src/edu_db/models.py`,
migrations under `.../alembic/versions` (50 of them as of 9 Nov 2026,
head `b8e4d21f6c39`).

The tables fall into six groups.

## Curriculum — the spine

| Table | What it holds |
|---|---|
| `subjects` | Physics, Chemistry, Biology, Maths, Computer Science, … |
| `grade_subjects` | A subject *in a year* — Physics XI is not Physics XII |
| `curriculum_domains` | The board's chapters within a grade subject |
| `slos` | Every Student Learning Outcome, with its cognitive level |

`slos` is the table everything else points at. An SLO carries the board's
own code, its text, and whether the paper examines it at Knowledge,
Understanding or Application.

This is the table that makes NISAAB what it is. A quiz question belongs
to an SLO. A practice attempt scores an SLO. Mastery is per SLO. Progress
is mastery over SLOs. See chapter 6 for how the board's PDFs become these
rows.

## People

| Table | What it holds |
|---|---|
| `users` | Identity, role, teacher approval, ban state |
| `student_profiles` | Year, group, explanation language, exam year |
| `teacher_profiles` | Subjects and years a teacher applied to teach |

A student has a `student_profile`; a teacher has a `teacher_profile`.
**They are different tables and an account normally has one of them, not
both.** That is why a teacher landing on a student page sees nothing —
there is no profile for it to read. Chapter 7 covers this properly.

`users.role` is `student` or `teacher`. Approval is
`users.teacher_approved_at`, a nullable timestamp, plus
`teacher_approved_by`. There is no `is_approved` boolean, deliberately
(chapter 13).

There is no `is_admin` column. Administrators are an environment
variable, `ADMIN_EMAILS` — also chapter 13.

## Study material

| Table | What it holds |
|---|---|
| `projects` | A workspace. One per subject, plus the student's own |
| `documents`, `document_segments` | Uploads, and their embedded chunks |
| `chats`, `chat_messages`, `chat_message_parts` | Tutor conversations |
| `quizzes`, `quiz_questions` | Generated quizzes |
| `flashcard_groups`, `flashcards`, `flashcard_progress` | Spaced practice |
| `notes`, `mind_maps`, `study_plans` | The other generated artefacts |
| `content_items` | Pre-generated, reviewable SLO content |

A chat message is split into *parts* rather than stored as one blob,
because an assistant turn is not one thing: it is text, tool calls, tool
results and generated artefacts interleaved, and the page has to render
them in order.

## Practice and progress

| Table | What it holds |
|---|---|
| `practice_records` | One answer to one SLO |
| `practice_attempts` | A sitting |
| `practice_papers` | A generated paper to the FBISE blueprint |
| `srq_questions`, `srq_attempts` | Written answers and their marking |

Mastery is **not** a column. It is computed from `practice_records` by
`edu_core.mastery`. Storing it would mean two sources of truth that drift
the first time a record is corrected or deleted.

## Class rooms

| Table | What it holds |
|---|---|
| `community_posts` | Posts and replies, scoped to a grade and group |
| `community_attachments` | Images and files on a post |
| `community_poll_options`, `community_poll_votes` | Polls |
| `community_reports` | What was reported, and the moderator's verdict |

A room is not a row. A room *is* a (grade, group) pair, and a post
carries that pair. There are exactly six rooms and they never need
creating.

## Weekly sessions

| Table | What it holds |
|---|---|
| `class_sessions` | A live class: subject, year, start, duration, link, teacher |

A session belongs to a **subject and a year**, not to a group. Physics XI
is one class, attended by Pre-Medical, Pre-Engineering and ICS students
alike, because all three study Physics. Which groups may attend is
derived from the subject by `edu_core.weekly_session.groups_for()` rather
than stored.

`class_sessions.teacher_id` is `ON DELETE SET NULL` and the row also
keeps `teacher_name`. Removing a teacher must not delete the timetable,
and a cancelled class is marked with `cancelled_at` rather than deleted:
an administrator looking at a gap in next week needs to know whether it
was called off or never arranged.

## Operational

`jobs` — the worker queue. `user_usage` — per-day counters for the limits
in chapter 11.

Next: [4. Domain logic](04-domain-logic.md)
