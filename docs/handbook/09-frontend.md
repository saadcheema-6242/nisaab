# 9. Frontend

`src/edu-web`. React 19, Vite 7, TypeScript.

## Stack

| Piece | Choice |
|---|---|
| Routing | TanStack Router, code-split per route |
| State and data | Effect + `@effect-atom/atom-react` |
| Styling | Tailwind v4, oklch tokens |
| Components | shadcn-style primitives in `components/ui` |
| Motion | `motion/react` |
| Auth | Firebase JS SDK |
| Maths | KaTeX |

## Data: atoms and Result

Server state is an **atom**. Reading one gives a `Result`, which is
`Initial`, `Success` or `Failure` — never a half-filled object:

```tsx
const result = useAtomValue(progressAtom)

Result.builder(result)
  .onInitialOrWaiting(() => <Skeleton />)
  .onFailure(() => <ErrorCard />)
  .onSuccess((data) => <Charts data={data} />)
  .render()
```

Every loading and failure state is therefore a thing the compiler asks
you to handle, not something you remember to add. Mutations are
`runtime.fn`, and refresh the atoms they invalidate.

Two traps worth knowing, both of which have bitten this codebase:

- **`Cause.squash()` returns `unknown`.** Narrow it with
  `instanceof Error` before touching `.message`.
- **A mutation's setter does not reject.** A `try/catch` around it never
  runs and the server's refusal vanishes. Read the outcome from the
  `Result` in an effect instead.

### Refreshing the right atom

When two atoms answer the same question, a mutation must refresh the one
that is *read by the thing that acts on it*.

Completing onboarding used to refresh the profile but not the account
state, while the dashboard guard read the account state. The student
finished setup, was sent to the dashboard, and the guard — still holding
the answer from before they had a profile — sent them back. For ever.

One question, one source. There is a test asserting that refreshing the
profile alone does **not** navigate.

## Design system

Defined in `src/styles.css` as oklch tokens, light and dark.

**Type.** Inter for the interface, Source Serif 4 for page titles — both
self-hosted, variable weights. Self-hosted deliberately: the product is
demonstrated where the network may be poor, and a first impression should
not wait on a third party. The serif is on `h1` and `h2` only; it says
"considered" at 24px and stops saying it at 14px. `tabular-nums` globally
so columns of percentages do not wander.

**Elevation.** Four steps — hairline, resting, raised, floating — tinted
with the brand green rather than black, because a neutral shadow on a
warm cream surface goes grey. Both themes have the full ramp; the dark
one is re-tuned rather than copied, since there is little left to darken
on a dark surface and a light top edge is what reads as raised.

**Primitives** carry the behaviour so pages do not reinvent it:

- `Button` — top-edge highlight, rises on hover, presses in
- `Card` — `interactive` prop for cards that are links
- `Input` / `Textarea` — recessed, so an empty form looks like a form
- `Badge` — loud for a result, tinted for a state
- `PageHeader`, `TabStrip`, `Spinner`, `LoadingLine`, `Skeleton`

**Motion** is restrained and always suppressed under
`prefers-reduced-motion`, which is not hypothetical here: the machine the
product is demonstrated from has it on, so the still path is the one most
likely to be seen.

Where motion is used it carries meaning: the logo's noon draws as a
smile, the trend line draws left to right because it is a thing that
happened over time, and mastery bars grow from zero because the bar's
length *is* the value.

## Conventions

- Loading states use skeletons shaped like the eventual content, so the
  layout does not jump when data lands
- Empty states say what is missing and whose job it is to fix it
- Every destructive action confirms
- Icons are decorative; the text is the label

## Commands

```bash
pnpm dev          # dev server
pnpm build        # vite build && tsc
pnpm test         # vitest
pnpm lint         # eslint
pnpm check        # format + lint
pnpm gen:client   # regenerate the API client from the OpenAPI schema
```

Next: [10. API](10-api.md)
