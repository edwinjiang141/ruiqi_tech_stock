export type ApiResponse<T> = {
  success: boolean;
  code: string;
  message: string;
  data: T;
};

export type ListResponse<T> = {
  items: T[];
  total: number;
};

function formatApiError(status: number, payload: ApiResponse<unknown>): string {
  if (payload.code === "INTERNAL_ERROR") {
    return "采集任务执行失败，系统已记录失败日志，请在“最近任务日志”中查看任务状态。";
  }
  if (payload.code === "VALIDATION_ERROR") {
    return "输入参数不符合要求，请检查日期范围和报告期。";
  }
  if (payload.code === "TUSHARE_TOKEN_MISSING") {
    return "Tushare Token 未配置，请先在 backend/.env 中配置后重启后端。";
  }
  return payload.message || `请求失败：${status}`;
}

export async function apiGet<T>(url: string): Promise<T> {
  const response = await fetch(url);
  const payload = (await response.json()) as ApiResponse<T>;

  if (!response.ok || !payload.success) {
    throw new Error(formatApiError(response.status, payload));
  }

  return payload.data;
}

export async function apiPost<T>(url: string, body?: unknown): Promise<T> {
  const response = await fetch(url, {
    method: "POST",
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body)
  });
  const payload = (await response.json()) as ApiResponse<T>;

  if (!response.ok || !payload.success) {
    throw new Error(formatApiError(response.status, payload));
  }

  return payload.data;
}
