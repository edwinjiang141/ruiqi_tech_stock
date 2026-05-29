import { apiGet, type ListResponse } from "./client";

export type ModuleKey = "stocks" | "recommendations" | "factors" | "simulations";

export type ModuleStatus = {
  key: ModuleKey;
  title: string;
  description: string;
  endpoint: string;
  total: number;
};

const modules: Array<Omit<ModuleStatus, "total">> = [
  {
    key: "stocks",
    title: "股票池",
    description: "创业板、科创板和科技属性股票基础数据",
    endpoint: "/api/stocks"
  },
  {
    key: "recommendations",
    title: "推荐结果",
    description: "每日 S/A/B/C/D 推荐等级和推荐理由",
    endpoint: "/api/recommendations"
  },
  {
    key: "factors",
    title: "因子评分",
    description: "质量、成长、估值、动量、资金流等量化评分",
    endpoint: "/api/factors"
  },
  {
    key: "simulations",
    title: "模拟复盘",
    description: "模拟交易、持仓、收益和回撤评估",
    endpoint: "/api/simulations"
  }
];

export async function fetchModuleStatuses(): Promise<ModuleStatus[]> {
  return Promise.all(
    modules.map(async (item) => {
      const result = await apiGet<ListResponse<unknown>>(item.endpoint);
      return { ...item, total: result.total };
    })
  );
}
