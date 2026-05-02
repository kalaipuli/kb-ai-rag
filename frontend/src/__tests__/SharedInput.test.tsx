import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SharedInput } from "@/components/SharedInput";

describe("SharedInput", () => {
  it("onSubmit is NOT called when isDisabled is true", async () => {
    const onSubmit = vi.fn();
    render(<SharedInput onSubmit={onSubmit} isDisabled={true} />);

    const textarea = screen.getByRole("textbox");
    await userEvent.type(textarea, "my question");
    await userEvent.keyboard("{Enter}");

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("onSubmit is NOT called via button click when isDisabled is true", async () => {
    const onSubmit = vi.fn();
    render(<SharedInput onSubmit={onSubmit} isDisabled={true} />);

    const textarea = screen.getByRole("textbox");
    await userEvent.type(textarea, "my question");

    const button = screen.getByRole("button", { name: /processing/i });
    await userEvent.click(button);

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("onSubmit is called with trimmed query when isDisabled is false", async () => {
    const onSubmit = vi.fn();
    render(<SharedInput onSubmit={onSubmit} isDisabled={false} />);

    const textarea = screen.getByRole("textbox");
    await userEvent.type(textarea, "  hello world  ");
    await userEvent.keyboard("{Enter}");

    expect(onSubmit).toHaveBeenCalledWith("hello world");
  });

  it("input value is cleared after successful submit", async () => {
    const onSubmit = vi.fn();
    render(<SharedInput onSubmit={onSubmit} isDisabled={false} />);

    const textarea = screen.getByRole("textbox") as HTMLTextAreaElement;
    await userEvent.type(textarea, "my question");
    await userEvent.keyboard("{Enter}");

    expect(textarea.value).toBe("");
  });

  it("shows processing placeholder when isDisabled is true", () => {
    render(<SharedInput onSubmit={vi.fn()} isDisabled={true} />);
    const textarea = screen.getByRole("textbox");
    expect(textarea).toHaveAttribute("placeholder", "Processing both pipelines…");
  });

  it("shows ask placeholder when isDisabled is false", () => {
    render(<SharedInput onSubmit={vi.fn()} isDisabled={false} />);
    const textarea = screen.getByRole("textbox");
    expect(textarea).toHaveAttribute("placeholder", "Ask a question for both pipelines…");
  });
});
