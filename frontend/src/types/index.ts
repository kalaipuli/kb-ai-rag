export interface Citation {
  filename: string;
  page: number | null;
  chunk_index: number;
  score: number;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  timestamp: string;
}

export interface Session {
  id: string;
  created_at: string;
  message_count: number;
}

export interface QueryRequest {
  question: string;
  session_id?: string;
  filters?: QueryFilters;
}

export interface QueryFilters {
  filename?: string;
  file_type?: string;
  tags?: string[];
}

export interface HealthResponse {
  status: string;
  qdrant: string;
  collection_count: number;
}

export interface DonePayload {
  session_id: string;
  confidence: number;
}

export interface StreamEvent {
  type: "token" | "citations" | "done";
  data: string | Citation[] | DonePayload;
}

export interface IngestResponse {
  job_id: string;
  status: string;
  file_count: number;
}

export interface ApiError {
  // domain errors: plain message; 422 validation errors: JSON-stringified list
  detail: string;
}
