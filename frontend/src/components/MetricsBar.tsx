"use client";

import type { JSX } from "react";

interface MetricsBarProps {
  metrics: { faithfulness: number; relevancy: number; precision: number; recall: number } | null;
  isOpen: boolean;
  onDismiss: () => void;
}

function pillColor(value: number): string {
  if (value >= 0.85) return 'var(--status-success)';
  if (value >= 0.70) return 'var(--status-warning)';
  return 'var(--status-danger)';
}

export function MetricsBar({ metrics, isOpen, onDismiss }: MetricsBarProps): JSX.Element | null {
  if (!isOpen || metrics === null) return null;

  const pills: Array<{ label: string; value: number }> = [
    { label: 'Faithfulness', value: metrics.faithfulness },
    { label: 'Relevancy', value: metrics.relevancy },
    { label: 'Precision', value: metrics.precision },
    { label: 'Recall', value: metrics.recall },
  ];

  return (
    <div
      className="flex items-center gap-3 px-4 animate-slide-down"
      style={{
        minHeight: '48px',
        background: 'var(--surface-raised)',
        borderBottom: '1px solid var(--border-subtle)',
      }}
    >
      <div className="flex flex-wrap gap-2 flex-1">
        {pills.map(({ label, value }) => (
          <span
            key={label}
            className="px-2 py-0.5 rounded-full text-xs font-medium"
            style={{
              background: pillColor(value),
              color: 'var(--text-primary)',
            }}
          >
            {label} {value.toFixed(2)}
          </span>
        ))}
        <span className="text-xs self-center" style={{ color: 'var(--text-muted)' }}>
          RAGAS evaluation · last run from baseline
        </span>
      </div>
      <button
        onClick={onDismiss}
        aria-label="Dismiss metrics"
        className="text-sm flex-shrink-0"
        style={{ color: 'var(--text-muted)' }}
      >
        ×
      </button>
    </div>
  );
}
