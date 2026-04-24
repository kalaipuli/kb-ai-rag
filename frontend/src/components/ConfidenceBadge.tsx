import { clsx } from "clsx";

interface ConfidenceBadgeProps {
  confidence: number;
}

export function ConfidenceBadge({ confidence }: ConfidenceBadgeProps): React.JSX.Element {
  const pct = Math.round(confidence * 100);

  const colorClass = clsx({
    "bg-green-100 text-green-800": confidence >= 0.8,
    "bg-amber-100 text-amber-800": confidence >= 0.5 && confidence < 0.8,
    "bg-red-100 text-red-800": confidence < 0.5,
  });

  const label = confidence >= 0.8 ? "High" : confidence >= 0.5 ? "Medium" : "Low";

  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
        colorClass,
      )}
      aria-label={`Confidence: ${pct}%`}
    >
      {label} ({pct}%)
    </span>
  );
}
