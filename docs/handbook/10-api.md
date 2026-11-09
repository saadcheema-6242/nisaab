# 10. API

FastAPI, under `/api/v1`. Routers in `src/edu-api/routers/`.

Authentication is an Identity Platform ID token in
`Authorization: Bearer …`, verified on every request against Google's
published keys. No sessions, no cookies.

## The routers

| Router | Covers |
|---|---|
| `auth`, `users`, `profile` | Account, profile, onboarding |
| `projects`, `documents`, `notes` | Workspaces and material |
| `chats` | The tutor |
| `quizzes`, `flashcard_groups`, `mind_maps`, `study_plans` | Generated artefacts |
| `curriculum` | Subjects, domains, SLOs, the syllabus map |
| `practice_records`, `attempts`, `srq`, `papers` | Practice and marking |
| `progress` | Mastery, cognitive levels, trend, activity |
| `community` | Class rooms, posts, polls, reports |
| `sessions` | Weekly class sessions |
| `teachers` | Applying, the queue, approval |
| `admin` | Accounts, counts, bans |
| `review` | Reviewing generated content |
| `usage` | Daily limits |

The generated OpenAPI schema is the reference:
`python scripts/export_openapi.py`. With `API_DOCS=true` the service also
serves interactive docs.

## How the routes are guarded

Four patterns, used consistently.

**Signed in.** `Depends(get_current_user)`. The default.

**Administrator.** `Depends(require_admin)`, which raises **404, not
403**:

```python
def require_admin(current_user = Depends(get_current_user)) -> UserDto:
    if not is_admin(current_user):
        raise HTTPException(status_code=404, detail="Not found")
    return current_user
```

A signed-in student guessing `/api/v1/sessions` learns nothing about
whether it exists. 403 confirms the endpoint is real and that they are
simply the wrong person.

**Open, but answered from the token.** `GET /sessions/teaching` is open
to any signed-in account; a student calling it gets their own empty list,
which is both true and harmless. It means the page does not need to know
the caller's role before it can load.

**Answered in one call.** `GET /teachers/me` returns the whole account
state — role, admin, onboarded, approved, and `send_to`. One request, so
the router can decide where an account belongs before anything renders.
Asking three questions separately would mean guessing while the answers
arrived, and a teacher awaiting approval would see a flash of the student
dashboard on the way to the waiting page.

## What the server decides, not the page

Worth stating because it is the difference between a guard and a
decoration:

- **Join links.** `for_student` attaches `join_url` only inside the
  fifteen-minute window. Outside it, the field is `null` on the wire. The
  page never receives a link it should not show.
- **Which room.** A post's grade and group come from the caller's
  profile. The client cannot ask for another room.
- **Who may teach.** `create()` re-checks `is_approved_teacher` against
  the database even though the dropdown only offered approved teachers.
- **What a post may contain.** Checked server-side; the page's own check
  is a courtesy to the typist.

## Errors

`edu_core.exceptions` maps to status codes in the routers.
`NotFoundError` → 404, domain errors (`SessionError`, `RoleError`) → 400
with the message passed through, because those messages are written for
the person reading them to act on — "That account is not an approved
teacher. Approve it from the Teachers tab first." is more use than "Bad
request".

Next: [11. Operations](11-operations.md)
