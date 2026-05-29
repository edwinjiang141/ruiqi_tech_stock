import { apiGet, type ListResponse } from "./client";

export type TaskLog = {
  id: number;
  task_name: string;
  task_type: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  message: string | null;
  created_at: string;
};

export async function fetchTaskLogs(): Promise<ListResponse<TaskLog>> {
  return apiGet<ListResponse<TaskLog>>("/api/tasks");
}
