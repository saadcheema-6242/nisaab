> **Superseded.** This describes an earlier version of NISAAB and is no
> longer maintained. The current documentation is
> [docs/handbook](../handbook/README.md), written 9 November 2026.
> This file is kept only so older links still resolve.

# 9 · Operations

[← Curriculum data](08-curriculum-data.md) · [Contents](README.md)

Running it, checking it works, and what has actually gone wrong.

---

## Everyday commands

Run from `edu-agent/` in Git Bash. No `GCLOUD=` prefix needed.

```bash
bash deploy/gcp/deploy.sh deploy
```

```bash
bash deploy/gcp/deploy.sh e2e
```

```bash
bash deploy/gcp/deploy.sh script scripts/admin/<name>.py
```

## Verifying a deploy

`e2e` runs the real flows against the live cloud stack. The run on **27 October 2026**
returned **52 checks, 52 passed, 0 failed**, with these timings:

| Operation | Time |
|---|---|
| Half board paper built | 38 s |
| Half board paper marked | 11 s |
| Short paper built / marked | 9 s / 9 s |
| Quiz card generated | 4 s |
| SRQ marked | 6 s |

That run also confirmed the marks fix live — *"paper made: 10 questions, 12 marks"*,
which is the mini-paper total from [Curriculum data](08-curriculum-data.md).

Run `e2e` after any deploy that touches generation, marking or papers.

---

## Google Forms

**Status: working.** First real form published 27 October 2026.

### Maths has to be converted first

Google Forms renders nothing — whatever is sent appears literally. Questions are
written in LaTeX because the app renders them with KaTeX, so the first published form
showed options reading `$\sqrt{x^2 + y^2}$` and `$4$`.

`edu_core.plain_math.latex_to_text` converts LaTeX to Unicode before publishing:
`x^2` → `x²`, `\sqrt{a}` → `√(a)`, `\alpha` → `α`, `H_2SO_4` → `H₂SO₄`. It runs on the
question, every option, the explanation, the title and the description.

The answer key is picked **from the converted options**, because Google matches the key
against the option text as a string — converting one but not the other would silently
break every answer key.

```bash
python scripts/admin/check_plain_math.py
```

31 cases, taken from the form that came out wrong and from the notation the five
subjects use. Run it after touching the converter.

### Why it needs an authorisation step

### Why it needs one

A **service account cannot own a Google Form.** Service accounts get no Drive storage
quota, and a Form is a Drive file, so creating one returns:

```
POST https://forms.googleapis.com/v1/forms
500  { "code": 500, "message": "Internal error", "status": "INTERNAL" }
```

A 500, not a 403 — which is why this looked like a Google outage through several
attempts. Verified on 27 October 2026 with the Forms, Drive and IAM Credentials APIs all
enabled and a correctly scoped token.

Both documented workarounds — a **shared drive**, or **domain-wide delegation** — require
Google Workspace. The project's account is a plain Gmail account, so neither is
available.

**The path that works without Workspace:** one real Google account authorises the app
once, offline, and its refresh token is stored in Secret Manager. Every form is created
in that account's Drive. Students never sign in to anything.

### Setting it up

One-time, in the Cloud console:

1. **OAuth consent screen** → External, app name NISAAB
2. **Audience** → add the owning Google account under **Test users**
3. **Data access** → add scopes `.../auth/forms.body` and `.../auth/drive.file`
4. **Credentials** → Create credentials → OAuth client ID → **Desktop app** → download the JSON

Then, on your own machine:

```bash
python scripts/admin/authorise_google_forms.py path/to/client_secret_*.json
```

It opens a browser, you consent (click through the "Google hasn't verified this app"
screen — expected, and only you ever see it), and it writes three secrets. **The refresh
token is never printed.** Then deploy and verify:

```bash
bash deploy/gcp/deploy.sh deploy
```

```bash
bash deploy/gcp/deploy.sh script scripts/admin/try_google_form.py
```

### The seven-day catch

While the OAuth app's publishing status is **Testing**, Google expires refresh tokens
after about **seven days**. Moving to **In production** with the Forms scope requires
Google's verification review.

Until then, re-run the authorise script when it lapses — it takes under a minute. Before
any demonstration, re-run it that morning regardless.

Symptom when it has lapsed: the API returns **503** with *"The stored Google
authorisation is no longer valid"*. That is deliberately distinct from a 502, which
means Google refused the call for some other reason.

---

## Troubleshooting

Everything here has actually happened.

### `can't open file 'D:\c\Program Files (x86)\...\gcloud.py'`

Git Bash mangled the SDK path. The wrapper is now auto-detected, so this should not
recur — if it does, the wrapper is missing from `deploy/gcp/gcloud-win`.

### A script change does not take effect

`deploy.sh script` **does not rebuild**. It runs whatever is in `edu-worker:latest`. Run
`deploy` first.

### A paper hangs, or takes minutes

Check `llm_request_timeout` is set (90 s). Without a timeout a stalled LLM connection
never returns. `BUILD_TIMEOUT_SECONDS` (9 min) is the backstop that fails the job so the
student is offered another attempt rather than an endless spinner.

### Jobs are queued but nothing runs

- `WORKER_ALWAYS_ON=false`? Then jobs wait up to a minute for Cloud Scheduler's
  `POST /drain`.
- Otherwise check `edu-worker` logs, and look for `running` rows with an old
  `locked_at` — `requeue_stale` should recover them.

### Vertex returns 429

`AI_CONCURRENCY` is 5. It was 8, which rate-limited us; every 429 is paid for twice,
once in the backoff and once in the retry. Do not raise it without watching the logs.

### The local `.venv` will not run

It points at a Python 3.12 that may no longer exist on the machine. Recreate it with
`uv sync`. The cloud builds are unaffected — they build their own environment.

---

## Known limits

| Limit | Detail |
|---|---|
| Curriculum coverage | Computer Science has 22 SLOs; Class XII is Physics only |
| Google Forms token | Expires ~7 days while the OAuth app is unverified |
| Queue throughput | A Postgres table, not a broker — ample here, not web-scale |
| AI correctness | SLO grounding constrains *what* is asked, not whether it is right. The teacher review queue exists for this |
| Generated content | Reviewable, not presumed correct |

---

## Routine maintenance

| When | Do |
|---|---|
| After the competition | Set `WORKER_ALWAYS_ON=false` and `API_MIN_INSTANCES=0`, then `deploy --skip-build` |
| Weekly, until verified | Re-run `authorise_google_forms.py` if Forms is in use |
| Before any demo | `deploy`, then `e2e`, then re-authorise Forms |
| Adding curriculum | Add the JSON, run `deploy.sh seed` |

### Backups

Cloud SQL backups run daily at 20:00, and deletion protection is on. A manual backup
labelled *"before deleting all users 2026-10-27"* exists from the pre-competition
cleanup.

---

[← Curriculum data](08-curriculum-data.md) · [Contents](README.md)
