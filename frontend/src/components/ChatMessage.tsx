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

        {!isUser && message.citations && message.citations.length > 0 && (
          <CitationList citations={message.citations} />
        )}

        {!isUser && message.confidence !== undefined && (
          <div className="mt-2">
            <ConfidenceBadge confidence={message.confidence} />
          </div>
        )}
      </div>
    </div>
  );
}
