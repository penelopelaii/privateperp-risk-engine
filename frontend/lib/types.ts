/**
 * Mirrors the Pydantic models in `risk_engine/inputs.py`.
 *
 * Kept in sync by hand: the models are small and stable enough that generating
 * them from the OpenAPI schema is not yet worth the build step.
 */

export interface RiskInputs {
  liquidity_score: number;
  oracle_confidence: number;
  price_staleness_days: number;
  oracle_dispersion: number;
  jump_risk: number;
  hedgeability_score: number;
  event_proximity: number;
  current_open_interest: number;
  market_depth: number;
}

export interface RiskOutputs {
  risk_score: number;
  recommended_max_leverage: number;
  initial_margin: number;
  maintenance_margin: number;
  position_limit: number;
  open_interest_cap: number;
  liquidation_buffer: number;
  score_breakdown: Record<string, number>;
  engine_version: string;
}

export interface RiskEvaluationResponse {
  inputs: RiskInputs;
  outputs: RiskOutputs;
}
