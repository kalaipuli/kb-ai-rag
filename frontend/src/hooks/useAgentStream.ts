"use client";

import { useCallback, useReducer } from "react";
import type { Dispatch } from "react";
import type { AgentMessage, AgentStep, AgentStreamEvent, Citation, QueryRequest } from "@/types";
import { streamAgentQuery } from "@/lib/streaming";

const SESSION_STORAGE_KEY = "kb_rag_session_id";

const generateUUID = (): string => {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return generateUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
};

function getOrCreateSessionId(): string {
  try {
    const existing = sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (existing) return existing;
    const id = generateUUID();
    sessionStorage.setItem(SESSION_STORAGE_KEY, id);
    return id;
  } catch {
    // sessionStorage not available (e.g. SSR)
    return generateUUID();
  }
}

interface AgentStreamState {
  messages: AgentMessage[];
  isStreaming: boolean;
  error: Error | null;
  sessionId: string;
}

type AgentStreamAction =
  | { type: "SUBMIT"; userMessage: AgentMessage; assistantMessage: AgentMessage }
  | { type: "AGENT_STEP"; step: AgentStep }
  | { type: "TOKEN"; token: string }
  | { type: "CITATIONS"; citations: Citation[]; confidence: number; chunksRetrieved: number }
  | { type: "DONE" }
  | { type: "STREAM_END" }
  | { type: "ERROR"; error: Error };

function agentStreamReducer(
  state: AgentStreamState,
  action: AgentStreamAction,
): AgentStreamState {
  switch (action.type) {
    case "SUBMIT":
      return {
        ...state,
        messages: [...state.messages, action.userMessage, action.assistantMessage],
        isStreaming: true,
        error: null,
      };
    case "AGENT_STEP": {
      const messages = [...state.messages];
      const last = messages[messages.length - 1];
      if (last?.role === "assistant") {
        const existingSteps = last.agentSteps ?? [];
        messages[messages.length - 1] = {
          ...last,
          agentSteps: [...existingSteps, action.step],
        };
      }
      return { ...state, messages };
    }
    case "TOKEN": {
      const messages = [...state.messages];
      const last = messages[messages.length - 1];
      if (last?.role === "assistant") {
        messages[messages.length - 1] = { ...last, content: last.content + action.token };
      }
      return { ...state, messages };
    }
    case "CITATIONS": {
      const messages = [...state.messages];
      const last = messages[messages.length - 1];
      if (last?.role === "assistant") {
        messages[messages.length - 1] = {
          ...last,
          citations: action.citations,
          confidence: action.confidence,
          chunksRetrieved: action.chunksRetrieved,
        };
      }
      return { ...state, messages };
    }
    case "DONE":
      return { ...state, isStreaming: false };
    case "STREAM_END":
      return { ...state, isStreaming: false };
    case "ERROR":
      return { ...state, isStreaming: false, error: action.error };
    default:
      return state;
  }
}

export interface UseAgentStreamReturn {
  messages: AgentMessage[];
  isStreaming: boolean;
  error: Error | null;
  sessionId: string;
  submit: (query: string) => Promise<void>;
}

export function useAgentStream(): UseAgentStreamReturn {
  const [state, dispatch] = useReducer(agentStreamReducer, undefined, () => ({
    messages: [],
    isStreaming: false,
    error: null,
    sessionId: getOrCreateSessionId(),
  }));

  const submit = useCallback(
    async (query: string): Promise<void> => {
      if (state.isStreaming) return;

      const userMessage: AgentMessage = {
        id: generateUUID(),
        role: "user",
        content: query,
        timestamp: new Date().toISOString(),
      };
      const assistantMessage: AgentMessage = {
        id: generateUUID(),
        role: "assistant",
        content: "",
        timestamp: new Date().toISOString(),
        agentSteps: [],
      };
      dispatch({ type: "SUBMIT", userMessage, assistantMessage });

      let hadError = false;

      for await (const event of streamAgentQuery(
        { query } as QueryRequest,
        state.sessionId,
        (err) => {
          hadError = true;
          dispatch({ type: "ERROR", error: err });
        },
      )) {
        if (!hadError) {
          handleEvent(event, dispatch);
        }
      }

      if (!hadError) {
        dispatch({ type: "STREAM_END" });
      }
    },
    [state.isStreaming, state.sessionId],
  );

  return {
    messages: state.messages,
    isStreaming: state.isStreaming,
    error: state.error,
    sessionId: state.sessionId,
    submit,
  };
}

function handleEvent(
  event: AgentStreamEvent,
  dispatch: Dispatch<AgentStreamAction>,
): void {
  if (event.type === "agent_step") {
    const step: AgentStep = {
      node: event.node,
      payload: event.payload,
      timestamp: new Date().toISOString(),
    };
    dispatch({ type: "AGENT_STEP", step });
  } else if (event.type === "token") {
    dispatch({ type: "TOKEN", token: event.content });
  } else if (event.type === "citations") {
    dispatch({
      type: "CITATIONS",
      citations: event.citations,
      confidence: event.confidence,
      chunksRetrieved: event.chunks_retrieved,
    });
  } else if (event.type === "done") {
    dispatch({ type: "DONE" });
  }
}
