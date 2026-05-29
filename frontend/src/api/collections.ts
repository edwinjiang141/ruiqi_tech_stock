import { apiGet, apiPost } from "./client";

export type TushareConfigStatus = {
  token_configured: boolean;
  api_url: string;
  timeout: number;
};

export type CollectionTask = {
  task_name: string;
  title: string;
  method: string;
  endpoint: string;
  required_params: string[];
  description: string;
  data_scope: string;
  date_description: string;
  idempotency_key: string;
  frequency: string;
};

export type CollectionResult = {
  task_name: string;
  source: string;
  fetched_count: number;
  inserted_or_updated_count: number;
  status: string;
  message: string;
};

export type QualityMetric = {
  name: string;
  value: number | string | boolean;
  passed: boolean;
  message: string;
};

export type QualityReport = {
  target: string;
  passed: boolean;
  metrics: QualityMetric[];
};

export async function fetchStockBasicQuality(): Promise<QualityReport> {
  return apiGet<QualityReport>("/api/collections/quality/stock-basic");
}

export async function fetchScoringDataQuality(): Promise<QualityReport> {
  return apiGet<QualityReport>("/api/collections/quality/scoring-data");
}

export async function fetchTushareConfigStatus(): Promise<TushareConfigStatus> {
  return apiGet<TushareConfigStatus>("/api/collections/config");
}

export async function fetchCollectionTasks(): Promise<CollectionTask[]> {
  return apiGet<CollectionTask[]>("/api/collections/tasks");
}

export async function triggerStockPoolCollection(): Promise<{ collection: CollectionResult; quality: QualityReport }> {
  return apiPost<{ collection: CollectionResult; quality: QualityReport }>("/api/collections/stock-pool");
}

export async function triggerTradingDayCollection(tradeDate: string): Promise<CollectionResult> {
  return apiPost<CollectionResult>(`/api/collections/trading-day?trade_date=${encodeURIComponent(tradeDate)}`);
}

export async function triggerTradingRangeCollection(startDate: string, endDate: string): Promise<CollectionResult> {
  return apiPost<CollectionResult>(
    `/api/collections/trading-range?start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`
  );
}

export async function triggerFinancialCollection(period: string): Promise<CollectionResult> {
  return apiPost<CollectionResult>(`/api/collections/financial?period=${encodeURIComponent(period)}`);
}

export async function triggerFinancialRangeCollection(startPeriod: string, endPeriod: string): Promise<CollectionResult> {
  return apiPost<CollectionResult>(
    `/api/collections/financial-range?start_period=${encodeURIComponent(startPeriod)}&end_period=${encodeURIComponent(endPeriod)}`
  );
}

export async function triggerScoringFinancialRangeCollection(startPeriod: string, endPeriod: string): Promise<CollectionResult> {
  return apiPost<CollectionResult>(
    `/api/collections/scoring-financial-range?start_period=${encodeURIComponent(startPeriod)}&end_period=${encodeURIComponent(endPeriod)}`
  );
}

export async function triggerScoringRiskDataCollection(startDate: string, endDate: string): Promise<CollectionResult> {
  return apiPost<CollectionResult>(
    `/api/collections/scoring-risk-data?start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`
  );
}

export async function triggerIndexWeightRangeCollection(indexCodes: string, startDate: string, endDate: string): Promise<CollectionResult> {
  return apiPost<CollectionResult>(
    `/api/collections/index-weight-range?index_codes=${encodeURIComponent(indexCodes)}&start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}`
  );
}
