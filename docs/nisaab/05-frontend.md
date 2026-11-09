> **Superseded.** This describes an earlier version of NISAAB and is no
> longer maintained. The current documentation is
> [docs/handbook](../handbook/README.md), written 9 November 2026.
> This file is kept only so older links still resolve.

# 5 · Frontend

[← Backend](04-backend.md) · [Contents](README.md) · [Next: AI layer →](06-ai.md)

React 19 · TypeScript 5.9 · Vite 7 · Tailwind CSS 4 · 232 source files

---

## The stack, and why

| Choice | Version | Why this one |
|---|---|---|
| **React** | 19.2 | — |
| **Vite** | 7.1 | Fast builds; the whole app builds in under a minute |
| **TanStack Router** | 1.132 | **Type-safe routing** — a `<Link>` to a path that does not exist fails to compile |
| **Effect + `@effect-atom/atom-react`** | 3.18 / 0.3 | Async state as values: loading, failure and success are cases you must handle, not a flag you might forget |
| **Tailwind CSS** | 4.1 | Theme as CSS custom properties, which made the full retheme a token change |
| **Radix UI** | — | Accessible primitives behind the visible components |
| **KaTeX** | 0.16 | Mathematics rendering |
| **`@xyflow/react`** | 12.8 | Mind map canvas |
| **`html-to-image` + `jsPDF`** | — | The export pipeline |
| **Firebase JS SDK** | 12.19 | Identity Platform login |

---

## Routing

**23 routes**, in `src/routes/_config.tsx`.

### Public

`/` · `/features` · `/about` · `/contact` — the marketing site, behind a shared
`marketing-layout`. `/sign-in` · `/sign-up` · `/onboarding`.

### The app

```
/dashboard                                   subjects
/dashboard/p/$projectId                      a subject: Syllabus · Study · History
                      /c/$chatId             a tutor conversation
                      /d/$documentId         an uploaded document
                      /q/$quizId  [/edit]    a quiz
                      /f/$groupId [/edit]    flashcards
                      /n/$noteId             a note
                      /m/$mindMapId          a mind map
                      /paper/$paperId        a practice paper
                      /srq/$questionId       a short-response question
                      /study-plan            the study plan
/review                                      teacher review queue
/settings                                    class, group, language
```

### One routing subtlety worth recording

The landing page once hung on "Loading…" forever. `useAuth` **suspends**, and it was
being read above the layout, so the whole page waited on an auth check that the public
site does not need.

The fix: an isolated `AuthRedirect` behind its own `<Suspense fallback={null}>`. The
marketing page renders immediately; the redirect resolves when it resolves. Worth
remembering — suspending hooks pull their *entire* subtree into the wait.

---

## State

Effect atoms, roughly 118 atom definitions across `src/data-acess/`.

`Atom.family` gives one atom per entity key (`projectId:quizId`), and `Atom.keepAlive`
holds the ones worth caching. Reads come back as a `Result` the component matches on:

```ts
const quiz = useAtomValue(quizAtom(key))
if (!Result.isSuccess(quiz)) return null
// quiz.value is typed and definitely present here
```

> **`registry.refresh(atom)` is fire-and-forget.** It starts a refetch; it does not wait
> for one. Code that assumed otherwise caused the onboarding bug below.

### The onboarding redirect bug

Finishing onboarding navigated straight to `/dashboard`, the route guard read a profile
that still said `onboarded: false`, and bounced the student back to step 1.

The fix was not to add a delay but to **wait for the fact**:

```tsx
await completeOnboarding({...})
setFinished(true)

// completeOnboarding refreshes the profile but does not wait for it,
// so leave only once the profile we can see agrees we are onboarded.
useEffect(() => {
  if (!finished) return
  if (Result.isSuccess(profileResult) && !profileResult.value.onboarded) return
  navigate({ to: '/dashboard', replace: true })
}, [finished, profileResult, navigate])
```

The effect mirrors the guard's own condition, so the two cannot disagree. A regression
test covers it — it failed against the old code with `navigate` called once, too early.

---

## Theming

64 colour tokens in `styles.css`, derived from the NISAAB logo:

```css
--primary: oklch(0.4725 0.0914 160.6173);  /* #1F6B4A */
```

Dark mode redefines the same names (`#6FCF9F` for primary). Components never name a
colour; they name a token. **All 16 foreground/background pairs were checked against
WCAG AA** and pass.

---

## The export pipeline

`src/lib/export/` — `core.tsx` plus one module per artefact (quiz, flashcards, paper,
note, mind map).

How it works: the artefact is rendered into an off-screen React tree, each element
marked `data-block`, then rasterised block by block and laid onto A4 pages **without
splitting a block across a page break**.

```ts
const scale = blocks.length > 60 ? 1.25 : blocks.length > 25 ? 1.5 : 2
const canvas = await toCanvas(block, scale, fontCss)
...
canvas.width = 0            // release the bitmap immediately
canvas.height = 0
await new Promise((r) => setTimeout(r, 0))   // let the browser reclaim it
```

Two lessons are encoded there. **Resolution scales down as the document grows** — an
80-question board paper at full resolution exhausted memory and took far too long.
And **each canvas is freed as soon as it is drawn**, with a yield to the event loop;
without that, a long export accumulated every page's bitmap at once.

Papers export in three modes — `blank`, `answers`, `solutions` — driven by one
component, with ruled writing space sized by the marks each question is worth.

---

## Rendering mathematics

`src/lib/math.ts` splits text into maths and prose. The tokeniser is **brace-aware**:

```ts
const braceDepth = (word: string) =>
  (word.match(/(?<!\\)\{/g)?.length ?? 0) - (word.match(/(?<!\\)\}/g)?.length ?? 0)
```

Without it, `9.5\text{ m}` was split at the space inside `\text{...}`, producing the
literal `$$9.5\text{$$ m}` on screen — raw LaTeX in front of the student. The
regression test asserts exactly that old output, so the bug cannot return quietly.

---

## Tests

Five test files, each written against a bug that actually happened rather than for
coverage:

| Test | Guards |
|---|---|
| `onboarding-page.test.tsx` | The redirect race above |
| `math.test.ts` | The brace-aware tokeniser |
| `paper-page.test.tsx` | Paper rendering and submission |
| `chat-labels.test.ts` | Chat labelling |
| `typing-cursor.test.tsx` | The streaming cursor |

Types and lint are the wider net: `pnpm build` runs `vite build && tsc`, and ESLint has
caught real mistakes — a `any` cast that hid a wrong type, and a cast that claimed a
cognitive-level code was valid when it might not be. That one became:

```ts
if (!(code in cognitiveLevelNames)) return null
```

---

[← Backend](04-backend.md) · [Contents](README.md) · [Next: AI layer →](06-ai.md)
