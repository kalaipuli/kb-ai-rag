import { describe, expect, it } from "vitest";
import {
  isCriticPayload,
  isGeneratorPayload,
  isGraderPayload,
  isRetrieverPayload,
  isRouterPayload,
} from "@/lib/agentTypeGuards";
import type {
  CriticStepPayload,
  GeneratorStepPayload,
  GraderStepPayload,
  RetrieverStepPayload,
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

const retrieverPayload: RetrieverStepPayload = {
  strategy: "hybrid",
  docs_retrieved: 5,
  duration_ms: 78,
};

const generatorPayload: GeneratorStepPayload = {
  docs_used: 3,
  confidence: 0.85,
  duration_ms: 150,
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

describe("isRetrieverPayload", () => {
  it("returns true for a RetrieverStepPayload", () => {
    expect(isRetrieverPayload(retrieverPayload)).toBe(true);
  });

  it("returns false for a RouterStepPayload", () => {
    expect(isRetrieverPayload(routerPayload)).toBe(false);
  });

  it("returns false for a GraderStepPayload", () => {
    expect(isRetrieverPayload(graderPayload)).toBe(false);
  });

  it("returns false for a CriticStepPayload", () => {
    expect(isRetrieverPayload(criticPayload)).toBe(false);
  });
});

describe("isGeneratorPayload", () => {
  it("returns true for a GeneratorStepPayload", () => {
    expect(isGeneratorPayload(generatorPayload)).toBe(true);
  });

  it("returns false for a RouterStepPayload", () => {
    expect(isGeneratorPayload(routerPayload)).toBe(false);
  });

  it("returns false for a GraderStepPayload", () => {
    expect(isGeneratorPayload(graderPayload)).toBe(false);
  });

  it("returns false for a CriticStepPayload", () => {
    expect(isGeneratorPayload(criticPayload)).toBe(false);
  });
});
