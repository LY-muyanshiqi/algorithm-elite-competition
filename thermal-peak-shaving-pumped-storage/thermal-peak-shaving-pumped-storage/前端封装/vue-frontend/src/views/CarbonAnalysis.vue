<template>
  <div class="carbon-page">
    <ScreenHeader title="西北五省区碳减排监测中心" subtitle="抽水蓄能协同调峰 · 碳排趋势 · 减排贡献分析" status-label="碳监测在线" />
    <div class="page-header">
      <h2>💨 碳减排分析</h2>
      <p class="page-desc">抽水蓄能对火电调峰和碳排放的全年影响分析</p>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>计算中...</p>
    </div>

    <template v-if="!loading">
      <!-- 核心指标 -->
      <div class="kpi-grid">
        <div class="kpi-card big" style="border-color: rgba(0, 255, 136, 0.4)">
          <div class="kpi-label">🌍 全年碳减排量</div>
          <div class="kpi-val" style="color: #00ff88">
            {{ data?.carbon_change?.toFixed(2) ?? "..." }}
          </div>
          <div class="kpi-unit">万吨 CO₂</div>
        </div>
        <div class="kpi-card big" style="border-color: rgba(0, 212, 255, 0.4)">
          <div class="kpi-label">⚡ 火电变化量</div>
          <div class="kpi-val" style="color: #00d4ff">
            {{ data?.power_change?.toFixed(2) ?? "..." }}
          </div>
          <div class="kpi-unit">亿 kWh</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">🔥 有抽蓄总火电</div>
          <div class="kpi-val-sm" style="color: #ff6b6b">
            {{ (ntTotal / 10000).toFixed(1) }}
          </div>
          <div class="kpi-unit">亿 kWh</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">🔥 无抽蓄总火电</div>
          <div class="kpi-val-sm" style="color: #ff9800">
            {{ (nt2Total / 10000).toFixed(1) }}
          </div>
          <div class="kpi-unit">亿 kWh</div>
        </div>
      </div>

      <div class="section-card regional-carbon-map">
        <h3>西北五省区减排协同网络</h3>
        <MapFlow :intensity="0.9" />
      </div>

      <!-- ===== 碳中和当量换算（Streamlit没有的新功能） ===== -->
      <div class="section-card">
        <h3>🌳 碳中和当量换算</h3>
        <p class="section-desc">把抽象的碳减排数据换算成直观易懂的日常概念</p>
        <div class="equivalent-grid">
          <div class="equiv-item" style="border-color: rgba(0, 200, 83, 0.4)">
            <span class="equiv-icon">🌲</span>
            <div class="equiv-body">
              <div class="equiv-label">相当于种植</div>
              <div class="equiv-val" style="color: #00c853">
                {{ treesPlanted }}
              </div>
              <div class="equiv-unit">棵松树（年吸碳量）</div>
            </div>
          </div>
          <div class="equiv-item" style="border-color: rgba(33, 150, 243, 0.4)">
            <span class="equiv-icon">🚗</span>
            <div class="equiv-body">
              <div class="equiv-label">相当于减少</div>
              <div class="equiv-val" style="color: #2196f3">
                {{ carsRemoved }}
              </div>
              <div class="equiv-unit">辆乘用车年排放</div>
            </div>
          </div>
          <div class="equiv-item" style="border-color: rgba(255, 193, 7, 0.4)">
            <span class="equiv-icon">💡</span>
            <div class="equiv-body">
              <div class="equiv-label">相当于节约</div>
              <div class="equiv-val" style="color: #ffc107">
                {{ homesPowered }}
              </div>
              <div class="equiv-unit">户家庭年用电量</div>
            </div>
          </div>
          <div class="equiv-item" style="border-color: rgba(156, 39, 176, 0.4)">
            <span class="equiv-icon">✈️</span>
            <div class="equiv-body">
              <div class="equiv-label">相当于停飞</div>
              <div class="equiv-val" style="color: #9c27b0">
                {{ flightsCancelled }}
              </div>
              <div class="equiv-unit">次北京→上海航班</div>
            </div>
          </div>
        </div>
        <div class="equiv-footnote">
          基于 IPCC 碳排放系数和国内平均数据换算，仅供参考
        </div>
      </div>

      <!-- 有/无抽蓄对比曲线 -->
      <div class="section-card">
        <h3>📈 有抽蓄 vs 无抽蓄 火电负荷（前30天）</h3>
        <div ref="compareChartRef" class="chart-lg"></div>
      </div>

      <!-- 每日碳减排 + 累计 -->
      <div class="row-2col">
        <div class="section-card">
          <h3>📆 每日碳减排量</h3>
          <div ref="dailyChartRef" class="chart-md"></div>
        </div>
        <div class="section-card">
          <h3>📊 累计碳减排</h3>
          <div ref="cumChartRef" class="chart-md"></div>
        </div>
      </div>

      <!-- 月度汇总 -->
      <div class="section-card">
        <h3>🗓️ 月度碳减排</h3>
        <div ref="monthlyChartRef" class="chart-lg"></div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from "vue";
import * as echarts from "echarts";
import { fetchCarbonAnalysis } from "../api";
import ScreenHeader from "../components/ScreenHeader.vue";
import MapFlow from "../components/MapFlow.vue";

const loading = ref(true);
const data = ref(null);
const compareChartRef = ref(null);
const dailyChartRef = ref(null);
const cumChartRef = ref(null);
const monthlyChartRef = ref(null);
const compareChart = ref(null);
const dailyChart = ref(null);
const cumChart = ref(null);
const monthlyChart = ref(null);

const ntTotal = computed(() => data.value?.Nt_total ?? 0);
const nt2Total = computed(() => data.value?.Nt2_total ?? 0);

// 碳中和当量换算（基于标准系数）
const carbonTons = computed(() => (data.value?.carbon_change ?? 0) * 10000); // 万吨→吨
const treesPlanted = computed(() => Math.round(carbonTons.value / 0.018)); // 一棵松树年吸碳 ~18kg
const carsRemoved = computed(() => Math.round(carbonTons.value / 4.6)); // 一辆乘用车年排放 ~4.6吨
const homesPowered = computed(() => Math.round(carbonTons.value / 2.5)); // 一户家庭年用电碳排放 ~2.5吨
const flightsCancelled = computed(() =>
  Math.round(((data.value?.power_change ?? 0) * 10000) / 180),
); // 北京→上海航班 ~180kWh/人

function initCompareChart() {
  if (!compareChartRef.value || !data.value) return;
  compareChart.value = echarts.init(compareChartRef.value);
  const d = data.value;
  const hours = Array.from(
    { length: 720 },
    (_, i) => `${Math.floor(i / 24) + 1}d`,
  );
  compareChart.value.setOption({
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    legend: { data: ["有抽蓄", "无抽蓄"], textStyle: { color: "#8ba4c4" } },
    grid: { left: 60, right: 20, top: 50, bottom: 40 },
    xAxis: {
      type: "category",
      data: hours,
      axisLabel: { color: "#8ba4c4", interval: 120 },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#8ba4c4" },
      name: "MW",
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.05)" } },
    },
    dataZoom: [{ type: "inside", start: 0, end: 100 }],
    series: [
      {
        name: "有抽蓄",
        type: "line",
        data: d.Nt_first30,
        lineStyle: { color: "#00d4ff", width: 1 },
        symbol: "none",
      },
      {
        name: "无抽蓄",
        type: "line",
        data: d.Nt2_first30,
        lineStyle: { color: "#ff6b6b", width: 1, type: "dashed" },
        symbol: "none",
      },
    ],
  });
}

function initDailyChart() {
  if (!dailyChartRef.value || !data.value) return;
  dailyChart.value = echarts.init(dailyChartRef.value);
  const days = Array.from({ length: 365 }, (_, i) => i + 1);
  dailyChart.value.setOption({
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    grid: { left: 55, right: 20, top: 20, bottom: 40 },
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
        data: data.value.daily_carbon,
        itemStyle: {
          color: (p) =>
            p.value >= 0 ? "rgba(0,212,255,0.6)" : "rgba(0,255,136,0.6)",
        },
      },
    ],
  });
}

function initCumChart() {
  if (!cumChartRef.value || !data.value) return;
  cumChart.value = echarts.init(cumChartRef.value);
  cumChart.value.setOption({
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      formatter: (p) => `累计碳减排: ${p[0].value.toFixed(2)} 万吨`,
    },
    grid: { left: 55, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: "category",
      data: Array.from({ length: 365 }, (_, i) => i + 1),
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
        type: "line",
        data: data.value.cumulative_carbon,
        lineStyle: { color: "#00ff88", width: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(0,255,136,0.3)" },
            { offset: 1, color: "rgba(0,255,136,0.02)" },
          ]),
        },
        symbol: "none",
      },
    ],
  });
}

function initMonthlyChart() {
  if (!monthlyChartRef.value || !data.value) return;
  monthlyChart.value = echarts.init(monthlyChartRef.value);
  monthlyChart.value.setOption({
    backgroundColor: "transparent",
    tooltip: {
      trigger: "axis",
      formatter: (p) => `${p[0].name}: ${p[0].value.toFixed(2)} 万吨`,
    },
    grid: { left: 55, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: "category",
      data: Array.from({ length: 12 }, (_, i) => `${i + 1}月`),
      axisLabel: { color: "#8ba4c4" },
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
        data: data.value.monthly_carbon,
        itemStyle: {
          color: (p) =>
            p.value >= 0 ? "rgba(0,212,255,0.7)" : "rgba(0,255,136,0.7)",
          borderRadius: [4, 4, 0, 0],
        },
        markLine: {
          data: [{ yAxis: 0 }],
          lineStyle: { color: "rgba(255,255,255,0.2)", type: "dashed" },
          label: { show: false },
        },
      },
    ],
  });
}

onMounted(async () => {
  try {
    data.value = await fetchCarbonAnalysis();
    loading.value = false;
    await nextTick();
    initCompareChart();
    initDailyChart();
    initCumChart();
    initMonthlyChart();
    window.addEventListener("resize", handleResize);
  } catch (e) {
    console.error(e);
    loading.value = false;
  }
});

function handleResize() {
  [compareChartRef, dailyChartRef, cumChartRef, monthlyChartRef].forEach(
    (ref) => {
      echarts.getInstanceByDom(ref.value)?.resize();
    },
  );
}

onBeforeUnmount(() => {
  window.removeEventListener("resize", handleResize);
  [compareChart, dailyChart, cumChart, monthlyChart].forEach((ref) => {
    ref.value?.dispose();
    ref.value = null;
  });
});
</script>

<style scoped>
.carbon-page {
  animation: fadeIn 0.3s ease;
  min-height: 100vh;
  padding: 10px;
  background: radial-gradient(circle at 50% 8%, rgba(20,241,190,.08), transparent 32%), repeating-linear-gradient(90deg, rgba(86,217,255,.015) 0 1px, transparent 1px 32px), #020d15;
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
  display: none;
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
  margin: 10px 0;
}
.kpi-card {
  background: linear-gradient(
    135deg,
    rgba(0, 212, 255, 0.08),
    rgba(0, 150, 255, 0.03)
  );
  border: 1px solid var(--border-color);
  border-radius: 2px;
  padding: 20px;
}
.kpi-card.big {
  grid-column: span 2;
  text-align: center;
  padding: 28px;
}
.kpi-label {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin-bottom: 8px;
}
.kpi-val {
  font-size: 2.5rem;
  font-weight: 700;
}
.kpi-val-sm {
  font-size: 1.5rem;
  font-weight: 700;
}
.kpi-unit {
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin-top: 4px;
}

.section-card {
  background: linear-gradient(
    135deg,
    rgba(0, 212, 255, 0.08),
    rgba(0, 150, 255, 0.03)
  );
  border: 1px solid var(--border-color);
  border-radius: 2px;
  padding: 20px;
  margin-bottom: 10px;
  border-color: rgba(20,241,190,.24);
  box-shadow: inset 0 0 30px rgba(20,241,190,.025);
}
.section-card h3 {
  font-size: 1rem;
  color: var(--accent);
  margin-bottom: 16px;
}
.chart-lg {
  width: 100%;
  height: 380px;
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

/* 碳中和当量换算 */
.equivalent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 12px;
}
.equiv-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.04),
    rgba(255, 255, 255, 0.01)
  );
  border: 1px solid;
  border-radius: 2px;
  transition: all 0.3s;
}
.equiv-item:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
}
.equiv-icon {
  font-size: 2.4rem;
  line-height: 1;
}
.equiv-body {
  flex: 1;
}
.equiv-label {
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin-bottom: 4px;
}
.equiv-val {
  font-size: 1.8rem;
  font-weight: 700;
  line-height: 1.2;
}
.equiv-unit {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-top: 2px;
}
.equiv-footnote {
  font-size: 0.75rem;
  color: var(--text-secondary);
  opacity: 0.6;
  text-align: center;
}
.section-desc {
  color: var(--text-secondary);
  font-size: 0.85rem;
  margin-bottom: 16px;
}
.regional-carbon-map { position: relative; height: 500px; padding: 0; overflow: hidden; }
.regional-carbon-map h3 { position: absolute; z-index: 5; margin: 16px; padding-left: 10px; border-left: 3px solid var(--color-accent); }
</style>
