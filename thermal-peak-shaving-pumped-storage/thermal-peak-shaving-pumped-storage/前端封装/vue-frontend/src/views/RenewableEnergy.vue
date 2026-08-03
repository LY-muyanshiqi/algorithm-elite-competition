<template>
  <div class="renewable-page">
    <div class="page-header">
      <h2>🌤️ 新能源数据</h2>
      <p class="page-desc">风电、光伏、水电 365天×24小时出力数据可视化</p>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>加载数据中...</p>
    </div>

    <template v-if="!loading">
      <!-- 年度总览 KPI -->
      <div class="kpi-row">
        <div class="mini-card" v-for="item in totals" :key="item.label">
          <span class="mini-icon">{{ item.icon }}</span>
          <span class="mini-val" :style="{ color: item.color }">{{
            item.value
          }}</span>
          <span class="mini-unit">{{ item.unit }}</span>
        </div>
      </div>

      <!-- 时间范围选择 -->
      <div class="control-bar">
        <div class="ctrl-group">
          <label>数据源</label>
          <select v-model="selectedSource" class="sel">
            <option value="all">全部</option>
            <option value="wind">风电</option>
            <option value="solar">光伏</option>
            <option value="hydro">水电</option>
          </select>
        </div>
        <div class="ctrl-group">
          <label>视图</label>
          <select v-model="viewMode" class="sel">
            <option value="全年">全年</option>
            <option value="按月">按月</option>
            <option value="典型日">典型日</option>
          </select>
        </div>
        <div class="ctrl-group" v-if="viewMode === '按月'">
          <label>月份</label>
          <select v-model.number="selectedMonth" class="sel">
            <option v-for="m in 12" :key="m" :value="m">{{ m }}月</option>
          </select>
        </div>
        <div class="ctrl-group" v-if="viewMode === '典型日'">
          <label>日期</label>
          <select v-model.number="selectedDay" class="sel">
            <option v-for="d in 365" :key="d" :value="d - 1">
              第{{ d }}天
            </option>
          </select>
        </div>
      </div>

      <!-- 主力图表 -->
      <div class="section-card">
        <div ref="mainChartRef" class="chart-lg"></div>
      </div>

      <!-- 月度/季度对比 -->
      <div class="row-2col" v-if="viewMode === '全年'">
        <div class="section-card">
          <h3>📊 月度发电量</h3>
          <div ref="monthChartRef" class="chart-md"></div>
        </div>
        <div class="section-card">
          <h3>📈 出力分布</h3>
          <div ref="distChartRef" class="chart-md"></div>
        </div>
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
const mainChartRef = ref(null);
const monthChartRef = ref(null);
const distChartRef = ref(null);

const selectedSource = ref("all");
const viewMode = ref("全年");
const selectedMonth = ref(1);
const selectedDay = ref(0);

const totals = ref([]);

function getSourceData(key) {
  if (!allData.value) return [];
  if (key === "all")
    return {
      wind: allData.value.wind,
      solar: allData.value.solar,
      hydro: allData.value.hydro,
    };
  return { [key]: allData.value[key] };
}

function initMainChart() {
  if (!mainChartRef.value || !allData.value) return;
  const chart = echarts.init(mainChartRef.value);
  const d = allData.value;
  let series = [];
  const colors = { wind: "#00c8ff", solar: "#ffb400", hydro: "#00ff88" };
  const names = { wind: "风电", solar: "光伏", hydro: "水电" };

  if (selectedSource.value === "all") {
    series = ["wind", "solar", "hydro"].map((k) => ({
      name: names[k],
      type: "line",
      data: d[k].flat().slice(0, 8760),
      lineStyle: { width: 1, color: colors[k] },
      smooth: true,
      symbol: "none",
    }));
  } else {
    series = [
      {
        name: names[selectedSource.value],
        type: "line",
        data: d[selectedSource.value].flat().slice(0, 8760),
        lineStyle: { width: 1.5, color: colors[selectedSource.value] },
        smooth: true,
        symbol: "none",
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: colors[selectedSource.value] + "40" },
            { offset: 1, color: colors[selectedSource.value] + "05" },
          ]),
        },
      },
    ];
  }

  chart.setOption({
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    legend: {
      data: series.map((s) => s.name),
      textStyle: { color: "#8ba4c4" },
    },
    grid: { left: 60, right: 20, top: 50, bottom: 40 },
    xAxis: {
      type: "category",
      data: Array.from(
        { length: 8760 },
        (_, i) => `${Math.floor(i / 24) + 1}d ${i % 24}h`,
      ),
      axisLabel: { color: "#8ba4c4", interval: 720 },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#8ba4c4" },
      name: "MW",
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.05)" } },
    },
    dataZoom: [
      { type: "inside", start: 0, end: 100 },
      { type: "slider", start: 0, end: 100, height: 20, bottom: 0 },
    ],
    series,
  });
}

function initMonthChart() {
  if (!monthChartRef.value || !allData.value) return;
  const chart = echarts.init(monthChartRef.value);
  const d = allData.value;
  const daysInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  const months = [];
  let start = 0;
  for (let m = 0; m < 12; m++) {
    const end = start + daysInMonth[m];
    const windSlice = d.wind.slice(start, end);
    const solarSlice = d.solar.slice(start, end);
    const hydroSlice = d.hydro.slice(start, end);
    months.push({
      wind:
        windSlice.reduce((a, b) => a + b.reduce((x, y) => x + y, 0), 0) / 10000,
      solar:
        solarSlice.reduce((a, b) => a + b.reduce((x, y) => x + y, 0), 0) /
        10000,
      hydro:
        hydroSlice.reduce((a, b) => a + b.reduce((x, y) => x + y, 0), 0) /
        10000,
    });
    start = end;
  }
  chart.setOption({
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    legend: { data: ["风电", "光伏", "水电"], textStyle: { color: "#8ba4c4" } },
    grid: { left: 50, right: 20, top: 40, bottom: 40 },
    xAxis: {
      type: "category",
      data: Array.from({ length: 12 }, (_, i) => `${i + 1}月`),
      axisLabel: { color: "#8ba4c4" },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#8ba4c4" },
      name: "亿kWh",
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.05)" } },
    },
    series: [
      {
        name: "风电",
        type: "bar",
        data: months.map((m) => m.wind),
        itemStyle: { color: "#00c8ff" },
      },
      {
        name: "光伏",
        type: "bar",
        data: months.map((m) => m.solar),
        itemStyle: { color: "#ffb400" },
      },
      {
        name: "水电",
        type: "bar",
        data: months.map((m) => m.hydro),
        itemStyle: { color: "#00ff88" },
      },
    ],
  });
}

function initDistChart() {
  if (!distChartRef.value || !allData.value) return;
  const chart = echarts.init(distChartRef.value);
  const d = allData.value;
  // 计算每个小时的平均值、最小值、最大值
  const hours = Array.from({ length: 24 }, (_, h) => `${h}:00`);
  const calcStats = (data) => {
    const byHour = Array.from({ length: 24 }, (_, h) => data.map((r) => r[h]));
    return byHour.map((arr) => {
      const sorted = [...arr].sort((a, b) => a - b);
      const sum = arr.reduce((a, b) => a + b, 0);
      return {
        avg: sum / arr.length,
        min: sorted[0],
        max: sorted[sorted.length - 1],
        q1: sorted[~~(sorted.length * 0.25)],
        median: sorted[~~(sorted.length * 0.5)],
        q3: sorted[~~(sorted.length * 0.75)],
      };
    });
  };
  const windStats = calcStats(d.wind);
  const solarStats = calcStats(d.solar);
  const hydroStats = calcStats(d.hydro);

  chart.setOption({
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      formatter: (params) =>
        params
          .map(
            (p) =>
              `${p.seriesName}<br/>${p.axisValue}: 平均${p.value.toFixed(0)} MW`,
          )
          .join("<br/>"),
    },
    legend: { data: ["风电", "光伏", "水电"], textStyle: { color: "#8ba4c4" } },
    grid: { left: 50, right: 20, top: 40, bottom: 40 },
    xAxis: { type: "category", data: hours, axisLabel: { color: "#8ba4c4" } },
    yAxis: {
      type: "value",
      axisLabel: { color: "#8ba4c4" },
      name: "MW",
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.05)" } },
    },
    series: [
      {
        name: "风电",
        type: "line",
        data: windStats.map((s) => s.avg),
        lineStyle: { color: "#00c8ff", width: 2 },
        symbol: "none",
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(0,200,255,0.3)" },
            { offset: 1, color: "rgba(0,200,255,0.02)" },
          ]),
        },
      },
      {
        name: "光伏",
        type: "line",
        data: solarStats.map((s) => s.avg),
        lineStyle: { color: "#ffb400", width: 2 },
        symbol: "none",
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(255,180,0,0.3)" },
            { offset: 1, color: "rgba(255,180,0,0.02)" },
          ]),
        },
      },
      {
        name: "水电",
        type: "line",
        data: hydroStats.map((s) => s.avg),
        lineStyle: { color: "#00ff88", width: 2 },
        symbol: "none",
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(0,255,136,0.3)" },
            { offset: 1, color: "rgba(0,255,136,0.02)" },
          ]),
        },
      },
    ],
  });
}

watch([selectedSource, viewMode, selectedMonth, selectedDay], async () => {
  await nextTick();
  initMainChart();
  if (viewMode.value === "全年") {
    initMonthChart();
    initDistChart();
  }
});

onMounted(async () => {
  try {
    allData.value = await fetchAllData();
    const d = allData.value;
    const sum2d = (arr) =>
      arr.reduce((a, b) => a + b.reduce((x, y) => x + y, 0), 0);
    const tw = sum2d(d.wind),
      ts = sum2d(d.solar),
      th = sum2d(d.hydro);
    totals.value = [
      {
        icon: "🌬️",
        label: "风电",
        value: (tw / 10000).toFixed(1),
        unit: "亿kWh",
        color: "#00c8ff",
      },
      {
        icon: "☀️",
        label: "光伏",
        value: (ts / 10000).toFixed(1),
        unit: "亿kWh",
        color: "#ffb400",
      },
      {
        icon: "💧",
        label: "水电",
        value: (th / 10000).toFixed(1),
        unit: "亿kWh",
        color: "#00ff88",
      },
      {
        icon: "📊",
        label: "新能源合计",
        value: ((tw + ts + th) / 10000).toFixed(1),
        unit: "亿kWh",
        color: "#00d4ff",
      },
    ];
    loading.value = false;
    await nextTick();
    initMainChart();
    initMonthChart();
    initDistChart();
  } catch (e) {
    console.error(e);
    loading.value = false;
  }
});
</script>

<style scoped>
.renewable-page {
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

.kpi-row {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}
.mini-card {
  display: flex;
  align-items: center;
  gap: 10px;
  background: linear-gradient(
    135deg,
    rgba(0, 212, 255, 0.08),
    rgba(0, 150, 255, 0.03)
  );
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 14px 18px;
  flex: 1;
  min-width: 160px;
}
.mini-icon {
  font-size: 1.3rem;
}
.mini-val {
  font-size: 1.2rem;
  font-weight: 700;
}
.mini-unit {
  font-size: 0.75rem;
  color: var(--text-secondary);
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
  margin-bottom: 20px;
}
.ctrl-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 120px;
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
.chart-lg {
  width: 100%;
  height: 400px;
}
.chart-md {
  width: 100%;
  height: 320px;
}
.row-2col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
</style>
