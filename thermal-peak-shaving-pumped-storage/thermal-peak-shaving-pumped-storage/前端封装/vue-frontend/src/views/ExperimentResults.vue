<template>
  <div class="experiment-page">
    <div class="page-head">
      <h2>🧪 历史 NSLDE 消融实验分析</h2>
      <span class="data-badge" :class="dataSource">
        {{ dataSource === "pending" ? "等待历史实验" : "MATLAB 历史真实结果" }}
      </span>
    </div>
    <p class="subtitle">
      MATLAB 历史运行记录 · 混沌初始化 / DE差分 / Lévy飞行 / 旧版 Q-Learning
      各模块独立贡献验证；当前场景鲁棒 RLDE-F 实验请进入“算法对比”页
    </p>

    <!-- KPI 卡 -->
    <section class="kpi-row">
      <div class="kpi-card">
        <div class="kpi-label">NSLDE vs NSGA-II</div>
        <div class="kpi-val" style="color: #2ecc71">{{ displayPercent(kpis.hvImprove, "+") }}</div>
        <div class="kpi-unit">HV 提升</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">可行率</div>
        <div class="kpi-val">{{ kpis.feasibility }}</div>
        <div class="kpi-unit">A4 完整 NSLDE</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">f1 均值降低</div>
        <div class="kpi-val" style="color: #3498db">{{ displayPercent(kpis.f1Drop, "-") }}</div>
        <div class="kpi-unit">火电调峰深度</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">f2 均值降低</div>
        <div class="kpi-val" style="color: #f39c12">{{ displayPercent(kpis.f2Drop, "-") }}</div>
        <div class="kpi-unit">系统碳排放</div>
      </div>
    </section>

    <!-- 指标总览表格 -->
    <section v-if="ablationData.length" class="section">
      <h3>消融实验指标对比</h3>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>配置</th>
              <th>初始化</th>
              <th>交叉/变异</th>
              <th>可行率</th>
              <th>f1均值(MW)</th>
              <th>f2均值(kg)</th>
              <th>HV</th>
              <th>IGD</th>
              <th>Spacing</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in ablationData"
              :key="row.name"
              :class="{ highlight: row.name === 'A4_NSLDE' }"
            >
              <td>
                <strong>{{ row.name }}</strong>
              </td>
              <td>{{ row.init }}</td>
              <td>{{ row.operators }}</td>
              <td>{{ row.feasibility_rate }}</td>
              <td>{{ row.f1_mean }}</td>
              <td>{{ row.f2_mean }}</td>
              <td>{{ row.hv }}</td>
              <td>{{ row.igd }}</td>
              <td>{{ row.spacing }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    <section v-else class="section empty-state">
      尚未生成真实消融实验结果。请先运行 MATLAB `run_ablation.m`，再执行
      `experiment_runner.py --mode ablation --mat-path <结果文件>`。
    </section>

    <!-- 统计显著性 -->
    <section class="section">
      <h3>统计显著性检验 (Mann–Whitney U + Kruskal–Wallis)</h3>
      <div v-if="statsData.length" class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>对比</th>
              <th>f1 p-value</th>
              <th>f2 p-value</th>
              <th>可行性 p-value</th>
              <th>Cohen's d</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in statsData" :key="row.comparison">
              <td>{{ row.comparison }}</td>
              <td :class="sigClass(row.p_f1)">{{ row.p_f1 }}</td>
              <td :class="sigClass(row.p_f2)">{{ row.p_f2 }}</td>
              <td :class="sigClass(row.p_feas)">{{ row.p_feas }}</td>
              <td>{{ row.cohens_d }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="empty-state compact-empty">
        样本量不足或统计结果尚未生成，暂不显示显著性结论。
      </div>
    </section>

    <!-- 图表区 -->
    <section class="section chart-grid">
      <div class="chart-box">
        <h3>Pareto 前沿对比</h3>
        <div v-if="hasParetoData" ref="paretoChart" class="chart"></div>
        <div v-else class="chart chart-empty">当前消融文件只包含汇总指标，暂无 Pareto 点集。</div>
      </div>
      <div class="chart-box">
        <h3>收敛曲线 (HV vs 代数)</h3>
        <div v-if="hasConvergenceData" ref="convergeChart" class="chart"></div>
        <div v-else class="chart chart-empty">当前实验文件未提供逐代收敛历史。</div>
      </div>
    </section>

    <section v-if="ablationData.length" class="section">
      <h3>各配置性能指标对比</h3>
      <div ref="metricChart" class="chart" style="height: 360px"></div>
    </section>

    <p class="note">
      {{
        dataSource === "pending"
          ? "当前没有可用于展示的历史消融结果，页面不会填充模拟数值。"
          : "当前展示为 MATLAB run_ablation.m 生成的历史真实结果；新 RLDE-F 结果不从这里读取。"
      }}
      真实数据生成方式：MATLAB 运行 run_ablation(1, 'shaanxi', 5) 后，通过
      experiment_runner.py 写入 experiment_results/ablation_results.json。
    </p>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from "vue";
import * as echarts from "echarts";
import {
  fetchAblationResults,
  fetchExperimentStatistics,
} from "../api";

const dataSource = ref("pending");
const paretoChart = ref(null);
const convergeChart = ref(null);
const metricChart = ref(null);
const hasParetoData = ref(false);
const hasConvergenceData = ref(false);
const ablationData = ref([]);
const statsData = ref([]);

const kpis = ref({ hvImprove: "-", feasibility: "-", f1Drop: "-", f2Drop: "-" });
const displayPercent = (value, prefix = "") => {
  const number = Number(value);
  return Number.isFinite(number) ? `${prefix}${number.toFixed(1)}%` : "-";
};

// ============ 数据归一化（兼容后端字段） ============
function normalizeAblation(list) {
  const records = Array.isArray(list) ? list : (Array.isArray(list?.results) ? list.results : []);
  if (!records.length) return [];
  return records.map((item) => {
    const cfg = item.config && typeof item.config === "object" ? item.config : {};
    const m = item.metrics || {};
    const num = (v, digits = 3) => {
      const number = Number(v);
      return Number.isFinite(number) ? number.toFixed(digits) : "-";
    };
    const pct = (v) => {
      const number = Number(v);
      return Number.isFinite(number) ? (number * 100).toFixed(1) + "%" : "-";
    };
    const f1 = m.f1_mean ?? m.f1;
    const f2 = m.f2_mean ?? m.f2;
    const hasMetrics = [m.feasibility_rate, f1, f2, m.hv, m.igd, m.spacing]
      .some((value) => Number.isFinite(Number(value)));
    if (!hasMetrics) return null;
    const rawPareto = Array.isArray(item.pareto) ? item.pareto : [];
    const rawConvergence = Array.isArray(item.convergence) ? item.convergence : [];
    return {
      name: cfg.name || item.name || "config",
      init:
        cfg.init ||
        (String(cfg.name || "").includes("chaos") ? "logistic" : "random"),
      operators:
        cfg.operators ||
        cfg.description ||
        (String(cfg.name || "").includes("levy") ? "SBX+Levy" : "SBX+PM"),
      feasibility_rate: pct(m.feasibility_rate ?? m.feasibility),
      f1_mean: num(f1),
      f2_mean: num(f2, 0),
      hv: num(m.hv),
      igd: num(m.igd),
      spacing: num(m.spacing ?? m.spacing_mean),
      status: item.status || "complete",
      pareto: rawPareto.filter((point) => Array.isArray(point) && point.length >= 2 &&
        Number.isFinite(Number(point[0])) && Number.isFinite(Number(point[1]))),
      convergence: rawConvergence.filter((point) => Array.isArray(point) && point.length >= 2 &&
        Number.isFinite(Number(point[0])) && Number.isFinite(Number(point[1]))),
    };
  }).filter(Boolean);
}

function formatP(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "-";
  return number < 0.001 ? "<0.001" : number.toFixed(3);
}

function normalizeStatistics(payload) {
  const direct = payload?.frontend || payload?.wilcoxon;
  if (Array.isArray(direct)) {
    return direct.map((row) => ({
      comparison: row.comparison || row.name || "-",
      p_f1: formatP(row.p_f1 ?? row.p_f1_mean),
      p_f2: formatP(row.p_f2 ?? row.p_f2_mean),
      p_feas: formatP(row.p_feas ?? row.p_feasibility_rate),
      cohens_d: Number.isFinite(Number(row.cohens_d)) ? Number(row.cohens_d).toFixed(2) : "-",
    }));
  }
  const statistics = payload?.statistics;
  if (!statistics || typeof statistics !== "object") return [];
  const grouped = new Map();
  for (const [metric, block] of Object.entries(statistics)) {
    const pairs = Array.isArray(block?.pairwise_vs_baseline) ? block.pairwise_vs_baseline : [];
    for (const pair of pairs) {
      const comparison = pair.comparison || pair.name || "-";
      const row = grouped.get(comparison) || {
        comparison, p_f1: "-", p_f2: "-", p_feas: "-", cohens_d: "-",
      };
      const p = pair.p_value_holm ?? pair.p_value;
      if (metric === "f1_mean") row.p_f1 = formatP(p);
      if (metric === "f2_mean") row.p_f2 = formatP(p);
      if (metric === "feasibility_rate") row.p_feas = formatP(p);
      if (metric === "f1_mean" && Number.isFinite(Number(pair.effect_size))) {
        row.cohens_d = Number(pair.effect_size).toFixed(2);
      }
      grouped.set(comparison, row);
    }
  }
  return [...grouped.values()];
}

// ============ 图表：只使用真实实验记录 ============
function renderCharts() {
  const rows = ablationData.value || [];
  if (!rows.length) return;
  if (hasParetoData.value && paretoChart.value) {
    const pChart = echarts.getInstanceByDom(paretoChart.value) || echarts.init(paretoChart.value);
    pChart.setOption({
      tooltip: { trigger: "item", formatter: (point) => `f1=${point.value[0]} · f2=${point.value[1]}` },
      legend: { data: rows.filter((row) => row.pareto.length).map((row) => row.name), textStyle: { color: "#ccc" } },
      grid: { left: 60, right: 30, top: 40, bottom: 55 },
      xAxis: { name: "f1", axisLine: { lineStyle: { color: "#444" } } },
      yAxis: { name: "f2", axisLine: { lineStyle: { color: "#444" } } },
      backgroundColor: "#1a1a2e",
      series: rows.filter((row) => row.pareto.length).map((row, index) => ({
        name: row.name, type: "scatter", data: row.pareto,
        itemStyle: { color: ["#e74c3c", "#2ecc71", "#3498db", "#f39c12"][index % 4] },
      })),
    });
  }
  if (hasConvergenceData.value && convergeChart.value) {
    const cChart = echarts.getInstanceByDom(convergeChart.value) || echarts.init(convergeChart.value);
    cChart.setOption({
      tooltip: { trigger: "axis" },
      legend: { data: rows.filter((row) => row.convergence.length).map((row) => row.name), textStyle: { color: "#ccc" }, top: 0 },
      grid: { left: 50, right: 30, top: 40, bottom: 45 },
      xAxis: { name: "代数", axisLine: { lineStyle: { color: "#444" } } },
      yAxis: { name: "HV", axisLine: { lineStyle: { color: "#444" } } },
      backgroundColor: "#1a1a2e",
      series: rows.filter((row) => row.convergence.length).map((row) => ({
        name: row.name, type: "line", data: row.convergence, showSymbol: false,
      })),
    });
  }
  if (!metricChart.value) return;
  const metricRows = rows.map((row) => ({
    name: row.name,
    hv: row.hv === "-" ? null : Number(row.hv),
    igd: row.igd === "-" ? null : Number(row.igd),
    spacing: row.spacing === "-" ? null : Number(row.spacing),
  }));
  const mChart = echarts.getInstanceByDom(metricChart.value) || echarts.init(metricChart.value);
  mChart.setOption({
    tooltip: { trigger: "axis" },
    legend: { data: ["HV", "IGD", "Spacing"], textStyle: { color: "#ccc" }, top: 0 },
    grid: { left: 60, right: 30, top: 40, bottom: 70 },
    xAxis: {
      type: "category",
      data: metricRows.map((row) => row.name),
      axisLabel: { color: "#ccc", rotate: 20 },
      axisLine: { lineStyle: { color: "#444" } },
    },
    yAxis: { type: "value", name: "指标值", nameTextStyle: { color: "#999" }, axisLine: { lineStyle: { color: "#444" } } },
    backgroundColor: "#1a1a2e",
    series: [
      { name: "HV", type: "bar", data: metricRows.map((row) => row.hv), itemStyle: { color: "#2ecc71" } },
      { name: "IGD", type: "line", data: metricRows.map((row) => row.igd), itemStyle: { color: "#e74c3c" } },
      { name: "Spacing", type: "line", data: metricRows.map((row) => row.spacing), itemStyle: { color: "#f39c12" } },
    ],
  });
}

function sigClass(val) {
  if (!val || val === "-") return "";
  const n = parseFloat(val);
  if (n < 0.001) return "sig-high";
  if (n < 0.01) return "sig-mid";
  if (n < 0.05) return "sig-low";
  return "";
}

// ============ 加载：优先后端真实数据 ============
async function loadData() {
  try {
    const [ab, st] = await Promise.allSettled([
      fetchAblationResults(),
      fetchExperimentStatistics(),
    ]);
    const abRes = ab.status === "fulfilled" ? ab.value : null;
    const stRes = st.status === "fulfilled" ? st.value : null;
    const normalized = normalizeAblation(abRes?.data);
    if (normalized.length) {
      ablationData.value = normalized;
      dataSource.value = "live";
      hasParetoData.value = normalized.some((row) => row.pareto.length);
      hasConvergenceData.value = normalized.some((row) => row.convergence.length);
      // KPI 只从真实有限指标计算，缺失时保持 "-"。
      const a0 = normalized.find((r) => String(r.name).includes("A0"));
      const a4 = normalized.find((r) => String(r.name).includes("A4"));
      if (a0 && a4) {
        const f1a = parseFloat(a0.f1_mean);
        const f14 = parseFloat(a4.f1_mean);
        const f2a = parseFloat(a0.f2_mean);
        const f24 = parseFloat(a4.f2_mean);
        if (!Number.isNaN(f1a) && !Number.isNaN(f14) && f1a !== 0)
          kpis.value.f1Drop = (((f1a - f14) / f1a) * 100).toFixed(1);
        if (!Number.isNaN(f2a) && !Number.isNaN(f24) && f2a !== 0)
          kpis.value.f2Drop = (((f2a - f24) / f2a) * 100).toFixed(1);
        if (a0.hv !== "-" && a4.hv !== "-" && parseFloat(a0.hv) !== 0) {
          const hv0 = parseFloat(a0.hv);
          const hv4 = parseFloat(a4.hv);
          kpis.value.hvImprove = (((hv4 - hv0) / hv0) * 100).toFixed(1);
        }
        kpis.value.feasibility = a4.feasibility_rate;
      }
    }
    statsData.value = normalizeStatistics(stRes?.data);
  } catch (e) {
    console.warn("[ExperimentResults] 真实实验结果加载失败", e);
  }
  await nextTick();
  renderCharts();
}

onMounted(() => {
  loadData();
  window.addEventListener("resize", () => {
    [paretoChart, convergeChart, metricChart].forEach((r) => {
      if (r.value) echarts.getInstanceByDom(r.value)?.resize();
    });
  });
});
</script>

<style scoped>
.experiment-page {
  padding: 24px;
  color: #e0e0e0;
  max-width: 1400px;
  margin: 0 auto;
}
.page-head {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 6px;
}
.page-head h2 {
  margin: 0;
  color: #eee;
}
.data-badge {
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 11px;
  border: 1px solid;
}
.data-badge.pending {
  color: #f39c12;
  border-color: rgba(243, 156, 18, 0.5);
  background: rgba(243, 156, 18, 0.08);
}
.data-badge.live {
  color: #2ecc71;
  border-color: rgba(46, 204, 113, 0.5);
  background: rgba(46, 204, 113, 0.08);
}
.subtitle {
  color: #888;
  margin-bottom: 24px;
}
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 28px;
}
.kpi-card {
  padding: 18px 20px;
  background: rgba(22, 33, 62, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  text-align: center;
}
.kpi-label {
  color: #999;
  font-size: 12px;
  margin-bottom: 8px;
}
.kpi-val {
  font-size: 28px;
  font-weight: 700;
}
.kpi-unit {
  color: #777;
  font-size: 11px;
  margin-top: 4px;
}
.section {
  margin-bottom: 32px;
}
.section h3,
.chart-box h3 {
  color: #ccc;
  margin-bottom: 12px;
  border-left: 3px solid #2ecc71;
  padding-left: 8px;
  font-size: 14px;
}
.table-wrapper {
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
th,
td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid #333;
}
th {
  background: #16213e;
  color: #999;
  position: sticky;
  top: 0;
}
tr:hover {
  background: rgba(46, 204, 113, 0.1);
}
.highlight {
  background: rgba(46, 204, 113, 0.15);
}
.sig-high {
  color: #2ecc71;
  font-weight: bold;
}
.sig-mid {
  color: #3498db;
}
.sig-low {
  color: #f39c12;
}
.chart-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
.chart-box {
  background: rgba(26, 26, 46, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  padding: 14px;
}
.chart {
  width: 100%;
  height: 400px;
}
.chart-empty,
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 120px;
  padding: 18px;
  border: 1px dashed rgba(255, 255, 255, 0.16);
  color: #888;
  text-align: center;
}
.chart-empty {
  height: 400px;
  box-sizing: border-box;
}
.compact-empty {
  min-height: 70px;
}
.note {
  margin-top: 32px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  color: #666;
  font-size: 12px;
}
@media (max-width: 900px) {
  .kpi-row {
    grid-template-columns: repeat(2, 1fr);
  }
  .chart-grid {
    grid-template-columns: 1fr;
  }
}
</style>
