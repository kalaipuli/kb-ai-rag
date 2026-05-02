"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChatMessage } from "@/components/ChatMessage";
import { SharedInput } from "@/components/SharedInput";
import { AgentPanel } from "@/components/AgentPanel";
import { AgentVerdict } from "@/components/AgentVerdict";
import { Topbar } from "@/components/Topbar";
import { MetricsBar } from "@/components/MetricsBar";
import { AboutBanner } from "@/components/AboutBanner";
import { CollectionsDrawer } from "@/components/CollectionsDrawer";
import { useStream } from "@/hooks/useStream";
import { useAgentStream } from "@/hooks/useAgentStream";
import { getCollections } from "@/lib/api";
import { emptySuggestions } from "@/lib/config";

interface EvalMetrics {
  faithfulness: number;
  relevancy: number;
  precision: number;
  recall: number;
}

export default function ChatPage(): React.JSX.Element {
  const {
    messages: staticMessages,
    isStreaming: staticStreaming,
    error: staticError,
    submit: submitStatic,
    resetError,
  } = useStream();

  const {
    messages: agentMessages,
    isStreaming: agentStreaming,
    error: agentError,
    submit: submitAgentic,
  } = useAgentStream();

  const isEitherStreaming = staticStreaming || agentStreaming;

  const [metricsOpen, setMetricsOpen] = useState(true);
  const [aboutOpen, setAboutOpen] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    setMetricsOpen(localStorage.getItem('kb_rag_metrics_dismissed') !== 'true');
    setAboutOpen(localStorage.getItem('kb_rag_about_dismissed') !== 'true');
  }, []);

  const handleMetricsDismiss = (): void => {
    setMetricsOpen(false);
    localStorage.setItem('kb_rag_metrics_dismissed', 'true');
  };

  const handleAboutDismiss = (): void => {
    setAboutOpen(false);
    localStorage.setItem('kb_rag_about_dismissed', 'true');
  };

  const [evalMetrics, setEvalMetrics] = useState<EvalMetrics | null>(null);

  useEffect(() => {
    void fetch('/api/proxy/eval/baseline')
      .then((r) => r.ok ? r.json() : null)
      .then((data: unknown) => {
        if (
          data !== null &&
          typeof data === 'object' &&
          'faithfulness' in data &&
          'answer_relevancy' in data &&
          'context_precision' in data &&
          'context_recall' in data
        ) {
          const d = data as Record<string, number>;
          setEvalMetrics({
            faithfulness: d.faithfulness,
            relevancy: d.answer_relevancy,
            precision: d.context_precision,
            recall: d.context_recall,
          });
        }
      })
      .catch(() => { /* no baseline available */ });
  }, []);

  const { data: collectionsData } = useQuery({
    queryKey: ["collections"],
    queryFn: getCollections,
    staleTime: 30_000,
  });

  const collectionsCount = collectionsData?.collections.length ?? 0;
  const totalChunks = collectionsData?.collections.reduce((sum, c) => sum + c.vector_count, 0) ?? 0;

  const handleSubmit = useCallback(
    (query: string): void => {
      void submitStatic(query);
      void submitAgentic(query);
    },
    [submitStatic, submitAgentic],
  );

  const staticBottomRef = useRef<HTMLDivElement>(null);
  const agentBottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    staticBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [staticMessages]);

  useEffect(() => {
    agentBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [agentMessages]);

  return (
    <div className="flex flex-col h-screen" style={{ background: 'var(--surface-base)' }}>
      <AboutBanner isOpen={aboutOpen} onDismiss={handleAboutDismiss} />
      <Topbar
        collectionsCount={collectionsCount}
        totalChunks={totalChunks}
        metricsOpen={metricsOpen}
        onMetricsToggle={() => {
          const next = !metricsOpen;
          setMetricsOpen(next);
          if (!next) {
            localStorage.setItem('kb_rag_metrics_dismissed', 'true');
          } else {
            localStorage.removeItem('kb_rag_metrics_dismissed');
          }
        }}
        onCollectionsOpen={() => setDrawerOpen(true)}
      />
      <MetricsBar metrics={evalMetrics} isOpen={metricsOpen} onDismiss={handleMetricsDismiss} />

      <SharedInput onSubmit={handleSubmit} isDisabled={isEitherStreaming} />

      {!isEitherStreaming && staticMessages.length > 0 && agentMessages.length > 0 && (
        <AgentVerdict staticMessages={staticMessages} agentMessages={agentMessages} />
      )}

      <main className="grid grid-cols-1 md:grid-cols-2 flex-1 overflow-hidden">
        {/* Static Chain panel */}
        <div
          className="flex flex-col overflow-hidden"
          style={{ borderTop: '3px solid var(--static-chain)', borderRight: '1px solid var(--border-subtle)' }}
        >
          <div className="flex items-center gap-2 px-4 py-3" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
            <span>⚡</span>
            <span className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>Static Chain</span>
            {staticStreaming && (
              <span
                className="animate-pulse-dot w-2 h-2 rounded-full ml-1"
                style={{ background: 'var(--static-chain)', display: 'inline-block' }}
              />
            )}
            <span className="text-xs ml-auto" style={{ color: 'var(--text-muted)' }}>
              Phase 1 — BM25 + Dense Retrieval
            </span>
          </div>
          <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
            {staticMessages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full gap-4 px-4">
                <p className="text-sm text-center" style={{ color: 'var(--text-muted)' }}>
                  BM25 hybrid retrieval + single-pass generation
                </p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {emptySuggestions.static.map((s) => (
                    <button
                      key={s}
                      onClick={() => handleSubmit(s)}
                      className="px-3 py-1.5 rounded-full text-xs"
                      style={{
                        background: 'var(--surface-overlay)',
                        color: 'var(--text-secondary)',
                        border: '1px solid var(--border-subtle)',
                      }}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {staticMessages.map((msg) => (
                  <ChatMessage key={msg.id} message={msg} accentColor="static" />
                ))}
                <div ref={staticBottomRef} />
              </>
            )}
          </div>
          {staticError && (
            <div className="mx-4 mb-4 flex items-center justify-between rounded-lg px-3 py-2 text-xs"
              style={{ background: 'var(--status-danger)', color: 'var(--text-primary)' }}>
              <span>{staticError.message}</span>
              <button onClick={resetError} className="ml-4 font-medium underline">Dismiss</button>
            </div>
          )}
        </div>

        {/* Agentic Pipeline panel */}
        <div
          className="flex flex-col overflow-hidden"
          style={{ borderTop: '3px solid var(--agentic)' }}
        >
          <div className="flex items-center gap-2 px-4 py-3" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
            <span>🔮</span>
            <span className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>Agentic Pipeline</span>
            {agentStreaming && (
              <span
                className="animate-pulse-dot w-2 h-2 rounded-full ml-1"
                style={{ background: 'var(--agentic)', display: 'inline-block' }}
              />
            )}
            <span className="text-xs ml-auto" style={{ color: 'var(--text-muted)' }}>
              Phase 2 — Router → Grader → Critic
            </span>
          </div>
          <div className="flex-1 overflow-y-auto">
            {agentMessages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full gap-4 px-4">
                <p className="text-sm text-center" style={{ color: 'var(--text-muted)' }}>
                  Router → Retriever → Grader → Generator → Critic
                </p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {emptySuggestions.agentic.map((s) => (
                    <button
                      key={s}
                      onClick={() => handleSubmit(s)}
                      className="px-3 py-1.5 rounded-full text-xs"
                      style={{
                        background: 'var(--surface-overlay)',
                        color: 'var(--text-secondary)',
                        border: '1px solid var(--border-subtle)',
                      }}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <AgentPanel
                messages={agentMessages}
                isStreaming={agentStreaming}
                error={agentError}
              />
            )}
          </div>
        </div>
      </main>

      <CollectionsDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        collections={collectionsData?.collections ?? []}
        onIngest={() => {}}
      />
    </div>
  );
}
