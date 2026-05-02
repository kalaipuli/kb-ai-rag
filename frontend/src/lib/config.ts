export const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
export const API_KEY = process.env.API_KEY ?? "";

export const emptySuggestions = {
  static: [
    "What is the escalation policy for critical incidents?",
    "Summarise the onboarding process",
  ],
  agentic: [
    "Compare the SLA tiers across enterprise plans",
    "What changed in the last policy update?",
  ],
} as const;
