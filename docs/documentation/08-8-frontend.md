# 8. Frontend

The frontend is a single-page application in React 19 and TypeScript, built with Vite and served as static files from Cloud Run.

## 8.1 Libraries

| Library | Version | Role |
|---|---|---|
| React | 19 | Components and rendering |
| TypeScript | 5.7 | Static typing across the application |
| Vite | 6 | Development server and bundler |
| TanStack Router | 1.132 | Type-safe routing; route parameters are checked at compile time |
| TanStack Query | 5.66 | Server-state caching and revalidation |
| Effect + Effect Atom | 3.18 / 0.3 | Typed effects and reactive state |
| Tailwind CSS | 4 | Utility-first styling |
| Radix UI | 1.x | Accessible primitives: dialog, dropdown, tooltip, select |
| streamdown | 1.3 | Renders Markdown while it is still streaming in |
| KaTeX | 0.16.23 | Maths typesetting, with the mhchem extension for chemistry |
| React Flow (xyflow) | 12.8 | Interactive mind-map graphs |
| Firebase JS SDK | 12.19 | Sign-in and ID token management |
| react-hook-form + Zod | 7.65 / 4.1 | Form state and validation |
| Vitest + Testing Library | 3.2 / 16.2 | Component and unit tests |

## 8.2 State management

Most React applications use a store such as Redux. NISAAB uses Effect Atom on top of the Effect library. In Effect, an asynchronous operation is a value that carries its success type, its error type and its requirements, so a failed network request is a typed value that the interface must handle rather than an exception that can escape. Data access is written as atoms, for example one atom family keyed by project and paper.

```ts
export const paperAtom = Atom.family((input: string) => {
  const [projectId, paperId] = input.split(':')
  return runtime.atom(
    Effect.fn(function* () {
      const { apiClient } = yield* ApiClientService
      return yield* apiClient.getPaperApiV1ProjectsProjectIdPapersPaperIdGet(
        projectId, paperId,
      )
    }),
  )
})
```

Components read the atom with `useAtomValue` and receive a `Result` that is explicitly initial, success or failure.

## 8.3 Generated API client

The frontend never hand-writes HTTP calls. FastAPI produces an OpenAPI schema, and a generator turns it into a fully typed TypeScript client. A backend change that alters a response shape therefore becomes a compile-time error in the frontend instead of a failure in front of a user.

```
python scripts/export_openapi.py    # FastAPI app -> openapi.json
pnpm run gen:client                 # openapi.json -> src/integrations/api/client.ts
```

## 8.4 Streaming the tutor's reply

The chat does not poll for the answer. `edu-api` returns a Server-Sent Events stream and the client reads it step by step. Each event has a message identifier, a status and either a text delta or a complete non-text part such as a tool call.

- Text deltas are appended to the current text part, so the answer appears as it is written.
- Tool-call parts are matched by `tool_call_id`, so a quiz card appears once and is updated in place.
- Status values `thinking` and `generating` drive the indicator: bouncing dots and a line saying what the tutor is doing, then a blinking cursor at the end of the text.

## 8.5 Mathematics rendering

KaTeX renders formulas while the text streams in. KaTeX also emits a hidden MathML copy of each formula for screen readers. Those copies once escaped the chat's scroll container and caused blank space, so the stylesheet pins `.katex` to `position: relative`. Formulas that the AI writes in a broken format are repaired on screen and cleaned before saving.

## 8.6 Accessibility and languages

- Radix primitives provide keyboard navigation and ARIA roles for dialogs, menus and tooltips.
- Status indicators carry `role="status"` and an `aria-label`, so a screen reader is told the tutor is working.
- All motion respects `prefers-reduced-motion` and is replaced by a gentle fade.
- The tutor's interface strings exist in English, Roman Urdu and Urdu script. Urdu text uses `dir="auto"` so the browser sets right-to-left direction from the content.

## 8.7 Frontend tests

Vitest with Testing Library in a jsdom environment. The tests check behaviour that would otherwise break silently: that a choice pair in an examination paper counts once, that the typing cursor attaches to the right element in the rendered Markdown, and that every tool label exists in all three languages.
