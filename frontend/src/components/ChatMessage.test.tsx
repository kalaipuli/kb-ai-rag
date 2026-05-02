import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatMessage } from "./ChatMessage";
import type { Message } from "@/types";

const makeMessage = (overrides: Partial<Message> = {}): Message => ({
  id: "1",
  role: "user",
  content: "Hello",
  timestamp: new Date().toISOString(),
  ...overrides,
});

describe("ChatMessage", () => {
  it("renders user message with right-aligned bubble", () => {
    const { container } = render(<ChatMessage message={makeMessage()} />);
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toMatch(/justify-end/);
  });

  it("renders assistant message with left-aligned bubble", () => {
    const { container } = render(
      <ChatMessage message={makeMessage({ role: "assistant", content: "Hi there" })} />,
    );
    const wrapper = container.firstChild as HTMLElement;
    expect(wrapper.className).toMatch(/justify-start/);
  });

  it("shows spinner when assistant content is empty", () => {
    const { container } = render(
      <ChatMessage message={makeMessage({ role: "assistant", content: "" })} />,
    );
    expect(container.querySelector(".animate-spin")).toBeInTheDocument();
  });

  it("renders citations for assistant messages", () => {
    const citations = [
      {
        chunk_id: "c1",
        filename: "guide.pdf",
        source_path: "/docs/guide.pdf",
        page_number: 2,
      },
    ];
    render(
      <ChatMessage
        message={makeMessage({ role: "assistant", content: "Answer", citations })}
      />,
    );
    expect(screen.getByText("guide.pdf")).toBeInTheDocument();
  });

  it("renders confidence badge for assistant messages with confidence", () => {
    render(
      <ChatMessage
        message={makeMessage({ role: "assistant", content: "Answer", confidence: 0.9 })}
      />,
    );
    expect(screen.getByText(/High/)).toBeInTheDocument();
  });

  it("does not render citations or badge for user messages", () => {
    const citations = [
      {
        chunk_id: "c1",
        filename: "guide.pdf",
        source_path: "/docs/guide.pdf",
        page_number: 2,
      },
    ];
    render(
      <ChatMessage
        message={makeMessage({ role: "user", content: "Question", citations, confidence: 0.9 })}
      />,
    );
    expect(screen.queryByText("guide.pdf")).not.toBeInTheDocument();
    expect(screen.queryByText(/High/)).not.toBeInTheDocument();
  });

  it("renders collapsible Sources panel for assistant messages with citations", () => {
    const citations = [
      { chunk_id: "c1", filename: "guide.pdf", source_path: "/docs/guide.pdf", page_number: 2 },
      { chunk_id: "c2", filename: "guide.pdf", source_path: "/docs/guide.pdf", page_number: 5 },
    ];
    render(
      <ChatMessage
        message={makeMessage({ role: "assistant", content: "Answer", citations })}
      />,
    );
    expect(screen.getByText("Sources (2)")).toBeInTheDocument();
  });

  it("shows chunks retrieved count after opening the panel", async () => {
    const citations = [
      { chunk_id: "c1", filename: "a.pdf", source_path: "/a.pdf", page_number: 1 },
    ];
    render(
      <ChatMessage
        message={makeMessage({
          role: "assistant",
          content: "Answer",
          citations,
          chunksRetrieved: 8,
        })}
      />,
    );
    await userEvent.click(screen.getByText("Sources (1)"));
    expect(screen.getByText("8 chunks retrieved")).toBeInTheDocument();
  });

  it("renders without crashing when chunksRetrieved is undefined", () => {
    const citations = [
      { chunk_id: "c1", filename: "a.pdf", source_path: "/a.pdf", page_number: 1 },
    ];
    render(
      <ChatMessage
        message={makeMessage({ role: "assistant", content: "Answer", citations })}
      />,
    );
    expect(screen.getByText("Sources (1)")).toBeInTheDocument();
    expect(screen.queryByText(/chunks retrieved/)).not.toBeInTheDocument();
  });

  it("shows distinct source count in expanded panel", async () => {
    const citations = [
      { chunk_id: "c1", filename: "a.pdf", source_path: "/a.pdf", page_number: 1 },
      { chunk_id: "c2", filename: "a.pdf", source_path: "/a.pdf", page_number: 2 },
      { chunk_id: "c3", filename: "b.pdf", source_path: "/b.pdf", page_number: 1 },
    ];
    render(
      <ChatMessage
        message={makeMessage({ role: "assistant", content: "Answer", citations })}
      />,
    );
    await userEvent.click(screen.getByText("Sources (3)"));
    expect(screen.getByText("2 distinct sources")).toBeInTheDocument();
  });

  it("accepts accentColor prop without TypeScript error", () => {
    const { container } = render(
      <ChatMessage
        message={makeMessage({ role: "assistant", content: "Answer" })}
        accentColor="static"
      />,
    );
    expect(container.firstChild).toBeInTheDocument();
  });

  it("accepts agentic accentColor prop", () => {
    const { container } = render(
      <ChatMessage
        message={makeMessage({ role: "assistant", content: "Answer" })}
        accentColor="agentic"
      />,
    );
    expect(container.firstChild).toBeInTheDocument();
  });
});
