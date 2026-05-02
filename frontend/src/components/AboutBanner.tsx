"use client";

import type { JSX } from "react";

interface AboutBannerProps {
  isOpen: boolean;
  onDismiss: () => void;
  githubUrl?: string;
}

export function AboutBanner({ isOpen, onDismiss, githubUrl }: AboutBannerProps): JSX.Element | null {
  if (!isOpen) return null;

  return (
    <div
      className="flex items-center gap-3 px-4 text-xs animate-slide-down"
      style={{
        minHeight: '40px',
        background: 'var(--surface-raised)',
        borderTop: '3px solid',
        borderImage: 'linear-gradient(to right, hsl(38 92% 50%), hsl(249 100% 70%)) 1',
      }}
    >
      <span>🔬</span>
      <span style={{ color: 'var(--text-secondary)' }}>
        Portfolio demo — Enterprise Agentic RAG platform. Two pipelines process the same query in parallel.
      </span>
      {githubUrl && (
        <a
          href={githubUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="underline flex-shrink-0"
          style={{ color: 'var(--accent-primary)' }}
        >
          View on GitHub ↗
        </a>
      )}
      <div className="flex-1" />
      <button
        onClick={onDismiss}
        aria-label="Dismiss banner"
        className="text-sm"
        style={{ color: 'var(--text-muted)' }}
      >
        ×
      </button>
    </div>
  );
}
