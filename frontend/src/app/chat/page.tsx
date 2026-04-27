"use client";

import { useCallback, useEffect, useRef } from "react";
import { Bot } from "lucide-react";
import { ChatMessage } from "@/components/ChatMessage";
import { Sidebar } from "@/components/Sidebar";
import { SharedInput } from "@/components/SharedInput";
import { AgentPanel } from "@/components/AgentPanel";
import { AgentVerdict } from "@/components/AgentVerdict";
import { useStream } from "@/hooks/useStream";
import { useAgentStream } from "@/hooks/useAgentStream";

export default function ChatPage(): React.JSX.Element {
  const {
    messages: staticMessages,
    isStreaming: staticStreaming,
    error: staticError,
    submit: submitStatic,
    resetError,
  } = useStream();

  const {
    messages: agentMessages,
    isStreaming: agentStreaming,
    error: agentError,
    submit: submitAgentic,
  } = useAgentStream();

  const isEitherStreaming = staticStreaming || agentStreaming;

  const handleSubmit = useCallback(
    (query: string): void => {
      void submitStatic(query);
      void submitAgentic(query);
    },
    [submitStatic, submitAgentic],
  );

  const staticBottomRef = useRef<HTMLDivElement>(null);
  const agentBottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    staticBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [staticMessages]);

  useEffect(() => {
    agentBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [agentMessages]);

  return (
    <div className="flex h-screen overflow-hidden bg-white">
      <Sidebar />

      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex items-center gap-2 border-b border-gray-200 px-6 py-3">
          <Bot size={20} className="text-blue-600" />
          <h1 className="text-sm font-semibold text-gray-800">
            KB AI RAG — Knowledge Assistant (Parallel View)
          </h1>
        </header>

        <div className="border-b border-gray-200 px-6 py-3">
          <SharedInput onSubmit={handleSubmit} isDisabled={isEitherStreaming} />
          {!isEitherStreaming && staticMessages.length > 0 && agentMessages.length > 0 && (
            <div className="mt-2">
              <AgentVerdict staticMessages={staticMessages} agentMessages={agentMessages} />
            </div>
          )}
        </div>

        <main className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1 overflow-hidden">
          {/* Left column: Static Chain */}
          <div className="flex flex-col overflow-hidden border-r border-gray-200 px-4 py-4">
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
              Static Chain
            </h2>
            <div className="flex-1 overflow-y-auto space-y-4">
              {staticMessages.length === 0 ? (
                <div className="flex h-full flex-col items-center justify-center text-center">
                  <Bot size={32} className="mb-3 text-gray-300" />
                  <p className="text-xs text-gray-400">Ask a question to see results here.</p>
                </div>
              ) : (
                <>
                  {staticMessages.map((msg) => (
                    <ChatMessage key={msg.id} message={msg} />
                  ))}
                  <div ref={staticBottomRef} />
                </>
              )}
            </div>
            {staticError && (
              <div className="mt-2 flex items-center justify-between rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">
                <span>{staticError.message}</span>
                <button onClick={resetError} className="ml-4 font-medium underline">
                  Dismiss
                </button>
              </div>
            )}
          </div>

          {/* Right column: Agentic Pipeline */}
          <div className="flex flex-col overflow-hidden px-4 py-4">
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
              Agentic Pipeline
            </h2>
            <div className="flex-1 overflow-y-auto">
              {agentMessages.length === 0 ? (
                <div className="flex h-full flex-col items-center justify-center text-center">
                  <Bot size={32} className="mb-3 text-gray-300" />
                  <p className="text-xs text-gray-400">Ask a question to see results here.</p>
                </div>
              ) : (
                <>
                  <AgentPanel
                    messages={agentMessages}
                    isStreaming={agentStreaming}
                    error={agentError}
                  />
                  <div ref={agentBottomRef} />
                </>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
