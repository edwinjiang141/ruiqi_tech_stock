import { apiGet, apiPost, type ListResponse } from "./client";
import type { CollectionResult } from "./collections";

export type FactorScore = {
  ts_code: string;
  name: string | null;
  industry: string | null;
  market: string | null;
  trade_date: string;
  quality_score: number | string | null;
  growth_score: number | string | null;
  valuation_score: number | string | null;
  momentum_score: number | string | null;
  capital_flow_score: number | string | null;
  leadership_score: number | string | null;
  risk_penalty: number | string | null;
  final_score: number | string | null;
  rank_in_universe: number | null;
  rank_in_industry: number | null;
  recommendation_level: string | null;
  formula_version: string | null;
};

export type FactorScoreHistoryItem = {
  trade_date: string;
  factor_score_count: number;
  recommendation_count: number;
};

export async function fetchFactorScores(tradeDate?: string, limit = 50): Promise<ListResponse<FactorScore>> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (tradeDate) {
    params.set("trade_date", tradeDate);
  }
  return apiGet<ListResponse<FactorScore>>(`/api/factors?${params.toString()}`);
}

export async function fetchFactorScoreHistory(limit = 10, offset = 0): Promise<ListResponse<FactorScoreHistoryItem>> {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  return apiGet<ListResponse<FactorScoreHistoryItem>>(`/api/factors/history?${params.toString()}`);
}

export async function triggerFactorCalculation(tradeDate: string, topN = 50): Promise<CollectionResult> {
  return apiPost<CollectionResult>(`/api/factors/calculate?trade_date=${encodeURIComponent(tradeDate)}&top_n=${topN}`);
}
