/**
 * API 客户端 — 调用 FastAPI 后端
 * 开发时通过 Vite proxy 转发到 localhost:8000
 * 生产时直接连接后端地址
 */
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 30000,
})

// ==================== 数据获取 ====================

/** 获取总览指标 */
export async function fetchSummary() {
  const { data } = await api.get('/data/summary')
  return data
}

/** 获取新能源发电数据 */
export async function fetchPowerData() {
  const { data } = await api.get('/data/power')
  return data
}

/** 获取抽水蓄能功率 */
export async function fetchNpump() {
  const { data } = await api.get('/data/npump')
  return data
}

/** 获取火电功率（有/无抽蓄） */
export async function fetchThermal() {
  const { data } = await api.get('/data/thermal')
  return data
}

/** 获取碳减排数据 */
export async function fetchCarbon() {
  const { data } = await api.get('/data/carbon')
  return data
}

/** 获取全量数据（含 carbon_result / ps_stats） */
export async function fetchAllData() {
  const { data } = await api.get('/data/all')
  return data
}

/** 获取总览页轻量数据（不含完整 365×24 数组） */
export async function fetchDashboard() {
  const { data } = await api.get('/data/dashboard')
  return data
}

/** 获取碳减排分析页轻量数据 */
export async function fetchCarbonAnalysis() {
  const { data } = await api.get('/data/carbon-analysis')
  return data
}

/** 获取抽水蓄能调度统计 */
export async function fetchPsSchedule() {
  const { data } = await api.get('/data/pumped-storage-schedule')
  return data
}

/** 获取 Pareto 解集 */
export async function fetchPareto() {
  const { data } = await api.get('/data/pareto')
  return data
}

// ==================== 模拟计算 ====================

/** 调参重新计算 */
export async function simulate(params) {
  const { data } = await api.post('/simulate', params)
  return data
}

// ==================== 原始数据浏览 ====================

/** 获取原始数据集切片 */
export async function fetchRawDataset(dataset, dayStart = 0, dayEnd = 6) {
  const { data } = await api.get('/data/raw', {
    params: { dataset, day_start: dayStart, day_end: dayEnd },
  })
  return data
}

// ==================== 健康检查 ====================

export async function checkHealth() {
  try {
    const { data } = await api.get('/health')
    return data
  } catch {
    return { status: 'unreachable' }
  }
}

// ==================== 历史记录 ====================

/** 获取历史运行列表 */
export async function fetchHistoryList() {
  const { data } = await api.get('/history/list')
  return data
}

/** 加载历史运行 */
export async function fetchHistoryRun(runId) {
  const { data } = await api.get(`/history/load/${runId}`)
  return data
}

/** 保存运行到历史 */
export async function saveHistory(params) {
  const { data } = await api.post('/history/save', params)
  return data
}

// ==================== 实验分析 ====================

/** 获取消融实验结果 */
export async function fetchAblationResults() {
  const { data } = await api.get('/experiments/ablation')
  return data
}

/** 获取Benchmark对比结果 */
export async function fetchBenchmarkResults() {
  const { data } = await api.get('/experiments/benchmark')
  return data
}

/** 获取统计显著性检验结果 */
export async function fetchExperimentStatistics() {
  const { data } = await api.get('/experiments/statistics')
  return data
}

/** 获取 Q-Learning 策略贡献数据 */
export async function fetchStrategyResults() {
  const { data } = await api.get('/experiments/strategy')
  return data
}

export default api
