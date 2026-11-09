# 12. Testing

Three layers, each answering a different question.

## Offline checkers — "do the rules still hold?"

`scripts/admin/check_*.py`, 22 of them. Plain Python, no test runner, no
database, no API key, no pgvector. They run in seconds.

```
check_answer_check      check_group_change        check_progress_trend
check_chat_attachments  check_migration           check_roles
check_code_run          check_moderation          check_schema
check_community         check_openly_licensed     check_source_hygiene
check_community_rules   check_paper_blueprint     check_study_plan
check_community_wiring  check_paper_plan          check_tool_loops
check_docs_gate         check_personal_details    check_weekly_session
                        check_plain_math
```

This is the pay-off from the pure-module split in chapter 2. Because
`mastery.py`, `weekly_session.py`, `roles.py` and the rest import no
database, the rules that matter most can be checked by a script a
developer will actually run — not a suite needing a Postgres container,
which is a suite nobody runs before pushing.

`check_weekly_session.py` has 62 assertions; `check_roles.py` has 40.

Two are worth singling out:

- **`check_schema.py`** compares models against migrations and fails
  locally with `ModuleNotFoundError: edu_db` — it is a cloud-only check.
- **`check_source_hygiene.py`** and **`check_openly_licensed.py`** guard
  provenance: content must be traceable and licensing honest.

## The end-to-end suite — "does it work against the real thing?"

`scripts/e2e_ai_check.py`, run in the cloud:

```bash
deploy/gcp/deploy.sh e2e
```

A real database, real models, real services. **244 checks** across
sections including:

| | |
|---|---|
| 1–4 | Documents, search, chat, worker generation |
| 5–6 | Onboarding, the syllabus map, every group and subject |
| 7 | The tutor in Roman Urdu |
| 8 | SLO practice and mastery, quizzes/flashcards/mind maps in chat |
| 9 | Written-answer marking, practice papers |
| 10 | Progress and predicted grade |
| 12 | Class rooms: two students, visibility, refused contact details |
| 14 | Weekly sessions (50 checks) |
| 15 | Teacher accounts and approval (48 checks) |

Section 15 is arranged entirely around one question — *can an account
that merely ticked "teacher" be put in front of a class?* — asked in
every way it can be asked, because the answer has to be no in all of
them and a single yes is a stranger teaching real students.

## Frontend tests — Vitest

58 tests, 9 files. Router guards, the paper page's choice pairs, the
onboarding redirect, the teacher surface rule.

```bash
cd src/edu-web && pnpm test
```

## What a test suite cannot tell you

Two real failures, recorded because the lesson generalises.

**The mastery bug.** `advance()` existed twice, once in the estimator and
once in the trend, and they disagreed: 0.882 where the answer was 1.0.
The checker passed. Why? **Every case in it used a single SLO**, and with
one outcome, pooling answers and averaging per-outcome estimates give the
same number. The test was correct and the coverage was a mirage. The fix
was to make one definition of the step and fold over it.

**The onboarding loop.** The test asserted that finishing onboarding
navigates to the dashboard, and it passed against code that bounced every
new student back to onboarding for ever. Why? **Its mock answered every
atom with the same value**, so it could not see that the page was
watching a different atom from the guard. The test is now written with
the two atoms distinct, and asserts the bug directly: refreshing the
profile alone must *not* navigate.

Both have the same shape. A test that passes tells you the code does what
the test describes; it does not tell you the test describes the thing
that matters. When something ships broken, the first question is not
"why was there no test" but **"why did the test that existed not see
it?"**

## Before pushing

```bash
python scripts/admin/check_roles.py          # and the others relevant to the change
cd src/edu-web && pnpm exec tsc --noEmit && pnpm test && pnpm lint
cd src/edu-web && pnpm build
```

Next: [13. Design decisions](13-decisions.md)
