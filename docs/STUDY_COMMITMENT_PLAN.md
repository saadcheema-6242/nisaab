# Plan: study commitments (the student's own agent)

Written 18 Oct 2026, from the user's idea: a student sets a goal and a time,
NISAAB prepares the work, and if they skip it the app holds them to it when
they next open it.

This is a commitment device, not a background worker. The student binds their
future self, and the enforcement happens when they open the app — so it needs
no email, push or notifications, which is what blocked the earlier "agents
running 24/7" idea.

## What the student sets

Three choices, not a free-form builder, so cost stays predictable and nothing
strange can be configured.

| Setting | Options |
|---|---|
| **What** | Subjects (one, some or all); how many questions; weakest SLOs, a chosen domain, or mixed; quiz / flashcards / short questions |
| **When** | Time of day; which days; optionally "until my exam" |
| **If I skip it** | Nothing · remind me on the dashboard · hold practice until I attempt it |

## How it runs

```
Overnight job (jobs.run_after already supports this)
  -> picks the student's weakest SLOs from mastery
  -> builds the set from the bank (instant) and tops up with AI if short
  -> stores it as "today's commitment", ready and waiting
Student opens the app
  -> it is already there, no generation wait
  -> if yesterday's was missed, the chosen consequence applies
```

Building it overnight also removes the 45-90 second wait, so the set opens
instantly.

## The lock, which is the part that can backfire

A lock a student feels is unfair gets the app deleted, not respected.

- Opt-in, and the student picks the severity. Never a default.
- Grace built in: a few skips a week, plus "I am ill" and "exam tomorrow".
- **Never hold the tutor chat.** Hold practice only. A student stuck on
  homework at 11pm must always be able to ask for help.
- Turning it off takes effect the next day, not instantly. Instant off has no
  teeth; no off at all is a trap. A cooling-off period is the honest middle.
- Wording stays encouraging, never punishing. These are 16-18 year olds.

## Work

1. `study_commitments` table: user, project(s), what, when, consequence, grace
   used, created/paused.
2. A nightly scheduler pass that enqueues one build job per active commitment.
3. A worker processor that builds the set and stores it as pending.
4. Dashboard: today's commitment, a streak, and missed ones.
5. The hold: a check in the practice routes and the web app, with the escape
   hatches above.
6. Settings screen to create, pause and delete, with the cooling-off rule.

Roughly 3-4 days.

## Cost

One build per student per day, mostly from the bank, so close to free. If a
student sets all three subjects, that is three small sets. Cap it at one
commitment per subject per day so the bill cannot run away.

## Timing

After 29 October. For the competition it is worth a line on the board under
what comes next — "students set their own study commitment and NISAAB holds
them to it" is memorable, and costs nothing to say.
