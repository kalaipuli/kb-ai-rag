"use client";

import { useState, useRef } from "react";
import type { JSX, KeyboardEvent, ChangeEvent } from "react";

interface SharedInputProps {
  onSubmit: (query: string) => void;
  isDisabled: boolean;
}

export function SharedInput({ onSubmit, isDisabled }: SharedInputProps): JSX.Element {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function handleSubmit(): void {
    if (isDisabled) return;
    const trimmed = value.trim();
    if (!trimmed) return;
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    onSubmit(trimmed);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>): void {
    if ((e.key === "Enter" && e.metaKey) || (e.key === "Enter" && !e.shiftKey)) {
      e.preventDefault();
      handleSubmit();
    }
  }

  function handleChange(e: ChangeEvent<HTMLTextAreaElement>): void {
    setValue(e.target.value);
    const el = e.target;
    el.style.height = 'auto';
    const lineHeight = 24;
    const maxLines = 4;
    el.style.height = `${Math.min(el.scrollHeight, lineHeight * maxLines)}px`;
  }

  return (
    <div
      className="px-4 py-3"
      style={{ background: 'var(--surface-base)' }}
    >
      <div
        className="relative flex items-end gap-2 rounded-xl px-3 py-2"
        style={{
          background: 'var(--surface-raised)',
          border: '1px solid var(--border-default)',
          outline: 'none',
        }}
        onFocusCapture={(e) => {
          (e.currentTarget as HTMLDivElement).style.boxShadow = '0 0 0 2px var(--accent-primary)';
        }}
        onBlurCapture={(e) => {
          (e.currentTarget as HTMLDivElement).style.boxShadow = 'none';
        }}
      >
        <textarea
          ref={textareaRef}
          rows={1}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={isDisabled ? "Processing both pipelines…" : "Ask a question for both pipelines…"}
          className="flex-1 resize-none bg-transparent text-sm outline-none"
          style={{
            color: 'var(--text-primary)',
            caretColor: 'var(--accent-primary)',
            minHeight: '24px',
            maxHeight: '96px',
            overflow: 'auto',
          }}
        />
        {!value && !isDisabled && (
          <span
            className="absolute right-12 bottom-2 text-xs pointer-events-none hidden md:block"
            style={{ color: 'var(--text-muted)' }}
          >
            ⌘↵ to send
          </span>
        )}
        <button
          onClick={handleSubmit}
          disabled={isDisabled || !value.trim()}
          aria-label={isDisabled ? "Processing" : "Send to both pipelines"}
          className="flex flex-shrink-0 items-center justify-center rounded-full text-sm transition-colors disabled:cursor-not-allowed disabled:opacity-40"
          style={{
            width: '36px',
            height: '36px',
            background: 'var(--accent-primary)',
            color: 'white',
          }}
        >
          {isDisabled ? (
            <span className="animate-pulse-dot">⏹</span>
          ) : (
            <span>→</span>
          )}
        </button>
      </div>
    </div>
  );
}
