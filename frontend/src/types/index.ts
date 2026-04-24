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
  confidence?: number;
  timestamp: string;
}

export interface QueryRequest {
  question: string;
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

export interface ApiError {
  // domain errors: plain message; 422 validation errors: JSON-stringified list
  detail: string;
}
