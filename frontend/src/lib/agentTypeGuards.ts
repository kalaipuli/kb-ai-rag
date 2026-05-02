import type {
  AgentStep,
  CriticStepPayload,
  GeneratorStepPayload,
  GraderStepPayload,
  RetrieverStepPayload,
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
  return "web_fallback_used" in payload;
}

export function isCriticPayload(
  payload: AgentStep["payload"],
): payload is CriticStepPayload {
  return "critic_score" in payload;
}

export function isRetrieverPayload(
  payload: AgentStep["payload"],
): payload is RetrieverStepPayload {
  return "docs_retrieved" in payload;
}

export function isGeneratorPayload(
  payload: AgentStep["payload"],
): payload is GeneratorStepPayload {
  return "docs_used" in payload;
}
