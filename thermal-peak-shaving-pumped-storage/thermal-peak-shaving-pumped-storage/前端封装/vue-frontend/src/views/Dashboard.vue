<template>
  <div class="dashboard">
    <div class="page-header">
      <h2>📊 系统总览</h2>
      <p class="page-desc">
        基于 NSLDE 多目标优化算法的火电深度调峰与抽水蓄能协同调度系统关键指标
      </p>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>加载数据中...</p>
    </div>

    <template v-if="!loading">
      <!-- KPI 卡片 -->
      <div class="kpi-grid">
        <div class="kpi-card" v-for="kpi in kpiList" :key="kpi.label">
          <div class="kpi-icon" :style="{ background: kpi.bg }">
            {{ kpi.icon }}
          </div>
          <div class="kpi-body">
            <div class="kpi-label">{{ kpi.label }}</div>
            <div class="kpi-value" :style="{ color: kpi.color }">
              {{ kpi.value }}
            </div>
            <div class="kpi-unit">{{ kpi.unit }}</div>
          </div>
        </div>
      </div>

      <!-- 发电构成 -->
      <div class="section-card">
        <h3>⚡ 年度发电量构成</h3>
        <div ref="pieChartRef" class="chart-lg"></div>
      </div>

      <!-- 年排放 vs 逐日 -->
      <div class="row-2col">
        <div class="section-card">
          <h3>📈 有/无抽蓄火电负荷对比</h3>
          <div ref="thermalChartRef" class="chart-md"></div>
        </div>
        <div class="section-card">
          <h3>📆 每日碳减排量</h3>
          <div ref="dailyCarbonChartRef" class="chart-md"></div>
        </div>
      </div>

      <!-- 抽蓄调度概览 -->
      <div class="section-card">
        <h3>🏭 抽水蓄能调度统计</h3>
        <div class="ps-stats">
          <div class="stat-bar">
            <span class="stat-label">发电</span>
            <div class="bar-track">
              <div
                class="bar-fill bar-gen"
                :style="{ width: psPct + '%' }"
              ></div>
            </div>
            <span class="stat-num">{{ psStats.generating_hours }}h</span>
          </div>
          <div class="stat-bar">
            <span class="stat-label">抽水</span>
            <div class="bar-track">
              <div
                class="bar-fill bar-pump"
                :style="{ width: pumpPct + '%' }"
              ></div>
            </div>
            <span class="stat-num">{{ psStats.pumping_hours }}h</span>
          </div>
          <div class="stat-bar">
            <span class="stat-label">停机</span>
            <div class="bar-track">
              <div
                class="bar-fill bar-idle"
                :style="{ width: idlePct + '%' }"
              ></div>
            </div>
            <span class="stat-num">{{ psStats.idle_hours }}h</span>
          </div>
          <div class="ps-meta">
            <span
              >总发电量:
              <strong>{{
                (psStats.total_generation / 10000).toFixed(1)
              }}</strong>
              万MWh</span
            >
            <span
              >总抽水耗电:
              <strong>{{ (psStats.total_pumping / 10000).toFixed(1) }}</strong>
              万MWh</span
            >
            <span
              >综合效率:
              <strong>{{ psStats.efficiency.toFixed(1) }}%</strong></span
            >
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from "vue";
import * as echarts from "echarts";
import { fetchDashboard } from "../api";

const loading = ref(true);
const dash = ref(null);
const pieChartRef = ref(null);
const thermalChartRef = ref(null);
const dailyCarbonChartRef = ref(null);

const kpiList = ref([]);
const psStats = ref({
  generating_hours: 0,
  pumping_hours: 0,
  idle_hours: 0,
  total_generation: 0,
  total_pumping: 0,
  efficiency: 0,
});

const psPct = computed(() =>
  ((psStats.value.generating_hours / 8760) * 100).toFixed(1),
);
const pumpPct = computed(() =>
  ((psStats.value.pumping_hours / 8760) * 100).toFixed(1),
);
const idlePct = computed(() =>
  ((psStats.value.idle_hours / 8760) * 100).toFixed(1),
);

function initPieChart() {
  if (!pieChartRef.value || !dash.value) return;
  const chart = echarts.init(pieChartRef.value);
  const s = dash.value;
  chart.setOption({
    backgroundColor: "transparent",
    tooltip: { trigger: "item", formatter: "{b}: {c} 亿kWh ({d}%)" },
    series: [
      {
        type: "pie",
        radius: ["40%", "70%"],
        center: ["50%", "50%"],
        data: [
          {
            value: s.total_wind,
            name: "风电",
            itemStyle: { color: "#00c8ff" },
          },
          {
            value: s.total_solar,
            name: "光伏",
            itemStyle: { color: "#ffb400" },
          },
          {
            value: s.total_hydro,
            name: "水电",
            itemStyle: { color: "#00ff88" },
          },
          { value: s.total_fh, name: "火电", itemStyle: { color: "#ff6b6b" } },
        ],
        label: { color: "#8ba4c4", fontSize: 12 },
        labelLine: { lineStyle: { color: "rgba(255,255,255,0.1)" } },
      },
    ],
  });
}

function initThermalChart() {
  if (!thermalChartRef.value || !dash.value) return;
  const chart = echarts.init(thermalChartRef.value);
  const d = dash.value;
  const hours = Array.from({ length: 720 }, (_, i) => i + 1);
  chart.setOption({
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    legend: {
      data: ["有抽蓄火电", "无抽蓄火电"],
      textStyle: { color: "#8ba4c4" },
    },
    grid: { left: 50, right: 20, top: 40, bottom: 40 },
    xAxis: {
      type: "category",
      data: hours.slice(0, 720),
      axisLabel: { color: "#8ba4c4", interval: 120 },
      name: "小时",
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#8ba4c4" },
      name: "MW",
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.05)" } },
    },
    series: [
      {
        name: "有抽蓄火电",
        type: "line",
        data: d.Nt_first30,
        lineStyle: { color: "#00d4ff", width: 1 },
        smooth: true,
        symbol: "none",
      },
      {
        name: "无抽蓄火电",
        type: "line",
        data: d.Nt2_first30,
        lineStyle: { color: "#ff6b6b", width: 1, type: "dashed" },
        smooth: true,
        symbol: "none",
      },
    ],
  });
}

function initDailyCarbonChart() {
  if (!dailyCarbonChartRef.value || !dash.value) return;
  const chart = echarts.init(dailyCarbonChartRef.value);
  const daily = dash.value.daily_carbon;
  const days = Array.from({ length: 365 }, (_, i) => `第${i + 1}天`);
  chart.setOption({
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: "category",
      data: days,
      axisLabel: { color: "#8ba4c4", interval: 60 },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#8ba4c4" },
      name: "万吨",
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.05)" } },
    },
    series: [
      {
        type: "bar",
        data: daily,
        itemStyle: {
          color: (p) =>
            p.value >= 0 ? "rgba(0,212,255,0.7)" : "rgba(0,255,136,0.7)",
        },
      },
    ],
  });
}

onMounted(async () => {
  try {
    dash.value = await fetchDashboard();
    const d = dash.value;
    psStats.value = d.ps_stats;
    const total = d.total_wind + d.total_solar + d.total_hydro + d.total_fh;
    kpiList.value = [
      {
        icon: "🌍",
        label: "碳减排量",
        value: d.carbon_result.carbon_change.toFixed(2),
        unit: "万吨",
        color: "#00ff88",
        bg: "rgba(0,255,136,0.15)",
      },
      {
        icon: "🌿",
        label: "新能源占比",
        value: (
          ((d.total_wind + d.total_solar + d.total_hydro) / total) *
          100
        ).toFixed(1),
        unit: "%",
        color: "#00d4ff",
        bg: "rgba(0,212,255,0.15)",
      },
      {
        icon: "💧",
        label: "抽水小时",
        value: psStats.value.pumping_hours,
        unit: "h",
        color: "#00d4ff",
        bg: "rgba(0,212,255,0.15)",
      },
      {
        icon: "⚡",
        label: "发电小时",
        value: psStats.value.generating_hours,
        unit: "h",
        color: "#00ff88",
        bg: "rgba(0,255,136,0.15)",
      },
      {
        icon: "🔄",
        label: "抽发效率",
        value: psStats.value.efficiency.toFixed(1),
        unit: "%",
        color: "#ffcc00",
        bg: "rgba(255,204,0,0.15)",
      },
      {
        icon: "🌬️",
        label: "风电总量",
        value: d.total_wind.toFixed(1),
        unit: "亿kWh",
        color: "#00c8ff",
        bg: "rgba(0,200,255,0.15)",
      },
    ];
    loading.value = false;
    await nextTick();
    initPieChart();
    initThermalChart();
    initDailyCarbonChart();
    window.addEventListener("resize", () => {
      echarts.getInstanceByDom(pieChartRef.value)?.resize();
      echarts.getInstanceByDom(thermalChartRef.value)?.resize();
      echarts.getInstanceByDom(dailyCarbonChartRef.value)?.resize();
    });
  } catch (e) {
    console.error(e);
    loading.value = false;
  }
});
</script>

<style scoped>
.dashboard {
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

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}
.kpi-card {
  display: flex;
  gap: 16px;
  align-items: center;
  background: linear-gradient(
    135deg,
    rgba(0, 212, 255, 0.08),
    rgba(0, 150, 255, 0.03)
  );
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
  transition: all 0.3s;
}
.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 212, 255, 0.15);
}
.kpi-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.4rem;
  flex-shrink: 0;
}
.kpi-body {
  flex: 1;
  min-width: 0;
}
.kpi-label {
  font-size: 0.78rem;
  color: var(--text-secondary);
  margin-bottom: 4px;
}
.kpi-value {
  font-size: 1.5rem;
  font-weight: 700;
}
.kpi-unit {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-top: 2px;
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
  height: 360px;
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

.ps-stats {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.stat-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}
.stat-label {
  width: 40px;
  font-size: 0.85rem;
  color: var(--text-secondary);
  flex-shrink: 0;
}
.bar-track {
  flex: 1;
  height: 20px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  border-radius: 10px;
  transition: width 0.5s;
}
.bar-gen {
  background: linear-gradient(
    90deg,
    rgba(0, 255, 136, 0.6),
    rgba(0, 255, 136, 0.3)
  );
}
.bar-pump {
  background: linear-gradient(
    90deg,
    rgba(0, 212, 255, 0.6),
    rgba(0, 212, 255, 0.3)
  );
}
.bar-idle {
  background: linear-gradient(
    90deg,
    rgba(255, 255, 255, 0.2),
    rgba(255, 255, 255, 0.1)
  );
}
.stat-num {
  width: 50px;
  text-align: right;
  font-size: 0.85rem;
  color: var(--text-primary);
  flex-shrink: 0;
}
.ps-meta {
  display: flex;
  gap: 24px;
  padding-top: 8px;
  border-top: 1px solid var(--border-color);
  font-size: 0.8rem;
  color: var(--text-secondary);
  flex-wrap: wrap;
}
.ps-meta strong {
  color: var(--text-primary);
}
</style>
