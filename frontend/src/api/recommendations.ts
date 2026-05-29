import { apiGet, type ListResponse } from "./client";

export type RecommendationItem = {
  ts_code: string;
  name: string | null;
  industry: string | null;
  market: string | null;
  trade_date: string;
  final_score: number | string | null;
  recommendation_level: string;
  rank_no: number | null;
  quality_score: number | string | null;
  growth_score: number | string | null;
  valuation_score: number | string | null;
  momentum_score: number | string | null;
  capital_flow_score: number | string | null;
  leadership_score: number | string | null;
  risk_penalty: number | string | null;
  summary: string | null;
  risk_warning: string | null;
  formula_version: string | null;
};

export async function fetchRecommendations(tradeDate?: string, limit = 50): Promise<ListResponse<RecommendationItem>> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (tradeDate) {
    params.set("trade_date", tradeDate);
  }
  return apiGet<ListResponse<RecommendationItem>>(`/api/recommendations?${params.toString()}`);
}
