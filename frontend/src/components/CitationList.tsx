import type { JSX } from "react";
import type { Citation } from "@/types";

interface CitationListProps {
  citations: Citation[];
  accentColor?: "static" | "agentic";
}

const ACCENT_MAP: Record<"static" | "agentic", string> = {
  static: "var(--static-chain)",
  agentic: "var(--agentic)",
};

export function CitationList({ citations, accentColor }: CitationListProps): JSX.Element | null {
  if (citations.length === 0) return null;
  const accentCss = accentColor ? ACCENT_MAP[accentColor] : 'var(--accent-primary)';

  return (
    <details open className="mt-2">
      <summary
        className="cursor-pointer text-xs font-semibold select-none"
        style={{ color: 'var(--text-secondary)' }}
      >
        Sources ({citations.length})
      </summary>
      <ul className="mt-2 space-y-2">
        {citations.map((c) => {
          const scorePct =
            c.retrieval_score !== undefined
              ? Math.min(100, Math.max(0, Math.round(c.retrieval_score * 100)))
              : undefined;

          return (
            <li
              key={c.chunk_id}
              className="rounded-md p-2 text-xs"
              style={{
                background: 'var(--surface-overlay)',
                border: '1px solid var(--border-subtle)',
              }}
            >
              <div className="flex items-center gap-1 mb-1">
                <span
                  className="font-medium overflow-hidden text-ellipsis whitespace-nowrap"
                  style={{ color: 'var(--text-primary)', maxWidth: '200px' }}
                  title={c.filename}
                >
                  {c.filename}
                </span>
                <span style={{ color: 'var(--text-muted)' }}>·</span>
                <span style={{ color: 'var(--text-muted)' }}>p.{c.page_number ?? "—"}</span>
              </div>
              {scorePct !== undefined && (
                <div className="flex items-center gap-1.5">
                  <span style={{ color: 'var(--text-muted)' }} className="w-14 shrink-0">Relevance</span>
                  <div className="flex-1 h-1 rounded-full" style={{ background: 'var(--border-subtle)' }}>
                    <div
                      className="h-1 rounded-full"
                      style={{ width: `${scorePct}%`, backgroundColor: accentCss }}
                      aria-label={`Relevance ${scorePct}%`}
                    />
                  </div>
                  <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }} className="w-8 text-right">{scorePct}%</span>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </details>
  );
}
