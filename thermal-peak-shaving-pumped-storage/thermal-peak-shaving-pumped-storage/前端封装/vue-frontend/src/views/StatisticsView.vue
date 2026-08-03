<template>
  <div class="stats-page">
    <div class="page-header">
      <h2>📊 统计与相关性分析</h2>
      <p class="page-desc">全年8760小时数据的分布特征、相关性矩阵与统计指标</p>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>计算中...</p>
    </div>

    <template v-if="!loading">
      <!-- 描述性统计表 -->
      <div class="section-card">
        <h3>📋 描述性统计</h3>
        <div class="table-wrap">
          <table class="stats-table">
            <thead>
              <tr>
                <th>指标</th>
                <th>风电</th>
                <th>光伏</th>
                <th>水电</th>
                <th>火电负荷</th>
                <th>抽水蓄能</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in descTable" :key="row.name">
                <td class="row-name">{{ row.name }}</td>
                <td v-for="v in row.vals" :key="v" class="row-val">{{ v }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 相关性热力图 -->
      <div class="row-2col">
        <div class="section-card">
          <h3>🔗 相关性矩阵</h3>
          <div ref="corrChartRef" class="chart-md"></div>
          <div class="corr-notes">
            <span v-for="(v, k) in corrPairs" :key="k" class="corr-chip">
              {{ k }}:
              <strong
                :style="{
                  color: v > 0.5 ? '#00ff88' : v > 0.3 ? '#ffcc00' : '#ff6b6b',
                }"
                >{{ v.toFixed(3) }}</strong
              >
            </span>
          </div>
        </div>
        <div class="section-card">
          <h3>📈 分布直方图</h3>
          <div class="ctrl-inline">
            <select v-model="histKey" class="sel-sm">
              <option value="wind">风电</option>
              <option value="solar">光伏</option>
              <option value="hydro">水电</option>
              <option value="fh">火电</option>
              <option value="np_raw">抽蓄</option>
            </select>
            <span class="hist-info"
              >均值: <strong>{{ histStats.avg.toFixed(1) }}</strong> &nbsp;
              标准差: <strong>{{ histStats.std.toFixed(1) }}</strong></span
            >
          </div>
          <div ref="histChartRef" class="chart-md"></div>
        </div>
      </div>

      <!-- 分位数分析 -->
      <div class="section-card">
        <h3>🎯 分位数分析</h3>
        <div ref="quantileChartRef" class="chart-lg"></div>
      </div>

      <!-- ===== 新增：分布拟合检验 ===== -->
      <div class="section-card">
        <h3>📐 分布拟合检验</h3>
        <p class="section-desc">
          自动判断数据最符合哪种统计分布，并绘制拟合曲线
        </p>
        <div class="ctrl-inline">
          <select v-model="distKey" class="sel-sm">
            <option value="wind">风电</option>
            <option value="solar">光伏</option>
            <option value="hydro">水电</option>
            <option value="fh">火电</option>
            <option value="np_raw">抽蓄</option>
          </select>
          <span class="dist-result" v-if="distFitResult">
            🏆 最佳拟合:
            <strong :style="{ color: '#00ff88' }">{{
              distFitResult.best
            }}</strong>
            &nbsp;|&nbsp; 正态 LL:
            {{ distFitResult.normalLL.toFixed(0) }} &nbsp;|&nbsp; 对数正态 LL:
            {{ distFitResult.lognormalLL.toFixed(0) }}
          </span>
        </div>
        <div ref="distFitChartRef" class="chart-md"></div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from "vue";
import * as echarts from "echarts";
import { fetchAllData } from "../api";

const loading = ref(true);
const allData = ref(null);
const histKey = ref("wind");
const corrChartRef = ref(null);
const histChartRef = ref(null);
const quantileChartRef = ref(null);
const distFitChartRef = ref(null);
const corrChart = ref(null);
const histChart = ref(null);
const quantileChart = ref(null);
const distFitChart = ref(null);
const distKey = ref("wind");

const keys = ["wind", "solar", "hydro", "fh", "np_raw"];
const labels = {
  wind: "风电",
  solar: "光伏",
  hydro: "水电",
  fh: "火电",
  np_raw: "抽蓄",
};

const descTable = ref([]);
const corrPairs = ref({});
const histStats = ref({ avg: 0, std: 0 });
const distFitResult = ref(null);

function calcDesc(data) {
  const flat = data.flat();
  const sorted = [...flat].sort((a, b) => a - b);
  const n = flat.length;
  const sum = flat.reduce((a, b) => a + b, 0);
  const avg = sum / n;
  const variance = flat.reduce((a, b) => a + (b - avg) ** 2, 0) / n;
  const std = Math.sqrt(variance);
  const skew = flat.reduce((a, b) => a + ((b - avg) / std) ** 3, 0) / n;
  const p1 = sorted[Math.floor(n * 0.01)];
  const p5 = sorted[Math.floor(n * 0.05)];
  const p25 = sorted[Math.floor(n * 0.25)];
  const p50 = sorted[Math.floor(n * 0.5)];
  const p75 = sorted[Math.floor(n * 0.75)];
  const p95 = sorted[Math.floor(n * 0.95)];
  const p99 = sorted[Math.floor(n * 0.99)];
  return {
    min: sorted[0],
    max: sorted[n - 1],
    avg,
    std,
    skew,
    p1,
    p5,
    p25,
    median: p50,
    p75,
    p95,
    p99,
  };
}

function calcCorr(x, y) {
  const n = x.length;
  const mx = x.reduce((a, b) => a + b, 0) / n;
  const my = y.reduce((a, b) => a + b, 0) / n;
  const cov = x.reduce((a, b, i) => a + (b - mx) * (y[i] - my), 0) / n;
  const sx = Math.sqrt(x.reduce((a, b) => a + (b - mx) ** 2, 0) / n);
  const sy = Math.sqrt(y.reduce((a, b) => a + (b - my) ** 2, 0) / n);
  const r = cov / (sx * sy + 1e-10);
  return isNaN(r) || !isFinite(r) ? 0 : r;
}

onMounted(async () => {
  try {
    allData.value = await fetchAllData();
    const d = allData.value;
    loading.value = false;
    await nextTick();

    // 描述性统计表
    const rows = [];
    const fields = [
      "min",
      "p1",
      "p5",
      "p25",
      "median",
      "avg",
      "p75",
      "p95",
      "p99",
      "max",
      "std",
      "skew",
    ];
    const fieldLabels = {
      min: "最小值",
      p1: "1%分位",
      p5: "5%分位",
      p25: "25%分位",
      median: "中位数",
      avg: "平均值",
      p75: "75%分位",
      p95: "95%分位",
      p99: "99%分位",
      max: "最大值",
      std: "标准差",
      skew: "偏度",
    };
    const stats = {};
    for (const k of keys) {
      stats[k] = calcDesc(d[k]);
    }
    for (const f of fields) {
      rows.push({
        name: fieldLabels[f],
        vals: keys.map((k) => stats[k][f].toFixed(1)),
      });
    }
    descTable.value = rows;

    // 相关性
    const flat = {};
    for (const k of keys) {
      flat[k] = d[k].flat();
    }
    const pairs = {};
    for (let i = 0; i < keys.length; i++) {
      for (let j = i + 1; j < keys.length; j++) {
        const ki = keys[i],
          kj = keys[j];
        pairs[`${labels[ki]}-${labels[kj]}`] = calcCorr(flat[ki], flat[kj]);
      }
    }
    corrPairs.value = pairs;

    // 初始化图表
    initCorrChart(stats);
    refreshHistogram();
    initQuantileChart(stats);
    nextTick(() => initDistFit());
  } catch (e) {
    console.error(e);
    loading.value = false;
  }
});

onBeforeUnmount(() => {
  [corrChart, histChart, quantileChart, distFitChart].forEach((ref) => {
    ref.value?.dispose();
    ref.value = null;
  });
});

function initCorrChart(stats) {
  if (!corrChartRef.value) return;
  corrChart.value = echarts.init(corrChartRef.value);
  const matrix = keys.map((k1) =>
    keys.map((k2) => {
      if (k1 === k2) return 1;
      const f1 = allData.value[k1].flat(),
        f2 = allData.value[k2].flat();
      const mx = f1.reduce((a, b) => a + b, 0) / f1.length;
      const my = f2.reduce((a, b) => a + b, 0) / f2.length;
      const cov =
        f1.reduce((a, b, i) => a + (b - mx) * (f2[i] - my), 0) / f1.length;
      const sx =
        Math.sqrt(f1.reduce((a, b) => a + (b - mx) ** 2, 0) / f1.length) +
        1e-10;
      const sy =
        Math.sqrt(f2.reduce((a, b) => a + (b - my) ** 2, 0) / f2.length) +
        1e-10;
      const r = cov / (sx * sy);
      return isNaN(r) || !isFinite(r) ? 0 : r;
    }),
  );
  corrChart.value.setOption({
    backgroundColor: "transparent",
    tooltip: {
      formatter: (p) =>
        `${labels[keys[p.value[0]]]} - ${labels[keys[p.value[1]]]}: <strong>${matrix[p.value[0]][p.value[1]].toFixed(3)}</strong>`,
    },
    grid: { left: 60, right: 40, top: 20, bottom: 50 },
    xAxis: {
      type: "category",
      data: keys.map((k) => labels[k]),
      splitArea: { show: true },
      axisLabel: { color: "#8ba4c4" },
    },
    yAxis: {
      type: "category",
      data: keys.map((k) => labels[k]),
      splitArea: { show: true },
      axisLabel: { color: "#8ba4c4" },
    },
    visualMap: {
      min: -1,
      max: 1,
      calculable: false,
      orient: "horizontal",
      left: "center",
      bottom: 5,
      inRange: { color: ["#ff6b6b", "#0a1628", "#00ff88"] },
      textStyle: { color: "#8ba4c4" },
    },
    series: [
      {
        type: "heatmap",
        data: matrix.flatMap((row, i) => row.map((v, j) => [j, i, v])),
        label: {
          show: true,
          color: "#e0e6ed",
          fontSize: 11,
          formatter: (p) => p.value[2].toFixed(2),
        },
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowColor: "rgba(0,0,0,0.5)" },
        },
      },
    ],
  });
}

watch(histKey, () => {
  if (!allData.value) return;
  refreshHistogram();
  nextTick(() => initDistFit());
});

watch(distKey, () => {
  nextTick(() => initDistFit());
});

function refreshHistogram() {
  if (!allData.value) return;
  const data = allData.value[histKey.value].flat();
  const sorted = [...data].sort((a, b) => a - b);
  const avg = data.reduce((a, b) => a + b, 0) / data.length;
  const std = Math.sqrt(
    data.reduce((a, b) => a + (b - avg) ** 2, 0) / data.length,
  );
  histStats.value = { avg, std };
  const min = sorted[0],
    max = sorted[sorted.length - 1];
  const binCount = 40,
    rawBinWidth = (max - min) / binCount;
  // 处理常数数据（如水电全为 1600.0）：强制分箱宽度为 1
  const binWidth = rawBinWidth > 0 ? rawBinWidth : 1;
  const bins = Array.from({ length: binCount }, (_, i) => ({
    min: min + i * binWidth,
    max: min + (i + 1) * binWidth,
    count: 0,
  }));
  for (const v of data) {
    const idx = Math.min(
      Math.max(Math.floor((v - min) / binWidth), 0),
      binCount - 1,
    );
    bins[idx].count++;
  }
  nextTick(() => {
    if (!histChartRef.value) return;
    let chart = echarts.getInstanceByDom(histChartRef.value);
    if (!chart) {
      histChart.value = echarts.init(histChartRef.value);
      chart = histChart.value;
    }
    chart.setOption({
      backgroundColor: "transparent",
      tooltip: {
        trigger: "axis",
        formatter: (p) => `${p[0].axisValue}: ${p[0].value} 小时`,
      },
      grid: { left: 50, right: 20, top: 20, bottom: 40 },
      xAxis: {
        type: "category",
        data: bins.map((b) => `${b.min.toFixed(0)}-${b.max.toFixed(0)}`),
        axisLabel: { color: "#8ba4c4", interval: 4, rotate: 45 },
      },
      yAxis: {
        type: "value",
        axisLabel: { color: "#8ba4c4" },
        name: "频次(小时)",
        splitLine: { lineStyle: { color: "rgba(255,255,255,0.05)" } },
      },
      series: [
        {
          type: "bar",
          data: bins.map((b) => b.count),
          itemStyle: {
            color: "rgba(0,212,255,0.7)",
            borderRadius: [2, 2, 0, 0],
          },
          markLine: {
            data: [{ xAxis: "平均" }],
            silent: true,
            lineStyle: { color: "#00ff88", type: "dashed" },
          },
        },
      ],
    });
  });
}

function initHistChart(stats) {
  histStats.value = {
    avg: stats[histKey.value].avg,
    std: stats[histKey.value].std,
  };
  watch.redirect = true; // trigger the watch
  // Direct call
  const data = allData.value[histKey.value].flat();
  const sorted = [...data].sort((a, b) => a - b);
  const min = sorted[0],
    max = sorted[sorted.length - 1];
  const binCount = 40,
    binWidth = (max - min) / binCount;
  const bins = Array.from({ length: binCount }, (_, i) => ({
    min: min + i * binWidth,
    max: min + (i + 1) * binWidth,
    count: 0,
  }));
  for (const v of data) {
    const idx = Math.min(Math.floor((v - min) / binWidth), binCount - 1);
    bins[idx].count++;
  }
  histChart.value = echarts.init(histChartRef.value);
  histChart.value.setOption({
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      formatter: (p) => `${p[0].axisValue}: ${p[0].value} 小时`,
    },
    grid: { left: 50, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: "category",
      data: bins.map((b) => `${b.min.toFixed(0)}-${b.max.toFixed(0)}`),
      axisLabel: { color: "#8ba4c4", interval: 4, rotate: 45 },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#8ba4c4" },
      name: "频次(小时)",
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.05)" } },
    },
    series: [
      {
        type: "bar",
        data: bins.map((b) => b.count),
        itemStyle: { color: "rgba(0,212,255,0.7)", borderRadius: [2, 2, 0, 0] },
      },
    ],
  });
}

function initQuantileChart(stats) {
  if (!quantileChartRef.value) return;
  quantileChart.value = echarts.init(quantileChartRef.value);
  const fields = ["p1", "p5", "p25", "median", "avg", "p75", "p95", "p99"];
  const fLabels = {
    p1: "1%",
    p5: "5%",
    p25: "25%",
    median: "50%",
    avg: "均值",
    p75: "75%",
    p95: "95%",
    p99: "99%",
  };
  quantileChart.value.setOption({
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    legend: {
      data: keys.map((k) => labels[k]),
      textStyle: { color: "#8ba4c4" },
    },
    grid: { left: 50, right: 20, top: 40, bottom: 40 },
    xAxis: {
      type: "category",
      data: fields.map((f) => fLabels[f]),
      axisLabel: { color: "#8ba4c4" },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#8ba4c4" },
      name: "MW",
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.05)" } },
    },
    series: keys.map((k, i) => ({
      name: labels[k],
      type: "line",
      data: fields.map((f) => stats[k][f]),
      lineStyle: { width: 2 },
      symbol: "circle",
      symbolSize: 6,
    })),
  });
}

// 分布拟合检验：计算正态分布和对数正态分布的对数似然
function calcNormalLL(data, mean, std) {
  if (std <= 0) return -Infinity;
  let ll = 0;
  for (const v of data) {
    ll -= Math.log(std * Math.sqrt(2 * Math.PI));
    ll -= (v - mean) ** 2 / (2 * std * std);
  }
  return ll;
}
function calcLognormalLL(data) {
  const logData = data.filter((v) => v > 0).map(Math.log);
  if (logData.length < 2) return -Infinity;
  const mean = logData.reduce((a, b) => a + b, 0) / logData.length;
  const std = Math.sqrt(
    logData.reduce((a, b) => a + (b - mean) ** 2, 0) / logData.length,
  );
  return calcNormalLL(logData, mean, std);
}
function initDistFit() {
  if (!distFitChartRef.value || !allData.value) return;
  const data = allData.value[distKey.value].flat();
  const mean = data.reduce((a, b) => a + b, 0) / data.length;
  const std = Math.sqrt(
    data.reduce((a, b) => a + (b - mean) ** 2, 0) / data.length,
  );
  const normalLL = calcNormalLL(data, mean, std);
  const lognormalLL = calcLognormalLL(data);
  const best = normalLL > lognormalLL ? "正态分布" : "对数正态分布";
  distFitResult.value = { best, normalLL, lognormalLL };

  // 绘制直方图 + 拟合曲线
  distFitChart.value = echarts.init(distFitChartRef.value);
  const bins = 40;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const binWidth = (max - min) / bins;
  const hist = Array.from({ length: bins }, () => 0);
  for (const v of data) {
    const idx = Math.min(Math.floor((v - min) / binWidth), bins - 1);
    hist[idx]++;
  }
  const binCenters = hist.map((_, i) => min + (i + 0.5) * binWidth);
  const total = data.length * binWidth;

  // 正态拟合曲线
  const normalCurve = binCenters.map(
    (x) =>
      (total / (std * Math.sqrt(2 * Math.PI))) *
      Math.exp(-((x - mean) ** 2) / (2 * std * std)),
  );

  // 对数正态拟合曲线
  const logData = data.filter((v) => v > 0).map(Math.log);
  const logMean = logData.reduce((a, b) => a + b, 0) / logData.length;
  const logStd = Math.sqrt(
    logData.reduce((a, b) => a + (b - logMean) ** 2, 0) / logData.length,
  );
  const lognormalCurve = binCenters.map((x) => {
    if (x <= 0) return 0;
    const lnx = Math.log(x);
    return (
      (total / (x * logStd * Math.sqrt(2 * Math.PI))) *
      Math.exp(-((lnx - logMean) ** 2) / (2 * logStd * logStd))
    );
  });

  distFitChart.value.setOption({
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    legend: {
      data: ["实际分布", "正态拟合", "对数正态拟合"],
      textStyle: { color: "#8ba4c4" },
    },
    grid: { left: 60, right: 30, top: 40, bottom: 40 },
    xAxis: {
      type: "value",
      axisLabel: { color: "#8ba4c4" },
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.05)" } },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#8ba4c4" },
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.05)" } },
    },
    series: [
      {
        name: "实际分布",
        type: "bar",
        data: binCenters.map((x, i) => [x, hist[i]]),
        barWidth: binWidth * 0.8,
        itemStyle: { color: "rgba(0,212,255,0.4)" },
      },
      {
        name: "正态拟合",
        type: "line",
        data: binCenters.map((x, i) => [x, normalCurve[i]]),
        lineStyle: { color: "#00ff88", width: 2 },
        symbol: "none",
      },
      {
        name: "对数正态拟合",
        type: "line",
        data: binCenters.map((x, i) => [x, lognormalCurve[i]]),
        lineStyle: { color: "#ffcc00", width: 2, type: "dashed" },
        symbol: "none",
      },
    ],
  });
}
</script>

<style scoped>
.stats-page {
  animation: fadeIn 0.3s ease;
}
@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.page-header {
  margin-bottom: 24px;
}
.page-header h2 {
  font-size: 1.5rem;
  color: var(--accent);
  margin-bottom: 8px;
}
.page-desc {
  color: var(--text-secondary);
  font-size: 0.9rem;
}
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 80px 0;
  color: var(--text-secondary);
}
.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(0, 212, 255, 0.2);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 16px;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.section-card {
  background: linear-gradient(
    135deg,
    rgba(0, 212, 255, 0.08),
    rgba(0, 150, 255, 0.03)
  );
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
}
.section-card h3 {
  font-size: 1rem;
  color: var(--accent);
  margin-bottom: 16px;
}
.chart-md {
  width: 100%;
  height: 320px;
}
.chart-lg {
  width: 100%;
  height: 360px;
}
.row-2col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

/* 分布拟合 */
.section-desc {
  color: var(--text-secondary);
  font-size: 0.85rem;
  margin-bottom: 12px;
}
.dist-result {
  font-size: 0.85rem;
  color: var(--text-secondary);
}
.dist-result strong {
  font-size: 1rem;
}

.table-wrap {
  overflow-x: auto;
}
.stats-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.82rem;
}
.stats-table th,
.stats-table td {
  padding: 8px 14px;
  text-align: right;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}
.stats-table th {
  color: var(--text-secondary);
  font-weight: 500;
  background: rgba(0, 212, 255, 0.05);
}
.stats-table th:first-child,
.stats-table td:first-child {
  text-align: left;
}
.stats-table .row-name {
  color: var(--accent);
  font-weight: 600;
}
.stats-table .row-val {
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}
.stats-table tr:hover td {
  background: rgba(0, 212, 255, 0.03);
}

.corr-notes {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
.corr-chip {
  padding: 4px 10px;
  background: rgba(0, 212, 255, 0.06);
  border-radius: 6px;
  font-size: 0.78rem;
  color: var(--text-secondary);
}

.ctrl-inline {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
}
.sel-sm {
  padding: 5px 8px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 0.85rem;
}
.hist-info {
  font-size: 0.8rem;
  color: var(--text-secondary);
}
.hist-info strong {
  color: var(--text-primary);
}
</style>
