export interface Citation {
  chunk_id: string;
  filename: string;
  source_path: string;
  page_number: number | null;
  retrieval_score?: number;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  confidence?: number;
  chunksRetrieved?: number;
  timestamp: string;
}

export interface QueryRequest {
  query: string;
  filters?: Record<string, string> | null;
  k?: number | null;
}

export interface TokenEvent {
  type: "token";
  content: string;
}

export interface CitationsEvent {
  type: "citations";
  citations: Citation[];
  confidence: number;
  chunks_retrieved: number;
}

export interface DoneEvent {
  type: "done";
}

export type StreamEvent = TokenEvent | CitationsEvent | DoneEvent;

export interface IngestAcceptedResponse {
  status: string;
  message: string;
}

export interface CollectionInfo {
  name: string;
  document_count: number;
  vector_count: number;
}

export interface CollectionsResponse {
  collections: CollectionInfo[];
}

// --- Phase 2: Agentic Pipeline SSE Types ---

export type AgentStepNode = "router" | "retriever" | "grader" | "generator" | "critic";

export interface RouterStepPayload {
  query_type: "factual" | "analytical" | "multi_hop" | "ambiguous";
  strategy: "dense" | "hybrid" | "web";
  duration_ms: number;
}

export interface RetrieverStepPayload {
  strategy: "dense" | "hybrid" | "web";
  docs_retrieved: number;
  duration_ms: number;
}

export interface GraderStepPayload {
  scores: number[];
  web_fallback_used: boolean;
  duration_ms: number;
}

export interface GeneratorStepPayload {
  docs_used: number;
  confidence: number;
  duration_ms: number;
}

export interface CriticStepPayload {
  critic_score: number;
  reruns: number;
  duration_ms: number;
}

export interface AgentStepEvent {
  type: "agent_step";
  node: AgentStepNode;
  run: number;
  payload: RouterStepPayload | RetrieverStepPayload | GraderStepPayload | GeneratorStepPayload | CriticStepPayload;
}

export type AgentStreamEvent = StreamEvent | AgentStepEvent;

export interface AgentStep {
  node: AgentStepNode;
  payload: RouterStepPayload | RetrieverStepPayload | GraderStepPayload | GeneratorStepPayload | CriticStepPayload;
  timestamp: string;
}

export interface AgentMessage extends Message {
  agentSteps?: AgentStep[];
}
