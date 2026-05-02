import type { JSX } from "react";
import type { Message } from "@/types";
import { ConfidenceBadge } from "./ConfidenceBadge";

interface ChatMessageProps {
  message: Message;
  accentColor?: "static" | "agentic";
}

const ACCENT_MAP: Record<"static" | "agentic", string> = {
  static: "var(--static-chain)",
  agentic: "var(--agentic)",
};

export function ChatMessage({ message, accentColor }: ChatMessageProps): JSX.Element {
  const isUser = message.role === "user";
  const hasCitations = !isUser && message.citations && message.citations.length > 0;
  const distinctSources = hasCitations
    ? new Set(message.citations!.map((c) => c.filename)).size
    : 0;
  const accentStyle = accentColor ? ACCENT_MAP[accentColor] : "var(--text-muted)";
  const accentCss = accentColor ? ACCENT_MAP[accentColor] : 'var(--accent-primary)';

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className="text-sm leading-relaxed"
        style={
          isUser
            ? {
                maxWidth: '75%',
                background: 'var(--accent-muted)',
                color: 'var(--text-primary)',
                borderRadius: '1rem 1rem 0.25rem 1rem',
                padding: '0.75rem 1rem',
              }
            : {
                maxWidth: '85%',
                background: 'var(--surface-overlay)',
                color: 'var(--text-primary)',
                borderLeft: `3px solid ${accentStyle}`,
                borderRadius: '1rem 1rem 1rem 0.25rem',
                padding: '0.75rem 1rem',
              }
        }
      >
        <p className="whitespace-pre-wrap break-words">
          {message.content || (
            <span
              className="inline-block w-4 h-4 border-2 rounded-full animate-spin"
              style={{ borderColor: 'var(--border-default)', borderTopColor: 'var(--accent-primary)' }}
            />
          )}
        </p>

        {!isUser && message.confidence !== undefined && (
          <div className="mt-2">
            <ConfidenceBadge confidence={message.confidence} />
          </div>
        )}

        {hasCitations && (
          <details className="mt-2">
            <summary
              className="cursor-pointer text-xs font-semibold select-none"
              style={{ color: 'var(--text-secondary)' }}
            >
              Sources ({message.citations!.length})
            </summary>
            <div className="mt-1 space-y-0.5 text-xs" style={{ color: 'var(--text-muted)' }}>
              {message.chunksRetrieved !== undefined && (
                <p>{message.chunksRetrieved} chunks retrieved</p>
              )}
              {distinctSources > 0 && (
                <p>{distinctSources} distinct source{distinctSources !== 1 ? "s" : ""}</p>
              )}
            </div>
            <ul className="mt-2 space-y-2">
              {message.citations!.map((c) => {
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
        )}
      </div>
    </div>
  );
}
