# TypeScript / Frontend Rules

Applies to every file under `frontend/`. Enforced by `tsc --noEmit` and `eslint` before any commit.

## TypeScript Strict Mode
- `"strict": true` in `tsconfig.json` — no exceptions
- Never use `any`; define proper types for every value

## API Response Types
- All API response types are defined in `src/types/index.ts`
- No inline type definitions in components or hooks

## Components
- Components live in `src/components/` and use **named exports** — not default exports
- Use `shadcn/ui` components before writing custom UI primitives

## Data Fetching
- All `fetch()` calls live in `src/lib/api.ts` only
- No `fetch()` calls inside components or hooks

## SSE Streaming
- All SSE streaming logic lives in `src/lib/streaming.ts` only
- Consume `POST /api/v1/query` with `fetch` + `ReadableStream`, not `EventSource` (EventSource does not support POST)
- Three event types to handle: `token`, `citations`, `done`

## Commands
```bash
cd frontend

npm ci                   # install
npm run dev              # dev server
npm run build            # production build
npx tsc --noEmit         # type check (must pass — zero errors)
npx eslint src/          # lint (must pass — zero warnings)
```
