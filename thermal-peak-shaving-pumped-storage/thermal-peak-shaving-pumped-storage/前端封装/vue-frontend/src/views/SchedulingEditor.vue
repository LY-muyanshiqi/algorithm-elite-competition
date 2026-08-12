<template>
  <div class="scheduling-editor">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>🏭 抽水蓄能调度编辑器</h2>
      <p class="page-desc">
        拖拽曲线上的数据点调整每日抽水/发电策略，查看实时的碳减排和调峰效果变化
      </p>
    </div>

    <!-- 参数/日期选择栏 -->
    <div class="control-bar">
      <div class="control-group">
        <label>选择日期</label>
        <select v-model.number="selectedDay" class="select-input">
          <option v-for="d in 365" :key="d" :value="d - 1">
            第 {{ d }} 天
          </option>
        </select>
      </div>
      <div class="control-group">
        <label>抽蓄容量</label>
        <input
          type="range"
          v-model.number="params.Zpump"
          :min="500"
          :max="3000"
          :step="100"
          class="range-input"
        />
        <span class="range-value">{{ params.Zpump }} MW</span>
      </div>
      <div class="control-group">
        <label>蓄能时长</label>
        <input
          type="range"
          v-model.number="params.h"
          :min="1"
          :max="12"
          :step="1"
          class="range-input"
        />
        <span class="range-value">{{ params.h }} h</span>
      </div>
      <div class="control-group">
        <label>抽水效率</label>
        <input
          type="range"
          v-model.number="params.efficiency"
          :min="0.5"
          :max="0.95"
          :step="0.05"
          class="range-input"
        />
        <span class="range-value"
          >{{ (params.efficiency * 100).toFixed(0) }}%</span
        >
      </div>
    </div>

    <!-- 反馈消息 -->
    <transition name="toast">
      <div
        v-if="feedbackMessage"
        class="toast"
        :class="'toast--' + feedbackType"
      >
        {{ feedbackMessage }}
      </div>
    </transition>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>加载数据中...</p>
    </div>

    <!-- 主内容 -->
    <template v-if="!loading && dayData">
      <!-- 可拖拽调度曲线 -->
      <DragChart
        ref="dragChartRef"
        :data="chartData"
        title="抽水蓄能调度曲线（拖拽调整）"
        @change="onChartChange"
        @apply="onApplySchedule"
        @undo="onUndo"
        @reset="onReset"
      />

      <!-- 关键指标 -->
      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-label">发电量（本日）</div>
          <div class="metric-value" style="color: #00ff88">
            {{ dayStats.dailyGen.toFixed(0) }}
          </div>
          <div class="metric-unit">MWh</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">抽水电量（本日）</div>
          <div class="metric-value" style="color: #00d4ff">
            {{ dayStats.dailyPump.toFixed(0) }}
          </div>
          <div class="metric-unit">MWh</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">最大发电功率</div>
          <div class="metric-value" style="color: #ffcc00">
            {{ dayStats.maxGen.toFixed(0) }}
          </div>
          <div class="metric-unit">MW</div>
        </div>
        <div class="metric-card">
          <div class="metric-label">最大抽水功率</div>
          <div class="metric-value" style="color: #ff6b6b">
            {{ dayStats.maxPump.toFixed(0) }}
          </div>
          <div class="metric-unit">MW</div>
        </div>
      </div>

      <!-- 对比分析 -->
      <div class="comparison-section">
        <h3>📊 有/无抽蓄火电负荷对比</h3>
        <div class="comparison-charts">
          <!-- 这里用 ECharts 展示对比 -->
          <div ref="comparisonChartRef" class="comparison-chart-body"></div>
        </div>
        <div class="comparison-metrics">
          <div class="metric-card">
            <div class="metric-label">碳减排量（年度）</div>
            <div class="metric-value" style="color: #00ff88">
              {{ carbonResult.carbon_change.toFixed(2) }}
            </div>
            <div class="metric-unit">万吨</div>
          </div>
          <div class="metric-card">
            <div class="metric-label">火电变化</div>
            <div class="metric-value" style="color: #ffcc00">
              {{ carbonResult.power_change.toFixed(2) }}
            </div>
            <div class="metric-unit">亿kWh</div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import {
  ref,
  computed,
  onMounted,
  onBeforeUnmount,
  watch,
  nextTick,
} from "vue";
import * as echarts from "echarts";
import DragChart from "../components/DragChart.vue";
import { fetchAllData, fetchNpump, fetchCarbon, simulate } from "../api";

// ==================== 状态 ====================
const selectedDay = ref(0);
const loading = ref(true);
const allData = ref(null);
const carbonResult = ref({ carbon_change: 0, power_change: 0 });
const dragChartRef = ref(null);
const comparisonChartRef = ref(null);
let comparisonChartInstance = null; // 复用实例，避免重复创建

const params = ref({
  Zpump: 1400,
  h: 4,
  efficiency: 0.75,
  min_power_ratio: 0.2,
  carbon_factor: 0.5,
  coal_consumption_high: 300,
  coal_consumption_mid: 330,
  coal_consumption_low: 370,
});

// ==================== 响应式状态 ====================
const editedSchedule = ref(null);
const feedbackMessage = ref("");
const feedbackType = ref("success"); // 'success' | 'info'

// 滑块参数变化后的模拟结果缓存
const simulatedNpRaw = ref(null); // (365,24) 或 null
const simulatedNt = ref(null);
const simulatedNt2 = ref(null);
let simulateTimer = null;
let feedbackTimer = null;

// ==================== 计算属性 ====================

const dayData = computed(() => {
  if (!allData.value) return null;
  const d = allData.value;
  // 优先使用滑块参数模拟后的数据，否则用原始数据
  const np = simulatedNpRaw.value
    ? simulatedNpRaw.value[selectedDay.value]
    : d.np_raw[selectedDay.value];
  return {
    wind: d.wind[selectedDay.value],
    solar: d.solar[selectedDay.value],
    hydro: d.hydro[selectedDay.value],
    fh: d.fh[selectedDay.value],
    np_raw: np,
  };
});

const chartData = computed(() => {
  if (!dayData.value) return [];
  return dayData.value.np_raw.map((val, idx) => [idx, val]);
});

const dayStats = computed(() => {
  if (!dayData.value)
    return { dailyGen: 0, dailyPump: 0, maxGen: 0, maxPump: 0 };
  const np = editedSchedule.value || dayData.value.np_raw;
  const gen = np.filter((v) => v > 0);
  const pump = np.filter((v) => v < 0);
  return {
    dailyGen: gen.reduce((a, b) => a + b, 0),
    dailyPump: Math.abs(pump.reduce((a, b) => a + b, 0)),
    maxGen: gen.length > 0 ? Math.max(...gen) : 0,
    maxPump: pump.length > 0 ? Math.abs(Math.min(...pump)) : 0,
  };
});

// ==================== 图表操作 ====================

function initComparisonChart() {
  if (!comparisonChartRef.value || !allData.value) return;
  // 先销毁旧实例再创建，避免 DOM 上实例冲突
  if (comparisonChartInstance) {
    comparisonChartInstance.dispose();
  }
  comparisonChartInstance = echarts.init(comparisonChartRef.value);
  const chart = comparisonChartInstance;
  const d = allData.value;
  // 优先使用模拟数据
  const ntData = simulatedNt.value
    ? simulatedNt.value[selectedDay.value]
    : d.Nt[selectedDay.value];
  const nt2Data = simulatedNt2.value
    ? simulatedNt2.value[selectedDay.value]
    : d.Nt2[selectedDay.value];
  const hours = Array.from({ length: 24 }, (_, i) => `${i}:00`);

  chart.setOption({
    backgroundColor: "transparent",
    tooltip: { trigger: "axis" },
    legend: {
      data: ["有抽蓄火电", "无抽蓄火电"],
      textStyle: { color: "#8ba4c4" },
    },
    grid: { left: 60, right: 40, top: 60, bottom: 50 },
    xAxis: {
      type: "category",
      data: hours,
      axisLabel: { color: "#8ba4c4" },
    },
    yAxis: {
      type: "value",
      name: "功率 (MW)",
      nameTextStyle: { color: "#8ba4c4" },
      axisLabel: { color: "#8ba4c4" },
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.05)" } },
    },
    series: [
      {
        name: "有抽蓄火电",
        type: "line",
        data: ntData,
        lineStyle: { color: "#00d4ff", width: 2 },
        itemStyle: { color: "#00d4ff" },
        smooth: true,
      },
      {
        name: "无抽蓄火电",
        type: "line",
        data: nt2Data,
        lineStyle: { color: "#ff6b6b", width: 2, type: "dashed" },
        itemStyle: { color: "#ff6b6b" },
        smooth: true,
      },
    ],
  });

  return chart;
}

// ==================== 反馈消息 ====================

function showFeedback(msg, type = "success", duration = 2500) {
  feedbackMessage.value = msg;
  feedbackType.value = type;
  clearTimeout(feedbackTimer);
  feedbackTimer = setTimeout(() => {
    feedbackMessage.value = "";
  }, duration);
}

// ==================== 事件处理 ====================

function onChartChange(newData) {
  editedSchedule.value = newData.map((p) => p[1]);
  calculateDayMetrics();
}

function onApplySchedule() {
  if (!editedSchedule.value) {
    showFeedback("⚠️ 请先拖拽调整调度曲线", "info", 2000);
    return;
  }
  // 调度已通过 editedSchedule 存储到响应式状态
  // 触发指标重算
  calculateDayMetrics();
  showFeedback("✅ 调度策略已应用！指标已更新", "success");
}

function onUndo() {
  // DragChart 组件内已重置并 emit change → onChartChange 会同步更新指标
  showFeedback("↩️ 已撤销到原始调度", "info", 2000);
}

function onReset() {
  showFeedback("🔄 已重置为原始调度", "info", 2000);
}

function calculateDayMetrics() {
  // dayStats 是 computed，自动响应 editedSchedule.value 的变化
  // 这里触发一次 API 调用获取更新的碳减排指标
  if (editedSchedule.value && allData.value) {
    updateCarbonResult();
  }
}

async function updateCarbonResult() {
  try {
    const result = await simulate({
      ...params.value,
      Zpump: params.value.Zpump,
      h: params.value.h,
    });
    // 缓存模拟结果供图表使用
    simulatedNpRaw.value = result.np_raw;
    simulatedNt.value = result.Nt;
    simulatedNt2.value = result.Nt2;
    carbonResult.value = result.carbon_result;
  } catch {
    // 保持现有值
  }
}

// 监听滑块参数变化（300ms 防抖），自动重算
watch(
  () => [
    params.value.Zpump,
    params.value.h,
    params.value.efficiency,
    params.value.carbon_factor,
  ],
  () => {
    clearTimeout(simulateTimer);
    simulateTimer = setTimeout(() => {
      updateCarbonResult();
      // 等 DOM 更新后刷新对比图
      nextTick(() => initComparisonChart());
    }, 300);
  },
  { deep: false },
);

// ==================== 生命周期 ====================

onMounted(async () => {
  try {
    allData.value = await fetchAllData();
    carbonResult.value = allData.value.carbon_result;
    loading.value = false;

    await nextTick();
    initComparisonChart();

    // 响应式
    window.addEventListener("resize", () => comparisonChartInstance?.resize());
  } catch (e) {
    console.error("数据加载失败:", e);
    loading.value = false;
  }
});

// 日期切换时更新对比图
watch(selectedDay, async () => {
  await nextTick();
  initComparisonChart();
});

onBeforeUnmount(() => {
  clearTimeout(simulateTimer);
  clearTimeout(feedbackTimer);
  comparisonChartInstance?.dispose();
  comparisonChartInstance = null;
});
</script>

<style scoped>
.scheduling-editor {
  animation: fadeIn 0.3s ease;
  min-height: 100vh;
  padding: 10px;
  background:
    radial-gradient(
      circle at 50% 8%,
      rgba(20, 241, 190, 0.07),
      transparent 30%
    ),
    repeating-linear-gradient(
      0deg,
      rgba(86, 217, 255, 0.018) 0 1px,
      transparent 1px 30px
    ),
    #020d15;
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

.control-bar {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  padding: 16px;
  background: linear-gradient(
    135deg,
    rgba(0, 212, 255, 0.08),
    rgba(0, 150, 255, 0.03)
  );
  border: 1px solid var(--border-color);
  border-radius: 2px;
  margin: 10px 0;
  border-color: rgba(20, 241, 190, 0.3);
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 150px;
  flex: 1;
}

.control-group label {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.select-input {
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 0.9rem;
}

.range-input {
  width: 100%;
  height: 6px;
  -webkit-appearance: none;
  appearance: none;
  background: rgba(0, 212, 255, 0.2);
  border-radius: 3px;
  outline: none;
}

.range-input::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--accent);
  cursor: pointer;
}

.range-value {
  font-size: 0.85rem;
  color: var(--accent);
  font-weight: 600;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
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

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.metric-card {
  background: linear-gradient(
    135deg,
    rgba(0, 212, 255, 0.1),
    rgba(0, 150, 255, 0.05)
  );
  border: 1px solid var(--border-color);
  border-radius: 2px;
  padding: 20px;
  transition: all 0.3s;
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 212, 255, 0.15);
}

.metric-label {
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.metric-value {
  font-size: 1.8rem;
  font-weight: 700;
  margin-bottom: 4px;
}

.metric-unit {
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.comparison-section {
  margin-top: 24px;
}

.comparison-section h3 {
  font-size: 1.1rem;
  color: var(--accent);
  margin-bottom: 16px;
}

.comparison-chart-body {
  width: 100%;
  height: 400px;
  background: linear-gradient(
    135deg,
    rgba(0, 212, 255, 0.05),
    rgba(0, 150, 255, 0.02)
  );
  border: 1px solid var(--border-color);
  border-radius: 2px;
  border-color: rgba(20, 241, 190, 0.28);
  margin-bottom: 16px;
}

.comparison-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

/* Toast 反馈消息 */
.toast {
  position: fixed;
  top: 80px;
  left: 50%;
  transform: translateX(-50%);
  padding: 12px 28px;
  border-radius: 10px;
  font-size: 0.9rem;
  font-weight: 600;
  z-index: 9999;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(10px);
  pointer-events: none;
}
.toast--success {
  background: rgba(0, 255, 136, 0.2);
  border: 1px solid rgba(0, 255, 136, 0.4);
  color: #00ff88;
}
.toast--info {
  background: rgba(0, 212, 255, 0.2);
  border: 1px solid rgba(0, 212, 255, 0.4);
  color: #00d4ff;
}
.toast-enter-active {
  transition: all 0.3s ease;
}
.toast-leave-active {
  transition: all 0.3s ease;
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(-50%) translateY(-20px);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-20px);
}
</style>
