import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CitationList } from "./CitationList";
import type { Citation } from "@/types";

const makeCitation = (overrides: Partial<Citation> = {}): Citation => ({
  filename: "policy.pdf",
  page: 5,
  chunk_index: 0,
  score: 0.9,
  ...overrides,
});

describe("CitationList", () => {
  it("renders nothing for empty citations", () => {
    const { container } = render(<CitationList citations={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders filename and page number", () => {
    render(<CitationList citations={[makeCitation()]} />);
    expect(screen.getByText("policy.pdf")).toBeInTheDocument();
    expect(screen.getByText("p.5")).toBeInTheDocument();
  });

  it("renders em dash for null page", () => {
    render(<CitationList citations={[makeCitation({ page: null })]} />);
    expect(screen.getByText("p.—")).toBeInTheDocument();
  });

  it("renders multiple citations", () => {
    const citations = [
      makeCitation({ filename: "doc1.pdf", page: 1 }),
      makeCitation({ filename: "doc2.pdf", page: 2 }),
    ];
    render(<CitationList citations={citations} />);
    expect(screen.getByText("doc1.pdf")).toBeInTheDocument();
    expect(screen.getByText("doc2.pdf")).toBeInTheDocument();
  });
});
