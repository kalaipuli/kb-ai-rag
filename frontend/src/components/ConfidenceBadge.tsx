import type { JSX } from "react";

interface ConfidenceBadgeProps {
  confidence: number;
}

function fillColor(confidence: number): string {
  if (confidence >= 0.8) return 'var(--status-success)';
  if (confidence >= 0.5) return 'var(--status-warning)';
  return 'var(--status-danger)';
}

export function ConfidenceBadge({ confidence }: ConfidenceBadgeProps): JSX.Element {
  const pct = Math.round(confidence * 100);
  const color = fillColor(confidence);
  const label = confidence >= 0.8 ? "High" : confidence >= 0.5 ? "Medium" : "Low";

  return (
    <span
      className="inline-flex items-center gap-1.5"
      aria-label={`Confidence: ${pct}%`}
    >
      <span
        className="inline-flex items-center justify-center rounded-full text-xs font-medium"
        style={{
          width: '28px',
          height: '28px',
          background: `conic-gradient(${color} ${pct}%, var(--border-subtle) 0)`,
          color: 'var(--text-primary)',
          fontSize: '0.5rem',
          fontFamily: 'var(--font-mono)',
        }}
      >
        {pct}%
      </span>
      <span
        className="text-xs font-medium"
        style={{ color }}
      >
        {label}
      </span>
    </span>
  );
}
