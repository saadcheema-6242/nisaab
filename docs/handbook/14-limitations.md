# 14. Limitations and roadmap

Written to be read by someone deciding whether to trust this. Nothing
here is hidden elsewhere in the handbook.

## Not built

| | |
|---|---|
| **Attendance** | Sessions exist; who attended is not recorded |
| **Email reminders** | Nothing is sent. Cloudflare Email Routing is receive-only, so outbound needs a provider that does not exist yet |
| **Automatic Google Meet creation** | Links are pasted by hand. Needs `calendar.events`, a sensitive OAuth scope, on the same consent screen student sign-in depends on — deliberately deferred |
| **FSc Part 2** | Only Physics XII is loaded. Four subjects missing |

## Built but unproven

**AI marking has never been compared with a real examiner.** Written
answers are marked point by point at temperature 0 and totalled in code,
which is the most defensible arrangement available, but no study has been
done against human marking. Every mark says **AI-estimated**, and that
label should stay until somebody does the comparison.

**The content bank has not been reviewed.** Pre-generated explainers,
MCQs and SRQs exist, the review page is built, and the first pass over
the bank has not happened. Unreviewed items carry no "Teacher-checked"
badge, which is the honest signal, but a student can still meet them.

**Predicted grade** is derived from mastery against paper weights. It is
a reasonable model and has not been validated against actual results.

## Known weaknesses

**Role enforcement is complete on the server for the things that matter
and partial elsewhere.** Who may teach, who may schedule, which room a
post lands in and when a join link is released are all decided
server-side and re-checked. But a teacher calling the community or
progress endpoints directly would get a response — an empty one, because
those endpoints read the caller's own profile and a teacher has none. No
data leaks; it is simply not a refusal where it should be. The UI never
takes them there. **Worth closing, after 13 November.**

**CORS is wider than it needs to be.** Known, not yet tightened.

**App Check is not enforced.** The API is reachable with a valid user
token from anywhere.

**The main JS chunk is 1.5 MB (442 KB gzipped).** Routes are
code-split, but the vendor chunk is large. Shiki's language grammars and
Mermaid are most of it.

**`motion/react` now loads on the sign-in page** — about 37 KB gzipped —
for the logo animation. Anyone arriving via the landing page has it
cached. A direct visit to `/sign-in` pays for it.

**No service worker.** The PWA manifest exists and the app installs, but
it does not work offline.

**`check_schema.py` cannot run locally**, failing with
`ModuleNotFoundError: edu_db`. Cloud only.

**Two abandoned trees remain in the repo**: `src/eduagent-vibecode` and
`deploy/azure`, from the project this was forked from.

## Scale

Untested beyond a handful of concurrent users. Cloud Run will scale the
stateless parts; Cloud SQL is a single instance and the first thing that
would need attention. No load testing has been done.

## Roadmap

**Before 13 November 2026**
- Seed a demo account with real practice history, so the Progress graphs
  show something. This is the largest visible gap today
- A pass over `README.md`

**Soon after**
- Attendance
- Email reminders, once an outbound provider is chosen
- Close the server-side role gap above; tighten CORS; enforce App Check
- Review the content bank

**Later**
- FSc Part 2 for the remaining four subjects
- Automatic Meet creation, once the sensitive scope can be reviewed
  safely
- Compare AI marking against examiner marking, and either drop the
  "estimated" label or keep it on evidence
- A Tauri desktop build. Feasible; the work is almost entirely in moving
  OAuth to the system browser, since Google blocks OAuth in embedded
  webviews

Next: [15. Glossary](15-glossary.md)
