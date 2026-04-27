import type {
  AgentStep,
  CriticStepPayload,
  GraderStepPayload,
  RouterStepPayload,
} from "@/types";

export function isRouterPayload(
  payload: AgentStep["payload"],
): payload is RouterStepPayload {
  return "query_type" in payload;
}

export function isGraderPayload(
  payload: AgentStep["payload"],
): payload is GraderStepPayload {
  return "web_fallback" in payload;
}

export function isCriticPayload(
  payload: AgentStep["payload"],
): payload is CriticStepPayload {
  return "hallucination_risk" in payload;
}
