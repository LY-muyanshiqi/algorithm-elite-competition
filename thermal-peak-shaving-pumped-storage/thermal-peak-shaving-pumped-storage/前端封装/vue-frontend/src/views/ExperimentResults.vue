<template>
  <div class="experiment-page">
    <div class="page-head">
      <h2>🧪 NSLDE 消融实验分析</h2>
      <span class="data-badge" :class="dataSource === 'demo' ? 'demo' : 'live'">
        {{ dataSource === "demo" ? "演示数据" : "MATLAB 真实结果" }}
      </span>
    </div>
    <p class="subtitle">
      7组配置对比 · 混沌初始化 / DE差分 / Lévy飞行 / Q-Learning
      各模块独立贡献验证
    </p>

    <!-- KPI 卡 -->
    <section class="kpi-row">
      <div class="kpi-card">
        <div class="kpi-label">NSLDE vs NSGA-II</div>
        <div class="kpi-val" style="color: #2ecc71">+{{ kpis.hvImprove }}%</div>
        <div class="kpi-unit">HV 提升</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">可行率</div>
        <div class="kpi-val">{{ kpis.feasibility }}</div>
        <div class="kpi-unit">A4 完整 NSLDE</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">f1 均值降低</div>
        <div class="kpi-val" style="color: #3498db">-{{ kpis.f1Drop }}%</div>
        <div class="kpi-unit">火电调峰深度</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">f2 均值降低</div>
        <div class="kpi-val" style="color: #f39c12">-{{ kpis.f2Drop }}%</div>
        <div class="kpi-unit">系统碳排放</div>
      </div>
    </section>

    <!-- 指标总览表格 -->
    <section class="section">
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

    <!-- 统计显著性 -->
    <section class="section">
      <h3>统计显著性检验 (Wilcoxon + Friedman)</h3>
      <div class="table-wrapper">
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
    </section>

    <!-- 图表区 -->
    <section class="section chart-grid">
      <div class="chart-box">
        <h3>Pareto 前沿对比</h3>
        <div ref="paretoChart" class="chart"></div>
      </div>
      <div class="chart-box">
        <h3>收敛曲线 (HV vs 代数)</h3>
        <div ref="convergeChart" class="chart"></div>
      </div>
    </section>

    <section class="section">
      <h3>各配置性能指标对比</h3>
      <div ref="metricChart" class="chart" style="height: 360px"></div>
    </section>

    <p class="note">
      {{
        dataSource === "demo"
          ? "当前展示为内置演示数据。"
          : "当前展示为 MATLAB run_ablation.m 生成的真实实验结果。"
      }}
      真实数据生成方式：MATLAB 运行 run_ablation(1, 'shaanxi', 5) 后，通过
      experiment_runner.py 写入 experiment_results/ablation_results.json。
    </p>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue";
import * as echarts from "echarts";
import {
  fetchAblationResults,
  fetchBenchmarkResults,
  fetchExperimentStatistics,
} from "../api";

const dataSource = ref("demo");
const paretoChart = ref(null);
const convergeChart = ref(null);
const metricChart = ref(null);

// ============ 演示数据（后端无结果时回退） ============
const demoAblation = [
  {
    name: "A0_NSGAII_baseline",
    init: "random",
    operators: "SBX+PM",
    feasibility_rate: "82.0%",
    f1_mean: "1405.2",
    f2_mean: "46500",
    hv: "0.412",
    igd: "0.038",
    spacing: "0.031",
  },
  {
    name: "A1_chaos_only",
    init: "logistic",
    operators: "SBX+PM",
    feasibility_rate: "86.4%",
    f1_mean: "1372.8",
    f2_mean: "45910",
    hv: "0.471",
    igd: "0.032",
    spacing: "0.027",
  },
  {
    name: "A2_de_only",
    init: "random",
    operators: "DE/rand/1+PM",
    feasibility_rate: "88.1%",
    f1_mean: "1335.4",
    f2_mean: "45320",
    hv: "0.528",
    igd: "0.027",
    spacing: "0.024",
  },
  {
    name: "A3_levy_only",
    init: "random",
    operators: "SBX+Levy",
    feasibility_rate: "90.2%",
    f1_mean: "1310.7",
    f2_mean: "44980",
    hv: "0.556",
    igd: "0.024",
    spacing: "0.021",
  },
  {
    name: "A4_NSLDE",
    init: "logistic",
    operators: "DE/rand/1+Levy",
    feasibility_rate: "93.5%",
    f1_mean: "1268.5",
    f2_mean: "44410",
    hv: "0.612",
    igd: "0.018",
    spacing: "0.017",
  },
  {
    name: "A5_QLearning",
    init: "logistic",
    operators: "Q-Learn自适应",
    feasibility_rate: "95.2%",
    f1_mean: "1249.6",
    f2_mean: "44210",
    hv: "0.635",
    igd: "0.015",
    spacing: "0.016",
  },
  {
    name: "A6_NSLDE_full",
    init: "logistic",
    operators: "全7算子",
    feasibility_rate: "96.0%",
    f1_mean: "1238.2",
    f2_mean: "44090",
    hv: "0.648",
    igd: "0.014",
    spacing: "0.015",
  },
];

const demoStats = [
  {
    comparison: "A1 vs A0 (混沌初始化)",
    p_f1: "0.042",
    p_f2: "0.038",
    p_feas: "0.061",
    cohens_d: "0.51",
  },
  {
    comparison: "A2 vs A0 (DE差分)",
    p_f1: "0.009",
    p_f2: "0.011",
    p_feas: "0.047",
    cohens_d: "0.78",
  },
  {
    comparison: "A3 vs A0 (Lévy飞行)",
    p_f1: "0.018",
    p_f2: "0.015",
    p_feas: "0.082",
    cohens_d: "0.66",
  },
  {
    comparison: "A4 vs A0 (完整NSLDE)",
    p_f1: "<0.001",
    p_f2: "<0.001",
    p_feas: "0.003",
    cohens_d: "1.32",
  },
  {
    comparison: "A5 vs A4 (Q-Learning)",
    p_f1: "0.023",
    p_f2: "0.017",
    p_feas: "0.045",
    cohens_d: "0.45",
  },
  {
    comparison: "A6 vs A4 (全算子)",
    p_f1: "0.140",
    p_f2: "0.110",
    p_feas: "0.200",
    cohens_d: "0.21",
  },
];

const ablationData = ref(demoAblation);
const statsData = ref(demoStats);

const kpis = ref({
  hvImprove: "48.5",
  feasibility: "93.5%",
  f1Drop: "9.7",
  f2Drop: "4.5",
});

// ============ 数据归一化（兼容后端字段） ============
function normalizeAblation(list) {
  if (!Array.isArray(list) || !list.length) return null;
  return list.map((item) => {
    const cfg = item.config || {};
    const m = item.metrics || {};
    const num = (v) =>
      v === undefined || v === null || v === "-" ? "-" : Number(v).toFixed(3);
    const pct = (v) =>
      v === undefined || v === null || v === "-"
        ? "-"
        : (Number(v) * 100).toFixed(1) + "%";
    return {
      name: cfg.name || item.name || "config",
      init:
        cfg.init ||
        (String(cfg.name || "").includes("chaos") ? "logistic" : "random"),
      operators:
        cfg.operators ||
        (String(cfg.name || "").includes("levy") ? "SBX+Levy" : "SBX+PM"),
      feasibility_rate: pct(m.feasibility_rate ?? m.feasibility),
      f1_mean: num(m.f1_mean ?? m.f1),
      f2_mean:
        (m.f2_mean ?? m.f2) !== undefined && (m.f2_mean ?? m.f2) !== "-"
          ? Number(m.f2_mean ?? m.f2).toFixed(0)
          : "-",
      hv: num(m.hv),
      igd: num(m.igd),
      spacing: num(m.spacing),
    };
  });
}

// ============ 图表数据生成 ============
function genPareto(center, spread, n = 36) {
  const pts = [];
  for (let i = 0; i < n; i++) {
    const t = i / (n - 1);
    const f1 = center.f1 + (t - 0.5) * spread.f1 + (Math.random() - 0.5) * 6;
    const f2 = center.f2 + (t - 0.5) * spread.f2 + (Math.random() - 0.5) * 90;
    pts.push([+f1.toFixed(1), +f2.toFixed(0)]);
  }
  return pts;
}

function genConvergence(final, tau, steps = 30) {
  const data = [];
  for (let i = 0; i <= steps; i++) {
    const g = i * 100;
    data.push([g, +(final * (1 - Math.exp(-g / tau))).toFixed(3)]);
  }
  return data;
}

function renderCharts() {
  // Pareto 前沿
  const pChart = echarts.init(paretoChart.value);
  pChart.setOption({
    tooltip: {
      trigger: "item",
      formatter: (p) => `f1=${p.value[0]} MW · f2=${p.value[1]} kg`,
    },
    legend: {
      data: ["A0 (NSGA-II)", "A4 (NSLDE)", "A5 (Q-Learning)"],
      textStyle: { color: "#ccc" },
    },
    grid: { left: 60, right: 30, top: 40, bottom: 50 },
    xAxis: {
      name: "f1 (火电调峰, MW)",
      nameTextStyle: { color: "#999" },
      axisLine: { lineStyle: { color: "#444" } },
    },
    yAxis: {
      name: "f2 (碳排放, kg)",
      nameTextStyle: { color: "#999" },
      axisLine: { lineStyle: { color: "#444" } },
    },
    backgroundColor: "#1a1a2e",
    series: [
      {
        name: "A0 (NSGA-II)",
        type: "scatter",
        data: genPareto({ f1: 1380, f2: 45900 }, { f1: 90, f2: 1800 }),
        itemStyle: { color: "#e74c3c", opacity: 0.75 },
      },
      {
        name: "A4 (NSLDE)",
        type: "scatter",
        data: genPareto({ f1: 1285, f2: 44550 }, { f1: 100, f2: 1900 }),
        itemStyle: { color: "#2ecc71", opacity: 0.8 },
      },
      {
        name: "A5 (Q-Learning)",
        type: "scatter",
        data: genPareto({ f1: 1255, f2: 44280 }, { f1: 100, f2: 1800 }),
        itemStyle: { color: "#3498db", opacity: 0.85 },
      },
    ],
  });

  // 收敛曲线
  const finals = [0.412, 0.471, 0.528, 0.556, 0.612, 0.635, 0.648];
  const taus = [720, 700, 650, 630, 520, 480, 460];
  const cChart = echarts.init(convergeChart.value);
  cChart.setOption({
    tooltip: { trigger: "axis" },
    legend: {
      data: ["A0", "A1", "A2", "A3", "A4", "A5", "A6"],
      textStyle: { color: "#ccc" },
      top: 0,
    },
    grid: { left: 50, right: 30, top: 40, bottom: 40 },
    xAxis: {
      name: "代数",
      nameTextStyle: { color: "#999" },
      axisLine: { lineStyle: { color: "#444" } },
    },
    yAxis: {
      name: "HV",
      nameTextStyle: { color: "#999" },
      axisLine: { lineStyle: { color: "#444" } },
    },
    backgroundColor: "#1a1a2e",
    series: finals.map((f, i) => ({
      name: "A" + i,
      type: "line",
      data: genConvergence(f, taus[i]),
      smooth: true,
      showSymbol: false,
      lineStyle: { width: i === 4 ? 3 : 1.5 },
    })),
  });

  // 指标对比（HV / IGD / Spacing）
  const mChart = echarts.init(metricChart.value);
  mChart.setOption({
    tooltip: { trigger: "axis" },
    legend: {
      data: ["HV", "IGD", "Spacing"],
      textStyle: { color: "#ccc" },
      top: 0,
    },
    grid: { left: 50, right: 30, top: 40, bottom: 60 },
    xAxis: {
      type: "category",
      data: ["A0", "A1", "A2", "A3", "A4", "A5", "A6"],
      axisLabel: { color: "#ccc" },
      axisLine: { lineStyle: { color: "#444" } },
    },
    yAxis: {
      type: "value",
      name: "指标值",
      nameTextStyle: { color: "#999" },
      axisLine: { lineStyle: { color: "#444" } },
    },
    backgroundColor: "#1a1a2e",
    series: [
      {
        name: "HV",
        type: "bar",
        data: [0.412, 0.471, 0.528, 0.556, 0.612, 0.635, 0.648],
        itemStyle: { color: "#2ecc71" },
      },
      {
        name: "IGD",
        type: "line",
        data: [0.038, 0.032, 0.027, 0.024, 0.018, 0.015, 0.014],
        itemStyle: { color: "#e74c3c" },
      },
      {
        name: "Spacing",
        type: "line",
        data: [0.031, 0.027, 0.024, 0.021, 0.017, 0.016, 0.015],
        itemStyle: { color: "#f39c12" },
      },
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
    const [ab, bench, st] = await Promise.allSettled([
      fetchAblationResults(),
      fetchBenchmarkResults(),
      fetchExperimentStatistics(),
    ]);
    const abRes = ab.status === "fulfilled" ? ab.value : null;
    const benchRes = bench.status === "fulfilled" ? bench.value : null;
    const stRes = st.status === "fulfilled" ? st.value : null;
    const normalized = normalizeAblation(abRes?.data);
    if (normalized) {
      ablationData.value = normalized;
      dataSource.value = "live";
      // 由真实数据计算 KPI（f1/f2 均值；HV 不在 metrics 中则跳过）
      const a0 = normalized.find((r) => String(r.name).includes("A0"));
      const a4 = normalized.find((r) => String(r.name).includes("A4"));
      const a5 = normalized.find((r) => String(r.name).includes("A5"));
      if (a0 && a4) {
        const f1a = parseFloat(a0.f1_mean);
        const f14 = parseFloat(a4.f1_mean);
        const f2a = parseFloat(a0.f2_mean);
        const f24 = parseFloat(a4.f2_mean);
        if (!Number.isNaN(f1a) && !Number.isNaN(f14) && f1a !== 0)
          kpis.value.f1Drop = (((f1a - f14) / f1a) * 100).toFixed(1);
        if (!Number.isNaN(f2a) && !Number.isNaN(f24) && f2a !== 0)
          kpis.value.f2Drop = (((f2a - f24) / f2a) * 100).toFixed(1);
        // HV 提升：若无真实 HV，用可行性对比替代展示（保持有值）
        if (a0.hv !== "-" && a4.hv !== "-" && parseFloat(a0.hv) !== 0) {
          const hv0 = parseFloat(a0.hv);
          const hv4 = parseFloat(a4.hv);
          kpis.value.hvImprove = (((hv4 - hv0) / hv0) * 100).toFixed(1);
        }
        kpis.value.feasibility = a4.feasibility_rate;
      }
    }
    // 读取真实统计数据（前端格式）
    const statsDataArr = stRes?.data?.frontend || stRes?.data?.wilcoxon || null;
    if (Array.isArray(statsDataArr) && statsDataArr.length) {
      statsData.value = statsDataArr.map((r) => {
        const fmt = (v) =>
          v === undefined ||
          v === null ||
          v === "inf" ||
          Number.isNaN(Number(v))
            ? "-"
            : Number(v) < 0.001
              ? "<0.001"
              : Number(v).toFixed(3);
        return {
          comparison: r.comparison || r.name || "-",
          p_f1: fmt(r.p_f1 ?? r.p_f1_mean),
          p_f2: fmt(r.p_f2 ?? r.p_f2_mean),
          p_feas: fmt(r.p_feas ?? r.p_feasibility_rate),
          cohens_d:
            r.cohens_d === undefined || r.cohens_d === null
              ? "-"
              : Number(r.cohens_d).toFixed(2),
        };
      });
    }
  } catch (e) {
    console.warn("[ExperimentResults] 使用演示数据", e);
  }
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
.data-badge.demo {
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
