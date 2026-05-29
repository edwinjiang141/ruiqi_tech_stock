<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";

import {
  fetchCollectionTasks,
  fetchScoringDataQuality,
  fetchStockBasicQuality,
  fetchTushareConfigStatus,
  triggerFinancialCollection,
  triggerFinancialRangeCollection,
  triggerIndexWeightRangeCollection,
  triggerScoringFinancialRangeCollection,
  triggerScoringRiskDataCollection,
  triggerStockPoolCollection,
  triggerTradingDayCollection,
  triggerTradingRangeCollection,
  type CollectionResult,
  type CollectionTask,
  type QualityReport,
  type TushareConfigStatus
} from "./api/collections";
import { fetchHealth, type HealthResponse } from "./api/health";
import { fetchModuleStatuses, type ModuleStatus } from "./api/modules";
import { fetchFactorScoreHistory, fetchFactorScores, triggerFactorCalculation, type FactorScore, type FactorScoreHistoryItem } from "./api/factors";
import { fetchPortfolio, fetchPortfolios, runPortfolio, type PortfolioResult, type PortfolioSummary } from "./api/portfolios";
import { fetchRecommendations, type RecommendationItem } from "./api/recommendations";
import { fetchSimulationReview, fetchSimulationRuns, runSimulation, type SimulationResult, type SimulationRunSummary } from "./api/simulations";
import { fetchTaskLogs, type TaskLog } from "./api/tasks";

const health = ref<HealthResponse | null>(null);
const modules = ref<ModuleStatus[]>([]);
const tushareConfig = ref<TushareConfigStatus | null>(null);
const collectionTasks = ref<CollectionTask[]>([]);
const quality = ref<QualityReport | null>(null);
const scoringQuality = ref<QualityReport | null>(null);
const taskLogs = ref<TaskLog[]>([]);
const selectedTaskLog = ref<TaskLog | null>(null);
const activePage = ref<"application" | "portfolio" | "simulation" | "collection" | "tasks">("application");
const currentTask = ref<{ title: string; status: "running" | "success" | "warning" | "failed"; message: string } | null>(null);
const lastTaskRefreshAt = ref("");
const applicationTradeDate = ref(new Date().toISOString().slice(0, 10));
const recommendations = ref<RecommendationItem[]>([]);
const factorScores = ref<FactorScore[]>([]);
const factorScoreHistory = ref<FactorScoreHistoryItem[]>([]);
const factorScoreHistoryTotal = ref(0);
const factorScoreHistoryPage = ref(1);
const factorScoreHistoryPageSize = 5;
const isApplicationLoading = ref(false);
const applicationMessage = ref("");
const simulationStartDate = ref(dateDaysAgo(90));
const simulationEndDate = ref(new Date().toISOString().slice(0, 10));
const simulationStockCount = ref(20);
const simulationInitialCash = ref(1000000);
const simulationMinScore = ref(65);
const simulationReviewMode = ref<"hold" | "rebalance">("hold");
const simulationResult = ref<SimulationResult | null>(null);
const simulationRuns = ref<SimulationRunSummary[]>([]);
const selectedSimulationVersion = ref("");
const isSimulationRunning = ref(false);
const portfolioScoreDate = ref(new Date().toISOString().slice(0, 10));
const portfolioEndDate = ref(new Date().toISOString().slice(0, 10));
const portfolioStockCount = ref(20);
const portfolioInitialCash = ref(100000);
const portfolioMinScore = ref(65);
const portfolioBenchmarkCode = ref("399006.SZ");
const portfolioResult = ref<PortfolioResult | null>(null);
const portfolioRuns = ref<PortfolioSummary[]>([]);
const selectedPortfolioId = ref("");
const isPortfolioRunning = ref(false);
const tradeDate = ref(new Date().toISOString().slice(0, 10));
const tradeStartDate = ref(new Date().toISOString().slice(0, 10));
const tradeEndDate = ref(new Date().toISOString().slice(0, 10));
const financialPeriod = ref(`${new Date().getFullYear()}-03-31`);
const financialStartPeriod = ref(`${new Date().getFullYear() - 1}-12-31`);
const financialEndPeriod = ref(`${new Date().getFullYear()}-12-31`);
const scoringFinancialStartPeriod = ref(`${new Date().getFullYear() - 3}-12-31`);
const scoringFinancialEndPeriod = ref(`${new Date().getFullYear()}-12-31`);
const indexWeightCodes = ref("399006.SZ,000688.SH");
const indexWeightStartDate = ref(`${new Date().getFullYear() - 1}-01-01`);
const indexWeightEndDate = ref(new Date().toISOString().slice(0, 10));
const collectionMessage = ref("");
const isCollecting = ref(false);
const errorMessage = ref("");

const collectionSections = [
  { id: "stock-pool", label: "股票池", summary: "低频基础资料，构建创业板、科创板和科技属性股票池。" },
  { id: "trading-data", label: "交易数据", summary: "行情、复权、估值指标和资金流，支持单日与区间补采。" },
  { id: "financial-data", label: "财务数据", summary: "财务指标和现金流量表，按财报报告期末日采集。" },
  { id: "scoring-data", label: "评分前置数据", summary: "利润表、资产负债表、指数权重、质押和交易约束数据。" },
  { id: "quality", label: "质量检查", summary: "展示采集后的质量指标。" }
];

const topRecommendation = computed(() => recommendations.value[0]);
const averageFinalScore = computed(() => {
  const scores = recommendations.value
    .map((item) => Number(item.final_score))
    .filter((item) => Number.isFinite(item));
  if (!scores.length) {
    return "-";
  }
  return (scores.reduce((sum, item) => sum + item, 0) / scores.length).toFixed(2);
});

const simulationReturnMetric = computed(() => simulationResult.value?.metrics.find((item) => item.name === "累计收益率"));
const simulationDrawdownMetric = computed(() => simulationResult.value?.metrics.find((item) => item.name === "最大回撤"));
const simulationWinRateMetric = computed(() => simulationResult.value?.metrics.find((item) => item.name === "胜率"));
const portfolioRangeLabel = computed(() => `组合区间：${portfolioScoreDate.value} 至 ${portfolioEndDate.value}`);
const portfolioLatestNav = computed(() => portfolioResult.value?.nav[portfolioResult.value.nav.length - 1]);
const portfolioBenchmarkSourceLabel = computed(() => {
  if (!portfolioResult.value) {
    return "基准：待生成";
  }
  return portfolioResult.value.benchmark_source === "index"
    ? `基准：${portfolioResult.value.benchmark_name}`
    : `基准：股票池等权（${portfolioResult.value.benchmark_name}缺少指数行情时回退）`;
});
const factorScoreHistoryTotalPages = computed(() => Math.max(1, Math.ceil(factorScoreHistoryTotal.value / factorScoreHistoryPageSize)));
const applicationDateLabel = computed(() => `交易日：${applicationTradeDate.value}`);
const simulationRangeLabel = computed(() => `复盘区间：${simulationStartDate.value} 至 ${simulationEndDate.value}`);
const tradingRangeLabel = computed(() => `采集区间：${tradeStartDate.value} 至 ${tradeEndDate.value}`);
const financialRangeLabel = computed(() => `报告期区间：${financialStartPeriod.value} 至 ${financialEndPeriod.value}`);

function toApiDate(value: string): string {
  return value.replaceAll("-", "");
}

async function runSimulationReview(): Promise<void> {
  isSimulationRunning.value = true;
  errorMessage.value = "";
  applicationMessage.value = "";
  currentTask.value = {
    title: "模拟交易复盘",
    status: "running",
    message: "正在按照当前评分结果进行模拟交易和复盘计算。"
  };
  try {
    simulationResult.value = await runSimulation({
      start_date: toApiDate(simulationStartDate.value),
      end_date: toApiDate(simulationEndDate.value),
      stock_count: simulationStockCount.value,
      initial_cash: simulationInitialCash.value,
      min_score: simulationMinScore.value,
      review_mode: simulationReviewMode.value
    });
    currentTask.value = {
      title: "模拟交易复盘",
      status: "success",
      message: simulationResult.value.conclusion
    };
    selectedSimulationVersion.value = simulationResult.value.strategy_version;
    await refreshSimulationHistory();
    await refreshTaskLogs();
  } catch (error) {
    const message = error instanceof Error ? error.message : "模拟交易复盘失败";
    currentTask.value = {
      title: "模拟交易复盘",
      status: "failed",
      message
    };
    errorMessage.value = message;
  } finally {
    isSimulationRunning.value = false;
  }
}

async function refreshFactorScoreHistory(): Promise<void> {
  try {
    const offset = (factorScoreHistoryPage.value - 1) * factorScoreHistoryPageSize;
    const result = await fetchFactorScoreHistory(factorScoreHistoryPageSize, offset);
    factorScoreHistory.value = result.items;
    factorScoreHistoryTotal.value = result.total;
    if (factorScoreHistoryPage.value > factorScoreHistoryTotalPages.value) {
      factorScoreHistoryPage.value = factorScoreHistoryTotalPages.value;
      await refreshFactorScoreHistory();
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "历史评分记录刷新失败";
  }
}

async function changeFactorScoreHistoryPage(delta: number): Promise<void> {
  const nextPage = factorScoreHistoryPage.value + delta;
  if (nextPage < 1 || nextPage > factorScoreHistoryTotalPages.value) {
    return;
  }
  factorScoreHistoryPage.value = nextPage;
  await refreshFactorScoreHistory();
}

async function selectFactorScoreHistory(tradeDate: string): Promise<void> {
  applicationTradeDate.value = tradeDate;
  await refreshApplicationData();
}

async function refreshSimulationHistory(): Promise<void> {
  try {
    const result = await fetchSimulationRuns();
    simulationRuns.value = result.items;
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "历史复盘记录刷新失败";
  }
}

async function selectSimulationHistory(strategyVersion: string): Promise<void> {
  isSimulationRunning.value = true;
  errorMessage.value = "";
  try {
    simulationResult.value = await fetchSimulationReview(strategyVersion);
    selectedSimulationVersion.value = strategyVersion;
    simulationStartDate.value = simulationResult.value.start_date;
    simulationEndDate.value = simulationResult.value.end_date;
    simulationStockCount.value = simulationResult.value.stock_count;
    simulationInitialCash.value = simulationResult.value.initial_cash;
    simulationReviewMode.value = strategyVersion.includes("review-rebalance") ? "rebalance" : "hold";
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "历史复盘详情查询失败";
  } finally {
    isSimulationRunning.value = false;
  }
}

async function runSimulationPortfolio(): Promise<void> {
  isPortfolioRunning.value = true;
  errorMessage.value = "";
  currentTask.value = {
    title: "模拟组合生成",
    status: "running",
    message: "正在根据评分推荐生成组合，并按每日收盘价计算收益。"
  };
  try {
    portfolioResult.value = await runPortfolio({
      score_date: toApiDate(portfolioScoreDate.value),
      end_date: toApiDate(portfolioEndDate.value),
      stock_count: portfolioStockCount.value,
      initial_cash: portfolioInitialCash.value,
      min_score: portfolioMinScore.value,
      benchmark_code: portfolioBenchmarkCode.value
    });
    selectedPortfolioId.value = portfolioResult.value.portfolio_id;
    currentTask.value = {
      title: "模拟组合生成",
      status: "success",
      message: portfolioResult.value.conclusion
    };
    await refreshPortfolioHistory();
  } catch (error) {
    const message = error instanceof Error ? error.message : "模拟组合生成失败";
    currentTask.value = {
      title: "模拟组合生成",
      status: "failed",
      message
    };
    errorMessage.value = message;
  } finally {
    isPortfolioRunning.value = false;
  }
}

async function refreshPortfolioHistory(): Promise<void> {
  try {
    const result = await fetchPortfolios();
    portfolioRuns.value = result.items;
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "历史模拟组合刷新失败";
  }
}

async function selectPortfolioHistory(portfolioId: string): Promise<void> {
  isPortfolioRunning.value = true;
  errorMessage.value = "";
  try {
    portfolioResult.value = await fetchPortfolio(portfolioId);
    selectedPortfolioId.value = portfolioId;
    portfolioScoreDate.value = portfolioResult.value.score_date;
    portfolioEndDate.value = portfolioResult.value.end_date;
    portfolioStockCount.value = portfolioResult.value.stock_count;
    portfolioInitialCash.value = portfolioResult.value.initial_cash;
    portfolioMinScore.value = portfolioResult.value.min_score;
    portfolioBenchmarkCode.value = portfolioResult.value.benchmark_code || portfolioBenchmarkCode.value;
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "模拟组合详情查询失败";
  } finally {
    isPortfolioRunning.value = false;
  }
}

async function refreshApplicationData(): Promise<void> {
  isApplicationLoading.value = true;
  applicationMessage.value = "";
  errorMessage.value = "";
  try {
    const tradeDate = toApiDate(applicationTradeDate.value);
    const [recommendationResult, factorResult] = await Promise.all([fetchRecommendations(tradeDate, 50), fetchFactorScores(tradeDate, 50)]);
    recommendations.value = recommendationResult.items;
    factorScores.value = factorResult.items;
    applicationMessage.value = "应用侧数据已刷新。";
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "应用侧数据刷新失败";
  } finally {
    isApplicationLoading.value = false;
  }
}

async function runFactorCalculation(): Promise<void> {
  isApplicationLoading.value = true;
  applicationMessage.value = "";
  errorMessage.value = "";
  currentTask.value = {
    title: "因子评分与推荐生成",
    status: "running",
    message: "任务已提交，正在执行。"
  };
  try {
    const result = await triggerFactorCalculation(toApiDate(applicationTradeDate.value), 50);
    currentTask.value = {
      title: "因子评分与推荐生成",
      status: result.status === "warning" ? "warning" : "success",
      message: result.message
    };
    applicationMessage.value = result.message;
    await refreshApplicationData();
    factorScoreHistoryPage.value = 1;
    await refreshFactorScoreHistory();
    await refreshTaskLogs();
  } catch (error) {
    const message = error instanceof Error ? error.message : "因子评分任务触发失败";
    currentTask.value = {
      title: "因子评分与推荐生成",
      status: "failed",
      message
    };
    errorMessage.value = message;
  } finally {
    isApplicationLoading.value = false;
  }
}

function dateDaysAgo(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() - days);
  return date.toISOString().slice(0, 10);
}

const riskStartDate = ref(dateDaysAgo(30));
const riskEndDate = ref(new Date().toISOString().slice(0, 10));

function taskByName(name: string): CollectionTask | undefined {
  return collectionTasks.value.find((item) => item.task_name === name);
}

function summarizeMessage(message: string | null): string {
  if (!message) {
    return "-";
  }
  return message.length > 48 ? `${message.slice(0, 48)}...` : message;
}

function stockTitle(item: { ts_code: string; name?: string }): string {
  return item.name ? `${item.name} · ${item.ts_code}` : item.ts_code;
}

function stockSector(item: { industry?: string; market?: string }): string {
  return [item.industry, item.market].filter(Boolean).join(" · ") || "-";
}

async function refreshDashboard(): Promise<void> {
  try {
    const [healthResult, moduleResult, configResult, tasksResult, qualityResult, scoringQualityResult] = await Promise.all([
      fetchHealth(),
      fetchModuleStatuses(),
      fetchTushareConfigStatus(),
      fetchCollectionTasks(),
      fetchStockBasicQuality(),
      fetchScoringDataQuality()
    ]);
    health.value = healthResult;
    modules.value = moduleResult;
    tushareConfig.value = configResult;
    collectionTasks.value = tasksResult;
    quality.value = qualityResult;
    scoringQuality.value = scoringQualityResult;
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "基础接口检查失败";
  }
}

async function refreshTaskLogs(): Promise<void> {
  try {
    const taskResult = await fetchTaskLogs();
    taskLogs.value = taskResult.items;
    lastTaskRefreshAt.value = new Date().toLocaleString();
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "任务日志刷新失败";
  }
}

async function runCollection(action: () => Promise<unknown>, taskTitle: string, successText: string): Promise<void> {
  isCollecting.value = true;
  collectionMessage.value = "";
  errorMessage.value = "";
  currentTask.value = {
    title: taskTitle,
    status: "running",
    message: "任务已提交，正在执行。"
  };
  activePage.value = "collection";
  try {
    const result = (await action()) as CollectionResult | unknown;
    const status = typeof result === "object" && result !== null && "status" in result ? (result as CollectionResult).status : "success";
    const message = typeof result === "object" && result !== null && "message" in result ? (result as CollectionResult).message : successText;
    currentTask.value = {
      title: taskTitle,
      status: status === "warning" ? "warning" : "success",
      message: status === "warning" ? message : successText
    };
    collectionMessage.value = status === "warning" ? message : successText;
    await refreshDashboard();
    await refreshTaskLogs();
  } catch (error) {
    const message = error instanceof Error ? error.message : "采集任务触发失败";
    currentTask.value = {
      title: taskTitle,
      status: "failed",
      message
    };
    collectionMessage.value = message;
    await refreshDashboard();
    await refreshTaskLogs();
  } finally {
    isCollecting.value = false;
  }
}

let taskRefreshTimer: number | undefined;

onMounted(async () => {
  await refreshDashboard();
  await refreshApplicationData();
  await refreshFactorScoreHistory();
  await refreshSimulationHistory();
  await refreshPortfolioHistory();
  await refreshTaskLogs();
  taskRefreshTimer = window.setInterval(refreshTaskLogs, 10000);
});

onUnmounted(() => {
  if (taskRefreshTimer) {
    window.clearInterval(taskRefreshTimer);
  }
});
</script>

<template>
  <main class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <span class="brand-mark">量化</span>
        <strong>股票研究助手</strong>
      </div>
      <nav>
        <button class="nav-page" :class="{ active: activePage === 'application' }" @click="activePage = 'application'">
          <span>研究推荐应用</span>
          <small>因子评分、推荐列表和股票观察。</small>
        </button>
        <button class="nav-page" :class="{ active: activePage === 'portfolio' }" @click="activePage = 'portfolio'">
          <span>模拟组合</span>
          <small>每日收益、持仓跟踪和大盘对比。</small>
        </button>
        <button class="nav-page" :class="{ active: activePage === 'simulation' }" @click="activePage = 'simulation'">
          <span>模拟交易复盘</span>
          <small>资金分配、组合收益和复盘指标。</small>
        </button>
        <div class="nav-divider">运维与数据准备</div>
        <button class="nav-page" :class="{ active: activePage === 'collection' }" @click="activePage = 'collection'">
          <span>采集工作台</span>
          <small>股票池、交易数据、财务数据采集。</small>
        </button>
        <template v-if="activePage === 'collection'">
          <a v-for="item in collectionSections" :key="item.id" :href="`#${item.id}`">
            <span>{{ item.label }}</span>
            <small>{{ item.summary }}</small>
          </a>
        </template>
        <button class="nav-page" :class="{ active: activePage === 'tasks' }" @click="activePage = 'tasks'">
          <span>任务日志</span>
          <small>查看历史任务、失败原因和执行状态。</small>
        </button>
      </nav>
    </aside>

    <section v-if="activePage === 'application'" class="content">
      <section class="hero app-hero">
        <p class="eyebrow">股票研究</p>
        <h1>因子评分与股票推荐</h1>
        <p class="description">
          面向日常选股和跟踪使用，集中展示推荐结果、综合评分、因子拆解和风险提示。数据采集、补数和任务日志放在独立的运维区域。
        </p>
      </section>

      <p v-if="errorMessage" class="error card">{{ errorMessage }}</p>

      <section v-if="currentTask" class="current-task-card" :class="currentTask.status">
        <div>
          <span>最近应用任务</span>
          <strong>{{ currentTask.title }}</strong>
          <p>{{ currentTask.message }}</p>
        </div>
        <span class="status-badge" :class="currentTask.status">{{ currentTask.status }}</span>
      </section>

      <section class="card application-toolbar">
        <div>
          <p class="eyebrow">评分推荐</p>
          <h2>推荐结果工作台</h2>
          <p>选择交易日后查询推荐结果；也可以在这里手工触发评分和推荐生成。</p>
        </div>
        <label>
          交易日
          <input v-model="applicationTradeDate" type="date" />
        </label>
        <button class="secondary-action" :disabled="isApplicationLoading" @click="refreshApplicationData">刷新结果</button>
        <button class="primary-action" :disabled="isApplicationLoading" @click="runFactorCalculation">计算评分</button>
      </section>

      <p v-if="applicationMessage" class="notice">{{ applicationMessage }}</p>

      <section class="application-metrics">
        <article class="metric-card">
          <span>推荐股票数</span>
          <strong>{{ recommendations.length }}</strong>
          <small>{{ applicationDateLabel }} · Top N 推荐结果</small>
        </article>
        <article class="metric-card">
          <span>平均综合分</span>
          <strong>{{ averageFinalScore }}</strong>
          <small>{{ applicationDateLabel }} · 推荐池均值</small>
        </article>
        <article class="metric-card">
          <span>最高评分</span>
          <strong>{{ topRecommendation?.final_score || "-" }}</strong>
          <small>{{ applicationDateLabel }} · {{ topRecommendation?.name || topRecommendation?.ts_code || "暂无推荐" }}</small>
        </article>
      </section>

      <section class="card">
        <div class="section-heading">
          <p class="eyebrow">历史评分记录</p>
          <h2>已生成评分的交易日</h2>
          <p>当前共有 {{ factorScoreHistoryTotal }} 个历史评分交易日。点击记录可查询对应日期的推荐列表和因子拆解。</p>
        </div>
        <p v-if="factorScoreHistory.length === 0">暂无历史评分记录。请先选择交易日并计算评分。</p>
        <div v-else class="score-history-list">
          <button
            v-for="item in factorScoreHistory"
            :key="item.trade_date"
            class="score-history-item"
            :class="{ active: applicationTradeDate === item.trade_date }"
            :disabled="isApplicationLoading"
            @click="selectFactorScoreHistory(item.trade_date)"
          >
            <div class="history-card-main">
              <span class="history-date">{{ item.trade_date }}</span>
              <small>评分交易日</small>
            </div>
            <div class="history-card-metric">
              <strong>{{ item.recommendation_count }}</strong>
              <small>推荐股票</small>
            </div>
            <div class="history-card-metric subtle">
              <strong>{{ item.factor_score_count }}</strong>
              <small>完成评分</small>
            </div>
          </button>
        </div>
        <div v-if="factorScoreHistoryTotal > factorScoreHistoryPageSize" class="pagination-bar">
          <button class="secondary-action" :disabled="factorScoreHistoryPage <= 1 || isApplicationLoading" @click="changeFactorScoreHistoryPage(-1)">上一页</button>
          <span>第 {{ factorScoreHistoryPage }} / {{ factorScoreHistoryTotalPages }} 页</span>
          <button class="secondary-action" :disabled="factorScoreHistoryPage >= factorScoreHistoryTotalPages || isApplicationLoading" @click="changeFactorScoreHistoryPage(1)">下一页</button>
        </div>
      </section>

      <section class="card">
        <div class="section-heading">
          <p class="eyebrow">{{ applicationDateLabel }}</p>
          <h2>每日推荐列表</h2>
          <p>按综合评分排序，展示推荐等级、核心因子和规则化解释。</p>
        </div>
        <p v-if="recommendations.length === 0">暂无推荐结果。请先计算该交易日的评分，或切换到已有推荐结果的日期。</p>
        <div v-else class="recommendation-list">
          <article v-for="item in recommendations" :key="`${item.trade_date}-${item.ts_code}`" class="recommendation-card">
            <div class="recommendation-rank">
              <span>#{{ item.rank_no || "-" }}</span>
              <strong :class="`level-${item.recommendation_level}`">{{ item.recommendation_level }}</strong>
            </div>
            <div class="recommendation-main">
              <h3>{{ item.name || item.ts_code }} <small>{{ item.ts_code }}</small></h3>
              <p>{{ item.industry || "未分类" }} · {{ item.market || "-" }}</p>
              <p class="summary">{{ item.summary || "暂无推荐说明" }}</p>
              <p class="risk-text">{{ item.risk_warning || "暂无显著风险提示" }}</p>
            </div>
            <div class="score-panel">
              <span>综合分</span>
              <strong>{{ item.final_score }}</strong>
            </div>
          </article>
        </div>
      </section>

      <section class="card">
        <div class="section-heading">
          <p class="eyebrow">{{ applicationDateLabel }}</p>
          <h2>因子评分拆解</h2>
          <p>用于检查每只股票的质量、成长、估值、动量、资金、龙头和风险扣分，帮助理解推荐结果。</p>
        </div>
        <p v-if="factorScores.length === 0">暂无因子评分结果。</p>
        <table v-else class="task-table factor-table">
          <thead>
            <tr>
              <th>排名</th>
              <th>股票</th>
              <th>等级</th>
              <th>综合分</th>
              <th>质量</th>
              <th>成长</th>
              <th>估值</th>
              <th>动量</th>
              <th>资金</th>
              <th>龙头</th>
              <th>风险扣分</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in factorScores" :key="`${item.trade_date}-${item.ts_code}`">
              <td>{{ item.rank_in_universe || "-" }}</td>
              <td>
                <strong>{{ item.name || item.ts_code }}</strong>
                <small>{{ item.ts_code }} · {{ item.industry || "未分类" }}</small>
              </td>
              <td><span class="status-badge success">{{ item.recommendation_level || "-" }}</span></td>
              <td>{{ item.final_score }}</td>
              <td>{{ item.quality_score }}</td>
              <td>{{ item.growth_score }}</td>
              <td>{{ item.valuation_score }}</td>
              <td>{{ item.momentum_score }}</td>
              <td>{{ item.capital_flow_score }}</td>
              <td>{{ item.leadership_score }}</td>
              <td>{{ item.risk_penalty }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </section>

    <section v-else-if="activePage === 'portfolio'" class="content">
      <section class="hero app-hero">
        <p class="eyebrow">组合跟踪</p>
        <h1>模拟组合收益</h1>
        <p class="description">
          根据某个评分日的推荐股票生成模拟组合，按每日收盘价计算组合净值、收益率和相对大盘的超额收益，用于比较不同评分日组合的表现。
        </p>
      </section>

      <p v-if="errorMessage" class="error card">{{ errorMessage }}</p>

      <section v-if="currentTask" class="current-task-card" :class="currentTask.status">
        <div>
          <span>最近组合任务</span>
          <strong>{{ currentTask.title }}</strong>
          <p>{{ currentTask.message }}</p>
        </div>
        <span class="status-badge" :class="currentTask.status">{{ currentTask.status }}</span>
      </section>

      <section class="card portfolio-form">
        <div>
          <p class="eyebrow">{{ portfolioRangeLabel }}</p>
          <h2>组合参数</h2>
          <p>选择评分日后，系统取该日推荐 Top N 等权建仓；从下一个交易日起按每日收盘价计算组合收益。</p>
        </div>
        <label>
          评分日期
          <input v-model="portfolioScoreDate" type="date" />
        </label>
        <label>
          结束日期
          <input v-model="portfolioEndDate" type="date" />
        </label>
        <label>
          模拟股票数
          <input v-model.number="portfolioStockCount" type="number" min="1" max="100" />
        </label>
        <label>
          模拟资金规模
          <input v-model.number="portfolioInitialCash" type="number" min="1000" step="10000" />
        </label>
        <label>
          最低综合分
          <input v-model.number="portfolioMinScore" type="number" min="0" max="100" step="1" />
        </label>
        <label>
          对比基准
          <select v-model="portfolioBenchmarkCode">
            <option value="399006.SZ">创业板指</option>
            <option value="000688.SH">科创50</option>
            <option value="000300.SH">沪深300</option>
          </select>
        </label>
        <button class="primary-action" :disabled="isPortfolioRunning" @click="runSimulationPortfolio">生成模拟组合</button>
      </section>

      <section class="card">
        <div class="section-heading">
          <p class="eyebrow">历史组合</p>
          <h2>已生成的模拟组合</h2>
          <p>不同评分日期可以生成不同组合，点击历史组合可直接查看每日收益和持仓。</p>
        </div>
        <div class="section-actions">
          <button class="secondary-action" :disabled="isPortfolioRunning" @click="refreshPortfolioHistory">刷新组合</button>
        </div>
        <p v-if="portfolioRuns.length === 0">暂无模拟组合。选择评分日期并生成后会显示在这里。</p>
        <div v-else class="history-list">
          <button
            v-for="item in portfolioRuns"
            :key="item.portfolio_id"
            class="history-item"
            :class="{ active: selectedPortfolioId === item.portfolio_id }"
            :disabled="isPortfolioRunning"
            @click="selectPortfolioHistory(item.portfolio_id)"
          >
            <div class="history-card-main">
              <span class="history-date">{{ item.score_date }} 组合</span>
              <small>{{ item.start_date }} 至 {{ item.end_date }} · {{ item.created_at }}</small>
            </div>
            <div class="history-card-metric return-metric" :class="item.cumulative_return >= 0 ? 'positive' : 'negative'">
              <strong>{{ (item.cumulative_return * 100).toFixed(2) }}%</strong>
              <small>组合收益</small>
            </div>
            <div class="history-card-meta">
              <span>超额 {{ (item.excess_return * 100).toFixed(2) }}%</span>
              <span>基准 {{ (item.benchmark_return * 100).toFixed(2) }}%</span>
              <span>{{ item.benchmark_source === "index" ? item.benchmark_name : "股票池等权" }}</span>
            </div>
          </button>
        </div>
      </section>

      <section class="application-metrics">
        <article class="metric-card">
          <span>组合累计收益</span>
          <strong>{{ portfolioLatestNav ? (portfolioLatestNav.portfolio_return * 100).toFixed(2) : "-" }}%</strong>
          <small>{{ portfolioRangeLabel }}</small>
        </article>
        <article class="metric-card">
          <span>基准累计收益</span>
          <strong>{{ portfolioLatestNav ? (portfolioLatestNav.benchmark_return * 100).toFixed(2) : "-" }}%</strong>
          <small>{{ portfolioBenchmarkSourceLabel }}</small>
        </article>
        <article class="metric-card">
          <span>超额收益</span>
          <strong>{{ portfolioLatestNav ? (portfolioLatestNav.excess_return * 100).toFixed(2) : "-" }}%</strong>
          <small>组合收益减去基准收益</small>
        </article>
      </section>

      <section v-if="portfolioResult" class="card">
        <div class="section-heading">
          <p class="eyebrow">{{ portfolioBenchmarkSourceLabel }}</p>
          <h2>每日收益对比</h2>
          <p>{{ portfolioResult.conclusion }}</p>
        </div>
        <table class="task-table portfolio-nav-table">
          <thead>
            <tr>
              <th>价格日期</th>
              <th>组合资产</th>
              <th>组合收益</th>
              <th>基准收益</th>
              <th>超额收益</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in portfolioResult.nav" :key="item.trade_date">
              <td>{{ item.trade_date }}</td>
              <td>{{ item.portfolio_value }}</td>
              <td :class="item.portfolio_return >= 0 ? 'success' : 'error'">{{ (item.portfolio_return * 100).toFixed(2) }}%</td>
              <td :class="item.benchmark_return >= 0 ? 'success' : 'error'">{{ (item.benchmark_return * 100).toFixed(2) }}%</td>
              <td :class="item.excess_return >= 0 ? 'success' : 'error'">{{ (item.excess_return * 100).toFixed(2) }}%</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section v-if="portfolioResult" class="card">
        <div class="section-heading">
          <p class="eyebrow">当前持仓</p>
          <h2>组合持仓明细</h2>
          <p>建仓日为 {{ portfolioResult.start_date }}，当前价使用 {{ portfolioResult.end_date }} 收盘价。</p>
        </div>
        <table class="task-table portfolio-holding-table">
          <thead>
            <tr>
              <th>代码</th>
              <th>名称</th>
              <th>行业</th>
              <th>建仓日</th>
              <th>建仓价</th>
              <th>当前价</th>
              <th>价格日期</th>
              <th>收益</th>
              <th>建仓理由</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in portfolioResult.holdings" :key="item.ts_code">
              <td>{{ item.ts_code }}</td>
              <td><strong>{{ item.name || item.ts_code }}</strong></td>
              <td>{{ item.industry || "未分类" }}</td>
              <td>{{ portfolioResult.start_date }}</td>
              <td>{{ item.buy_price }}</td>
              <td>{{ item.current_price }}</td>
              <td>{{ portfolioResult.end_date }}</td>
              <td :class="item.return_rate >= 0 ? 'success' : 'error'">{{ (item.return_rate * 100).toFixed(2) }}%</td>
              <td class="message-summary">{{ item.reason }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </section>

    <section v-else-if="activePage === 'simulation'" class="content">
      <section class="hero app-hero simulation-hero">
        <p class="eyebrow">组合验证</p>
        <h1>模拟交易与复盘</h1>
        <p class="description">
          用历史行情验证推荐组合的表现。输入股票数和资金规模后，按综合评分自动选股、分配资金，并计算收益、回撤、胜率、换手率和 Rank IC。
        </p>
      </section>

      <p v-if="errorMessage" class="error card">{{ errorMessage }}</p>

      <section v-if="currentTask" class="current-task-card" :class="currentTask.status">
        <div>
          <span>最近复盘任务</span>
          <strong>{{ currentTask.title }}</strong>
          <p>{{ currentTask.message }}</p>
        </div>
        <span class="status-badge" :class="currentTask.status">{{ currentTask.status }}</span>
      </section>

      <section class="card simulation-form">
        <div>
          <p class="eyebrow">{{ simulationRangeLabel }}</p>
          <h2>复盘参数</h2>
          <p>
            默认固定验证开始信号日推荐列表：T+1 开盘价买入并持有到结束估值日；如需验证滚动策略，可切换为定期调仓。
          </p>
        </div>
        <label>
          开始信号日
          <input v-model="simulationStartDate" type="date" />
        </label>
        <label>
          结束估值日
          <input v-model="simulationEndDate" type="date" />
        </label>
        <label>
          模拟股票数
          <input v-model.number="simulationStockCount" type="number" min="1" max="100" />
        </label>
        <label>
          模拟资金规模
          <input v-model.number="simulationInitialCash" type="number" min="1000" step="10000" />
        </label>
        <label>
          最低综合分
          <input v-model.number="simulationMinScore" type="number" min="0" max="100" step="1" />
        </label>
        <label>
          复盘方式
          <select v-model="simulationReviewMode">
            <option value="hold">固定信号持有</option>
            <option value="rebalance">定期调仓复盘</option>
          </select>
        </label>
        <button class="primary-action" :disabled="isSimulationRunning" @click="runSimulationReview">执行模拟复盘</button>
      </section>

      <section class="card">
        <div class="section-heading">
          <p class="eyebrow">历史记录</p>
          <h2>历史复盘记录</h2>
          <p>已完成的复盘会自动保存。点击记录可直接回显指标、持仓和结论，不需要重复执行复盘。</p>
        </div>
        <div class="section-actions">
          <button class="secondary-action" :disabled="isSimulationRunning" @click="refreshSimulationHistory">刷新历史记录</button>
        </div>
        <p v-if="simulationRuns.length === 0">暂无历史复盘记录。完成一次模拟复盘后会显示在这里。</p>
        <div v-else class="history-list">
          <button
            v-for="item in simulationRuns"
            :key="item.strategy_version"
            class="history-item"
            :class="{ active: selectedSimulationVersion === item.strategy_version }"
            :disabled="isSimulationRunning"
            @click="selectSimulationHistory(item.strategy_version)"
          >
            <div class="history-card-main">
              <span class="history-date">{{ item.start_date }} 至 {{ item.end_date }}</span>
              <small>创建时间：{{ item.created_at }}</small>
            </div>
            <div class="history-card-metric return-metric" :class="item.cumulative_return >= 0 ? 'positive' : 'negative'">
              <strong>{{ (item.cumulative_return * 100).toFixed(2) }}%</strong>
              <small>累计收益</small>
            </div>
            <div class="history-card-meta">
              <span>股票数 {{ item.stock_count }}</span>
              <span>初始资金 {{ item.initial_cash }}</span>
              <span>最大回撤 {{ (item.max_drawdown * 100).toFixed(2) }}%</span>
            </div>
          </button>
        </div>
      </section>

      <section class="application-metrics">
        <article class="metric-card">
          <span>累计收益率</span>
          <strong>{{ simulationReturnMetric?.value ?? "-" }}%</strong>
          <small>{{ simulationRangeLabel }} · {{ simulationReturnMetric?.description || "组合总收益。" }}</small>
        </article>
        <article class="metric-card">
          <span>最大回撤</span>
          <strong>{{ simulationDrawdownMetric?.value ?? "-" }}%</strong>
          <small>{{ simulationRangeLabel }} · {{ simulationDrawdownMetric?.description || "衡量净值回撤风险。" }}</small>
        </article>
        <article class="metric-card">
          <span>胜率</span>
          <strong>{{ simulationWinRateMetric?.value ?? "-" }}%</strong>
          <small>{{ simulationRangeLabel }} · {{ simulationWinRateMetric?.description || "盈利交易和盈利持仓占比。" }}</small>
        </article>
      </section>

      <section v-if="simulationResult" class="card">
        <div class="section-heading">
          <p class="eyebrow">{{ simulationRangeLabel }}</p>
          <h2>复盘指标</h2>
          <p>{{ simulationResult.time_requirement }}</p>
        </div>
        <div class="quality-grid">
          <article v-for="item in simulationResult.metrics" :key="item.name" class="quality-card">
            <span>{{ item.name }}</span>
            <strong>{{ item.value }}</strong>
            <p>{{ item.description }}</p>
          </article>
        </div>
      </section>

      <section v-if="simulationResult && simulationResult.rebalances.length > 0" class="card">
        <div class="section-heading">
          <p class="eyebrow">{{ simulationRangeLabel }}</p>
          <h2>调仓过程明细</h2>
          <p>
            展示每次建仓或调仓的资金滚动过程：调仓前资产、卖出盈亏、新买入股票、调仓后现金和持仓市值，便于追溯最终资产如何累积而来。
          </p>
        </div>
        <div class="rebalance-list">
          <article v-for="step in simulationResult.rebalances" :key="`${step.trade_date}-${step.signal_date}`" class="rebalance-card">
            <div class="rebalance-header">
              <div>
                <span>调仓日期：{{ step.trade_date }}</span>
                <strong>使用信号日：{{ step.signal_date }}</strong>
              </div>
              <div class="rebalance-assets">
                <small>调仓前资产 {{ step.before_total_value }}</small>
                <small>调仓后资产 {{ step.after_total_value }}</small>
              </div>
            </div>
            <div class="rebalance-summary">
              <span>调仓前现金 {{ step.before_cash }}</span>
              <span>调仓前持仓市值 {{ step.before_market_value }}</span>
              <span>调仓后现金 {{ step.after_cash }}</span>
              <span>调仓后持仓市值 {{ step.after_market_value }}</span>
            </div>

            <div class="rebalance-section">
              <h3>调仓前持仓</h3>
              <p v-if="step.before_holdings.length === 0">调仓前没有持仓，本次为初始建仓。</p>
              <table v-else class="task-table compact-table">
                <thead>
                  <tr>
                    <th>股票</th>
                    <th>买入日</th>
                    <th>成本价</th>
                    <th>当前价</th>
                    <th>市值</th>
                    <th>浮动收益</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="holding in step.before_holdings" :key="`${step.trade_date}-before-${holding.ts_code}`">
                    <td>
                      <strong>{{ stockTitle(holding) }}</strong>
                      <small>{{ stockSector(holding) }}</small>
                    </td>
                    <td>{{ holding.buy_date }}</td>
                    <td>{{ holding.cost_price }}</td>
                    <td>{{ holding.current_price }}</td>
                    <td>{{ holding.market_value }}</td>
                    <td :class="holding.return_rate >= 0 ? 'success' : 'error'">{{ holding.return_rate }}%</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div class="rebalance-section">
              <h3>卖出股票与已实现盈亏</h3>
              <p v-if="step.sell_trades.length === 0">本次没有卖出股票。</p>
              <table v-else class="task-table compact-table">
                <thead>
                  <tr>
                    <th>股票</th>
                    <th>卖出价</th>
                    <th>数量</th>
                    <th>成交额</th>
                    <th>已实现盈亏</th>
                    <th>收益率</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="trade in step.sell_trades" :key="`${step.trade_date}-sell-${trade.ts_code}`">
                    <td>
                      <strong>{{ stockTitle(trade) }}</strong>
                      <small>{{ stockSector(trade) }}</small>
                    </td>
                    <td>{{ trade.price }}</td>
                    <td>{{ trade.quantity }}</td>
                    <td>{{ trade.amount }}</td>
                    <td :class="trade.profit_loss >= 0 ? 'success' : 'error'">{{ trade.profit_loss }}</td>
                    <td :class="trade.return_rate >= 0 ? 'success' : 'error'">{{ trade.return_rate }}%</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div class="rebalance-section">
              <h3>新买入股票</h3>
              <p v-if="step.buy_trades.length === 0">本次没有新买入股票。</p>
              <table v-else class="task-table compact-table">
                <thead>
                  <tr>
                    <th>股票</th>
                    <th>买入价</th>
                    <th>数量</th>
                    <th>成交额</th>
                    <th>原因</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="trade in step.buy_trades" :key="`${step.trade_date}-buy-${trade.ts_code}`">
                    <td>
                      <strong>{{ stockTitle(trade) }}</strong>
                      <small>{{ stockSector(trade) }}</small>
                    </td>
                    <td>{{ trade.price }}</td>
                    <td>{{ trade.quantity }}</td>
                    <td>{{ trade.amount }}</td>
                    <td>{{ trade.reason }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </article>
        </div>
      </section>

      <section v-if="simulationResult" class="card">
        <div class="section-heading">
          <p class="eyebrow">{{ simulationRangeLabel }}</p>
          <h2>资金分配与持仓收益</h2>
          <p>
            初始资金 {{ simulationResult.initial_cash }}，期末资产 {{ simulationResult.final_value }}。买入成交价按实际买入日开盘价并计入 0.05% 滑点，调仓买入日期可能晚于开始信号日。
          </p>
        </div>
        <table class="task-table">
          <thead>
            <tr>
              <th>股票</th>
              <th>买入日期</th>
              <th>权重</th>
              <th>分配资金</th>
              <th>买入成交价</th>
              <th>期末价</th>
              <th>持仓收益率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in simulationResult.holdings" :key="item.ts_code">
              <td>
                <strong>{{ stockTitle(item) }}</strong>
                <small>{{ stockSector(item) }}</small>
              </td>
              <td>{{ item.buy_date || "-" }}</td>
              <td>{{ (item.weight * 100).toFixed(2) }}%</td>
              <td>{{ item.allocated_cash }}</td>
              <td>{{ item.buy_price }}</td>
              <td>{{ item.end_price }}</td>
              <td :class="item.return_rate >= 0 ? 'success' : 'error'">{{ item.return_rate }}%</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section v-if="simulationResult" class="card">
        <div class="section-heading">
          <p class="eyebrow">{{ simulationRangeLabel }}</p>
          <h2>复盘结论</h2>
          <p>{{ simulationResult.conclusion }}</p>
        </div>
      </section>
    </section>

    <section v-else-if="activePage === 'collection'" class="content">
      <section class="hero">
        <p class="eyebrow">数据采集工作台</p>
        <h1>数据采集与质量检查</h1>
        <p class="description">
          面向测试与交付使用的采集控制台。支持股票池、交易数据、财务数据的手工触发，并明确展示每个采集项的数据范围、日期含义和幂等规则。
        </p>
      </section>

      <p v-if="errorMessage" class="error card">{{ errorMessage }}</p>

      <section v-if="currentTask" class="current-task-card" :class="currentTask.status">
        <div>
          <span>当前任务</span>
          <strong>{{ currentTask.title }}</strong>
          <p>{{ currentTask.message }}</p>
        </div>
        <span class="status-badge" :class="currentTask.status">{{ currentTask.status }}</span>
      </section>

      <section class="status-panel">
        <article class="status-card">
          <span>后端状态</span>
          <strong>{{ health?.status || "检查中" }}</strong>
          <small>{{ health?.database.schema || "stock_research_v12" }}</small>
        </article>
        <article class="status-card">
          <span>Tushare Token</span>
          <strong :class="tushareConfig?.token_configured ? 'success' : 'warning'">
            {{ tushareConfig?.token_configured ? "已配置" : "未配置" }}
          </strong>
          <small>{{ tushareConfig?.api_url || "http://api.waditu.com/dataapi" }}</small>
        </article>
        <article class="status-card">
          <span>股票基础表质量</span>
          <strong :class="quality?.passed ? 'success' : 'warning'">
            {{ quality?.passed ? "通过" : "待检查" }}
          </strong>
          <small>缺失、重复、股票池标记</small>
        </article>
      </section>

      <section id="stock-pool" class="card work-card">
        <div class="section-heading">
          <p class="eyebrow">基础资料</p>
          <h2>股票池采集</h2>
          <p>采集上市股票基础资料，并识别创业板、科创板和科技属性行业股票，是后续行情、因子评分和推荐的基础。</p>
        </div>
        <div class="info-grid">
          <div>
            <strong>采集数据</strong>
            <p>{{ taskByName("collect_stock_pool")?.data_scope }}</p>
          </div>
          <div>
            <strong>日期说明</strong>
            <p>{{ taskByName("collect_stock_pool")?.date_description }}</p>
          </div>
          <div>
            <strong>幂等规则</strong>
            <p>{{ taskByName("collect_stock_pool")?.idempotency_key }}</p>
          </div>
        </div>
        <div class="control-panel single-action">
          <div>
            <strong>执行方式</strong>
            <p>无需选择日期，直接拉取最新股票基础资料。建议先执行股票池采集，再补充行情和财务数据。</p>
          </div>
          <button class="primary-action" :disabled="isCollecting" @click="runCollection(triggerStockPoolCollection, '股票池采集', '股票池采集已完成')">
            立即采集股票池
          </button>
        </div>
      </section>

      <section id="trading-data" class="card work-card">
        <div class="section-heading">
          <p class="eyebrow">{{ tradingRangeLabel }}</p>
          <h2>交易基础数据采集</h2>
          <p>采集日线行情、复权因子、每日估值指标和资金流。支持单日采集和区间补采，重复采集同一天不会产生重复数据。</p>
        </div>
        <div class="info-grid">
          <div>
            <strong>采集数据</strong>
            <p>{{ taskByName("collect_trading_day")?.data_scope }}</p>
          </div>
          <div>
            <strong>日期说明</strong>
            <p>{{ taskByName("collect_trading_day")?.date_description }}</p>
          </div>
          <div>
            <strong>幂等规则</strong>
            <p>{{ taskByName("collect_trading_day")?.idempotency_key }}</p>
          </div>
        </div>
        <div class="control-panel">
          <div class="control-row">
            <div class="control-copy">
              <strong>单日采集</strong>
              <span>适合盘后补采某一个交易日的数据。</span>
            </div>
            <label>
              交易日
              <input v-model="tradeDate" type="date" />
            </label>
            <button
              class="primary-action"
              :disabled="isCollecting"
              @click="runCollection(() => triggerTradingDayCollection(toApiDate(tradeDate)), '单日交易基础数据采集', '单日交易基础数据采集已完成')"
            >
              采集单日
            </button>
          </div>

          <div class="control-row">
            <div class="control-copy">
              <strong>区间补采</strong>
              <span>{{ tradingRangeLabel }}。适合历史补数或数据修复，单次最多 31 个自然日。</span>
            </div>
            <label>
              开始日期
              <input v-model="tradeStartDate" type="date" />
            </label>
            <label>
              结束日期
              <input v-model="tradeEndDate" type="date" />
            </label>
            <button
              class="secondary-action"
              :disabled="isCollecting"
              @click="runCollection(() => triggerTradingRangeCollection(toApiDate(tradeStartDate), toApiDate(tradeEndDate)), '区间交易基础数据采集', '区间交易基础数据采集已完成')"
            >
              区间补采
            </button>
          </div>
        </div>
      </section>

      <section id="financial-data" class="card work-card">
        <div class="section-heading">
          <p class="eyebrow">{{ financialRangeLabel }}</p>
          <h2>财务数据采集</h2>
          <p>这里的财务数据指 Tushare 财务指标 `fina_indicator` 和现金流量表 `cashflow`，日期选择财报报告期末日，而不是交易日。</p>
        </div>
        <div class="info-grid">
          <div>
            <strong>采集数据</strong>
            <p>{{ taskByName("collect_financial")?.data_scope }}</p>
          </div>
          <div>
            <strong>如何选择时间</strong>
            <p>选择财报期末日：一季报 03-31、半年报 06-30、三季报 09-30、年报 12-31。区间采集会自动按季度期末日处理。</p>
          </div>
          <div>
            <strong>幂等规则</strong>
            <p>{{ taskByName("collect_financial")?.idempotency_key }}</p>
          </div>
        </div>
        <div class="control-panel">
          <div class="control-row">
            <div class="control-copy">
              <strong>单个报告期</strong>
              <span>选择财报期末日，例如 03-31、06-30、09-30、12-31。</span>
            </div>
            <label>
              报告期
              <input v-model="financialPeriod" type="date" />
            </label>
            <button
              class="primary-action"
              :disabled="isCollecting"
              @click="runCollection(() => triggerFinancialCollection(toApiDate(financialPeriod)), '财务数据采集', '财务数据采集已完成')"
            >
              采集报告期
            </button>
          </div>

          <div class="control-row">
            <div class="control-copy">
              <strong>区间补采</strong>
              <span>{{ financialRangeLabel }}。会按季度期末日自动处理，不需要逐个季度手工点击。</span>
            </div>
            <label>
              开始报告期
              <input v-model="financialStartPeriod" type="date" />
            </label>
            <label>
              结束报告期
              <input v-model="financialEndPeriod" type="date" />
            </label>
            <button
              class="secondary-action"
              :disabled="isCollecting"
              @click="runCollection(() => triggerFinancialRangeCollection(toApiDate(financialStartPeriod), toApiDate(financialEndPeriod)), '区间财务数据采集', '区间财务数据采集已完成')"
            >
              区间补采
            </button>
          </div>
        </div>
      </section>

      <section id="scoring-data" class="card work-card scoring-card">
        <div class="section-heading">
          <p class="eyebrow">评分所需数据</p>
          <h2>评分前置数据补齐</h2>
          <p>
            因子评分需要利润表、资产负债表、指数权重、股权质押、交易日历和涨跌停等数据。补齐任务可能耗时较长，部分失败会记录为 warning，可重复补采。
          </p>
        </div>
        <div class="info-grid">
          <div>
            <strong>财务前置数据</strong>
            <p>{{ taskByName("collect_scoring_financial_range")?.data_scope }}</p>
          </div>
          <div>
            <strong>风险与交易约束</strong>
            <p>{{ taskByName("collect_scoring_risk_data")?.data_scope }}</p>
          </div>
          <div>
            <strong>指数权重</strong>
            <p>{{ taskByName("collect_index_weight_range")?.data_scope }}</p>
          </div>
        </div>
        <div class="control-panel">
          <div class="control-row">
            <div class="control-copy">
              <strong>历史财务补齐</strong>
              <span>补齐 income 和 balancesheet，用于 3 年 CAGR、环比改善、营收排名、净资产和商誉风险。</span>
            </div>
            <label>
              开始报告期
              <input v-model="scoringFinancialStartPeriod" type="date" />
            </label>
            <label>
              结束报告期
              <input v-model="scoringFinancialEndPeriod" type="date" />
            </label>
            <button
              class="secondary-action"
              :disabled="isCollecting"
              @click="runCollection(() => triggerScoringFinancialRangeCollection(toApiDate(scoringFinancialStartPeriod), toApiDate(scoringFinancialEndPeriod)), '评分财务前置数据补齐', '评分财务前置数据补齐已完成')"
            >
              补齐财务前置
            </button>
          </div>

          <div class="control-row">
            <div class="control-copy">
              <strong>风险数据补齐</strong>
              <span>补齐 pledge_stat、trade_cal、stk_limit；单次日期区间最多 31 天。建议先补最近 31 天，评分计算至少要累计补齐 120 个交易日；如果要做历史复盘，需要覆盖完整复盘区间。</span>
            </div>
            <label>
              开始日期
              <input v-model="riskStartDate" type="date" />
            </label>
            <label>
              结束日期
              <input v-model="riskEndDate" type="date" />
            </label>
            <button
              class="secondary-action"
              :disabled="isCollecting"
              @click="runCollection(() => triggerScoringRiskDataCollection(toApiDate(riskStartDate), toApiDate(riskEndDate)), '评分风险前置数据补齐', '评分风险前置数据补齐已完成')"
            >
              补齐风险数据
            </button>
          </div>

          <div class="control-row">
            <div class="control-copy">
              <strong>指数权重补齐</strong>
              <span>用于龙头地位评分。默认 399006.SZ 是创业板指，000688.SH 是科创50；非专业用户保持默认即可。指数权重是月度数据，当前推荐建议补最近 12-18 个月，历史复盘需覆盖复盘区间。</span>
            </div>
            <label>
              指数代码
              <input v-model="indexWeightCodes" type="text" placeholder="399006.SZ,000688.SH" />
            </label>
            <label>
              开始日期
              <input v-model="indexWeightStartDate" type="date" />
            </label>
            <label>
              结束日期
              <input v-model="indexWeightEndDate" type="date" />
            </label>
            <button
              class="secondary-action"
              :disabled="isCollecting"
              @click="runCollection(() => triggerIndexWeightRangeCollection(indexWeightCodes, toApiDate(indexWeightStartDate), toApiDate(indexWeightEndDate)), '指数权重数据补齐', '指数权重数据补齐已完成')"
            >
              补齐指数权重
            </button>
          </div>
        </div>
      </section>

      <p v-if="collectionMessage" class="notice">{{ collectionMessage }}</p>

      <section id="quality" class="card">
        <div class="section-heading">
          <p class="eyebrow">检查时间：{{ lastTaskRefreshAt || "尚未刷新" }}</p>
          <h2>质量检查与任务状态</h2>
          <p>采集完成后应优先检查质量指标，再进入评分计算。</p>
        </div>
        <div v-if="quality" class="quality-grid">
          <article v-for="item in quality.metrics" :key="item.name" class="quality-card">
            <span>{{ item.name }}</span>
            <strong>{{ item.value }}</strong>
            <small :class="item.passed ? 'success' : 'warning'">{{ item.passed ? "通过" : "未通过" }}</small>
            <p>{{ item.message }}</p>
          </article>
        </div>
        <div v-if="scoringQuality" class="quality-grid scoring-quality">
          <article v-for="item in scoringQuality.metrics" :key="item.name" class="quality-card">
            <span>{{ item.name }}</span>
            <strong>{{ item.value }}</strong>
            <small :class="item.passed ? 'success' : 'warning'">{{ item.passed ? "通过" : "待补齐" }}</small>
            <p>{{ item.message }}</p>
          </article>
        </div>
      </section>

      <section class="card">
        <h2>采集任务说明</h2>
        <table class="task-table">
          <thead>
            <tr>
              <th>任务</th>
              <th>采集数据</th>
              <th>日期说明</th>
              <th>幂等规则</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in collectionTasks" :key="item.task_name">
              <td>
                <strong>{{ item.title }}</strong>
                <small>{{ item.method }} {{ item.endpoint }}</small>
              </td>
              <td>{{ item.data_scope }}</td>
              <td>{{ item.date_description }}</td>
              <td>{{ item.idempotency_key }}</td>
            </tr>
          </tbody>
        </table>
      </section>

    </section>

    <section v-else class="content">
      <section class="hero">
        <p class="eyebrow">刷新时间：{{ lastTaskRefreshAt || "尚未刷新" }}</p>
        <h1>任务日志</h1>
        <p class="description">集中查看采集、质量检查、评分和复盘任务的执行状态。页面每 10 秒自动刷新，也可以手动刷新。</p>
      </section>

      <section class="card task-toolbar">
        <div>
          <strong>历史任务状态</strong>
          <p>最后刷新：{{ lastTaskRefreshAt || "尚未刷新" }}</p>
        </div>
        <button class="primary-action" @click="refreshTaskLogs">手动刷新</button>
      </section>

      <section v-if="currentTask" class="current-task-card" :class="currentTask.status">
        <div>
          <span>最近提交任务</span>
          <strong>{{ currentTask.title }}</strong>
          <p>{{ currentTask.message }}</p>
        </div>
        <span class="status-badge" :class="currentTask.status">{{ currentTask.status }}</span>
      </section>

      <section class="card">
        <h2>任务日志列表</h2>
        <p v-if="taskLogs.length === 0">暂无任务日志，后续采集、评分和复盘任务会写入这里。</p>
        <table v-else class="task-table">
          <thead>
            <tr>
              <th>任务</th>
              <th>类型</th>
              <th>状态</th>
              <th>信息</th>
              <th>创建时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in taskLogs" :key="item.id">
              <td>{{ item.task_name }}</td>
              <td>{{ item.task_type }}</td>
              <td>
                <span class="status-badge" :class="item.status">{{ item.status }}</span>
              </td>
              <td class="message-summary">{{ summarizeMessage(item.message) }}</td>
              <td>{{ item.created_at }}</td>
              <td>
                <button class="text-action" :disabled="!item.message" @click="selectedTaskLog = item">详情</button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </section>

    <div v-if="selectedTaskLog" class="modal-backdrop" @click.self="selectedTaskLog = null">
      <section class="modal-card">
        <div class="modal-header">
          <div>
            <p class="eyebrow">创建时间：{{ selectedTaskLog.created_at }}</p>
            <h2>{{ selectedTaskLog.task_name }}</h2>
          </div>
          <button class="close-action" @click="selectedTaskLog = null">关闭</button>
        </div>
        <dl class="detail-grid">
          <dt>任务类型</dt>
          <dd>{{ selectedTaskLog.task_type }}</dd>
          <dt>状态</dt>
          <dd><span class="status-badge" :class="selectedTaskLog.status">{{ selectedTaskLog.status }}</span></dd>
          <dt>开始时间</dt>
          <dd>{{ selectedTaskLog.started_at || "-" }}</dd>
          <dt>结束时间</dt>
          <dd>{{ selectedTaskLog.finished_at || "-" }}</dd>
          <dt>创建时间</dt>
          <dd>{{ selectedTaskLog.created_at }}</dd>
        </dl>
        <h3>完整信息</h3>
        <pre class="message-detail">{{ selectedTaskLog.message || "-" }}</pre>
      </section>
    </div>
  </main>
</template>
