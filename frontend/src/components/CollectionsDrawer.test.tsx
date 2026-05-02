import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CollectionsDrawer } from "./CollectionsDrawer";

// Mock the API module
vi.mock("@/lib/api", () => ({
  getCollections: vi.fn().mockResolvedValue({
    collections: [
      { name: "test-collection", document_count: 5, vector_count: 100 },
    ],
  }),
  triggerIngest: vi.fn().mockResolvedValue({ message: "Ingest started" }),
}));

function wrapper({ children }: { children: React.ReactNode }): React.JSX.Element {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

describe("CollectionsDrawer", () => {
  it("drawer is not visible when isOpen is false", () => {
    const { container } = render(
      <CollectionsDrawer isOpen={false} onClose={vi.fn()} collections={[]} onIngest={vi.fn()} />,
      { wrapper },
    );
    // No backdrop when closed
    expect(container.querySelector('[aria-label="Close collections drawer"]')).not.toBeInTheDocument();
  });

  it("drawer is visible when isOpen is true", () => {
    render(
      <CollectionsDrawer isOpen={true} onClose={vi.fn()} collections={[]} onIngest={vi.fn()} />,
      { wrapper },
    );
    expect(screen.getByText("Collections")).toBeInTheDocument();
  });

  it("backdrop click calls onClose", async () => {
    const onClose = vi.fn();
    render(
      <CollectionsDrawer isOpen={true} onClose={onClose} collections={[]} onIngest={vi.fn()} />,
      { wrapper },
    );
    const backdrop = screen.getByLabelText("Close collections drawer");
    await userEvent.click(backdrop);
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("renders Trigger Ingest button", () => {
    render(
      <CollectionsDrawer isOpen={true} onClose={vi.fn()} collections={[]} onIngest={vi.fn()} />,
      { wrapper },
    );
    expect(screen.getByText("Trigger Ingest")).toBeInTheDocument();
  });

  it("close button in header calls onClose", async () => {
    const onClose = vi.fn();
    render(
      <CollectionsDrawer isOpen={true} onClose={onClose} collections={[]} onIngest={vi.fn()} />,
      { wrapper },
    );
    await userEvent.click(screen.getByLabelText("Close"));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
