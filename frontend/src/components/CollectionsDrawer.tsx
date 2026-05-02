"use client";

import { useState } from "react";
import type { JSX } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { getCollections, triggerIngest } from "@/lib/api";

interface CollectionsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  collections: Array<{ name: string; document_count: number; vector_count: number }>;
  onIngest: () => void;
}

export function CollectionsDrawer({ isOpen, onClose }: CollectionsDrawerProps): JSX.Element | null {
  const [ingestMessage, setIngestMessage] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["collections"],
    queryFn: getCollections,
    staleTime: 30_000,
  });

  const { mutate: runIngest, isPending: isIngesting } = useMutation({
    mutationFn: triggerIngest,
    onSuccess: (res) => setIngestMessage(res.message),
    onError: (err: Error) => setIngestMessage(`Error: ${err.message}`),
  });

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40"
          style={{ background: 'rgba(0,0,0,0.5)' }}
          onClick={onClose}
          aria-label="Close collections drawer"
        />
      )}

      {/* Drawer */}
      <div
        className="fixed top-0 left-0 h-full z-50 flex flex-col"
        style={{
          width: '320px',
          background: 'var(--surface-raised)',
          borderRight: '1px solid var(--border-default)',
          transform: isOpen ? 'translateX(0)' : 'translateX(-100%)',
          transition: 'transform 250ms ease-out',
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-4 py-3"
          style={{ borderBottom: '1px solid var(--border-subtle)' }}
        >
          <span className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>Collections</span>
          <button
            onClick={onClose}
            aria-label="Close"
            className="text-lg"
            style={{ color: 'var(--text-muted)' }}
          >
            ×
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {isLoading && <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Loading…</p>}
          {error && <p className="text-xs" style={{ color: 'var(--status-danger)' }}>Failed to load collections</p>}
          {data && (
            <ul className="space-y-2">
              {data.collections.map((col) => (
                <li
                  key={col.name}
                  className="rounded-lg p-2"
                  style={{ background: 'var(--surface-overlay)', border: '1px solid var(--border-subtle)' }}
                >
                  <p className="truncate text-xs font-medium" style={{ color: 'var(--text-primary)' }}>{col.name}</p>
                  <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                    {col.document_count.toLocaleString()} docs · {col.vector_count.toLocaleString()} vectors
                  </p>
                </li>
              ))}
              {data.collections.length === 0 && (
                <li className="text-xs" style={{ color: 'var(--text-muted)' }}>No collections indexed yet.</li>
              )}
            </ul>
          )}
        </div>

        {/* Footer — ingest button */}
        <div className="p-4" style={{ borderTop: '1px solid var(--border-subtle)' }}>
          <button
            onClick={() => {
              setIngestMessage(null);
              runIngest();
            }}
            disabled={isIngesting}
            className="flex w-full items-center justify-center gap-2 rounded-xl px-3 py-2 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50"
            style={{
              background: isIngesting ? 'var(--surface-overlay)' : 'var(--accent-primary)',
              color: isIngesting ? 'var(--text-muted)' : 'white',
            }}
          >
            {isIngesting ? "Ingesting…" : "Trigger Ingest"}
          </button>
          {ingestMessage && (
            <p className="mt-2 text-xs" style={{ color: 'var(--text-muted)' }}>{ingestMessage}</p>
          )}
        </div>
      </div>
    </>
  );
}
