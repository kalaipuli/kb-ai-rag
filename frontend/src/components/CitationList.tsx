import type { JSX } from "react";
import type { Citation } from "@/types";

interface CitationListProps {
  citations: Citation[];
}

export function CitationList({ citations }: CitationListProps): JSX.Element | null {
  if (citations.length === 0) return null;

  return (
    <div className="mt-2 border-t border-gray-100 pt-2">
      <p className="mb-1 text-xs font-semibold text-gray-500 uppercase tracking-wide">Sources</p>
      <ul className="space-y-1.5">
        {citations.map((c) => {
          // TODO Phase 2: normalize cross-encoder logit to [0,1] via sigmoid before display
          const scorePct =
            c.retrieval_score !== undefined
              ? Math.min(100, Math.max(0, Math.round(c.retrieval_score * 100)))
              : undefined;

          return (
            <li key={c.chunk_id} className="text-xs text-gray-600">
              <div className="flex items-center gap-1">
                <span className="font-medium truncate max-w-[200px]" title={c.filename}>
                  {c.filename}
                </span>
                <span className="text-gray-400">·</span>
                <span>p.{c.page_number ?? "—"}</span>
              </div>
              {scorePct !== undefined && (
                <div className="mt-0.5">
                  <div className="flex items-center gap-1.5">
                    <span className="text-gray-400 w-14 shrink-0">Relevance</span>
                    <div className="flex-1 h-1.5 rounded-full bg-gray-200">
                      <div
                        className="h-1.5 rounded-full bg-blue-400"
                        style={{ width: `${scorePct}%` }}
                        aria-label={`Relevance ${scorePct}%`}
                      />
                    </div>
                    <span className="text-gray-500 w-8 text-right">{scorePct}%</span>
                  </div>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
