"use client";

import { useEffect, useRef } from "react";
import { Bot } from "lucide-react";
import { ChatInput } from "@/components/ChatInput";
import { ChatMessage } from "@/components/ChatMessage";
import { Sidebar } from "@/components/Sidebar";
import { useStream } from "@/hooks/useStream";

export default function ChatPage(): React.JSX.Element {
  const { messages, isStreaming, error, submit, resetError } = useStream();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex h-screen overflow-hidden bg-white">
      <Sidebar />

      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex items-center gap-2 border-b border-gray-200 px-6 py-3">
          <Bot size={20} className="text-blue-600" />
          <h1 className="text-sm font-semibold text-gray-800">
            KB AI RAG — Knowledge Assistant
          </h1>
        </header>

        <main className="flex-1 overflow-y-auto px-6 py-4">
          {messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center text-center">
              <Bot size={40} className="mb-3 text-gray-300" />
              <p className="text-sm text-gray-400">
                Ask a question about your knowledge base.
              </p>
            </div>
          ) : (
            <div className="mx-auto max-w-2xl space-y-4">
              {messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} />
              ))}
              <div ref={bottomRef} />
            </div>
          )}
        </main>

        {error && (
          <div className="mx-6 mb-2 flex items-center justify-between rounded-lg bg-red-50 px-4 py-2 text-xs text-red-700">
            <span>{error.message}</span>
            <button onClick={resetError} className="ml-4 font-medium underline">
              Dismiss
            </button>
          </div>
        )}

        <footer className="border-t border-gray-200 px-6 py-3">
          <div className="mx-auto max-w-2xl">
            <ChatInput onSubmit={submit} disabled={isStreaming} />
          </div>
        </footer>
      </div>
    </div>
  );
}
