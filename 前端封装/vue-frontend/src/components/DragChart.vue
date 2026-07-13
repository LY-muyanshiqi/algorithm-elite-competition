<template>
  <div class="drag-chart-container">
    <div class="chart-header">
      <h3 class="chart-title">{{ title }}</h3>
      <div class="chart-actions">
        <button class="btn btn-sm" @click="undo">↩️ 撤销</button>
        <button class="btn btn-sm" @click="reset">🔄 重置</button>
        <button class="btn btn-primary btn-sm" @click="applyChanges">
          ✅ 应用调度
        </button>
      </div>
    </div>
    <div class="chart-info-bar">
      <span
        >💡 拖拽曲线上的
        <strong>圆点</strong> 调整调度策略，点击数字可直接输入</span
      >
      <span v-if="modified" class="modified-badge"
        >⚠️ 已修改，点击「应用调度」生效</span
      >
    </div>
    <div ref="chartRef" class="chart-body"></div>

    <!-- 点击编辑弹窗 -->
    <div v-if="editDialog.show" class="edit-dialog" @click.stop>
      <div class="edit-dialog-content" @click.stop>
        <div class="edit-dialog-header">
          <span>✏️ 编辑功率 — 时段 {{ editDialog.hour }}:00</span>
          <button class="edit-close" @click="closeEditDialog">✕</button>
        </div>
        <div class="edit-dialog-body">
          <input
            ref="editInputRef"
            v-model.number="editDialog.value"
            type="number"
            class="edit-input"
            :min="yMin"
            :max="yMax"
            :placeholder="`输入功率值 (${yMin} ~ ${yMax})`"
            @keyup.enter="confirmEdit"
            @keyup.escape="closeEditDialog"
          />
          <span class="edit-unit">{{ yUnit }}</span>
        </div>
        <div class="edit-dialog-hint">
          正数 = 发电 &nbsp;|&nbsp; 负数 = 抽水
        </div>
        <div class="edit-dialog-footer">
          <button class="btn btn-sm" @click="closeEditDialog">取消</button>
          <button class="btn btn-primary btn-sm" @click="confirmEdit">
            ✅ 确定
          </button>
        </div>
      </div>
    </div>
    <!-- 点击遮罩关闭 -->
    <div
      v-if="editDialog.show"
      class="edit-overlay"
      @click="closeEditDialog"
    ></div>
  </div>
</template>

<script setup>
import {
  ref,
  reactive,
  onMounted,
  onBeforeUnmount,
  watch,
  nextTick,
} from "vue";
import * as echarts from "echarts";

const props = defineProps({
  title: { type: String, default: "抽水蓄能调度曲线" },
  data: { type: Array, required: true },
  yUnit: { type: String, default: "MW" },
  yMin: { type: Number, default: -1500 },
  yMax: { type: Number, default: 1500 },
});

const emit = defineEmits(["change", "apply", "undo", "reset"]);

const chartRef = ref(null);
const editInputRef = ref(null);
let chart = null;
const modified = ref(false);
let originalData = [];
let currentData = [];
let appliedData = null; // 应用调度时保存的基准，用于 watch 判断

// ---- 编辑弹窗状态 ----
const editDialog = reactive({
  show: false,
  idx: -1,
  hour: 0,
  value: 0,
});

// ---- 拖拽状态 ----
let dragState = null; // { idx, startY, startVal } | null

// ==================== ECharts 配置 ====================

function buildOption() {
  return {
    backgroundColor: "transparent",
    grid: { left: 60, right: 40, top: 40, bottom: 50 },
    tooltip: {
      trigger: "axis",
      formatter: (params) => {
        const p = params[0];
        const val = p.value[1];
        const status = val >= 0 ? "🟢 发电" : "🔵 抽水";
        return `时段 ${p.value[0]}:00<br/>功率: ${Math.abs(val).toFixed(0)} MW ${status}`;
      },
      backgroundColor: "rgba(10, 22, 40, 0.9)",
      borderColor: "rgba(0, 212, 255, 0.3)",
      textStyle: { color: "#e0e6ed" },
    },
    xAxis: {
      type: "value",
      min: 0,
      max: 23,
      axisLabel: { formatter: "{value}:00", color: "#8ba4c4" },
      splitLine: { show: false },
    },
    yAxis: {
      type: "value",
      min: props.yMin,
      max: props.yMax,
      axisLabel: { formatter: `{value} ${props.yUnit}`, color: "#8ba4c4" },
      splitLine: {
        lineStyle: { color: "rgba(255,255,255,0.05)", type: "dashed" },
      },
    },
    series: [
      {
        type: "line",
        data: currentData,
        smooth: false,
        symbol: "circle",
        symbolSize: 14,
        lineStyle: { width: 3, color: "#00d4ff" },
        itemStyle: {
          color: (p) => (p.value[1] >= 0 ? "#00ff88" : "#00d4ff"),
          borderColor: "#0a1628",
          borderWidth: 2,
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(0, 212, 255, 0.3)" },
            { offset: 1, color: "rgba(0, 212, 255, 0.02)" },
          ]),
        },
        markLine: {
          silent: true,
          data: [{ yAxis: 0 }],
          lineStyle: { color: "rgba(255,255,255,0.2)", type: "dashed" },
          label: { show: false },
        },
      },
    ],
  };
}

// ==================== 拖拽（chart.on + document 级事件） ====================

function setupDrag() {
  if (!chart) return;
  const dom = chartRef.value;
  if (!dom) return;

  function findNearestPoint(x, y) {
    const point = chart.convertFromPixel("grid", [x, y]);
    if (!point) return -1;
    const idx = Math.round(point[0]);
    if (idx < 0 || idx >= 24) return -1;
    const sp = chart.convertToPixel("grid", [idx, currentData[idx][1]]);
    if (!sp) return -1;
    return Math.sqrt((x - sp[0]) ** 2 + (y - sp[1]) ** 2) < 35 ? idx : -1;
  }

  let dragIdx = -1;
  let startVal = 0;
  let startX = 0;
  let startY = 0;

  function getPos(e) {
    const r = dom.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  }

  // 在容器 dom 上用捕获阶段监听 mousedown（早于 ECharts canvas 事件）
  dom.addEventListener(
    "mousedown",
    (e) => {
      const pos = getPos(e);
      const idx = findNearestPoint(pos.x, pos.y);
      if (idx >= 0) {
        dragIdx = idx;
        startVal = currentData[idx][1];
        startX = pos.x;
        startY = pos.y;
      }
    },
    { capture: true },
  );

  // document 级 mousemove（拖拽中不掉事件）
  const onMove = (e) => {
    if (dragIdx < 0) return;
    const pos = getPos(e);
    const dy = pos.y - startY;
    const gridH = dom.offsetHeight - 90;
    const dataRange = props.yMax - props.yMin;
    const delta = gridH > 0 ? -(dy / gridH) * dataRange : 0;
    const val = Math.max(
      props.yMin,
      Math.min(props.yMax, Math.round(startVal + delta)),
    );

    if (currentData[dragIdx][1] !== val) {
      currentData[dragIdx] = [dragIdx, val];
      modified.value = true;
      chart.setOption({ series: [{ data: currentData.map((p) => [...p]) }] });
    }
  };

  // document 级 mouseup（拖拽结束）
  const onUp = (e) => {
    if (dragIdx < 0) return;
    const pos = getPos(e);
    const moved = Math.abs(pos.x - startX) > 3 || Math.abs(pos.y - startY) > 3;
    if (moved) {
      emit("change", [...currentData.map((p) => [...p])]);
    } else {
      editDialog.idx = dragIdx;
      editDialog.hour = dragIdx;
      editDialog.value = currentData[dragIdx][1];
      editDialog.show = true;
      nextTick(() => editInputRef.value?.focus());
    }
    dragIdx = -1;
  };

  document.addEventListener("mousemove", onMove);
  document.addEventListener("mouseup", onUp);

  // 清理
  const cleanup = () => {
    document.removeEventListener("mousemove", onMove);
    document.removeEventListener("mouseup", onUp);
  };
  // 存入 chart 以便生命周期清理
  chart._dragCleanup = cleanup;
}

// ==================== 生命周期 ====================

onMounted(() => {
  originalData = [...props.data.map((p) => [...p])];
  currentData = [...props.data.map((p) => [...p])];
  nextTick(() => {
    if (!chartRef.value) return;
    chart = echarts.init(chartRef.value, null, { renderer: "canvas" });
    chart.setOption(buildOption());
    // 延时启动确保 chart 渲染完成
    setTimeout(setupDrag, 300);
    window.addEventListener("resize", () => chart?.resize());
  });
});

onBeforeUnmount(() => {
  chart?._dragCleanup?.();
  chart?.dispose();
  chart = null;
});

watch(
  () => props.data,
  (newData) => {
    if (!newData?.length) return;
    const newOrig = newData.map((p) => [...p]);

    // 已通过「应用调度」保存后，任何与原始数据相同的传入都跳过
    if (appliedData) {
      const sameAsApplied =
        newOrig.length === appliedData.length &&
        newOrig.every(
          (p, i) =>
            p[0] === appliedData[i]?.[0] && p[1] === appliedData[i]?.[1],
        );
      const sameAsOrig =
        newOrig.length === originalData.length &&
        newOrig.every(
          (p, i) =>
            p[0] === originalData[i]?.[0] && p[1] === originalData[i]?.[1],
        );
      if (sameAsApplied || sameAsOrig) return;
    }

    // 有未保存修改时，不重置
    const sameAsOrig2 =
      newOrig.length === originalData.length &&
      newOrig.every(
        (p, i) =>
          p[0] === originalData[i]?.[0] && p[1] === originalData[i]?.[1],
      );
    if (sameAsOrig2 && modified.value) return;

    // 真正切换了数据（如切换日期），重置
    originalData = newOrig;
    currentData = [...newOrig.map((p) => [...p])];
    appliedData = null;
    modified.value = false;
    if (chart) {
      chart.setOption(buildOption(), { replaceMerge: ["series"] });
    }
  },
);

// ==================== 公开方法 ====================

function undo() {
  currentData = [...originalData.map((p) => [...p])];
  appliedData = null;
  modified.value = false;
  if (chart) {
    chart.setOption(buildOption(), { replaceMerge: ["series"] });
  }
  emit("change", [...currentData.map((p) => [...p])]);
  emit("undo");
}

function reset() {
  currentData = [...originalData.map((p) => [...p])];
  appliedData = null;
  modified.value = false;
  if (chart) {
    chart.setOption(buildOption(), { replaceMerge: ["series"] });
  }
  emit("change", [...currentData.map((p) => [...p])]);
  emit("reset");
}

function applyChanges() {
  // 数据已在拖拽时通过 change 事件发给父组件了，这里只需要发 apply 信号
  appliedData = [...currentData.map((p) => [...p])]; // 保存基准，防止 watch 重置
  modified.value = false;
  emit("apply");
}

// ==================== 编辑弹窗 ====================

function confirmEdit() {
  if (editDialog.idx < 0 || editDialog.idx >= 24) return;
  const val = Math.max(
    props.yMin,
    Math.min(props.yMax, Math.round(editDialog.value)),
  );
  currentData[editDialog.idx] = [editDialog.idx, val];
  modified.value = true;
  chart?.setOption({ series: [{ data: currentData }] });
  emit("change", [...currentData.map((p) => [...p])]);
  editDialog.show = false;
}

function closeEditDialog() {
  editDialog.show = false;
}

defineExpose({ getData: () => currentData });
</script>

<style scoped>
.drag-chart-container {
  background: linear-gradient(
    135deg,
    rgba(0, 212, 255, 0.08),
    rgba(0, 150, 255, 0.03)
  );
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.chart-title {
  font-size: 1rem;
  color: var(--accent);
}

.chart-actions {
  display: flex;
  gap: 8px;
}

.chart-info-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.8rem;
  color: var(--text-secondary);
  margin-bottom: 12px;
  padding: 6px 12px;
  background: rgba(0, 212, 255, 0.05);
  border-radius: 6px;
}

.modified-badge {
  color: var(--warning);
  font-weight: 600;
}

.chart-body {
  width: 100%;
  height: 400px;
}

/* 按钮样式 */
.btn {
  padding: 6px 14px;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 0.8rem;
  transition: all 0.2s;
}

.btn:hover {
  background: rgba(0, 212, 255, 0.1);
  color: var(--text-primary);
}

.btn-primary {
  background: linear-gradient(135deg, var(--accent), #0096ff);
  border: none;
  color: white;
  font-weight: 600;
}

.btn-primary:hover {
  box-shadow: 0 4px 15px rgba(0, 212, 255, 0.3);
}

.btn-sm {
  padding: 4px 10px;
  font-size: 0.75rem;
}

/* ========== 编辑弹窗 ========== */
.edit-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 9998;
}

.edit-dialog {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 9999;
}

.edit-dialog-content {
  background: linear-gradient(135deg, #0d1f3c 0%, #1a2f4b 100%);
  border: 1px solid rgba(0, 212, 255, 0.3);
  border-radius: 16px;
  padding: 24px;
  min-width: 320px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

.edit-dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  font-size: 1rem;
  color: var(--accent);
  font-weight: 600;
}

.edit-close {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 1.2rem;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.2s;
}
.edit-close:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.05);
}

.edit-dialog-body {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.edit-input {
  flex: 1;
  padding: 10px 14px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 1.2rem;
  font-weight: 600;
  outline: none;
  transition: border-color 0.2s;
}
.edit-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px rgba(0, 212, 255, 0.2);
}

.edit-unit {
  font-size: 1rem;
  color: var(--text-secondary);
  min-width: 40px;
}

.edit-dialog-hint {
  font-size: 0.75rem;
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.edit-dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
