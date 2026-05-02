import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Topbar } from "./Topbar";

describe("Topbar", () => {
  const defaultProps = {
    collectionsCount: 3,
    totalChunks: 1240,
    onMetricsToggle: vi.fn(),
    onCollectionsOpen: vi.fn(),
    metricsOpen: false,
  };

  it("renders wordmark kb·rag", () => {
    render(<Topbar {...defaultProps} />);
    expect(screen.getByText("kb·rag")).toBeInTheDocument();
  });

  it("calls onMetricsToggle on metrics button click", async () => {
    const onMetricsToggle = vi.fn();
    render(<Topbar {...defaultProps} onMetricsToggle={onMetricsToggle} />);
    await userEvent.click(screen.getByLabelText("Toggle metrics"));
    expect(onMetricsToggle).toHaveBeenCalledOnce();
  });

  it("calls onCollectionsOpen on collections button click", async () => {
    const onCollectionsOpen = vi.fn();
    render(<Topbar {...defaultProps} onCollectionsOpen={onCollectionsOpen} />);
    await userEvent.click(screen.getByLabelText("Open collections"));
    expect(onCollectionsOpen).toHaveBeenCalledOnce();
  });

  it("applies active style when metricsOpen is true", () => {
    render(<Topbar {...defaultProps} metricsOpen={true} />);
    const btn = screen.getByLabelText("Toggle metrics");
    expect(btn).toBeInTheDocument();
    // Active state applied — background set via inline style
    expect(btn.style.background).toBeTruthy();
  });

  it("renders collections count and chunks", () => {
    render(<Topbar {...defaultProps} />);
    expect(screen.getByText(/3 collections/)).toBeInTheDocument();
    expect(screen.getByText(/1,240 chunks/)).toBeInTheDocument();
  });

  it("renders singular collection label when count is 1", () => {
    render(<Topbar {...defaultProps} collectionsCount={1} />);
    expect(screen.getByText(/1 collection ·/)).toBeInTheDocument();
  });

  it("renders DEMO badge", () => {
    render(<Topbar {...defaultProps} />);
    expect(screen.getByText("DEMO")).toBeInTheDocument();
  });
});
