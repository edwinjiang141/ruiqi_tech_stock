import { apiGet, apiPost, type ListResponse } from "./client";

export type SimulationMetric = {
  name: string;
  value: number | string;
  description: string;
};

export type SimulationRunSummary = {
  strategy_version: string;
  start_date: string;
  end_date: string;
  stock_count: number;
  initial_cash: number;
  final_value: number;
  cumulative_return: number;
  max_drawdown: number;
  win_rate: number;
  conclusion: string;
  created_at: string;
};

export type SimulationHolding = {
  ts_code: string;
  name: string;
  industry: string;
  market: string;
  buy_date: string;
  weight: number;
  allocated_cash: number;
  buy_price: number;
  end_price: number;
  return_rate: number;
};

export type SimulationPositionSnapshot = {
  ts_code: string;
  name: string;
  industry: string;
  market: string;
  buy_date: string;
  quantity: number;
  cost_price: number;
  current_price: number;
  market_value: number;
  return_rate: number;
};

export type SimulationTradeDetail = {
  ts_code: string;
  name: string;
  industry: string;
  market: string;
  side: "buy" | "sell";
  price: number;
  quantity: number;
  amount: number;
  profit_loss: number;
  return_rate: number;
  reason: string;
};

export type SimulationRebalanceStep = {
  trade_date: string;
  signal_date: string;
  before_cash: number;
  before_market_value: number;
  before_total_value: number;
  before_holdings: SimulationPositionSnapshot[];
  sell_trades: SimulationTradeDetail[];
  buy_trades: SimulationTradeDetail[];
  after_cash: number;
  after_market_value: number;
  after_total_value: number;
  after_holdings: SimulationPositionSnapshot[];
};

export type SimulationResult = {
  strategy_version: string;
  start_date: string;
  end_date: string;
  stock_count: number;
  initial_cash: number;
  final_value: number;
  metrics: SimulationMetric[];
  holdings: SimulationHolding[];
  rebalances: SimulationRebalanceStep[];
  conclusion: string;
  time_requirement: string;
};

export type SimulationRunPayload = {
  start_date: string;
  end_date: string;
  stock_count: number;
  initial_cash: number;
  min_score: number;
  review_mode: "hold" | "rebalance";
};

export async function fetchSimulationRuns(): Promise<ListResponse<SimulationRunSummary>> {
  return apiGet<ListResponse<SimulationRunSummary>>("/api/simulations");
}

export async function fetchSimulationReview(strategyVersion: string): Promise<SimulationResult> {
  return apiGet<SimulationResult>(`/api/simulations/${encodeURIComponent(strategyVersion)}`);
}

export async function runSimulation(payload: SimulationRunPayload): Promise<SimulationResult> {
  return apiPost<SimulationResult>("/api/simulations/run", payload);
}
