import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MetricsBar } from "./MetricsBar";

const metrics = { faithfulness: 0.95, relevancy: 0.87, precision: 0.72, recall: 0.65 };

describe("MetricsBar", () => {
  it("renders all four metric names when open", () => {
    render(<MetricsBar metrics={metrics} isOpen={true} onDismiss={vi.fn()} />);
    expect(screen.getByText(/Faithfulness/)).toBeInTheDocument();
    expect(screen.getByText(/Relevancy/)).toBeInTheDocument();
    expect(screen.getByText(/Precision/)).toBeInTheDocument();
    expect(screen.getByText(/Recall/)).toBeInTheDocument();
  });

  it("does not render when isOpen is false", () => {
    const { container } = render(<MetricsBar metrics={metrics} isOpen={false} onDismiss={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it("does not render when metrics is null", () => {
    const { container } = render(<MetricsBar metrics={null} isOpen={true} onDismiss={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it("calls onDismiss when × button clicked", async () => {
    const onDismiss = vi.fn();
    render(<MetricsBar metrics={metrics} isOpen={true} onDismiss={onDismiss} />);
    await userEvent.click(screen.getByLabelText("Dismiss metrics"));
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("high metric (>=0.85) pill uses success color", () => {
    render(<MetricsBar metrics={metrics} isOpen={true} onDismiss={vi.fn()} />);
    const faithfulnessPill = screen.getByText(/Faithfulness 0.95/);
    expect(faithfulnessPill).toBeInTheDocument();
    expect(faithfulnessPill.style.background).toContain('var(--status-success)');
  });

  it("medium metric (>=0.70 <0.85) pill uses warning color", () => {
    render(<MetricsBar metrics={metrics} isOpen={true} onDismiss={vi.fn()} />);
    const precisionPill = screen.getByText(/Precision 0.72/);
    expect(precisionPill).toBeInTheDocument();
    expect(precisionPill.style.background).toContain('var(--status-warning)');
  });

  it("low metric (<0.70) pill uses danger color", () => {
    render(<MetricsBar metrics={metrics} isOpen={true} onDismiss={vi.fn()} />);
    const recallPill = screen.getByText(/Recall 0.65/);
    expect(recallPill).toBeInTheDocument();
    expect(recallPill.style.background).toContain('var(--status-danger)');
  });
});
