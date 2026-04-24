"use client";

import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Database, RefreshCw, AlertCircle } from "lucide-react";
import { clsx } from "clsx";
import { getCollections, triggerIngest } from "@/lib/api";

export function Sidebar(): React.JSX.Element {
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
    <aside className="flex w-64 flex-shrink-0 flex-col gap-4 border-r border-gray-200 bg-gray-50 p-4">
      <div>
        <h2 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
          <Database size={14} />
          Collections
        </h2>

        {isLoading && (
          <p className="mt-2 text-xs text-gray-400">Loading…</p>
        )}

        {error && (
          <p className="mt-2 flex items-center gap-1 text-xs text-red-500">
            <AlertCircle size={12} />
            Failed to load
          </p>
        )}

        {data && (
          <ul className="mt-2 space-y-2">
            {data.collections.map((col) => (
              <li key={col.name} className="rounded-lg bg-white p-2 shadow-sm">
                <p className="truncate text-xs font-medium text-gray-800">{col.name}</p>
                <p className="text-xs text-gray-500">
                  {col.document_count.toLocaleString()} docs ·{" "}
                  {col.vector_count.toLocaleString()} vectors
                </p>
              </li>
            ))}
            {data.collections.length === 0 && (
              <li className="text-xs text-gray-400">No collections indexed yet.</li>
            )}
          </ul>
        )}
      </div>

      <div className="mt-auto">
        <button
          onClick={() => {
            setIngestMessage(null);
            runIngest();
          }}
          disabled={isIngesting}
          className={clsx(
            "flex w-full items-center justify-center gap-2 rounded-xl px-3 py-2 text-xs font-medium transition-colors",
            isIngesting
              ? "cursor-not-allowed bg-gray-200 text-gray-400"
              : "bg-blue-600 text-white hover:bg-blue-700",
          )}
        >
          <RefreshCw size={12} className={clsx(isIngesting && "animate-spin")} />
          {isIngesting ? "Ingesting…" : "Trigger Ingest"}
        </button>

        {ingestMessage && (
          <p className="mt-2 text-xs text-gray-500">{ingestMessage}</p>
        )}
      </div>
    </aside>
  );
}
