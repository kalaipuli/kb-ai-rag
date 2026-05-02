# Phase 2g — UI/UX Redesign Tasks

> Status: ✅ Complete | Phase: 2g | Completed: 2026-05-02
> Prerequisite: Phase 2f gate must pass. Pre-work field rename (see §0) must land before T01.
> Full design rationale, color system, layout model, and component specs are in `plan.md`.

---

## §0 — Pre-Work: Field Name Alignment (Critical — before T01)

The 2026-04-27 architect review renamed two `AgentState` fields. Verify the frontend reflects the authoritative names before any Phase 2g implementation begins:

| Old name (wrong) | Authoritative name | Files to check |
|------------------|--------------------|----------------|
| `hallucination_risk` | `critic_score` | `types/index.ts`, `AgentTrace.tsx`, `AgentVerdict.tsx`, `agentTypeGuards.ts`, test fixtures |
| `web_fallback` | `web_fallback_used` | same files |

If any reference to the old names exists, create a pre-work commit (`fix(types): align frontend field names with authoritative AgentState schema`) before starting T01. Confirm with the backend SSE serializer that `agent_step` events already emit `critic_score` and `web_fallback_used`.

---

## Task Overview

| ID | Status | Task | Agent | Depends On |
|----|--------|------|-------|------------|
| T01 | ✅ | Foundation — CSS tokens + fonts + keyframes | frontend-developer | §0 pre-work |
| T02 | ✅ | `Topbar.tsx` — wordmark, metrics toggle, collections trigger | frontend-developer | T01 |
| T03 | ✅ | `MetricsBar.tsx` — RAGAS metrics surface with dismiss/restore | frontend-developer | T01, T02 |
| T04 | ✅ | `AboutBanner.tsx` — portfolio context banner with dismiss | frontend-developer | T01, T02 |
| T05 | ✅ | `SharedInput.tsx` redesign — full-width textarea, streaming state | frontend-developer | T01 |
| T06 | ✅ | `AgentVerdict.tsx` redesign — full-width banner, field names corrected | frontend-developer | T01 |
| T07 | ✅ | `chat/page.tsx` refactor — remove sidebar, Topbar, 2-panel grid + panel headers | frontend-developer | T02–T06 |
| T08 | ✅ | `ChatMessage.tsx` — dark theme, typed `"static"\|"agentic"` accent prop | frontend-developer | T01 |
| T09 | ✅ | `AgentTrace.tsx` — open by default, staggered cards, inline-style status colors | frontend-developer | T01, T08 |
| T10 | ✅ | `ConfidenceBadge.tsx` — conic-gradient ring with `@supports` fallback | frontend-developer | T01 |
| T11 | ✅ | `CitationList.tsx` — collapsible with score bars and chunk preview | frontend-developer | T01 |
| T12 | ✅ | `CollectionsDrawer.tsx` (new) — slide-over replacing `Sidebar.tsx` | frontend-developer | T02, T07 |
| T13 | ✅ | Empty state panels with query chips from `config.ts` | frontend-developer | T07 |
| T14 | ✅ | Update + extend all component tests | frontend-developer | T01–T13 |

---

## T01 — Foundation

**Files:**
- `frontend/src/app/globals.css` (modify)
- `frontend/src/app/layout.tsx` (modify)

**What:** Single commit establishing all three CSS foundations — design tokens, web fonts, and animation keyframes. These are atomically related (tokens reference font variables; keyframes reference token colors) and belong in one commit.

### CSS Design Token System (`globals.css`)

Replace `--background` / `--foreground` with the full semantic token set under `:root`:

```css
:root {
  /* Surface hierarchy */
  --surface-base:    hsl(222 14% 6%);
  --surface-raised:  hsl(222 14% 10%);
  --surface-overlay: hsl(222 14% 14%);

  /* Brand accent */
  --accent-primary:  hsl(249 100% 70%);
  --accent-muted:    hsl(249 40% 30%);

  /* Pipeline identity */
  --static-chain:    hsl(210 100% 60%);
  --agentic:         hsl(260 100% 72%);

  /* Semantic status */
  --status-success:  hsl(142 71% 45%);
  --status-warning:  hsl(38 92% 50%);
  --status-danger:   hsl(0 84% 60%);

  /* Typography */
  --text-primary:    hsl(210 40% 98%);
  --text-secondary:  hsl(215 20% 65%);
  --text-muted:      hsl(215 16% 47%);

  /* Borders */
  --border-subtle:   hsl(215 28% 17%);
  --border-default:  hsl(215 20% 25%);
}
```

Define under `@layer base`:
- `body { background: var(--surface-base); color: var(--text-primary); font-family: var(--font-inter), system-ui, sans-serif; }`
- Remove `font-family: Arial, Helvetica, sans-serif` from the existing `body` rule.

### Font Configuration (`layout.tsx`)

Load via `next/font/google`:

```tsx
import { Inter, JetBrains_Mono } from 'next/font/google'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
})

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
})
```

Apply both `.variable` className values to the `<html>` element.

### Animation Keyframes (`globals.css`, `@layer utilities`)

```css
@keyframes slide-down {
  from { transform: translateY(-8px); opacity: 0; }
  to   { transform: translateY(0);    opacity: 1; }
}
@keyframes fade-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}
@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.3; }
}
@keyframes bar-fill {
  from { width: 0%; }
  to   { width: var(--bar-target-width, 100%); }
}
@keyframes slide-in-left {
  from { transform: translateX(-100%); }
  to   { transform: translateX(0); }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

Utility classes under `@layer utilities`:
- `.animate-slide-down`, `.animate-fade-in`, `.animate-pulse-dot`, `.animate-bar-fill`, `.animate-slide-in-left`

**Acceptance criteria:**
- [ ] All tokens defined in `:root`
- [ ] Body uses `var(--surface-base)` and `var(--text-primary)`
- [ ] Arial/Helvetica removed from `body`
- [ ] Inter and JetBrains Mono loaded via `next/font`; both CSS variables applied to `<html>`
- [ ] All 5 keyframes + utility classes defined
- [ ] `prefers-reduced-motion` override present
- [ ] `npm run build` succeeds (fonts do not block build)
- [ ] tsc --noEmit, eslint pass

**Commit:** `style(ui): foundation — CSS tokens, Inter/JetBrains fonts, animation keyframes`

---

## T02 — Topbar Component

**File:** `frontend/src/components/Topbar.tsx` (new)

**Props:**
```ts
interface TopbarProps {
  collectionsCount: number
  totalChunks: number
  onMetricsToggle: () => void
  onCollectionsOpen: () => void
  metricsOpen: boolean
}
```

**Layout (left → right):**
1. Wordmark: `kb·rag` in Inter 600 + `DEMO` badge in `var(--font-mono)` and `var(--text-muted)`
2. Separator
3. Collections pill: `{collectionsCount} collections · {totalChunks.toLocaleString()} chunks` in `var(--text-secondary)`
4. Spacer (`flex-1`)
5. `[📊 Metrics]` icon button — calls `onMetricsToggle`; active state when `metricsOpen === true`
6. `[☰ Collections]` icon button — calls `onCollectionsOpen`

**Design:** 40px height, `background: var(--surface-raised)`, `border-bottom: 1px solid var(--border-subtle)`. Icon buttons: 32px × 32px rounded, hover `background: var(--surface-overlay)`.

**Acceptance criteria:**
- [ ] Wordmark, collections pill, both icon buttons present
- [ ] `onMetricsToggle` and `onCollectionsOpen` called on respective button click
- [ ] Active state applied to metrics button when `metricsOpen === true`
- [ ] tsc --noEmit, eslint pass

**Commit:** `feat(ui): add Topbar with wordmark, metrics toggle, and collections trigger`

---

## T03 — MetricsBar Component

**File:** `frontend/src/components/MetricsBar.tsx` (new)

**Props:**
```ts
interface MetricsBarProps {
  metrics: { faithfulness: number; relevancy: number; precision: number; recall: number } | null
  isOpen: boolean
  onDismiss: () => void
}
```

**Content when `isOpen && metrics !== null`:**
- Four metric pills: `Faithfulness {n}`, `Relevancy {n}`, `Precision {n}`, `Recall {n}`
- Pill color via inline style: `var(--status-success)` if `≥ 0.85`, `var(--status-warning)` if `0.70–0.84`, `var(--status-danger)` if `< 0.70`
- Subtitle: `"RAGAS evaluation · last run from baseline"` in `var(--text-muted)`
- `×` dismiss button calling `onDismiss`

**Parent responsibility (in `chat/page.tsx` T07):** Initialize `metricsOpen` state from `localStorage`:
```ts
const [metricsOpen, setMetricsOpen] = useState(true);
useEffect(() => {
  setMetricsOpen(localStorage.getItem('kb_rag_metrics_dismissed') !== 'true');
}, []);
const handleMetricsDismiss = () => {
  setMetricsOpen(false);
  localStorage.setItem('kb_rag_metrics_dismissed', 'true');
};
```
The `useEffect` pattern is required — direct `localStorage` access in `useState` initializer throws `ReferenceError` during Next.js SSR (even in `"use client"` files, the initial render runs server-side).

**Acceptance criteria:**
- [ ] Four metric pills with correct inline-style colors per threshold
- [ ] `onDismiss` called when `×` clicked
- [ ] Not rendered when `isOpen === false`
- [ ] tsc --noEmit, eslint pass

**Commit:** `feat(ui): add MetricsBar surfacing RAGAS evaluation metrics`

---

## T04 — AboutBanner Component

**File:** `frontend/src/components/AboutBanner.tsx` (new)

**Props:**
```ts
interface AboutBannerProps {
  isOpen: boolean
  onDismiss: () => void
  githubUrl?: string
}
```

**Content:**
- Icon `🔬` + text: `"Portfolio demo — Enterprise Agentic RAG platform. Two pipelines process the same query in parallel."`
- `[View on GitHub ↗]` — rendered only when `githubUrl` prop is provided; links to `githubUrl`
- `×` dismiss button

**Design:** 40px slim bar, 3px amber/indigo gradient `border-top`, `background: var(--surface-raised)`.

**Parent responsibility (in `chat/page.tsx` T07):**
```ts
const [aboutOpen, setAboutOpen] = useState(true);
useEffect(() => {
  setAboutOpen(localStorage.getItem('kb_rag_about_dismissed') !== 'true');
}, []);
```
Same `useEffect` pattern as T03 — no direct `localStorage` in `useState` initializer.

**Acceptance criteria:**
- [ ] Banner renders when `isOpen === true`, hidden when `false`
- [ ] `onDismiss` called on `×` click
- [ ] GitHub link renders only when `githubUrl` prop is set
- [ ] tsc --noEmit, eslint pass

**Commit:** `feat(ui): add AboutBanner portfolio context component`

---

## T05 — SharedInput Redesign

**File:** `frontend/src/components/SharedInput.tsx` (modify)

**Functional contract from 2e T04 is unchanged** — only visual treatment changes.

**Design changes:**
- Width: 100% of parent with `px-4` padding
- `<textarea>` element with `rows={1}`, `resize-none`, auto-grows up to 4 lines via JS height adjustment on `input` event
- Background: `var(--surface-raised)`, border: `1px solid var(--border-default)`, focus ring: `2px solid var(--accent-primary)` at 2px offset
- Send button: `→` arrow icon, `background: var(--accent-primary)`, 36px circle, right-anchored
- When `isDisabled === true`: send button replaced by pulsing stop icon; `placeholder="Processing both pipelines…"`
- Keyboard hint: `⌘↵ to send` in `var(--text-muted)` inside input border, hidden when input has content

**Functional guard from 2e preserved:**
- `onSubmit` must be a no-op when `isDisabled === true` (check inside handler body, not just DOM `disabled`)
- Input value clears after successful submit

**Acceptance criteria:**
- [ ] Textarea grows up to 4 lines
- [ ] Send button uses `var(--accent-primary)`, stop icon shown when streaming
- [ ] Focus ring uses `var(--accent-primary)`
- [ ] Functional guard (2e) preserved — `onSubmit` no-op when `isDisabled`
- [ ] tsc --noEmit, eslint pass

**Commit:** `style(ui): redesign SharedInput with full-width textarea and accent send button`

---

## T06 — AgentVerdict Banner Redesign

**File:** `frontend/src/components/AgentVerdict.tsx` (modify)

**Verdict logic from 2e T06 is unchanged.** Field names must use the authoritative names (see §0):
- Read `critic_score` (not `hallucination_risk`) for high-risk check
- Read `web_fallback_used` (not `web_fallback`) for fallback check

**Design changes:**
- Full-width banner replacing the inline badge
- Three variants using `style` props for border color (not Tailwind color classes):
  - `agentic`: `borderLeft: '4px solid var(--agentic)'`, heading `🔮 Agentic Pipeline wins`
  - `static`: `borderLeft: '4px solid var(--static-chain)'`, heading `⚡ Static Chain wins`
  - `tie`: neutral border, heading `≈ Comparable Results`
- Confidence delta: `+{delta} confidence` in `var(--font-mono)` badge
- One-sentence reason in `var(--text-secondary)`
- Animated reveal using `.animate-slide-down` from T01

**Acceptance criteria:**
- [ ] Full-width banner layout
- [ ] All three outcomes with correct border color via `style` prop (not Tailwind class)
- [ ] Confidence delta in monospace badge
- [ ] Reads `critic_score` and `web_fallback_used` (not old names)
- [ ] tsc --noEmit, eslint pass

**Commit:** `style(ui): redesign AgentVerdict as full-width banner with corrected field names`

---

## T07 — Page Layout Refactor + Panel Headers

**File:** `frontend/src/app/chat/page.tsx` (modify)

**What:** This is the hub commit. It removes the sidebar, wires all new components, adds `useEffect`-based localStorage state, and defines the panel header markup. Panel headers are included here (not a separate task) since they are direct JSX in this file.

**Sidebar removal:** Remove the `import { Sidebar }` statement and the `<Sidebar />` JSX. This must happen in this commit so that T12 (CollectionsDrawer) can safely delete `Sidebar.tsx` without breaking the build.

**State added at page level (all using `useEffect` pattern — no `localStorage` in `useState` initializers):**
```ts
const [metricsOpen, setMetricsOpen] = useState(true);
const [aboutOpen, setAboutOpen] = useState(true);
const [drawerOpen, setDrawerOpen] = useState(false);

useEffect(() => {
  setMetricsOpen(localStorage.getItem('kb_rag_metrics_dismissed') !== 'true');
  setAboutOpen(localStorage.getItem('kb_rag_about_dismissed') !== 'true');
}, []);
```

**New layout structure:**
```tsx
<div className="flex flex-col h-screen" style={{ background: 'var(--surface-base)' }}>
  <AboutBanner isOpen={aboutOpen} onDismiss={handleAboutDismiss} githubUrl={config.githubUrl} />
  <Topbar collectionsCount={...} totalChunks={...} metricsOpen={metricsOpen}
          onMetricsToggle={...} onCollectionsOpen={() => setDrawerOpen(true)} />
  <MetricsBar metrics={evalMetrics} isOpen={metricsOpen} onDismiss={handleMetricsDismiss} />
  <SharedInput onSubmit={handleSubmit} isDisabled={isEitherStreaming} />
  {!isEitherStreaming && <AgentVerdict ... />}
  <main className="grid grid-cols-2 md:grid-cols-2 grid-cols-1 flex-1 overflow-hidden">
    {/* Static Chain panel */}
    <div style={{ borderTop: '3px solid var(--static-chain)' }} className="flex flex-col overflow-hidden border-r" style={{ borderColor: 'var(--border-subtle)' }}>
      <div className="flex items-center gap-2 px-4 py-3">
        <span>⚡</span>
        <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>Static Chain</span>
        {isStaticStreaming && <span className="animate-pulse-dot w-2 h-2 rounded-full" style={{ background: 'var(--static-chain)' }} />}
        <span className="text-xs ml-auto" style={{ color: 'var(--text-muted)' }}>Phase 1 — BM25 + Dense Retrieval</span>
      </div>
      {/* existing Phase 1 chat components unchanged */}
    </div>
    {/* Agentic Pipeline panel */}
    <div style={{ borderTop: '3px solid var(--agentic)' }} className="flex flex-col overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-3">
        <span>🔮</span>
        <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>Agentic Pipeline</span>
        {isAgentStreaming && <span className="animate-pulse-dot w-2 h-2 rounded-full" style={{ background: 'var(--agentic)' }} />}
        <span className="text-xs ml-auto" style={{ color: 'var(--text-muted)' }}>Phase 2 — Router → Grader → Critic</span>
      </div>
      <AgentPanel ... />
    </div>
  </main>
  <CollectionsDrawer isOpen={drawerOpen} onClose={() => setDrawerOpen(false)} ... />
</div>
```
CollectionsDrawer can be a stub `{null}` until T12 is complete.

**Acceptance criteria:**
- [ ] No `<Sidebar>` import or JSX
- [ ] `<AboutBanner>`, `<Topbar>`, `<MetricsBar>` present and wired
- [ ] All localStorage state initialized via `useEffect` (not `useState` initializer)
- [ ] Panel headers have top border via `style` prop with pipeline CSS variables
- [ ] Pulsing dots on panel headers while streaming
- [ ] Two-panel grid with 2-column layout on desktop
- [ ] `handleSubmit` calls both static and agentic submit
- [ ] tsc --noEmit, eslint pass

**Commit:** `refactor(ui): restructure chat page — Topbar/MetricsBar replace sidebar, panel headers`

---

## T08 — ChatMessage Redesign

**File:** `frontend/src/components/ChatMessage.tsx` (modify)

**New prop (typed union — not a raw CSS string):**
```ts
accentColor?: "static" | "agentic";
```

Internal CSS variable resolution:
```ts
const ACCENT_MAP: Record<"static" | "agentic", string> = {
  static: "var(--static-chain)",
  agentic: "var(--agentic)",
};
const accentStyle = accentColor ? ACCENT_MAP[accentColor] : "var(--text-muted)";
```

Use as `style={{ borderLeft: `3px solid ${accentStyle}` }}` on the assistant message wrapper.

**User message:** Right-aligned (`ml-auto`), max-width 75%, `background: var(--accent-muted)`, `color: var(--text-primary)`, `border-radius: 1rem 1rem 0.25rem 1rem`.

**Assistant message:** Left-aligned, max-width 85%, `background: var(--surface-overlay)`, 3px left border using `accentStyle` above, `border-radius: 1rem 1rem 1rem 0.25rem`.

**Existing callers:** The prop is optional — existing callers that omit it get the muted default. No breaking change.

**Acceptance criteria:**
- [ ] `accentColor` typed as `"static" | "agentic"` (not `string`)
- [ ] CSS variable resolved internally via `ACCENT_MAP`
- [ ] User messages right-aligned with `var(--accent-muted)` background
- [ ] Assistant messages left-aligned with left border
- [ ] Existing 2e tests not broken
- [ ] tsc --noEmit, eslint pass

**Commit:** `style(ui): redesign ChatMessage with dark theme and typed pipeline accent prop`

---

## T09 — AgentTrace Redesign

**File:** `frontend/src/components/AgentTrace.tsx` (modify)

**Structural changes:**
- Remove `<details>` / `<summary>` wrapper entirely
- Replace with a `<div>` container; add optional collapse toggle button in header (defaults open/visible)
- Step cards: `background: var(--surface-overlay)`, `border-left: 4px solid var(--agentic)`, `border-radius: 0.5rem`
- Card node name: uppercase tracking-wider Inter 600 via `className`; latency in `var(--font-mono)` with `var(--text-muted)` via inline style
- Stagger animation per card: `style={{ animationDelay: `${index * 80}ms` }}`
- Hallucination risk gauge (Critic card): use **inline `style` prop**, not Tailwind color classes:
  ```ts
  const riskColor =
    step.payload.critic_score < 0.4 ? 'var(--status-success)'
    : step.payload.critic_score <= 0.7 ? 'var(--status-warning)'
    : 'var(--status-danger)';
  // ...
  <div style={{ backgroundColor: riskColor, width: `${step.payload.critic_score * 100}%` }} />
  ```
  This avoids hardcoded Tailwind color classes that would fail G02.
- Latency bar fill: `.animate-bar-fill` class + CSS `--bar-target-width` custom property via inline style

**Field names:** Use `critic_score` and `web_fallback_used` throughout (§0 pre-work).

**Acceptance criteria:**
- [ ] No `<details>` element in DOM
- [ ] Step cards visible without user interaction
- [ ] Stagger delay applied per card index
- [ ] Risk gauge uses `style={{ backgroundColor: riskColor }}` (not Tailwind color class)
- [ ] Latency bars animate on reveal via `.animate-bar-fill`
- [ ] Reads `critic_score` and `web_fallback_used` (not old names)
- [ ] tsc --noEmit, eslint pass

**Commit:** `style(ui): redesign AgentTrace — open by default, animated cards, inline-style status colors`

---

## T10 — ConfidenceBadge Redesign

**File:** `frontend/src/components/ConfidenceBadge.tsx` (modify)

**Replace the plain text badge with a conic-gradient ring:**
- 28px × 28px circle div with `background: conic-gradient(${fillColor} ${pct}%, var(--border-subtle) 0)` via inline style
- Center label: `{Math.round(confidence * 100)}%` in JetBrains Mono, small font, centered
- Fill color uses the same `var(--status-*)` tokens as T09

**`@supports` fallback:** Wrap the ring in `@supports (background: conic-gradient(red, blue))` CSS rule; the fallback is the existing plain colored pill (keep the old render path in a separate branch).

**Note on testing:** jsdom does not evaluate CSS `@supports` blocks. Tests for this component must assert on DOM structure (confidence percentage label, wrapper element presence) rather than computed visual styles.

**Acceptance criteria:**
- [ ] Conic-gradient ring rendered (verified visually in manual demo)
- [ ] Center label shows percentage value
- [ ] Colors use `var(--status-*)` tokens via inline style
- [ ] `@supports` fallback present in CSS
- [ ] Tests assert on DOM structure, not computed styles
- [ ] tsc --noEmit, eslint pass

**Commit:** `style(ui): redesign ConfidenceBadge with conic-gradient confidence ring`

---

## T11 — CitationList Redesign

**File:** `frontend/src/components/CitationList.tsx` (modify)

**New prop:**
```ts
accentColor?: "static" | "agentic";
```
Internal resolution: same `ACCENT_MAP` pattern as T08.

**Changes:**
- Wrap list in `<details open>` with `<summary>Sources ({citations.length})</summary>`
- Each citation: `<div>` card with `background: var(--surface-overlay)`, `border: 1px solid var(--border-subtle)`, `border-radius: 0.375rem`
- Filename: `overflow-hidden text-ellipsis whitespace-nowrap` with `color: var(--text-primary)`
- Score bar: `height: 4px`, `background: var(--border-subtle)` (track), inner fill `style={{ width: `${score * 100}%`, backgroundColor: accentCss }}`
- Chunk preview: 2 lines via CSS `-webkit-line-clamp: 2`, `color: var(--text-muted)`

**Acceptance criteria:**
- [ ] `<details open>` wrapper with summary count
- [ ] Score bars proportional to relevance score via inline style
- [ ] Chunk preview clamped to 2 lines
- [ ] `accentColor` prop typed as `"static" | "agentic"`
- [ ] tsc --noEmit, eslint pass

**Commit:** `style(ui): redesign CitationList with collapsible cards and proportional score bars`

---

## T12 — CollectionsDrawer Component

**Files:**
- `frontend/src/components/CollectionsDrawer.tsx` (new)
- `frontend/src/components/Sidebar.tsx` (delete — safe after T07 removes the import)

**Prerequisite:** T07 must have landed (removed `<Sidebar>` import from `chat/page.tsx`) before `Sidebar.tsx` is deleted. Verify with `grep -r "Sidebar" frontend/src/` — must return zero matches in non-test files.

**Props:**
```ts
interface CollectionsDrawerProps {
  isOpen: boolean
  onClose: () => void
  collections: Collection[]
  onIngest: () => void
}
```

**Layout:**
- `position: fixed; left: 0; top: 0; height: 100%; width: 320px; z-index: 50`
- `background: var(--surface-raised)`, `border-right: 1px solid var(--border-default)`
- Slides in via `.animate-slide-in-left` (from T01); hidden when `!isOpen` via `translate-x-[-100%]`
- Backdrop: `position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 40` — click calls `onClose`
- Header: "Collections" title + `×` close button
- Body: collections list + ingest button migrated verbatim from `Sidebar.tsx`

**Acceptance criteria:**
- [ ] Drawer slides in from left when `isOpen === true`
- [ ] Backdrop click calls `onClose`
- [ ] Collections list and ingest functionality preserved from `Sidebar.tsx`
- [ ] `Sidebar.tsx` deleted (zero grep matches outside tests)
- [ ] tsc --noEmit, eslint pass

**Commit:** `refactor(ui): replace Sidebar with CollectionsDrawer slide-over`

---

## T13 — Empty State Panels

**File:** `frontend/src/app/chat/page.tsx` (modify)
**File:** `frontend/src/lib/config.ts` (modify — add `emptySuggestions` export)

**Add to `config.ts`:**
```ts
export const emptySuggestions = {
  static: [
    "What is the escalation policy for critical incidents?",
    "Summarise the onboarding process",
  ],
  agentic: [
    "Compare the SLA tiers across enterprise plans",
    "What changed in the last policy update?",
  ],
} as const;
```

**In each panel, when `messages.length === 0`:**
```tsx
<div className="flex flex-col items-center justify-center flex-1 gap-4 px-8">
  <p style={{ color: 'var(--text-muted)' }}>...</p>
  <div className="flex flex-wrap gap-2 justify-center">
    {emptySuggestions.static.map(s => (
      <button key={s} onClick={() => handleSubmit(s)}
        className="px-3 py-1.5 rounded-full text-sm"
        style={{ background: 'var(--surface-overlay)', color: 'var(--text-secondary)',
                 border: '1px solid var(--border-subtle)' }}>
        {s}
      </button>
    ))}
  </div>
</div>
```

**Acceptance criteria:**
- [ ] Empty state shown when `messages.length === 0`; hidden when any message present
- [ ] Chips call `handleSubmit` with the suggestion text
- [ ] Suggestions sourced from `config.ts` `emptySuggestions` export (not hardcoded in JSX)
- [ ] tsc --noEmit, eslint pass

**Commit:** `feat(ui): add empty state panels with example query chips from config`

---

## T14 — Update and Extend Component Tests

**Files:** All `*.test.tsx` files under `frontend/src/`

**Existing tests to update:**

| File | What to update |
|------|---------------|
| `ChatMessage.test.tsx` | Color assertions: old Tailwind class checks → DOM structure + `accentColor` prop behavior |
| `AgentTrace.test.tsx` | Remove `<details>` assertions; assert step cards visible without user action; assert `critic_score` field (not `hallucination_risk`) |
| `AgentVerdict.test.tsx` | Update layout assertions to full-width banner; assert `web_fallback_used` and `critic_score` field names |
| `ConfidenceBadge.test.tsx` | Assert on DOM structure (percentage label, wrapper element) — not computed styles (jsdom cannot evaluate `@supports`) |
| `CitationList.test.tsx` | Update to test `<details open>` collapsible wrapper |
| `SharedInput.test.tsx` | Update streaming placeholder text assertion to new copy |

**New test files required:**

| File | Required test cases |
|------|---------------------|
| `Topbar.test.tsx` | (1) Renders wordmark; (2) `onMetricsToggle` called on metrics button click; (3) `onCollectionsOpen` called on collections button click; (4) Active state applied when `metricsOpen === true` |
| `MetricsBar.test.tsx` | (1) Renders all four metric names; (2) Correct color class/style for green/amber/red thresholds; (3) `onDismiss` called on `×` click; (4) Not rendered when `isOpen === false` |
| `AboutBanner.test.tsx` | (1) Renders text content; (2) `onDismiss` called on `×` click; (3) GitHub link present when `githubUrl` prop set; (4) GitHub link absent when `githubUrl` prop omitted |
| `CollectionsDrawer.test.tsx` | (1) Drawer not visible when `isOpen === false`; (2) Drawer visible when `isOpen === true`; (3) Backdrop click calls `onClose`; (4) Collections list renders from props |

**Acceptance criteria:**
- [ ] All existing tests updated (no stale class or field-name assertions)
- [ ] 4 new test files created, each with ≥ 4 test cases
- [ ] `npm run test` — all green, no regressions
- [ ] tsc --noEmit, eslint pass
- [ ] `npm run build` succeeds

**Commit:** `test(ui): update and extend component tests for Phase 2g redesign`

---

## Phase 2g Gate

| Gate | Check |
|------|-------|
| §0 | Pre-work: `hallucination_risk` and `web_fallback` absent from frontend source (grep = 0) |
| G01 | All design tokens defined in `globals.css` `:root` |
| G02 | No hardcoded `bg-gray-*`, `bg-blue-*`, `text-gray-*` in files changed in this phase |
| G03 | Inter + JetBrains Mono load without build error |
| G04 | `Sidebar.tsx` deleted; `CollectionsDrawer` functional |
| G05 | Two panels share ≥ 45% viewport width each in `grid-cols-2` |
| G06 | `MetricsBar` shows RAGAS metrics on first load |
| G07 | AgentTrace step cards open without user interaction; no `<details>` in DOM |
| G08 | AgentVerdict is a full-width banner with correct border color per outcome |
| G09 | Empty state chips present when `messages.length === 0` |
| G10 | All animation utility classes defined; `prefers-reduced-motion` override present |
| G11 | tsc --noEmit — zero errors |
| G12 | eslint — zero warnings |
| G13 | npm run build — succeeds |
| G14 | All tests pass (existing + 4 new files) |
| G15 | Manual: dark theme, both panels readable side-by-side at 1440px, drawer opens/closes |
