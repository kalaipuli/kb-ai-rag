import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { EvalBaseline } from "./EvalBaseline";

const BASELINE = {
  faithfulness: 0.9028,
  answer_relevancy: 0.9752,
  context_recall: 0.9542,
  context_precision: 0.9642,
  answer_correctness: 0.765,
};

describe("EvalBaseline", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders metric scores when fetch succeeds", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify(BASELINE), { status: 200 }),
    );

    render(<EvalBaseline />);

    await waitFor(() => {
      expect(screen.getByText("Faithfulness")).toBeInTheDocument();
      expect(screen.getByText("0.9028")).toBeInTheDocument();
      expect(screen.getByText("Answer Correctness")).toBeInTheDocument();
      expect(screen.getByText("0.7650")).toBeInTheDocument();
    });
  });

  it("renders fallback message when fetch returns 404", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "No evaluation baseline found." }), { status: 404 }),
    );

    render(<EvalBaseline />);

    await waitFor(() => {
      expect(screen.getByText(/No baseline available/)).toBeInTheDocument();
    });
  });

  it("renders fallback when fetch rejects", async () => {
    vi.spyOn(global, "fetch").mockRejectedValue(new Error("network error"));

    render(<EvalBaseline />);

    await waitFor(() => {
      expect(screen.getByText(/No baseline available/)).toBeInTheDocument();
    });
  });

  it("renders loading state before fetch resolves", () => {
    vi.spyOn(global, "fetch").mockReturnValue(new Promise(() => {})); // never resolves
    render(<EvalBaseline />);
    expect(screen.getByText(/Loading/)).toBeInTheDocument();
  });

  it("renders fallback message when fetch returns 500", async () => {
    vi.spyOn(global, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Internal Server Error" }), { status: 500 }),
    );

    render(<EvalBaseline />);

    await waitFor(() => {
      expect(screen.getByText(/No baseline available/)).toBeInTheDocument();
    });
  });
});
