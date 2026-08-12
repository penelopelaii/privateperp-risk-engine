import type { RiskEvaluationResponse, RiskInputs } from "./types";
import type {
  FrontierV1Response,
  MarketState,
  RiskEvaluationV1Response,
} from "./typesV1";

// Trailing slashes are stripped because paths are appended directly below, and
// a base URL ending in "/" would produce "//risk/v1/evaluate", which the API
// answers with a 404. Pasting a URL with its trailing slash from a hosting
// dashboard is the obvious way to configure this wrong.
const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000"
).replace(/\/+$/, "");

export async function evaluateRisk(
  inputs: RiskInputs,
  signal?: AbortSignal,
): Promise<RiskEvaluationResponse> {
  const response = await fetch(`${API_BASE_URL}/risk/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ inputs }),
    signal,
  });

  if (!response.ok) {
    throw new Error(`Risk evaluation failed (${response.status})`);
  }

  return response.json();
}

export async function evaluateRiskV1(
  state: MarketState,
  signal?: AbortSignal,
): Promise<RiskEvaluationV1Response> {
  const response = await fetch(`${API_BASE_URL}/risk/v1/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ state }),
    signal,
  });

  if (!response.ok) {
    throw new Error(`v1 risk evaluation failed (${response.status})`);
  }

  return response.json();
}

export async function evaluateFrontierV1(
  state: MarketState,
  signal?: AbortSignal,
): Promise<FrontierV1Response> {
  const response = await fetch(`${API_BASE_URL}/risk/v1/frontier`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ state }),
    signal,
  });

  if (!response.ok) {
    throw new Error(`v1 frontier evaluation failed (${response.status})`);
  }

  return response.json();
}
