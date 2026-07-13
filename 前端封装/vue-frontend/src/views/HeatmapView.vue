<template>
  <div class="heatmap-page">
    <div class="page-header">
      <h2>🔥 热力图分析</h2>
      <p class="page-desc">全年 365×24 小时数据热力图，颜色越亮表示出力越大</p>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>加载中...</p>
    </div>

    <template v-if="!loading">
      <!-- 控制栏 -->
      <div class="control-bar">
        <div class="ctrl-group">
          <label>数据类型</label>
          <select v-model="dataKey" class="sel">
            <option value="wind">风电出力</option>
            <option value="solar">光伏出力</option>
            <option value="hydro">水电出力</option>
            <option value="fh">火电负荷</option>
            <option value="np_raw">抽水蓄能</option>
          </select>
        </div>
        <div class="ctrl-group">
          <label>配色方案</label>
          <select v-model="colorScheme" class="sel">
            <option value="default">默认</option>
            <option value="reverse">反向</option>
            <option value="thermal">热力</option>
          </select>
        </div>
        <div class="ctrl-group">
          <button class="btn-download" @click="downloadCSV">📥 下载 CSV</button>
        </div>
      </div>

      <!-- 统计摘要 -->
      <div class="stats-row">
        <div class="stat-chip">
          最小值: <strong>{{ stats.min.toFixed(1) }}</strong> MW
        </div>
        <div class="stat-chip">
          最大值: <strong>{{ stats.max.toFixed(1) }}</strong> MW
        </div>
        <div class="stat-chip">
          平均值: <strong>{{ stats.avg.toFixed(1) }}</strong> MW
        </div>
        <div class="stat-chip">
          中位数: <strong>{{ stats.median.toFixed(1) }}</strong> MW
        </div>
        <div class="stat-chip">
          标准差: <strong>{{ stats.std.toFixed(1) }}</strong> MW
        </div>
      </div>

      <!-- 热力图 -->
      <div class="section-card">
        <h3>{{ dataLabel }} — 全年 365×24 热力图</h3>
        <div ref="heatmapRef" class="chart-heatmap"></div>
      </div>

      <!-- 月度统计 -->
      <div class="row-2col">
        <div class="section-card">
          <h3>📊 月度统计</h3>
          <div ref="monthStatsRef" class="chart-md"></div>
        </div>
        <div class="section-card">
          <h3>📈 24h 平均曲线</h3>
          <div ref="hourAvgRef" class="chart-md"></div>
        </div>
      </div>

      <!-- ===== 新增：工作日 vs 周末模式对比 ===== -->
      <div class="section-card">
        <h3>📅 工作日 vs 周末 模式对比</h3>
        <p class="section-desc">识别一周内不同日期类型的出力模式差异</p>
        <div ref="weekPatternRef" class="chart-lg"></div>
      </div>

      <!-- ===== 新增：异常日检测 ===== -->
      <div class="section-card">
        <h3>⚠️ 异常日检测</h3>
        <p class="section-desc">
          自动识别偏离正常模式 ±{{ anomalyThreshold }}σ 的异常日期
          <label class="anomaly-label">
            σ 倍数：
            <input
              type="range"
              v-model.number="anomalyThreshold"
              :min="1.0"
              :max="3.0"
              :step="0.5"
              class="range-inline"
            />
            <span class="range-val">{{ anomalyThreshold.toFixed(1) }}</span>
          </label>
        </p>
        <div class="anomaly-summary">
          <span class="anomaly-count">
            📌 共发现 <strong>{{ anomalyDays.length }}</strong> 个异常日
          </span>
          <span class="anomaly-pct">
            （占全年 {{ ((anomalyDays.length / 365) * 100).toFixed(1) }}%）
          </span>
        </div>
        <div class="anomaly-badges" v-if="anomalyDays.length > 0">
          <span
            v-for="d in anomalyDays.slice(0, 30)"
            :key="d"
            class="anomaly-badge"
            :title="`第${d + 1}天: ${allData[dataKey][d].reduce((a, b) => a + b, 0).toFixed(0)} MW`"
          >
            D{{ d + 1 }}
          </span>
          <span v-if="anomalyDays.length > 30" class="anomaly-more">
            +{{ anomalyDays.length - 30 }} 天...
          </span>
        </div>
        <div
          ref="anomalyChartRef"
          class="chart-md"
          style="margin-top: 12px"
        ></div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from "vue";
import * as echarts from "echarts";
import { fetchAllData } from "../api";

const loading = ref(true);
const allData = ref(null);
const dataKey = ref("wind");
const colorScheme = ref("default");
const heatmapRef = ref(null);
const monthStatsRef = ref(null);
const hourAvgRef = ref(null);
const weekPatternRef = ref(null);
const anomalyChartRef = ref(null);
const anomalyThreshold = ref(2.0);

const labels = {
  wind: "风电出力",
  solar: "光伏出力",
  hydro: "水电出力",
  fh: "火电负荷",
  np_raw: "抽水蓄能",
};
const dataLabel = computed(() => labels[dataKey.value]);

// 异常日检测：计算每日总出力，偏离均值超过 nσ 的标记为异常
const dailyTotals = computed(() => {
  if (!allData.value) return [];
  const raw = allData.value[dataKey.value];
  return raw.map((day) => day.reduce((a, b) => a + b, 0));
});
const anomalyStats = computed(() => {
  const d = dailyTotals.value;
  if (d.length === 0) return { mean: 0, std: 0 };
  const mean = d.reduce((a, b) => a + b, 0) / d.length;
  const std = Math.sqrt(d.reduce((a, b) => a + (b - mean) ** 2, 0) / d.length);
  return { mean, std };
});
const anomalyDays = computed(() => {
  const { mean, std } = anomalyStats.value;
  if (std === 0) return [];
  const thresh = anomalyThreshold.value * std;
  return dailyTotals.value
    .map((v, i) => (Math.abs(v - mean) > thresh ? i : -1))
    .filter((i) => i >= 0);
});

const stats = ref({ min: 0, max: 0, avg: 0, median: 0, std: 0 });

function computeStats(data) {
  const flat = data.flat();
  const sorted = [...flat].sort((a, b) => a - b);
  const n = flat.length;
  const sum = flat.reduce((a, b) => a + b, 0);
  const avg = sum / n;
  const variance = flat.reduce((a, b) => a + (b - avg) ** 2, 0) / n;
  return {
    min: sorted[0],
    max: sorted[n - 1],
    avg,
    median:
      n % 2 === 0
        ? (sorted[n / 2 - 1] + sorted[n / 2]) / 2
        : sorted[Math.floor(n / 2)],
    std: Math.sqrt(variance),
  };
}

function initHeatmap() {
  if (!heatmapRef.value || !allData.value) return;
  const chart = echarts.init(heatmapRef.value);
  const raw = allData.value[dataKey.value];
  // 转成 [day, hour, value] 格式
  const data = [];
  for (let d = 0; d < 365; d++) {
    for (let h = 0; h < 24; h++) {
      data.push([h, d, raw[d][h]]);
    }
  }
  stats.value = computeStats(raw);

  const colors = {
    default: [
      "#0a1628",
      "#003366",
      "#0066cc",
      "#0099ff",
      "#00ccff",
      "#66ffcc",
      "#ccff66",
      "#ffff00",
      "#ff9900",
      "#ff3300",
    ],
    reverse: [
      "#330000",
      "#660000",
      "#990000",
      "#cc3300",
      "#ff6600",
      "#ffcc00",
      "#ffff66",
      "#ccffcc",
      "#66ffcc",
      "#00ffff",
    ],
    thermal: [
      "#000000",
      "#330000",
      "#660000",
      "#990000",
      "#cc3300",
      "#ff6600",
      "#ff9900",
      "#ffcc00",
      "#ffff66",
      "#ffffff",
    ],
  };

  chart.setOption({
    backgroundColor: "transparent",
    tooltip: {
      formatter: (p) =>
        `第 ${p.value[1] + 1} 天 ${p.value[0]}:00<br/><strong>${p.value[2].toFixed(1)} MW</strong>`,
    },
    grid: { left: 60, right: 40, top: 10, bottom: 60 },
    xAxis: {
      type: "category",
      data: Array.from({ length: 24 }, (_, i) => `${i}:00`),
      splitArea: { show: true },
      axisLabel: { color: "#8ba4c4", interval: 2 },
    },
    yAxis: {
      type: "category",
      data: Array.from({ length: 365 }, (_, i) => `第${i + 1}天`),
      splitArea: { show: true },
      axisLabel: { show: false },
    },
    visualMap: {
      min: stats.value.min,
      max: stats.value.max,
      calculable: true,
      orient: "horizontal",
      left: "center",
      bottom: 10,
      inRange: { color: colors[colorScheme.value] },
      textStyle: { color: "#8ba4c4" },
    },
    series: [
      {
        type: "heatmap",
        data,
        label: { show: false },
        emphasis: {
          itemStyle: { shadowBlur: 10, shadowColor: "rgba(0,0,0,0.5)" },
        },
      },
    ],
  });
}

function initMonthStats() {
  if (!monthStatsRef.value || !allData.value) return;
  const chart = echarts.init(monthStatsRef.value);
  const raw = allData.value[dataKey.value];
  const daysInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  let start = 0;
  const months = daysInMonth.map((d) => {
    const slice = raw.slice(start, start + d);
    start += d;
    const flat = slice.flat();
    const sorted = [...flat].sort((a, b) => a - b);
    const sum = flat.reduce((a, b) => a + b, 0);
    return {
      avg: sum / flat.length,
      min: sorted[0],
      max: sorted[sorted.length - 1],
      median: sorted[Math.floor(sorted.length / 2)],
    };
  });
  chart.setOption({
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    legend: {
      data: ["平均", "中位数", "最小", "最大"],
      textStyle: { color: "#8ba4c4" },
    },
    grid: { left: 50, right: 20, top: 40, bottom: 40 },
    xAxis: {
      type: "category",
      data: Array.from({ length: 12 }, (_, i) => `${i + 1}月`),
      axisLabel: { color: "#8ba4c4" },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#8ba4c4" },
      name: "MW",
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.05)" } },
    },
    series: [
      {
        name: "平均",
        type: "line",
        data: months.map((m) => m.avg),
        lineStyle: { color: "#00d4ff", width: 2 },
        symbol: "circle",
      },
      {
        name: "中位数",
        type: "line",
        data: months.map((m) => m.median),
        lineStyle: { color: "#ffcc00", width: 1, type: "dashed" },
        symbol: "diamond",
      },
      {
        name: "最大",
        type: "line",
        data: months.map((m) => m.max),
        lineStyle: { color: "#ff6b6b", width: 1, type: "dotted" },
        symbol: "none",
      },
      {
        name: "最小",
        type: "line",
        data: months.map((m) => m.min),
        lineStyle: { color: "#00ff88", width: 1, type: "dotted" },
        symbol: "none",
      },
    ],
  });
}

function initHourAvg() {
  if (!hourAvgRef.value || !allData.value) return;
  const chart = echarts.init(hourAvgRef.value);
  const raw = allData.value[dataKey.value];
  const byHour = Array.from({ length: 24 }, (_, h) => raw.map((r) => r[h]));
  const hourStats = byHour.map((arr) => {
    const sorted = [...arr].sort((a, b) => a - b);
    const sum = arr.reduce((a, b) => a + b, 0);
    return {
      avg: sum / arr.length,
      min: sorted[0],
      max: sorted[sorted.length - 1],
      q1: sorted[~~(sorted.length * 0.25)],
      q3: sorted[~~(sorted.length * 0.75)],
    };
  });
  chart.setOption({
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    legend: { data: ["平均", "P25", "P75"], textStyle: { color: "#8ba4c4" } },
    grid: { left: 50, right: 20, top: 40, bottom: 40 },
    xAxis: {
      type: "category",
      data: Array.from({ length: 24 }, (_, i) => `${i}:00`),
      axisLabel: { color: "#8ba4c4" },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#8ba4c4" },
      name: "MW",
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.05)" } },
    },
    series: [
      {
        name: "P75",
        type: "line",
        data: hourStats.map((s) => s.q3),
        lineStyle: { width: 0 },
        symbol: "none",
        areaStyle: { color: "rgba(0,212,255,0.15)" },
      },
      {
        name: "平均",
        type: "line",
        data: hourStats.map((s) => s.avg),
        lineStyle: { color: "#00d4ff", width: 2 },
        symbol: "none",
      },
      {
        name: "P25",
        type: "line",
        data: hourStats.map((s) => s.q1),
        lineStyle: { width: 0 },
        symbol: "none",
        areaStyle: { color: "rgba(0,212,255,0.15)" },
      },
    ],
  });
}

// 工作日 vs 周末模式对比
function initWeekPattern() {
  if (!weekPatternRef.value || !allData.value) return;
  const chart = echarts.init(weekPatternRef.value);
  const raw = allData.value[dataKey.value];
  // 2026-01-01 是周四 → day0=周四
  const weekdayOffset = 4; // 周四=4
  const weekdayHours = Array.from({ length: 24 }, () => []);
  const weekendHours = Array.from({ length: 24 }, () => []);
  for (let d = 0; d < 365; d++) {
    const dow = (d + weekdayOffset) % 7;
    const isWeekend = dow === 0 || dow === 6; // 周日或周六
    for (let h = 0; h < 24; h++) {
      if (isWeekend) weekendHours[h].push(raw[d][h]);
      else weekdayHours[h].push(raw[d][h]);
    }
  }
  const avg = (arr) => arr.reduce((a, b) => a + b, 0) / arr.length;
  const hours = Array.from({ length: 24 }, (_, i) => `${i}:00`);
  chart.setOption({
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    legend: {
      data: ["工作日", "周末"],
      textStyle: { color: "#8ba4c4" },
    },
    grid: { left: 50, right: 20, top: 40, bottom: 40 },
    xAxis: {
      type: "category",
      data: hours,
      axisLabel: { color: "#8ba4c4" },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#8ba4c4" },
      name: "MW",
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.05)" } },
    },
    series: [
      {
        name: "工作日",
        type: "line",
        data: weekdayHours.map(avg),
        lineStyle: { color: "#00d4ff", width: 2 },
        itemStyle: { color: "#00d4ff" },
        smooth: true,
        areaStyle: { color: "rgba(0,212,255,0.1)" },
      },
      {
        name: "周末",
        type: "line",
        data: weekendHours.map(avg),
        lineStyle: { color: "#ffcc00", width: 2 },
        itemStyle: { color: "#ffcc00" },
        smooth: true,
        areaStyle: { color: "rgba(255,204,0,0.1)" },
      },
    ],
  });
}

// 异常日检测图表
function initAnomalyChart() {
  if (
    !anomalyChartRef.value ||
    !allData.value ||
    anomalyDays.value.length === 0
  )
    return;
  const chart = echarts.init(anomalyChartRef.value);
  const d = dailyTotals.value;
  const { mean, std } = anomalyStats.value;
  const upper = mean + anomalyThreshold.value * std;
  const lower = mean - anomalyThreshold.value * std;
  chart.setOption({
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      formatter: (p) =>
        `第${p[0].dataIndex + 1}天<br/>总出力: ${p[0].value.toFixed(0)} MW`,
    },
    grid: { left: 60, right: 30, top: 40, bottom: 40 },
    xAxis: {
      type: "category",
      data: Array.from({ length: 365 }, (_, i) =>
        i % 30 === 0 ? `${i + 1}` : "",
      ),
      axisLabel: { color: "#8ba4c4", fontSize: 10 },
      name: "天",
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#8ba4c4" },
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.05)" } },
    },
    series: [
      {
        name: "日总出力",
        type: "line",
        data: d,
        lineStyle: { color: "rgba(0,212,255,0.4)", width: 1 },
        symbol: "none",
      },
      {
        name: "异常日",
        type: "scatter",
        data: d
          .map((v, i) => (anomalyDays.value.includes(i) ? [i, v] : null))
          .filter(Boolean),
        itemStyle: { color: "#ff6b6b" },
        symbolSize: 6,
      },
      {
        name: "上界",
        type: "line",
        data: Array.from({ length: 365 }, () => upper),
        lineStyle: { color: "#ff6b6b", width: 1, type: "dashed" },
        symbol: "none",
      },
      {
        name: "下界",
        type: "line",
        data: Array.from({ length: 365 }, () => lower),
        lineStyle: { color: "#ff6b6b", width: 1, type: "dashed" },
        symbol: "none",
      },
    ],
  });
}

function downloadCSV() {
  if (!allData.value) return;
  const raw = allData.value[dataKey.value];
  let csv = "小时";
  for (let d = 0; d < 365; d++) csv += `,第${d + 1}天`;
  csv += "\n";
  for (let h = 0; h < 24; h++) {
    csv += `${h}:00`;
    for (let d = 0; d < 365; d++) csv += `,${raw[d][h]}`;
    csv += "\n";
  }
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${dataKey.value}_365x24.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

watch([dataKey, colorScheme, anomalyThreshold], async () => {
  await nextTick();
  initHeatmap();
  initMonthStats();
  initHourAvg();
  initWeekPattern();
  initAnomalyChart();
});

onMounted(async () => {
  try {
    allData.value = await fetchAllData();
    loading.value = false;
    await nextTick();
    initHeatmap();
    initMonthStats();
    initHourAvg();
    initWeekPattern();
    initAnomalyChart();
  } catch (e) {
    console.error(e);
    loading.value = false;
  }
});
</script>

<style scoped>
.heatmap-page {
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

.control-bar {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  padding: 16px;
  background: linear-gradient(
    135deg,
    rgba(0, 212, 255, 0.08),
    rgba(0, 150, 255, 0.03)
  );
  border: 1px solid var(--border-color);
  border-radius: 12px;
  margin-bottom: 16px;
  align-items: flex-end;
}
.ctrl-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 140px;
}
.ctrl-group label {
  font-size: 0.75rem;
  color: var(--text-secondary);
}
.sel {
  padding: 6px 10px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 0.85rem;
}

.btn-download {
  padding: 8px 16px;
  background: linear-gradient(135deg, var(--accent), #0096ff);
  border: none;
  border-radius: 6px;
  color: white;
  font-weight: 600;
  cursor: pointer;
  font-size: 0.85rem;
}
.btn-download:hover {
  box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3);
}

.stats-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.stat-chip {
  padding: 6px 14px;
  background: rgba(0, 212, 255, 0.08);
  border: 1px solid var(--border-color);
  border-radius: 20px;
  font-size: 0.8rem;
  color: var(--text-secondary);
}
.stat-chip strong {
  color: var(--text-primary);
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
.chart-heatmap {
  width: 100%;
  height: 520px;
}
.chart-md {
  width: 100%;
  height: 300px;
}
.row-2col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

/* 异常日检测 */
.section-desc {
  color: var(--text-secondary);
  font-size: 0.85rem;
  margin-bottom: 12px;
}
.anomaly-label {
  margin-left: 16px;
  font-size: 0.8rem;
  color: var(--text-secondary);
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.range-inline {
  width: 80px;
  height: 4px;
  accent-color: var(--accent);
}
.range-val {
  color: var(--accent);
  font-weight: 600;
  min-width: 30px;
}
.anomaly-summary {
  margin-bottom: 10px;
  font-size: 0.9rem;
}
.anomaly-count strong {
  color: #ff6b6b;
  font-size: 1.2rem;
}
.anomaly-pct {
  color: var(--text-secondary);
  font-size: 0.8rem;
}
.anomaly-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 8px;
}
.anomaly-badge {
  padding: 2px 8px;
  background: rgba(255, 107, 107, 0.15);
  border: 1px solid rgba(255, 107, 107, 0.3);
  border-radius: 4px;
  font-size: 0.7rem;
  color: #ff6b6b;
  cursor: help;
}
.anomaly-more {
  padding: 2px 8px;
  font-size: 0.7rem;
  color: var(--text-secondary);
}
.chart-lg {
  width: 100%;
  height: 380px;
}
</style>
