# 7. Accounts and access

Three kinds of account, and one of them is all three at once.

## Signing in

Google Identity Platform (Firebase Authentication). Email and password,
or Continue with Google.

The API verifies the ID token against Google's published keys
(`edu-api/auth.py`, `PyJWKClient`) on every request. There is no session
table and no cookie.

Email and password accounts must confirm the address before the API will
serve them. Google accounts arrive already confirmed. A new account that
skipped confirmation used to reach the dashboard and see every panel fail
with no explanation; `/verify-email` now holds them and polls, so the
page moves on by itself when they click the link in another tab.

## Student

The default. Picks a year and a group at onboarding, which creates a
`student_profile` and their subject projects.

Everything a student sees is scoped to that (grade, group): projects,
syllabus map, timetable, class room, progress.

## Teacher

Anyone may say at signup that they are a teacher, and **the claim grants
nothing**.

```
signup → "I am a teacher" → subjects and years → /awaiting-approval
                                                        ↓
                                        an administrator approves
                                                        ↓
                                              the teacher dashboard
```

The application is a `teacher_profile` row. Approval is
`users.teacher_approved_at` being set, by an administrator, from the
Teachers tab of the admin dashboard.

Until then the account is held on `/awaiting-approval`, which polls every
fifteen seconds so the teacher does not have to be told to refresh, and
offers a way to withdraw — a mistaken tap should not strand an account
for ever.

**An unapproved teacher is not offered in the scheduling dropdown.** This
is the single most important rule in the role system: filtering "who can
teach" by role alone looks correct and quietly makes every stranger who
ticked a box assignable to a class of real students. `can_teach()`
requires both the role and the date, and `ClassSessionService.create()`
refuses a teacher id that fails it even if the dropdown is bypassed.

### What a teacher sees

A teacher has no `student_profile`, so the student pages are not merely
empty for them — they are unanswerable. They read a profile that does not
exist.

So a teacher gets their own surface: **My classes**, **Sessions**,
**Settings**. No My FSc, no Progress, no class rooms, no project list.

`src/edu-web/src/lib/surface.ts` states this once:

- `surfaceFor(account)` → `'student' | 'teacher' | 'admin'`
- `teacherMayOpen(pathname)` → may a teacher open this page

Both the sidebar and the route guard read it. **Two places, because a
sidebar that hides a link is not access control — the URL still works —
and a guard that blocks a page the sidebar still offers is a dead end
the user is invited to walk into.** Sharing one function is what stops
them drifting apart.

A teacher who types `/dashboard/community` is returned to their own
dashboard rather than shown a refusal. There is nothing they can do about
it and the page does not exist for their kind of account.

## Administrator

An administrator is on the `ADMIN_EMAILS` list. **There is no `is_admin`
column** — chapter 13 explains why.

An administrator is deliberately all three at once: a student of every
cohort, a teacher, and the person who approves teachers. Not a fourth
kind of account with its own rules.

That means:

- They do onboarding exactly once, to pick a cohort to start in, and are
  never held for approval.
- They are not pinned to that cohort afterwards: the class rooms offer a
  room switcher, and their timetable is every class in the school.
- They keep the student dashboard, which is the more useful of the two
  for them.
- In the class rooms they post as **Admin**, shown as a badge beside
  their name rather than by renaming the author — a badge cannot be
  impersonated by someone calling themselves "Admin".

### The admin dashboard

Tabs: **Accounts**, **Teachers**, **Sessions**, **Moderation**.

- *Accounts* shows counts, not contents. Reading a student's own work is
  a different decision and this screen is not it.
- *Teachers* is the approval queue, with what each applicant said about
  themselves.
- *Sessions* arranges the weekly timetable and assigns approved teachers.
- *Moderation* is the report queue for the class rooms.

## Reviewer

A separate, smaller role from `REVIEWER_EMAILS`: access to the **Review
content** page, where generated SLO content is approved or rejected.
Independent of teacher approval.

## Where each rule lives

| Question | Answered by |
|---|---|
| Is this token valid? | `edu-api/auth.py` |
| Is this an administrator? | `ADMIN_EMAILS`, `config.py` |
| May this account teach? | `edu_core.roles.can_teach()` |
| Where must this account go first? | `edu_core.roles.needs_onboarding()` |
| Which surface is this? | `edu-web/src/lib/surface.ts` |

The first four are server-side. The fifth is navigation only — it decides
what the app shows, not what the API will answer. See chapter 14 for what
that currently does and does not protect.

Next: [8. Features](08-features.md)
