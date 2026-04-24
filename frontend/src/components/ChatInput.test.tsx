import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatInput } from "./ChatInput";

describe("ChatInput", () => {
  it("calls onSubmit with trimmed value on Enter", async () => {
    const onSubmit = vi.fn();
    render(<ChatInput onSubmit={onSubmit} disabled={false} />);
    const textarea = screen.getByRole("textbox");

    await userEvent.type(textarea, "my question{Enter}");
    expect(onSubmit).toHaveBeenCalledWith("my question");
  });

  it("does not submit on Shift+Enter — inserts newline", async () => {
    const onSubmit = vi.fn();
    render(<ChatInput onSubmit={onSubmit} disabled={false} />);
    const textarea = screen.getByRole("textbox");

    await userEvent.type(textarea, "line1{Shift>}{Enter}{/Shift}line2");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("clears input after submit", async () => {
    const onSubmit = vi.fn();
    render(<ChatInput onSubmit={onSubmit} disabled={false} />);
    const textarea = screen.getByRole("textbox");

    await userEvent.type(textarea, "question{Enter}");
    expect((textarea as HTMLTextAreaElement).value).toBe("");
  });

  it("disables textarea and button when disabled prop is true", () => {
    render(<ChatInput onSubmit={vi.fn()} disabled={true} />);
    expect(screen.getByRole("textbox")).toBeDisabled();
    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
  });

  it("does not submit empty or whitespace-only input", async () => {
    const onSubmit = vi.fn();
    render(<ChatInput onSubmit={onSubmit} disabled={false} />);
    const textarea = screen.getByRole("textbox");

    await userEvent.type(textarea, "   {Enter}");
    expect(onSubmit).not.toHaveBeenCalled();
  });
});
