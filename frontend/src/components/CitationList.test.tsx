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

  it("renders collapsible details element open by default", () => {
    const { container } = render(<CitationList citations={[makeCitation()]} />);
    const details = container.querySelector("details");
    expect(details).toBeInTheDocument();
    expect(details).toHaveAttribute("open");
  });

  it("accepts accentColor prop without error", () => {
    const { container } = render(
      <CitationList citations={[makeCitation()]} accentColor="static" />,
    );
    expect(container.firstChild).toBeInTheDocument();
  });

  it("accepts agentic accentColor prop", () => {
    const { container } = render(
      <CitationList citations={[makeCitation()]} accentColor="agentic" />,
    );
    expect(container.firstChild).toBeInTheDocument();
  });

  it("renders relevance bar from retrieval_score even when grader_score is also present", () => {
    const citation = makeCitation({ retrieval_score: 0.65, grader_score: 0.9 });
    render(<CitationList citations={[citation]} />);
    expect(screen.getByText("65%")).toBeInTheDocument();
    // grader_score value (90%) should NOT appear as the bar percentage
    expect(screen.queryByText("90%")).not.toBeInTheDocument();
  });
});
