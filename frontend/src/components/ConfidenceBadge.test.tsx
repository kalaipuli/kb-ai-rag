import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConfidenceBadge } from "./ConfidenceBadge";

describe("ConfidenceBadge", () => {
  it("shows green High badge for confidence >= 0.8", () => {
    render(<ConfidenceBadge confidence={0.9} />);
    const badge = screen.getByText(/High/);
    expect(badge).toBeInTheDocument();
    expect(badge.className).toMatch(/green/);
  });

  it("shows amber Medium badge for confidence 0.5–0.79", () => {
    render(<ConfidenceBadge confidence={0.6} />);
    const badge = screen.getByText(/Medium/);
    expect(badge).toBeInTheDocument();
    expect(badge.className).toMatch(/amber/);
  });

  it("shows red Low badge for confidence < 0.5", () => {
    render(<ConfidenceBadge confidence={0.3} />);
    const badge = screen.getByText(/Low/);
    expect(badge).toBeInTheDocument();
    expect(badge.className).toMatch(/red/);
  });

  it("displays percentage rounded to nearest integer", () => {
    render(<ConfidenceBadge confidence={0.856} />);
    expect(screen.getByText(/86%/)).toBeInTheDocument();
  });
});
