"use client";

import { useRef, useState } from "react";
import type { JSX, KeyboardEvent, ChangeEvent } from "react";
import { Send } from "lucide-react";

interface ChatInputProps {
  onSubmit: (question: string) => void;
  disabled: boolean;
}

export function ChatInput({ onSubmit, disabled }: ChatInputProps): JSX.Element {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function handleSubmit(): void {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>): void {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  function handleInput(e: ChangeEvent<HTMLTextAreaElement>): void {
    setValue(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }

  return (
    <div className="flex items-end gap-2 rounded-2xl border border-gray-200 bg-white p-2 shadow-sm">
      <textarea
        ref={textareaRef}
        rows={1}
        value={value}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        placeholder="Ask a question… (Enter to send, Shift+Enter for newline)"
        className="flex-1 resize-none bg-transparent text-sm text-gray-900 placeholder-gray-400 outline-none disabled:opacity-50"
        style={{ maxHeight: "8rem" }}
      />
      <button
        onClick={handleSubmit}
        disabled={disabled || !value.trim()}
        aria-label="Send message"
        className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40"
      >
        <Send size={14} />
      </button>
    </div>
  );
}
