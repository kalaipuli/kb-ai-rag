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

export type AgentStepNode = "router" | "grader" | "critic";

export interface RouterStepPayload {
  query_type: "factual" | "analytical" | "multi_hop" | "ambiguous";
  strategy: "dense" | "hybrid" | "web";
  duration_ms: number;
}

export interface GraderStepPayload {
  scores: number[];
  web_fallback: boolean;
  duration_ms: number;
}

export interface CriticStepPayload {
  hallucination_risk: number;
  reruns: number;
  duration_ms: number;
}

export interface AgentStepEvent {
  type: "agent_step";
  node: AgentStepNode;
  payload: RouterStepPayload | GraderStepPayload | CriticStepPayload;
}

export type AgentStreamEvent = StreamEvent | AgentStepEvent;

export interface AgentStep {
  node: AgentStepNode;
  payload: RouterStepPayload | GraderStepPayload | CriticStepPayload;
  timestamp: string;
}

export interface AgentMessage extends Message {
  agentSteps?: AgentStep[];
}
