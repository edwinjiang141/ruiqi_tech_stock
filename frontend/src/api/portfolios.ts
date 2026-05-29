import { apiGet, apiPost, type ListResponse } from "./client";

export type PortfolioSummary = {
  portfolio_id: string;
  name: string;
  score_date: string;
  start_date: string;
  end_date: string;
  stock_count: number;
  initial_cash: number;
  final_value: number;
  cumulative_return: number;
  benchmark_return: number;
  excess_return: number;
  max_drawdown: number;
  benchmark_name: string;
  benchmark_source: string;
  conclusion: string;
  created_at: string;
};

export type PortfolioHolding = {
  ts_code: string;
  name: string;
  industry: string;
  market: string;
  score: number;
  recommendation_level: string;
  weight: number;
  quantity: number;
  buy_price: number;
  current_price: number;
  market_value: number;
  return_rate: number;
  reason: string;
};

export type PortfolioNavPoint = {
  trade_date: string;
  portfolio_value: number;
  portfolio_return: number;
  benchmark_return: number;
  excess_return: number;
};

export type PortfolioResult = PortfolioSummary & {
  min_score: number;
  benchmark_code: string;
  holdings: PortfolioHolding[];
  nav: PortfolioNavPoint[];
};

export type PortfolioRunPayload = {
  score_date: string;
  end_date: string;
  stock_count: number;
  initial_cash: number;
  min_score: number;
  benchmark_code: string;
};

export async function fetchPortfolios(): Promise<ListResponse<PortfolioSummary>> {
  return apiGet<ListResponse<PortfolioSummary>>("/api/portfolios");
}

export async function fetchPortfolio(portfolioId: string): Promise<PortfolioResult> {
  return apiGet<PortfolioResult>(`/api/portfolios/${encodeURIComponent(portfolioId)}`);
}

export async function runPortfolio(payload: PortfolioRunPayload): Promise<PortfolioResult> {
  return apiPost<PortfolioResult>("/api/portfolios/run", payload);
}
