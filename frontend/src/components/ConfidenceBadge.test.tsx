import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConfidenceBadge } from "./ConfidenceBadge";

describe("ConfidenceBadge", () => {
  it("shows High label for confidence >= 0.8", () => {
    render(<ConfidenceBadge confidence={0.9} />);
    const label = screen.getByText("High");
    expect(label).toBeInTheDocument();
  });

  it("shows Medium label for confidence 0.5–0.79", () => {
    render(<ConfidenceBadge confidence={0.6} />);
    const label = screen.getByText("Medium");
    expect(label).toBeInTheDocument();
  });

  it("shows Low label for confidence < 0.5", () => {
    render(<ConfidenceBadge confidence={0.3} />);
    const label = screen.getByText("Low");
    expect(label).toBeInTheDocument();
  });

  it("displays percentage rounded to nearest integer", () => {
    render(<ConfidenceBadge confidence={0.856} />);
    expect(screen.getByText("86%")).toBeInTheDocument();
  });

  it("renders wrapper element with aria-label", () => {
    render(<ConfidenceBadge confidence={0.75} />);
    expect(screen.getByLabelText("Confidence: 75%")).toBeInTheDocument();
  });

  it("renders percentage in the ring element", () => {
    render(<ConfidenceBadge confidence={0.5} />);
    expect(screen.getByText("50%")).toBeInTheDocument();
  });
});
