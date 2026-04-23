# ADR-005: Next.js 14 with App Router for the Frontend

## Status
Accepted

## Context
The platform needs a chat UI that satisfies three requirements:
1. **SSE streaming**: The `POST /api/v1/query` endpoint streams response tokens via Server-Sent Events. The UI must consume this stream and render tokens progressively.
2. **Citation display**: Each answer includes source citations (filename, page number, chunk index, relevance score). The UI must display these clearly alongside the generated answer.
3. **Portfolio presentation**: The system targets an AI Architect hiring audience. The UI must look production-quality, not like an ML demo prototype.

The backend is already Python/FastAPI. The frontend choice is independent of backend language. TypeScript type safety is a stated project requirement in CLAUDE.md.

## Decision
Use Next.js 14 with the App Router, TypeScript strict mode (`"strict": true` in tsconfig.json), and Tailwind CSS for styling.

All API response types are defined in `src/types/index.ts`. All fetch calls live in `src/lib/api.ts`. SSE streaming logic lives in `src/lib/streaming.ts`. Components use named exports. No `any` types permitted.

## Alternatives Considered

**Streamlit**: Python-native web framework popular in ML demos. Rejected because: (a) Streamlit's SSE support for POST endpoints requires workarounds — it is designed for request-response, not streaming, (b) Streamlit UIs are visually identifiable as demo/prototype tooling, which undermines the portfolio goal of appearing production-grade, (c) Streamlit does not support TypeScript — the code cannot be type-checked the same way as the backend.

**Gradio**: Similar to Streamlit. Rejected for the same reasons: demo-quality UI, limited streaming control, Python-only.

**Raw React (Create React App / Vite)**: Full control, no framework conventions. Rejected because Next.js 14 App Router provides conventions (file-system routing, Server Components, streaming primitives) that are directly relevant to demonstrating modern React knowledge. A raw React SPA adds setup overhead without adding architectural relevance.

**Vue.js / Nuxt**: Technically equivalent to React/Next.js for this use case. Rejected because the enterprise job market for AI Architect roles skews heavily toward React. TypeScript support in Vue 3 is excellent but the ecosystem familiarity signal is lower.

**SvelteKit**: Excellent developer experience. Rejected for the same market-fit reason as Vue: React/Next.js is the dominant choice in enterprise frontend stacks and demonstrates broader relevance.

## Consequences

**Positive:**
- Next.js 14 App Router enables file-system routing, eliminating router configuration boilerplate
- TypeScript strict mode catches API contract mismatches at compile time — the `src/types/index.ts` types mirror the backend Pydantic schemas, and `tsc --noEmit` fails if they diverge
- SSE streaming from a POST endpoint uses `fetch` + `ReadableStream` in `src/lib/streaming.ts` — this is the correct browser API for POST-based SSE; `EventSource` only supports GET and is not suitable here
- Tailwind CSS + shadcn/ui provide production-quality component primitives without writing custom CSS
- The Next.js Dockerfile uses a multi-stage build (deps → builder → runner) that produces a minimal production image

**Negative:**
- Node.js toolchain (Node 20, npm) must be available alongside Python/Poetry in development environments and CI
- Next.js 14 App Router introduces Server Components and a new mental model that differs from Pages Router — developers unfamiliar with App Router may experience a learning curve
- `EventSource` is not used: SSE over POST requires custom `fetch`-based streaming code in `src/lib/streaming.ts`, which is less familiar than the standard `EventSource` API
- Next.js version must be pinned (14.2.x) to avoid App Router breaking changes between minor versions
