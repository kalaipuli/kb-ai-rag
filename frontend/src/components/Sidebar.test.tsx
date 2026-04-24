import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Sidebar } from "./Sidebar";
import * as api from "@/lib/api";

function renderWithQuery(ui: React.ReactElement): ReturnType<typeof render> {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("Sidebar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders collection name and counts", async () => {
    vi.spyOn(api, "getCollections").mockResolvedValue({
      collections: [{ name: "knowledge_base", document_count: 42, vector_count: 168 }],
    });

    renderWithQuery(<Sidebar />);

    await waitFor(() => {
      expect(screen.getByText("knowledge_base")).toBeInTheDocument();
      expect(screen.getByText(/42/)).toBeInTheDocument();
    });
  });

  it("renders empty state when no collections", async () => {
    vi.spyOn(api, "getCollections").mockResolvedValue({ collections: [] });

    renderWithQuery(<Sidebar />);

    await waitFor(() => {
      expect(screen.getByText(/No collections indexed/)).toBeInTheDocument();
    });
  });

  it("shows loading state during ingest", async () => {
    vi.spyOn(api, "getCollections").mockResolvedValue({ collections: [] });
    vi.spyOn(api, "triggerIngest").mockImplementation(
      () => new Promise(() => {}), // never resolves — simulates in-flight request
    );

    renderWithQuery(<Sidebar />);
    await waitFor(() => screen.getByText(/Trigger Ingest/));

    await userEvent.click(screen.getByText(/Trigger Ingest/));
    expect(screen.getByText(/Ingesting/)).toBeInTheDocument();
  });

  it("shows success message after ingest completes", async () => {
    vi.spyOn(api, "getCollections").mockResolvedValue({ collections: [] });
    vi.spyOn(api, "triggerIngest").mockResolvedValue({
      status: "accepted",
      message: "Ingestion started",
    });

    renderWithQuery(<Sidebar />);
    await waitFor(() => screen.getByText(/Trigger Ingest/));

    await userEvent.click(screen.getByText(/Trigger Ingest/));
    await waitFor(() => {
      expect(screen.getByText("Ingestion started")).toBeInTheDocument();
    });
  });

  it("shows error message on ingest failure (error path)", async () => {
    vi.spyOn(api, "getCollections").mockResolvedValue({ collections: [] });
    vi.spyOn(api, "triggerIngest").mockRejectedValue(new Error("Ingest failed: 503"));

    renderWithQuery(<Sidebar />);
    await waitFor(() => screen.getByText(/Trigger Ingest/));

    await userEvent.click(screen.getByText(/Trigger Ingest/));
    await waitFor(() => {
      expect(screen.getByText(/Error: Ingest failed: 503/)).toBeInTheDocument();
    });
  });
});
