"use client";

import type { JSX } from "react";
import type { AgentMessage } from "@/types";
import { ChatMessage } from "./ChatMessage";
import { AgentTrace } from "./AgentTrace";

interface AgentPanelProps {
  messages: AgentMessage[];
  isStreaming: boolean;
  error: Error | null;
}

export function AgentPanel({ messages, isStreaming, error }: AgentPanelProps): JSX.Element {
  return (
    <div className="flex flex-col gap-4">
      {error && (
        <div className="rounded-lg bg-red-50 px-4 py-2 text-xs text-red-700">
          {error.message}
        </div>
      )}
      {messages.map((message, index) => {
        const isLastMessage = index === messages.length - 1;
        return (
          <div key={message.id}>
            <ChatMessage message={message} />
            {message.role === "assistant" &&
              message.agentSteps &&
              message.agentSteps.length > 0 && (
                <AgentTrace
                  steps={message.agentSteps}
                  isStreaming={isStreaming && isLastMessage}
                />
              )}
          </div>
        );
      })}
    </div>
  );
}
