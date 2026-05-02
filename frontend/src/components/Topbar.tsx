"use client";

import type { JSX } from "react";

interface TopbarProps {
  collectionsCount: number;
  totalChunks: number;
  onMetricsToggle: () => void;
  onCollectionsOpen: () => void;
  metricsOpen: boolean;
}

export function Topbar({
  collectionsCount,
  totalChunks,
  onMetricsToggle,
  onCollectionsOpen,
  metricsOpen,
}: TopbarProps): JSX.Element {
  return (
    <header
      className="flex items-center gap-3 px-4"
      style={{
        height: '40px',
        background: 'var(--surface-raised)',
        borderBottom: '1px solid var(--border-subtle)',
      }}
    >
      {/* Wordmark */}
      <span className="font-semibold text-sm" style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-inter)' }}>
        kb·rag
      </span>
      <span
        className="text-xs px-1.5 py-0.5 rounded"
        style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', background: 'var(--surface-overlay)' }}
      >
        DEMO
      </span>

      {/* Separator */}
      <div className="w-px h-4" style={{ background: 'var(--border-subtle)' }} />

      {/* Collections pill */}
      <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
        {collectionsCount} collection{collectionsCount !== 1 ? 's' : ''} · {totalChunks.toLocaleString()} chunks
      </span>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Metrics toggle button */}
      <button
        onClick={onMetricsToggle}
        aria-label="Toggle metrics"
        className="flex items-center justify-center rounded text-xs px-2 py-1 transition-colors"
        style={{
          width: '32px',
          height: '32px',
          background: metricsOpen ? 'var(--accent-muted)' : 'transparent',
          color: metricsOpen ? 'var(--accent-primary)' : 'var(--text-secondary)',
          border: metricsOpen ? '1px solid var(--accent-primary)' : '1px solid transparent',
        }}
        onMouseEnter={(e) => {
          if (!metricsOpen) (e.currentTarget as HTMLButtonElement).style.background = 'var(--surface-overlay)';
        }}
        onMouseLeave={(e) => {
          if (!metricsOpen) (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
        }}
      >
        📊
      </button>

      {/* Collections button */}
      <button
        onClick={onCollectionsOpen}
        aria-label="Open collections"
        className="flex items-center justify-center rounded text-xs transition-colors"
        style={{
          width: '32px',
          height: '32px',
          background: 'transparent',
          color: 'var(--text-secondary)',
        }}
        onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'var(--surface-overlay)'; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = 'transparent'; }}
      >
        ☰
      </button>
    </header>
  );
}
