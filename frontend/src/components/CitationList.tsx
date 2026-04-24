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
      <ul className="space-y-0.5">
        {citations.map((c) => (
          <li key={c.chunk_id} className="flex items-center gap-1 text-xs text-gray-600">
            <span className="font-medium truncate max-w-[200px]" title={c.filename}>
              {c.filename}
            </span>
            <span className="text-gray-400">·</span>
            <span>p.{c.page_number ?? "—"}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
