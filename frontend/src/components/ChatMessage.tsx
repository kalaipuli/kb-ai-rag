import type { JSX } from "react";
import { clsx } from "clsx";
import type { Message } from "@/types";
import { CitationList } from "./CitationList";
import { ConfidenceBadge } from "./ConfidenceBadge";

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps): JSX.Element {
  const isUser = message.role === "user";
  const hasCitations = !isUser && message.citations && message.citations.length > 0;
  const distinctSources = hasCitations
    ? new Set(message.citations!.map((c) => c.filename)).size
    : 0;

  return (
    <div className={clsx("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={clsx(
          "max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
          isUser
            ? "bg-blue-600 text-white rounded-br-sm"
            : "bg-gray-100 text-gray-900 rounded-bl-sm",
        )}
      >
        <p className="whitespace-pre-wrap break-words">
          {message.content || (
            <span className="inline-block w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
          )}
        </p>

        {!isUser && message.confidence !== undefined && (
          <div className="mt-2">
            <ConfidenceBadge confidence={message.confidence} />
          </div>
        )}

        {hasCitations && (
          <details className="mt-2">
            <summary className="cursor-pointer text-xs font-semibold text-gray-500 select-none">
              Sources ({message.citations!.length})
            </summary>
            <div className="mt-1 space-y-0.5 text-xs text-gray-500">
              {message.chunksRetrieved !== undefined && (
                <p>{message.chunksRetrieved} chunks retrieved</p>
              )}
              {distinctSources > 0 && <p>{distinctSources} distinct source{distinctSources !== 1 ? "s" : ""}</p>}
            </div>
            <CitationList citations={message.citations!} />
          </details>
        )}
      </div>
    </div>
  );
}
