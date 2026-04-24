"use client";

import { useCallback, useReducer } from "react";
import type { Citation, Message, StreamEvent } from "@/types";
import { streamQuery } from "@/lib/streaming";

interface StreamState {
  messages: Message[];
  isStreaming: boolean;
  error: Error | null;
}

type StreamAction =
  | { type: "SUBMIT"; userMessage: Message; assistantMessage: Message }
  | { type: "TOKEN"; token: string }
  | { type: "CITATIONS"; citations: Citation[] }
  | { type: "DONE"; confidence: number }
  | { type: "STREAM_END" }
  | { type: "ERROR"; error: Error }
  | { type: "RESET_ERROR" };

function streamReducer(state: StreamState, action: StreamAction): StreamState {
  switch (action.type) {
    case "SUBMIT":
      return {
        ...state,
        messages: [...state.messages, action.userMessage, action.assistantMessage],
        isStreaming: true,
        error: null,
      };
    case "TOKEN": {
      const messages = [...state.messages];
      const last = messages[messages.length - 1];
      if (last?.role === "assistant") {
        messages[messages.length - 1] = {
          ...last,
          content: last.content + action.token,
        };
      }
      return { ...state, messages };
    }
    case "CITATIONS": {
      const messages = [...state.messages];
      const last = messages[messages.length - 1];
      if (last?.role === "assistant") {
        messages[messages.length - 1] = { ...last, citations: action.citations };
      }
      return { ...state, messages };
    }
    case "DONE": {
      const messages = [...state.messages];
      const last = messages[messages.length - 1];
      if (last?.role === "assistant") {
        messages[messages.length - 1] = { ...last, confidence: action.confidence };
      }
      return { ...state, messages, isStreaming: false };
    }
    case "STREAM_END":
      return { ...state, isStreaming: false };
    case "ERROR":
      return { ...state, isStreaming: false, error: action.error };
    case "RESET_ERROR":
      return { ...state, error: null };
    default:
      return state;
  }
}

export interface UseStreamReturn {
  messages: Message[];
  isStreaming: boolean;
  error: Error | null;
  submit: (question: string) => Promise<void>;
  resetError: () => void;
}

export function useStream(): UseStreamReturn {
  const [state, dispatch] = useReducer(streamReducer, {
    messages: [],
    isStreaming: false,
    error: null,
  });

  const submit = useCallback(async (question: string): Promise<void> => {
    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: question,
      timestamp: new Date().toISOString(),
    };
    const assistantMessage: Message = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      timestamp: new Date().toISOString(),
    };

    dispatch({ type: "SUBMIT", userMessage, assistantMessage });

    for await (const event of streamQuery(
      { question },
      (err) => dispatch({ type: "ERROR", error: err }),
    )) {
      handleEvent(event, dispatch);
    }
    // Reset isStreaming if no done event arrived (e.g. empty stream or error path)
    dispatch({ type: "STREAM_END" });
  }, []);

  const resetError = useCallback(() => dispatch({ type: "RESET_ERROR" }), []);

  return { ...state, submit, resetError };
}

function handleEvent(
  event: StreamEvent,
  dispatch: React.Dispatch<StreamAction>,
): void {
  if (event.type === "token") {
    dispatch({ type: "TOKEN", token: event.data as string });
  } else if (event.type === "citations") {
    dispatch({ type: "CITATIONS", citations: event.data as Citation[] });
  } else if (event.type === "done") {
    const payload = event.data as { confidence: number };
    dispatch({ type: "DONE", confidence: payload.confidence });
  }
}
