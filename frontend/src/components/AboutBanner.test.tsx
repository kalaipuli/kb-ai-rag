import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AboutBanner } from "./AboutBanner";

describe("AboutBanner", () => {
  it("renders portfolio text when open", () => {
    render(<AboutBanner isOpen={true} onDismiss={vi.fn()} />);
    expect(screen.getByText(/Portfolio demo/)).toBeInTheDocument();
  });

  it("does not render when isOpen is false", () => {
    const { container } = render(<AboutBanner isOpen={false} onDismiss={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it("calls onDismiss when × clicked", async () => {
    const onDismiss = vi.fn();
    render(<AboutBanner isOpen={true} onDismiss={onDismiss} />);
    await userEvent.click(screen.getByLabelText("Dismiss banner"));
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("renders GitHub link when githubUrl prop provided", () => {
    render(<AboutBanner isOpen={true} onDismiss={vi.fn()} githubUrl="https://github.com/user/repo" />);
    const link = screen.getByText("View on GitHub ↗");
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "https://github.com/user/repo");
  });

  it("does not render GitHub link when githubUrl is not provided", () => {
    render(<AboutBanner isOpen={true} onDismiss={vi.fn()} />);
    expect(screen.queryByText("View on GitHub ↗")).not.toBeInTheDocument();
  });

  it("GitHub link opens in new tab with noopener noreferrer", () => {
    render(<AboutBanner isOpen={true} onDismiss={vi.fn()} githubUrl="https://github.com/user/repo" />);
    const link = screen.getByText("View on GitHub ↗");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });
});
