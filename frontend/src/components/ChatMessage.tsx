import type { JSX } from "react";
import type { Message } from "@/types";
import { CitationList } from "./CitationList";
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
            <CitationList citations={message.citations!} accentColor={accentColor} />
          </details>
        )}
      </div>
    </div>
  );
}
