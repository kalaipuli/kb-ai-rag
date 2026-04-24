export interface Citation {
  chunk_id: string;
  filename: string;
  source_path: string;
  page_number: number | null;
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

