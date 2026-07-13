<template>
  <div class="simulation-view">
    <div class="page-header">
      <h2>🔬 实时仿真</h2>
      <p class="page-desc">
        调整关键参数组合，实时对比不同方案下的系统性能指标
      </p>
    </div>

    <!-- 场景管理 -->
    <div class="section-card scenarios-section">
      <details>
        <summary class="scenarios-summary">
          🗂️ 场景管理
          <span class="badge-count">{{ savedScenarios.length }}</span>
        </summary>
        <div class="scenarios-body">
          <div class="scenario-save-row">
            <input
              v-model="scenarioName"
              class="scenario-input"
              placeholder="输入场景名称..."
              @keyup.enter="saveScenario"
            />
            <button class="btn-sm btn-primary" @click="saveScenario">
              💾 保存当前方案
            </button>
          </div>
          <div v-if="savedScenarios.length === 0" class="scenarios-empty">
            暂无保存的场景
          </div>
          <div v-for="(sc, i) in savedScenarios" :key="i" class="scenario-item">
            <div class="scenario-info">
              <strong>{{ sc.name }}</strong>
              <span class="scenario-time">{{ sc.time }}</span>
              <span class="scenario-params">
                Zpump={{ sc.params.Zpump }}MW h={{ sc.params.h }}h η={{
                  (sc.params.efficiency * 100).toFixed(0)
                }}%
              </span>
            </div>
            <div class="scenario-actions">
              <button class="btn-tiny" @click="loadScenario(i)">📂 加载</button>
              <button class="btn-tiny" @click="compareScenario(i)">
                🔍 对比
              </button>
              <button class="btn-tiny btn-danger" @click="deleteScenario(i)">
                🗑️
              </button>
            </div>
          </div>
        </div>
      </details>
    </div>

    <!-- 方案对比区 -->
    <div class="scenario-grid">
      <!-- 方案 A -->
      <div class="scenario-card">
        <div class="scenario-header">
          <h3>🔵 方案 A</h3>
          <span
            class="badge"
            :class="
              scenarioALabel === '自定义' ? 'badge-warning' : 'badge-info'
            "
          >
            {{ scenarioALabel }}
          </span>
        </div>
        <div class="params-form">
          <div class="param-row">
            <label>抽蓄容量</label>
            <input
              type="number"
              v-model.number="paramsA.Zpump"
              :min="500"
              :max="3000"
              :step="100"
            />
            <span>MW</span>
          </div>
          <div class="param-row">
            <label>蓄能时长</label>
            <input
              type="number"
              v-model.number="paramsA.h"
              :min="1"
              :max="12"
            />
            <span>h</span>
          </div>
          <div class="param-row">
            <label>抽水效率</label>
            <input
              type="number"
              v-model.number="paramsA.efficiency"
              :min="0.5"
              :max="0.95"
              :step="0.05"
            />
          </div>
          <div class="param-row">
            <label>碳排放系数</label>
            <input
              type="number"
              v-model.number="paramsA.carbon_factor"
              :min="0.1"
              :max="1.0"
              :step="0.05"
            />
            <span>t/万kWh</span>
          </div>
        </div>
        <div v-if="resultA" class="scenario-result">
          <div class="result-visual-row">
            <div class="result-icon">🌍</div>
            <div class="result-body">
              <div class="result-label">碳减排量</div>
              <div class="result-bar-bg">
                <div
                  class="result-bar-fill"
                  :style="{
                    width: resultA.carbonPct + '%',
                    background: '#00ff88',
                  }"
                ></div>
              </div>
              <div class="result-value" style="color: #00ff88">
                {{ (resultA.carbon_change ?? 0).toFixed(2) }} 万吨
              </div>
            </div>
          </div>
          <div class="result-visual-row">
            <div class="result-icon">⚡</div>
            <div class="result-body">
              <div class="result-label">发电小时</div>
              <div class="result-bar-bg">
                <div
                  class="result-bar-fill"
                  :style="{
                    width: (resultA.generating_hours / 5000) * 100 + '%',
                    background: '#00d4ff',
                  }"
                ></div>
              </div>
              <div class="result-value" style="color: #00d4ff">
                {{ resultA.generating_hours }} h
              </div>
            </div>
          </div>
          <div class="result-visual-row">
            <div class="result-icon">💧</div>
            <div class="result-body">
              <div class="result-label">抽水小时</div>
              <div class="result-bar-bg">
                <div
                  class="result-bar-fill"
                  :style="{
                    width: (resultA.pumping_hours / 5000) * 100 + '%',
                    background: '#ffcc00',
                  }"
                ></div>
              </div>
              <div class="result-value" style="color: #ffcc00">
                {{ resultA.pumping_hours }} h
              </div>
            </div>
          </div>
          <div class="result-visual-row">
            <div class="result-icon">🔄</div>
            <div class="result-body">
              <div class="result-label">综合效率</div>
              <div class="result-bar-bg">
                <div
                  class="result-bar-fill"
                  :style="{
                    width: (resultA.efficiency ?? 0) + '%',
                    background: '#00ff88',
                  }"
                ></div>
              </div>
              <div class="result-value" style="color: #00ff88">
                {{ (resultA.efficiency ?? 0).toFixed(1) }}%
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 方案 B -->
      <div class="scenario-card">
        <div class="scenario-header">
          <h3>🟠 方案 B</h3>
          <span
            class="badge"
            :class="
              scenarioBLabel === '自定义' ? 'badge-warning' : 'badge-info'
            "
          >
            {{ scenarioBLabel }}
          </span>
        </div>
        <button class="btn-preset" @click="loadPresetB('高消纳方案')">
          📋 填入「高消纳方案」
        </button>
        <button class="btn-preset" @click="loadPresetB('深度低碳方案')">
          📋 填入「深度低碳方案」
        </button>
        <button class="btn-preset" @click="loadPresetB('灵活调峰方案')">
          📋 填入「灵活调峰方案」
        </button>
        <div class="params-form">
          <div class="param-row">
            <label>抽蓄容量</label>
            <input
              type="number"
              v-model.number="paramsB.Zpump"
              :min="500"
              :max="3000"
              :step="100"
            />
            <span>MW</span>
          </div>
          <div class="param-row">
            <label>蓄能时长</label>
            <input
              type="number"
              v-model.number="paramsB.h"
              :min="1"
              :max="12"
            />
            <span>h</span>
          </div>
          <div class="param-row">
            <label>抽水效率</label>
            <input
              type="number"
              v-model.number="paramsB.efficiency"
              :min="0.5"
              :max="0.95"
              :step="0.05"
            />
          </div>
          <div class="param-row">
            <label>碳排放系数</label>
            <input
              type="number"
              v-model.number="paramsB.carbon_factor"
              :min="0.1"
              :max="1.0"
              :step="0.05"
            />
            <span>t/万kWh</span>
          </div>
        </div>
        <div v-if="resultB" class="scenario-result">
          <div class="result-visual-row">
            <div class="result-icon">🌍</div>
            <div class="result-body">
              <div class="result-label">碳减排量</div>
              <div class="result-bar-bg">
                <div
                  class="result-bar-fill"
                  :style="{
                    width: resultB.carbonPct + '%',
                    background: '#ff9800',
                  }"
                ></div>
              </div>
              <div class="result-value" style="color: #ff9800">
                {{ (resultB.carbon_change ?? 0).toFixed(2) }} 万吨
              </div>
            </div>
          </div>
          <div class="result-visual-row">
            <div class="result-icon">⚡</div>
            <div class="result-body">
              <div class="result-label">发电小时</div>
              <div class="result-bar-bg">
                <div
                  class="result-bar-fill"
                  :style="{
                    width: (resultB.generating_hours / 5000) * 100 + '%',
                    background: '#00d4ff',
                  }"
                ></div>
              </div>
              <div class="result-value" style="color: #00d4ff">
                {{ resultB.generating_hours }} h
              </div>
            </div>
          </div>
          <div class="result-visual-row">
            <div class="result-icon">💧</div>
            <div class="result-body">
              <div class="result-label">抽水小时</div>
              <div class="result-bar-bg">
                <div
                  class="result-bar-fill"
                  :style="{
                    width: (resultB.pumping_hours / 5000) * 100 + '%',
                    background: '#ffcc00',
                  }"
                ></div>
              </div>
              <div class="result-value" style="color: #ffcc00">
                {{ resultB.pumping_hours }} h
              </div>
            </div>
          </div>
          <div class="result-visual-row">
            <div class="result-icon">🔄</div>
            <div class="result-body">
              <div class="result-label">综合效率</div>
              <div class="result-bar-bg">
                <div
                  class="result-bar-fill"
                  :style="{
                    width: (resultB.efficiency ?? 0) + '%',
                    background: '#ff9800',
                  }"
                ></div>
              </div>
              <div class="result-value" style="color: #ff9800">
                {{ (resultB.efficiency ?? 0).toFixed(1) }}%
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 对比按钮 -->
    <div class="action-bar">
      <button class="btn-compare" @click="runComparison" :disabled="computing">
        {{ computing ? "⏳ 计算中..." : "🔍 开始对比分析" }}
      </button>
      <button class="btn-save" @click="saveToHistory" :disabled="!showComparison">
        💾 保存到历史
      </button>
      <button class="btn-reset" @click="resetAll">↺ 重置</button>
    </div>

    <!-- 对比结果 -->
    <div v-if="showComparison" class="comparison-result">
      <h3>📊 方案对比结果</h3>
      <div class="comparison-chart-wrap">
        <div ref="compareChartRef" class="compare-chart-body"></div>
      </div>
      <div class="comparison-table-wrap">
        <table class="comparison-table">
          <thead>
            <tr>
              <th>指标</th>
              <th>🔵 方案 A</th>
              <th>🟠 方案 B</th>
              <th>差值</th>
              <th>变化率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in comparisonRows" :key="row.label">
              <td>{{ row.label }}</td>
              <td>{{ row.valA }}</td>
              <td>{{ row.valB }}</td>
              <td :style="{ color: row.diffColor }">{{ row.diff }}</td>
              <td :style="{ color: row.pctColor }">{{ row.pct }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import {
  ref,
  reactive,
  computed,
  nextTick,
  onMounted,
  onBeforeUnmount,
} from "vue";
import * as echarts from "echarts";
import { simulate, saveHistory } from "../api";

const compareChartRef = ref(null);
let compareChartInstance = null;

// ==================== 预设方案 ====================
const PRESETS = {
  默认方案: {
    Zpump: 1400,
    h: 4,
    efficiency: 0.75,
    min_power_ratio: 0.2,
    carbon_factor: 0.5,
    coal_consumption_high: 300,
    coal_consumption_mid: 330,
    coal_consumption_low: 370,
  },
  高消纳方案: {
    Zpump: 2000,
    h: 5,
    efficiency: 0.85,
    min_power_ratio: 0.15,
    carbon_factor: 0.4,
    coal_consumption_high: 290,
    coal_consumption_mid: 320,
    coal_consumption_low: 360,
  },
  深度低碳方案: {
    Zpump: 1600,
    h: 4,
    efficiency: 0.8,
    min_power_ratio: 0.15,
    carbon_factor: 0.35,
    coal_consumption_high: 285,
    coal_consumption_mid: 315,
    coal_consumption_low: 355,
  },
  灵活调峰方案: {
    Zpump: 2500,
    h: 3,
    efficiency: 0.7,
    min_power_ratio: 0.25,
    carbon_factor: 0.55,
    coal_consumption_high: 300,
    coal_consumption_mid: 330,
    coal_consumption_low: 380,
  },
};

// ==================== 状态 ====================
const computing = ref(false);
const showComparison = ref(false);

const paramsA = reactive({ ...PRESETS["默认方案"] });
const paramsB = reactive({ ...PRESETS["高消纳方案"] });

const resultA = ref(null);

// ==================== 场景管理 ====================
const scenarioName = ref("");
const savedScenarios = ref(loadScenarios());

function loadScenarios() {
  try {
    return JSON.parse(localStorage.getItem("ps_scenarios") || "[]");
  } catch {
    return [];
  }
}
function saveScenarios() {
  localStorage.setItem("ps_scenarios", JSON.stringify(savedScenarios.value));
}

function saveScenario() {
  const name = scenarioName.value.trim();
  if (!name) {
    alert("请输入场景名称");
    return;
  }
  savedScenarios.value.push({
    name,
    params: { ...paramsA },
    time: new Date().toLocaleString("zh-CN"),
    result: resultA.value ? { ...resultA.value } : null,
  });
  saveScenarios();

  // 同步保存到后端数据库
  saveHistory({
    params: { ...paramsA },
    note: name,
    region: '华东',
    year: 2024,
  }).catch(e => {
    console.warn('DB save failed (backend may be offline):', e)
  });

  scenarioName.value = "";
}

function loadScenario(i) {
  const sc = savedScenarios.value[i];
  if (!sc) return;
  Object.assign(paramsA, sc.params);
  resultA.value = sc.result;
  scenarioALabel.value = `📂 ${sc.name}`;
}

function compareScenario(i) {
  const sc = savedScenarios.value[i];
  if (!sc) return;
  Object.assign(paramsB, sc.params);
  resultB.value = sc.result;
  scenarioBLabel.value = `📂 ${sc.name}`;
}

function deleteScenario(i) {
  savedScenarios.value.splice(i, 1);
  saveScenarios();
}
const resultB = ref(null);

const scenarioALabel = ref("默认方案");
const scenarioBLabel = ref("高消纳方案");

function loadPresetB(name) {
  Object.assign(paramsB, PRESETS[name]);
  scenarioBLabel.value = name;
}

// ==================== 对比计算 ====================
async function runComparison() {
  computing.value = true;
  showComparison.value = false;

  try {
    const [ra, rb] = await Promise.all([simulate(paramsA), simulate(paramsB)]);

    resultA.value = { ...ra.carbon_result, ...ra.ps_stats };
    resultB.value = { ...rb.carbon_result, ...rb.ps_stats };
    // 计算碳减排百分比（用于进度条）
    const maxCarbon = Math.max(
      resultA.value.carbon_change ?? 0,
      resultB.value.carbon_change ?? 0,
      0.01,
    );
    resultA.value.carbonPct =
      ((resultA.value.carbon_change ?? 0) / maxCarbon) * 100;
    resultB.value.carbonPct =
      ((resultB.value.carbon_change ?? 0) / maxCarbon) * 100;
    showComparison.value = true;
    await nextTick();
    initCompareChart();
  } catch (e) {
    console.error("仿真计算失败:", e);
  } finally {
    computing.value = false;
  }
}

function resetAll() {
  Object.assign(paramsA, PRESETS["默认方案"]);
  Object.assign(paramsB, PRESETS["高消纳方案"]);
  resultA.value = null;
  resultB.value = null;
  showComparison.value = false;
  scenarioALabel.value = "默认方案";
  scenarioBLabel.value = "高消纳方案";
}

async function saveToHistory() {
  try {
    await saveHistory({ params: { ...paramsA }, note: scenarioALabel.value, region: '华东', year: 2024 })
    await saveHistory({ params: { ...paramsB }, note: scenarioBLabel.value, region: '华东', year: 2024 })
    alert('已保存到历史记录！')
  } catch (e) {
    console.error('保存失败:', e)
    alert('保存失败，请确认后端已启动')
  }
}

onBeforeUnmount(() => {
  compareChartInstance?.dispose();
  compareChartInstance = null;
});

// ==================== 对比表数据 ====================
const comparisonRows = computed(() => {
  if (!resultA.value || !resultB.value) return [];
  const a = resultA.value;
  const b = resultB.value;

  const items = [
    { label: "碳减排量 (万吨)", key: "carbon_change", unit: "", isNum: true },
    { label: "火电变化量 (亿kWh)", key: "power_change", unit: "", isNum: true },
    { label: "发电小时数 (h)", key: "generating_hours", unit: "", isNum: true },
    { label: "抽水小时数 (h)", key: "pumping_hours", unit: "", isNum: true },
    { label: "总发电量 (MWh)", key: "total_generation", unit: "", isNum: true },
    { label: "综合效率 (%)", key: "efficiency", unit: "%", isNum: true },
  ];

  return items.map((item) => {
    const va = a[item.key] ?? 0;
    const vb = b[item.key] ?? 0;
    const diff = va - vb;
    const pct = vb !== 0 ? ((diff / vb) * 100).toFixed(1) + "%" : "--";
    const fmt = item.isNum
      ? (v) => {
          if (Number.isInteger(v)) return v;
          return v.toFixed(2);
        }
      : (v) => v;

    return {
      label: item.label,
      valA: fmt(va) + (item.unit ? " " + item.unit : ""),
      valB: fmt(vb) + (item.unit ? " " + item.unit : ""),
      diff: (diff >= 0 ? "+" : "") + fmt(diff),
      diffColor: diff >= 0 ? "#00ff88" : "#ff6b6b",
      pct,
      pctColor: pct.startsWith("+")
        ? "#00ff88"
        : pct.startsWith("-")
          ? "#ff6b6b"
          : "#8ba4c4",
    };
  });
});

function initCompareChart() {
  if (!compareChartRef.value || !resultA.value || !resultB.value) return;
  if (compareChartInstance) compareChartInstance.dispose();
  compareChartInstance = echarts.init(compareChartRef.value);
  const a = resultA.value;
  const b = resultB.value;
  const labels = ["碳减排\n(万吨)", "发电\n(百h)", "抽水\n(百h)", "效率(%)"];
  const valA = [
    a.carbon_change ?? 0,
    (a.generating_hours ?? 0) / 100,
    (a.pumping_hours ?? 0) / 100,
    a.efficiency ?? 0,
  ];
  const valB = [
    b.carbon_change ?? 0,
    (b.generating_hours ?? 0) / 100,
    (b.pumping_hours ?? 0) / 100,
    b.efficiency ?? 0,
  ];
  compareChartInstance.setOption({
    backgroundColor: "transparent",
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    legend: { data: ["🔵 方案A", "🟠 方案B"], textStyle: { color: "#8ba4c4" } },
    grid: { left: 60, right: 30, top: 50, bottom: 40 },
    xAxis: { type: "category", data: labels, axisLabel: { color: "#8ba4c4" } },
    yAxis: {
      type: "value",
      axisLabel: { color: "#8ba4c4" },
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.05)" } },
    },
    series: [
      {
        name: "🔵 方案A",
        type: "bar",
        data: valA,
        itemStyle: { color: "#00d4ff", borderRadius: [4, 4, 0, 0] },
        barWidth: "30%",
      },
      {
        name: "🟠 方案B",
        type: "bar",
        data: valB,
        itemStyle: { color: "#ff9800", borderRadius: [4, 4, 0, 0] },
        barWidth: "30%",
      },
    ],
  });
}
</script>

<style scoped>
.simulation-view {
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

.scenario-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.scenario-card {
  background: linear-gradient(
    135deg,
    rgba(0, 212, 255, 0.08),
    rgba(0, 150, 255, 0.03)
  );
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 20px;
}

.scenario-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.scenario-header h3 {
  font-size: 1.1rem;
}

.badge {
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 0.75rem;
}

.badge-info {
  background: rgba(0, 212, 255, 0.15);
  color: var(--accent);
}
.badge-warning {
  background: rgba(255, 204, 0, 0.15);
  color: var(--warning);
}

.btn-preset {
  display: inline-block;
  margin: 2px 4px 8px 0;
  padding: 4px 10px;
  font-size: 0.75rem;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.btn-preset:hover {
  background: rgba(0, 212, 255, 0.1);
  color: var(--text-primary);
}

.params-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}

.param-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.param-row label {
  width: 90px;
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.param-row input {
  flex: 1;
  padding: 6px 10px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 0.85rem;
}

.param-row span {
  font-size: 0.75rem;
  color: var(--text-secondary);
  width: 60px;
}

.scenario-result {
  border-top: 1px solid var(--border-color);
  padding-top: 12px;
}

.result-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 0.85rem;
}

.result-row span {
  color: var(--text-secondary);
}

.action-bar {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-bottom: 24px;
}

.btn-compare {
  padding: 12px 40px;
  background: linear-gradient(135deg, var(--accent), #0096ff);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-compare:hover:not(:disabled) {
  box-shadow: 0 6px 20px rgba(0, 212, 255, 0.4);
  transform: translateY(-2px);
}

.btn-compare:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-reset {
  padding: 12px 24px;
  background: transparent;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.btn-reset:hover {
  background: rgba(255, 107, 107, 0.1);
  color: var(--danger);
  border-color: var(--danger);
}

.btn-save {
  padding: 12px 24px;
  background: linear-gradient(135deg, rgba(0,255,136,0.15), rgba(0,200,80,0.08));
  border: 1px solid rgba(0,255,136,0.3);
  border-radius: 8px;
  color: #00ff88;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 600;
  transition: all 0.2s;
}
.btn-save:hover:not(:disabled) {
  background: rgba(0,255,136,0.2);
  box-shadow: 0 4px 15px rgba(0,255,136,0.2);
}
.btn-save:disabled { opacity: 0.4; cursor: not-allowed; }

.comparison-result {
  background: linear-gradient(
    135deg,
    rgba(0, 212, 255, 0.08),
    rgba(0, 150, 255, 0.03)
  );
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 24px;
}

.comparison-result h3 {
  font-size: 1.1rem;
  color: var(--accent);
  margin-bottom: 16px;
}

.comparison-table-wrap {
  overflow-x: auto;
}

.comparison-table {
  width: 100%;
  border-collapse: collapse;
}

.comparison-table th,
.comparison-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.comparison-table th {
  color: var(--text-secondary);
  font-size: 0.85rem;
  font-weight: 500;
  background: rgba(0, 212, 255, 0.05);
}

.comparison-table td {
  font-size: 0.9rem;
}

.comparison-table tr:hover td {
  background: rgba(0, 212, 255, 0.03);
}

.comparison-chart-wrap {
  margin-bottom: 20px;
}
.compare-chart-body {
  width: 100%;
  height: 280px;
  background: transparent;
}

/* 进度条结果展示 */
.scenario-result {
  margin-top: 16px;
}
.result-visual-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}
.result-visual-row:last-child {
  border-bottom: none;
}
.result-icon {
  font-size: 1.4rem;
  width: 32px;
  text-align: center;
  flex-shrink: 0;
}
.result-body {
  flex: 1;
  min-width: 0;
}
.result-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-bottom: 3px;
}
.result-bar-bg {
  width: 100%;
  height: 6px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 3px;
  overflow: hidden;
}
.result-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.5s ease;
}
.result-value {
  font-size: 0.85rem;
  font-weight: 700;
  margin-top: 2px;
}

/* 场景管理 */
.scenarios-section {
  margin-bottom: 20px;
}
.scenarios-summary {
  cursor: pointer;
  font-size: 1rem;
  color: var(--accent);
  padding: 4px 0;
  user-select: none;
}
.scenarios-summary::-webkit-details-marker {
  color: var(--accent);
}
.badge-count {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 10px;
  background: rgba(0, 212, 255, 0.15);
  font-size: 0.75rem;
  margin-left: 8px;
}
.scenarios-body {
  margin-top: 12px;
}
.scenario-save-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.scenario-input {
  flex: 1;
  padding: 8px 12px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  color: var(--text-primary);
  font-size: 0.85rem;
}
.scenarios-empty {
  color: var(--text-secondary);
  font-size: 0.85rem;
  padding: 12px;
  text-align: center;
}
.scenario-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  margin-bottom: 6px;
  transition: background 0.2s;
}
.scenario-item:hover {
  background: rgba(0, 212, 255, 0.04);
}
.scenario-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.scenario-info strong {
  font-size: 0.9rem;
  color: var(--text-primary);
}
.scenario-time {
  font-size: 0.7rem;
  color: var(--text-secondary);
}
.scenario-params {
  font-size: 0.78rem;
  color: var(--text-secondary);
}
.scenario-actions {
  display: flex;
  gap: 4px;
}
.btn-tiny {
  padding: 4px 8px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 0.72rem;
  transition: all 0.2s;
}
.btn-tiny:hover {
  background: rgba(0, 212, 255, 0.1);
  color: var(--text-primary);
}
.btn-danger:hover {
  background: rgba(255, 107, 107, 0.15);
  color: var(--danger);
  border-color: var(--danger);
}
</style>
