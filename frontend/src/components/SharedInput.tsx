"use client";

import { useState } from "react";
import type { JSX, KeyboardEvent, ChangeEvent } from "react";
import { Send } from "lucide-react";

interface SharedInputProps {
  onSubmit: (query: string) => void;
  isDisabled: boolean;
}

export function SharedInput({ onSubmit, isDisabled }: SharedInputProps): JSX.Element {
  const [value, setValue] = useState("");

  function handleSubmit(): void {
    if (isDisabled) return;
    const trimmed = value.trim();
    if (!trimmed) return;
    setValue("");
    onSubmit(trimmed);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>): void {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  function handleChange(e: ChangeEvent<HTMLTextAreaElement>): void {
    setValue(e.target.value);
  }

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-end gap-2 rounded-2xl border border-gray-200 bg-white p-2 shadow-sm">
        <textarea
          rows={1}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          disabled={isDisabled}
          placeholder="Ask a question for both pipelines… (Enter to send)"
          className="flex-1 resize-none bg-transparent text-sm text-gray-900 placeholder-gray-400 outline-none disabled:opacity-50"
          style={{ maxHeight: "8rem" }}
        />
        <button
          onClick={handleSubmit}
          disabled={isDisabled || !value.trim()}
          aria-label="Send to both pipelines"
          className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Send size={14} />
        </button>
      </div>
      {isDisabled && (
        <p className="text-xs text-gray-500">Both pipelines processing...</p>
      )}
    </div>
  );
}
