import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { CitationList } from "./CitationList";
import type { Citation } from "@/types";

const makeCitation = (overrides: Partial<Citation> = {}): Citation => ({
  chunk_id: "c1",
  filename: "policy.pdf",
  source_path: "/docs/policy.pdf",
  page_number: 5,
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
    render(<CitationList citations={[makeCitation({ page_number: null })]} />);
    expect(screen.getByText("p.—")).toBeInTheDocument();
  });

  it("renders multiple citations", () => {
    const citations = [
      makeCitation({ chunk_id: "c1", filename: "doc1.pdf", page_number: 1 }),
      makeCitation({ chunk_id: "c2", filename: "doc2.pdf", page_number: 2 }),
    ];
    render(<CitationList citations={citations} />);
    expect(screen.getByText("doc1.pdf")).toBeInTheDocument();
    expect(screen.getByText("doc2.pdf")).toBeInTheDocument();
  });

  it("renders relevance score bar when retrieval_score is defined", () => {
    render(<CitationList citations={[makeCitation({ retrieval_score: 0.75 })]} />);
    expect(screen.getByText("Relevance")).toBeInTheDocument();
    expect(screen.getByText("75%")).toBeInTheDocument();
  });

  it("does not render score bar when retrieval_score is undefined", () => {
    render(<CitationList citations={[makeCitation({ retrieval_score: undefined })]} />);
    expect(screen.queryByText("Relevance")).not.toBeInTheDocument();
  });

  it("clamps score bar to 100% for values above 1", () => {
    render(<CitationList citations={[makeCitation({ retrieval_score: 5.0 })]} />);
    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  it("clamps score bar to 0% for negative values", () => {
    render(<CitationList citations={[makeCitation({ retrieval_score: -2.0 })]} />);
    expect(screen.getByText("0%")).toBeInTheDocument();
  });
});
