# Phase 2g — UI/UX Redesign: Portfolio-Grade Interface

> Status: 📋 Planned | Phase: 2g | Estimated Days: 3–4
> Prerequisite: Phase 2f gate must pass before implementation starts.
> Goal: Transform the functional parallel-view UI into a visually compelling, portfolio-grade application that communicates technical depth to AI hiring managers and engineering teams.

---

## 1. UX Audit — Current State

### 1.1 Layout Problems

| Issue | Root Cause | Impact |
|-------|-----------|--------|
| Content area is severely cramped | Three panes (sidebar + two equal columns) inside a single viewport with no breathing room | Each panel gets ≈ 32% of viewport width, making AgentTrace unreadable |
| Sidebar is always-visible dead weight on wide screens | Fixed 256px `w-64` left sidebar eats horizontal space that should go to content | Reduces usable chat width by ~25% |
| No vertical space budget | Header + input + verdict + two scrollable panels = stacked in one screen height | Messages overflow immediately; scrolling becomes confusing across two independent panels |
| Mobile layout is broken by intent | `md:grid-cols-2 grid-cols-1` hides half the demo on small screens | Portfolio viewers on mobile see nothing meaningful |

### 1.2 Visual Design Problems

| Issue | Root Cause | Impact |
|-------|-----------|--------|
| No typographic hierarchy | Arial/Helvetica at default sizes with only `font-semibold` and `font-medium` differentiation | Feels like unstyled HTML; every text element has the same visual weight |
| No brand identity | No logo, no custom color palette, no personality | Indistinguishable from a boilerplate Next.js starter |
| No design theme | `--background: white` / `--foreground: dark-gray` with Tailwind default palette hardcoded at point of use | Cannot change the feel without touching every component |
| Color system is ad-hoc | 40+ hardcoded Tailwind color classes scattered across 12 components | Blues, grays, greens, ambers, reds with no semantic naming |
| No ambient identity | Nothing on screen explains what the app is, who built it, or why it matters | A visitor landing cold has zero context |
| Sidebar communicates nothing | Collections list + eval metrics dumped in a gray panel with no visual hierarchy | Critical eval metrics (faithfulness 0.91, relevancy 0.87) are invisible to the eye |
| AgentTrace is buried | Wrapped in a `<details>` collapse with a generic summary line | The most technically impressive part of the app is hidden by default |
| No motion or feedback | Static layout changes; no transition when streams start/end; no progressive reveal | AI-at-work feeling is absent; responses feel like form submits |

### 1.3 Portfolio Framing Problems

| Issue | Impact |
|-------|--------|
| Title "KB AI RAG — Knowledge Assistant (Parallel View)" communicates nothing about the engineering | A hiring manager sees a chat app, not an AI systems showcase |
| No explanation of what's being demonstrated | Side-by-side panels are not obviously a Static Chain vs Agentic Pipeline comparison |
| Evaluation metrics hidden in sidebar | RAGAS scores (the quantitative proof of quality) are not surfaced prominently |
| No author/project attribution | Zero signal that this is a portfolio project by a named engineer |

---

## 2. Design Direction

### 2.1 Core Principles

1. **Content first** — The two panels are the star. Everything else (sidebar, header, input) must yield space to them.
2. **Technical storytelling** — Every UI element should reinforce that this is an AI systems comparison tool, not a generic chatbot.
3. **Progressive disclosure** — Sidebar details on demand; AgentTrace open by default; RAGAS scores surfaced in a dismissible info bar.
4. **Calm, professional dark theme** — Modern AI tooling aesthetic (Vercel AI SDK, OpenAI Playground, Cursor) without being a clone.
5. **Motion with purpose** — Animate only state transitions that communicate information (stream start, pipeline completion, verdict reveal).

### 2.2 Color System

Replace scattered Tailwind hardcoded classes with a semantic CSS custom property system defined in `globals.css`:

```css
:root {
  /* Surface hierarchy */
  --surface-base:    hsl(222 14% 6%);   /* page background */
  --surface-raised:  hsl(222 14% 10%);  /* card / panel */
  --surface-overlay: hsl(222 14% 14%);  /* popover / tooltip */

  /* Brand accent — electric indigo */
  --accent-primary:  hsl(249 100% 70%); /* primary CTA, active states */
  --accent-muted:    hsl(249 40% 30%);  /* subtle highlight backgrounds */

  /* Pipeline identity colors */
  --static-chain:    hsl(210 100% 60%); /* left panel accent — sky blue */
  --agentic:         hsl(260 100% 72%); /* right panel accent — violet */

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

Light mode can be added later via a `.light` class override — the CSS variable approach enables this without touching components.

### 2.3 Typography

Replace `Arial, Helvetica, sans-serif` with:
- **Inter** (Google Fonts / `next/font`) — body text, UI labels, badges
- **JetBrains Mono** — code snippets, latency numbers, session IDs

Type scale (CSS custom properties):
```css
--text-xs:   0.75rem / 1rem;
--text-sm:   0.875rem / 1.25rem;
--text-base: 1rem / 1.5rem;
--text-lg:   1.125rem / 1.75rem;
--text-xl:   1.25rem / 1.75rem;
--text-2xl:  1.5rem / 2rem;
```

### 2.4 Layout Model

**Replace the always-visible sidebar with a slide-over drawer.**

```
BEFORE (current):
┌──────────────────────────────────────────────────────────────────────┐
│ [Sidebar 256px]  │  [Header]                                         │
│                  │  [Input]                                           │
│                  ├──────────────────────┬────────────────────────────┤
│                  │  Static Chain        │  Agentic Pipeline          │
│                  │  (≈36% viewport)     │  (≈36% viewport)           │
└──────────────────────────────────────────────────────────────────────┘

AFTER (proposed):
┌──────────────────────────────────────────────────────────────────────┐
│  [Topbar: Logo | Nav | Collections badge | Theme toggle]             │
├─────────────────────────────────────────────────────────────────────┤
│  [RAGAS Metrics bar — collapsible, shown above input on first load]  │
├─────────────────────────────────────────────────────────────────────┤
│  [Input bar — full width, prominent]                                 │
├─────────────────────────────────────────────────────────────────────┤
│  [Verdict banner — full width, appears after completion]             │
├──────────────────────────────┬───────────────────────────────────────┤
│  Static Chain                │  Agentic Pipeline                     │
│  (48% viewport — blue tint) │  (48% viewport — violet tint)         │
│                              │                                        │
│  Chat messages               │  Chat messages                         │
│  Citations                   │  AgentTrace (OPEN by default)          │
│                              │  Latency bars                          │
└──────────────────────────────┴────────────────────────────────────────┘
      [⚙ Collections drawer trigger]   [↗ GitHub link]
```

**Key layout changes:**
- Sidebar becomes an off-canvas drawer opened by a toolbar button
- The two panels now share ~96% of the viewport width (8% for gap + scrollbars)
- Topbar is slim (40px) — branding + utility only
- RAGAS metrics surface in a collapsible inline bar above the input, not hidden in a sidebar
- Verdict renders as a full-width banner, not squeezed between panels

---

## 3. Component-by-Component Redesign

### 3.1 Topbar (new component: `Topbar.tsx`)

Replaces the current `<header>` block in `chat/page.tsx`.

**Contents (left to right):**
- Minimal wordmark: `kb·rag` in Inter 600 + small `DEMO` badge in monospace
- Separator
- Active collections count pill: `3 collections · 1,240 chunks`
- Spacer
- `[📊 Metrics]` button — toggles RAGAS metrics bar
- `[☰ Collections]` button — opens slide-over drawer
- Theme toggle (dark/light)

**Design:** 40px height, `var(--surface-raised)` background, `var(--border-subtle)` bottom border. No shadows — flat and minimal.

### 3.2 RAGAS Metrics Bar (new component: `MetricsBar.tsx`)

Surfaces the evaluation metrics that are currently buried in the sidebar.

**Contents:**
- Four metric pills in a flex row: `Faithfulness 0.91 ✓`, `Relevancy 0.87 ✓`, `Precision 0.83`, `Recall 0.79`
- Each pill is color-coded: green ≥ 0.85, amber 0.70–0.84, red < 0.70
- `[×]` dismiss button — collapses bar and saves preference to `localStorage`
- Below the pills: faint label `"RAGAS evaluation over 25 golden questions · last run 2026-04-30"`

**Behavior:** Shown by default on first visit. Collapsed state persists. Can be reopened via Topbar `[📊 Metrics]` button.

**Design:** `var(--surface-raised)` background, 48px height when open, animated slide-down on first render.

### 3.3 Input Bar (replace `SharedInput.tsx`)

**Changes:**
- Full viewport width minus 32px horizontal padding
- Textarea grows vertically up to 4 lines, then scrolls
- Send button is an icon button (`→`) with `var(--accent-primary)` background
- Streaming state: send button replaced by a pulsing "Stop" icon; input shows `"Processing both pipelines…"` placeholder
- Focus ring uses `var(--accent-primary)` at 2px offset
- Keyboard shortcut hint: `⌘↵ to send` in muted text inside the input border

### 3.4 Verdict Banner (replace `AgentVerdict.tsx`)

**Changes:**
- Full-width banner instead of a small inline badge
- Three visual states:
  - **Agentic wins**: violet left border + `🔮 Agentic Pipeline` in `var(--agentic)` + reason text
  - **Static wins**: blue left border + `⚡ Static Chain` in `var(--static-chain)` + reason text
  - **Tie**: neutral border + `≈ Comparable Results` in gray + reason text
- Animated slide-down reveal with `transition: transform 300ms ease-out`
- Confidence delta shown as `+0.12 confidence` in a mono badge

**Field name alignment (architect review 2026-04-27):**
Verdict computation reads `critic_score` (not `hallucination_risk`) and `web_fallback_used` (not `web_fallback`) from the agentic step payload. These are the authoritative field names established in the 2026-04-27 architect review of `AgentState`.

### 3.5 Panel Headers (modify `chat/page.tsx`)

Each panel gets a colored identity strip at the top:

**Static Chain panel:**
- 3px top border in `var(--static-chain)`
- Title: `Static Chain` in `--text-primary` + `⚡` icon
- Subtitle: `Phase 1 — BM25 + Dense Retrieval` in `--text-muted`
- Live streaming indicator: pulsing blue dot while active

**Agentic Pipeline panel:**
- 3px top border in `var(--agentic)`
- Title: `Agentic Pipeline` in `--text-primary` + `🔮` icon
- Subtitle: `Phase 2 — Router → Grader → Critic` in `--text-muted`
- Live streaming indicator: pulsing violet dot while active

### 3.6 Chat Messages (modify `ChatMessage.tsx`)

**User messages:**
- Right-aligned, `var(--accent-muted)` background, `var(--text-primary)` text
- No avatar

**Assistant messages:**
- Left-aligned, `var(--surface-overlay)` background
- Panel-colored left border (blue for Static Chain, violet for Agentic)
- Token-by-token reveal with no flicker (current behavior preserved)

**`accentColor` prop — typed union, not raw string:**
The prop is typed as `"static" | "agentic"` (not `string`). The component resolves the CSS variable internally:
```ts
const ACCENT_MAP: Record<"static" | "agentic", string> = {
  static: "var(--static-chain)",
  agentic: "var(--agentic)",
};
```
This keeps the type system meaningful and matches the existing `BADGE_CLASSES`/`BADGE_LABELS` record pattern already used in `AgentVerdict.tsx`.

### 3.7 AgentTrace (modify `AgentTrace.tsx`)

**Open by default** — remove the `<details>` closed state; replace with a styled expandable section that opens automatically when steps arrive.

**Step cards redesign:**
- Each card is a `var(--surface-overlay)` rounded panel with a `4px` left border in `var(--agentic)`
- Step node name (Router / Grader / Critic) in Inter 600 uppercase tracking-wider
- Content inside each card uses a two-column layout: key labels on left, values on right
- Latency shown in JetBrains Mono as `{n}ms` in `--text-muted`
- Cards appear with a staggered `translateY(8px) → 0` animation as they stream in
- Hallucination risk gauge uses `style={{ backgroundColor: 'var(--status-success/warning/danger)' }}` inline style — **not** hardcoded Tailwind color classes (which would break G02)

**Field name alignment (architect review 2026-04-27):**
- Critic risk displayed from `AgentStep.payload.critic_score` (not `hallucination_risk`)
- Web fallback indicator read from `AgentStep.payload.web_fallback_used` (not `web_fallback`)

**Latency bar chart:**
- Replace plain horizontal bars with labeled segments
- Bar track is `var(--border-subtle)` background; fill uses `var(--agentic)` with opacity proportional to duration
- Animate fill width from 0 to final value over 400ms when `isStreaming` transitions to `false`

### 3.8 ConfidenceBadge (modify `ConfidenceBadge.tsx`)

**Current:** Small colored span with text.
**New:** Pill with an arc/ring visual. A partial-circle SVG or conic-gradient background encodes the confidence score visually without requiring a chart library.

| Confidence | Color |
|-----------|-------|
| ≥ 0.8 | `var(--status-success)` |
| 0.5–0.79 | `var(--status-warning)` |
| < 0.5 | `var(--status-danger)` |

### 3.9 CitationList (modify `CitationList.tsx`)

**Current:** Bare list of file names + scores.
**New:**
- Collapsible section titled `Sources (n)` with an expand chevron
- Each citation is a card with: filename (truncated with ellipsis), relevance score bar (thin, colored), chunk preview (2 lines, muted)
- Score bar uses inline style `width: {score * 100}%` with `var(--static-chain)` fill

### 3.10 Collections Drawer (modify `Sidebar.tsx`)

**Transforms from a fixed sidebar to a slide-over drawer:**
- Triggered by `[☰ Collections]` Topbar button
- Slides in from the left, overlays the content (does not push it)
- Contains collections list + ingest button unchanged
- `×` close button in top-right corner
- Backdrop overlay (`rgba(0,0,0,0.5)`) with click-to-close
- Responsive: drawer behavior on all screen sizes (no breakpoint reveal)

---

## 4. Portfolio Landing Context

### 4.1 About Banner (new component: `AboutBanner.tsx`)

A slim, dismissible info bar shown at the top on first load (above the RAGAS metrics bar):

```
🔬  This is a portfolio demo by Kalai — an Enterprise Agentic RAG platform.
    Two pipelines process the same query in parallel. [Learn more ↗]  [×]
```

- Dismissed state persisted to `localStorage`
- `[Learn more ↗]` links to the project's GitHub README (configurable via `config.ts`)
- Design: amber/indigo gradient top border, dark background, white text

### 4.2 Empty State (new inline content in `chat/page.tsx`)

When no messages exist in either panel, show an empty state in each panel:

**Static Chain panel empty state:**
```
⚡ Static Chain
   BM25 hybrid retrieval + single-pass generation
   
   Try: "What is the escalation policy for critical incidents?"
```

**Agentic Pipeline empty state:**
```
🔮 Agentic Pipeline
   Router → Retriever → Grader → Generator → Critic
   
   Demonstrates: query routing, relevance grading, hallucination detection
```

Each suggestion is a clickable chip that pre-fills the input.

---

## 5. Animation & Motion Budget

All animations are defined in `globals.css` as utility keyframes. No animation library is needed.

| Animation | Trigger | Duration | Easing |
|-----------|---------|----------|--------|
| `slide-down` | Panel/banner appears | 200ms | ease-out |
| `fade-in` | Message appears | 150ms | ease |
| `pulse-dot` | Streaming indicator | 1.2s | ease-in-out, loop |
| `bar-fill` | Latency bar after stream ends | 400ms | ease-out |
| `slide-in-left` | Drawer opens | 250ms | ease-out |
| `stagger-cards` | AgentTrace step cards appear | 80ms stagger per card | ease-out |

**Rule:** `prefers-reduced-motion` must suppress all animations. Add `@media (prefers-reduced-motion: reduce)` override for every keyframe.

---

## 6. Implementation Tasks

> **Architect review note (2026-05-02):** Three sub-atomic tasks (original T02 fonts, T09 panel headers, T16 keyframes) were merged into their logical parents to avoid trivial commits — T01 now covers foundation (tokens + fonts + keyframes), and T07 (was T08) now covers page layout + panel headers. Total reduced from 17 → 14 tasks.
>
> **ADR note:** The implementing agent should consider writing a frontend ADR for (a) the CSS custom property token system over Tailwind theme extension, and (b) the slide-over drawer pattern replacing the fixed sidebar. This is advisory — the architect reviewer noted both as candidates. The implementing agent makes the final call.

### Task Overview

| ID | Task | Agent | Depends On |
|----|------|-------|------------|
| T01 | Foundation — CSS tokens + Inter/JetBrains Mono fonts + animation keyframes in `globals.css` + `layout.tsx` | frontend-developer | — |
| T02 | `Topbar.tsx` — slim header with wordmark, metrics toggle, collections trigger | frontend-developer | T01 |
| T03 | `MetricsBar.tsx` — RAGAS metrics surface with dismiss/restore | frontend-developer | T01, T02 |
| T04 | `AboutBanner.tsx` — portfolio context banner with dismiss | frontend-developer | T01, T02 |
| T05 | `SharedInput.tsx` redesign — full-width, grow textarea, streaming state | frontend-developer | T01 |
| T06 | `AgentVerdict.tsx` redesign — full-width banner, animated reveal | frontend-developer | T01 |
| T07 | `chat/page.tsx` layout refactor — remove sidebar, add Topbar, 2-panel grid + panel headers | frontend-developer | T02–T06 |
| T08 | `ChatMessage.tsx` redesign — dark theme, typed `"static"\|"agentic"` accent prop | frontend-developer | T01 |
| T09 | `AgentTrace.tsx` redesign — open by default, staggered cards, inline style status colors | frontend-developer | T01, T08 |
| T10 | `ConfidenceBadge.tsx` — conic-gradient ring with `@supports` fallback | frontend-developer | T01 |
| T11 | `CitationList.tsx` — collapsible with score bars and chunk preview | frontend-developer | T01 |
| T12 | `CollectionsDrawer.tsx` (new) — slide-over replacing `Sidebar.tsx`; T07 must land first | frontend-developer | T02, T07 |
| T13 | Empty state panels with example query chips from `config.ts` | frontend-developer | T07 |
| T14 | Update + extend component tests — cover all new and redesigned components | frontend-developer | T01–T13 |

### Batch Execution Order

**Batch 1 (no deps):**
- T01 — Foundation (tokens, fonts, keyframes in one commit)

**Batch 2 (after T01):**
- T02 — Topbar
- T05 — SharedInput redesign
- T06 — AgentVerdict banner
- T08 — ChatMessage redesign

**Batch 3 (after T02):**
- T03 — MetricsBar
- T04 — AboutBanner

**Batch 4 (after T02–T06):**
- T07 — Page layout refactor + panel headers (hub commit)

**Batch 5 (after T07):**
- T09 — AgentTrace redesign
- T10 — ConfidenceBadge
- T11 — CitationList
- T12 — CollectionsDrawer (T07 must have removed Sidebar import first)
- T13 — Empty states

**Batch 6 (after all above):**
- T14 — Test updates and new test files

---

## 7. Definition of Done (Phase Gate)

> **Pre-work gate (before T01 starts):** Verify that `frontend/src/types/index.ts`, `agentTypeGuards.ts`, `AgentTrace.tsx`, and `AgentVerdict.tsx` use the authoritative field names `critic_score` and `web_fallback_used`. If they still reference `hallucination_risk` or `web_fallback`, those renames must land as a separate pre-work commit before any Phase 2g task begins. Coordinate with the backend SSE serializer to confirm it already emits the correct names.

| Gate | Check | Pass Condition |
|------|-------|----------------|
| G01 | Design tokens | `globals.css` defines all `--surface-*`, `--accent-*`, `--static-chain`, `--agentic`, `--text-*` variables |
| G02 | No hardcoded colors in changed files | `git diff main --name-only \| xargs grep -l "bg-gray-\|bg-blue-\|text-gray-"` returns 0 matches among files changed in this phase (scoped to Phase 2g output — does not apply to unchanged files) |
| G03 | Fonts | Inter and JetBrains Mono load from `next/font`; no `font-family: Arial` in CSS |
| G04 | Layout | Sidebar is gone from `chat/page.tsx`; `CollectionsDrawer` replaces it |
| G05 | Two panels | Each panel uses `≥ 45%` viewport width in a `grid-cols-2` layout |
| G06 | RAGAS metrics visible | `MetricsBar` renders faithfulness, relevancy, precision, recall on first load |
| G07 | AgentTrace open | `<details>` element replaced; step cards visible without user interaction |
| G08 | Verdict banner | Full-width banner with correct color per outcome |
| G09 | Empty states | Query chips present in each panel when `messages.length === 0` |
| G10 | Animations | `pulse-dot`, `slide-down`, `bar-fill` keyframes defined; `prefers-reduced-motion` suppresses all |
| G11 | tsc --noEmit | Zero errors |
| G12 | eslint | Zero warnings |
| G13 | npm run build | Succeeds |
| G14 | All tests pass | Existing + new component tests green |
| G15 | Manual demo | Dark theme, both panels readable side-by-side on a 1440px screen, drawer opens/closes |

---

## 8. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Removing sidebar breaks ingest workflow | Low | Medium | `CollectionsDrawer` preserves all sidebar functionality unchanged |
| CSS variable approach conflicts with Tailwind v4 `@theme` | Low | Medium | Define all new tokens under `@layer base` (not `@theme`) to avoid Tailwind conflicts |
| Dark theme breaks existing light-mode tests | Medium | Low | Update snapshot/class assertions in T17; ensure `prefers-color-scheme` mock in test setup |
| Animation jank on low-end devices | Low | Low | All animations are CSS-only (no JS); `prefers-reduced-motion` disables them |
| `next/font` Inter CDN dependency in CI | Low | Low | Use `display: 'swap'` and include a system-font fallback stack |
| Conic-gradient for ConfidenceBadge not supported in older browsers | Very Low | Low | Add `@supports` fallback to a plain colored pill |

---

## 9. Design Reference Palette (Quick Copy)

```
Dark surfaces:   #0D0F14   #11151C   #161B24
Accent indigo:   hsl(249, 100%, 70%)   = #7C5CFF
Static chain:    hsl(210, 100%, 60%)   = #3399FF
Agentic violet:  hsl(260, 100%, 72%)   = #9966FF
Success green:   hsl(142, 71%, 45%)    = #22C55E
Warning amber:   hsl(38, 92%, 50%)     = #F59E0B
Danger red:      hsl(0, 84%, 60%)      = #EF4444
Text primary:    hsl(210, 40%, 98%)    = #F8FAFC
Text secondary:  hsl(215, 20%, 65%)    = #94A3B8
Text muted:      hsl(215, 16%, 47%)    = #64748B
Border subtle:   hsl(215, 28%, 17%)    = #1E293B
Border default:  hsl(215, 20%, 25%)    = #334155
```
