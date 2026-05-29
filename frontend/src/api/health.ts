import { apiGet } from "./client";

export type HealthResponse = {
  status: string;
  app_name: string;
  version: string;
  environment: string;
  database: {
    database: string;
    user: string;
    schema: string;
    schema_exists: boolean;
  };
};

export async function fetchHealth(): Promise<HealthResponse> {
  return apiGet<HealthResponse>("/api/health");
}
