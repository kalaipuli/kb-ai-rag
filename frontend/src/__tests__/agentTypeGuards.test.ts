import { describe, expect, it } from "vitest";
import {
  isCriticPayload,
  isGraderPayload,
  isRouterPayload,
} from "@/lib/agentTypeGuards";
import type {
  CriticStepPayload,
  GraderStepPayload,
  RouterStepPayload,
} from "@/types";

const routerPayload: RouterStepPayload = {
  query_type: "factual",
  strategy: "dense",
  duration_ms: 12,
};

const graderPayload: GraderStepPayload = {
  scores: [0.9, 0.7],
  web_fallback: false,
  duration_ms: 34,
};

const criticPayload: CriticStepPayload = {
  hallucination_risk: 0.2,
  reruns: 0,
  duration_ms: 56,
};

describe("isRouterPayload", () => {
  it("returns true for a RouterStepPayload", () => {
    expect(isRouterPayload(routerPayload)).toBe(true);
  });

  it("returns false for a GraderStepPayload", () => {
    expect(isRouterPayload(graderPayload)).toBe(false);
  });

  it("returns false for a CriticStepPayload", () => {
    expect(isRouterPayload(criticPayload)).toBe(false);
  });
});

describe("isGraderPayload", () => {
  it("returns true for a GraderStepPayload", () => {
    expect(isGraderPayload(graderPayload)).toBe(true);
  });

  it("returns false for a RouterStepPayload", () => {
    expect(isGraderPayload(routerPayload)).toBe(false);
  });

  it("returns false for a CriticStepPayload", () => {
    expect(isGraderPayload(criticPayload)).toBe(false);
  });
});

describe("isCriticPayload", () => {
  it("returns true for a CriticStepPayload", () => {
    expect(isCriticPayload(criticPayload)).toBe(true);
  });

  it("returns false for a RouterStepPayload", () => {
    expect(isCriticPayload(routerPayload)).toBe(false);
  });

  it("returns false for a GraderStepPayload", () => {
    expect(isCriticPayload(graderPayload)).toBe(false);
  });
});
