<template>
  <div class="history-compare">
    <div class="page-header">
      <h2>📜 历史运行对比</h2>
      <p class="page-desc">对比不同参数方案下的系统性能指标变化</p>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>加载历史记录...</p>
    </div>

    <template v-if="!loading">
      <!-- 空状态 -->
      <div v-if="runs.length === 0" class="empty-state">
        <p>暂无历史运行记录</p>
        <p class="sub">在参数调整页进行调参后，系统会自动保存运行结果</p>
      </div>

      <template v-else>
        <div class="info-row">
          共 <strong>{{ runs.length }}</strong> 条历史记录
        </div>

        <!-- 方案选择 -->
        <div class="select-row">
          <div class="select-group">
            <label>方案 A</label>
            <select v-model="selectedA" class="styled-select">
              <option v-for="(r, i) in runs" :key="r.id" :value="i">
                #{{ r.id }} — {{ r.note?.slice(0, 30) || '无备注' }} ({{ r.created_at }})
              </option>
            </select>
          </div>
          <div class="select-group">
            <label>方案 B</label>
            <select v-model="selectedB" class="styled-select">
              <option v-for="(r, i) in runs" :key="r.id" :value="i">
                #{{ r.id }} — {{ r.note?.slice(0, 30) || '无备注' }} ({{ r.created_at }})
              </option>
            </select>
          </div>
        </div>

        <div v-if="selectedA === selectedB" class="warn-banner">
          ⚠️ 请选择两个不同的方案进行对比
        </div>

        <template v-if="selectedA !== selectedB && dataA && dataB">
          <!-- KPI 卡片 -->
          <div class="kpi-grid">
            <div class="kpi-card">
              <div class="kpi-label">碳排放均值 (A)</div>
              <div class="kpi-value">{{ avgCarbonA }}</div>
              <div class="kpi-delta" :class="carbonDelta >= 0 ? 'up' : 'down'">
                {{ carbonDelta >= 0 ? '+' : '' }}{{ carbonDelta }}
              </div>
            </div>
            <div class="kpi-card">
              <div class="kpi-label">碳排放均值 (B)</div>
              <div class="kpi-value">{{ avgCarbonB }}</div>
            </div>
            <div class="kpi-card">
              <div class="kpi-label">火电调峰均值 (A)</div>
              <div class="kpi-value">{{ avgPeakA }}</div>
            </div>
            <div class="kpi-card">
              <div class="kpi-label">火电调峰均值 (B)</div>
              <div class="kpi-value">{{ avgPeakB }}</div>
            </div>
          </div>

          <!-- 逐日对比图 -->
          <div class="chart-section">
            <h3>逐日碳排放对比 (目标2: 碳成本)</h3>
            <div ref="dailyChart" class="chart-body"></div>
          </div>
        </template>
      </template>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { fetchHistoryList, fetchHistoryRun } from '../api'

const loading = ref(true)
const runs = ref([])
const selectedA = ref(0)
const selectedB = ref(1)
const dataA = ref(null)
const dataB = ref(null)
const dailyChart = ref(null)
let dailyInstance = null

const avgCarbonA = computed(() => dataA.value ? dataA.value.daily.map(r => r[2]).reduce((a, b) => a + b, 0) / 365 : '-')
const avgCarbonB = computed(() => dataB.value ? dataB.value.daily.map(r => r[2]).reduce((a, b) => a + b, 0) / 365 : '-')
const carbonDelta = computed(() => {
  if (!dataA.value || !dataB.value) return 0
  return (parseFloat(avgCarbonB.value) - parseFloat(avgCarbonA.value)).toFixed(2)
})
const avgPeakA = computed(() => dataA.value ? dataA.value.daily.map(r => r[1]).reduce((a, b) => a + b, 0) / 365 : '-')
const avgPeakB = computed(() => dataB.value ? dataB.value.daily.map(r => r[1]).reduce((a, b) => a + b, 0) / 365 : '-')

async function loadRunA() {
  const r = runs.value[selectedA.value]
  if (!r) return
  try {
    const d = await fetchHistoryRun(r.id)
    dataA.value = d
  } catch { dataA.value = null }
}

async function loadRunB() {
  const r = runs.value[selectedB.value]
  if (!r) return
  try {
    const d = await fetchHistoryRun(r.id)
    dataB.value = d
  } catch { dataB.value = null }
}

function initDailyChart() {
  if (!dailyChart.value || !dataA.value || !dataB.value) return
  if (dailyInstance) dailyInstance.dispose()
  dailyInstance = echarts.init(dailyChart.value)

  const days = Array.from({ length: 365 }, (_, i) => i + 1)
  const carbonA = dataA.value.daily.map(r => r[2])
  const carbonB = dataB.value.daily.map(r => r[2])

  dailyInstance.setOption({
    tooltip: { trigger: 'axis' },
    legend: {
      data: [`方案A (#${runs.value[selectedA.value]?.id})`, `方案B (#${runs.value[selectedB.value]?.id})`],
      textStyle: { color: '#8ba4c4' }, top: 10,
    },
    grid: { left: 70, right: 30, top: 60, bottom: 60 },
    xAxis: { type: 'category', name: 'Day', nameTextStyle: { color: '#8ba4c4' }, axisLabel: { show: false } },
    yAxis: { name: '碳成本', nameTextStyle: { color: '#8ba4c4' }, axisLabel: { color: '#8ba4c4' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } } },
    series: [
      { name: `方案A (#${runs.value[selectedA.value]?.id})`, type: 'line', data: carbonA, lineStyle: { color: '#00d4ff', width: 1 }, symbol: 'none', areaStyle: { color: 'rgba(0,212,255,0.05)' } },
      { name: `方案B (#${runs.value[selectedB.value]?.id})`, type: 'line', data: carbonB, lineStyle: { color: '#ff9800', width: 1 }, symbol: 'none', areaStyle: { color: 'rgba(255,152,0,0.05)' } },
    ],
  })
}

watch([selectedA, selectedB], async () => {
  await Promise.all([loadRunA(), loadRunB()])
  await nextTick()
  initDailyChart()
})

onMounted(async () => {
  try {
    const res = await fetchHistoryList()
    runs.value = res.runs || []
    if (runs.value.length >= 2) {
      selectedA.value = 0
      selectedB.value = 1
      await Promise.all([loadRunA(), loadRunB()])
    }
  } catch (e) {
    console.error('加载历史记录失败:', e)
  }
  loading.value = false
  await nextTick()
  initDailyChart()
})

onBeforeUnmount(() => { dailyInstance?.dispose() })
</script>

<style scoped>
.history-compare { animation: fadeIn 0.3s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

.page-header { margin-bottom: 24px; }
.page-header h2 { font-size: 1.5rem; color: var(--accent); margin-bottom: 8px; }
.page-desc { color: var(--text-secondary); font-size: 0.9rem; }

.loading-state { display: flex; flex-direction: column; align-items: center; padding: 80px 0; color: var(--text-secondary); }
.spinner { width: 40px; height: 40px; border: 3px solid rgba(0,212,255,0.2); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; margin-bottom: 16px; }
@keyframes spin { to { transform: rotate(360deg); } }

.empty-state { text-align: center; padding: 80px 0; color: var(--text-secondary); }
.empty-state .sub { font-size: 0.85rem; margin-top: 8px; opacity: 0.6; }

.info-row { margin-bottom: 16px; font-size: 0.95rem; color: var(--text-secondary); }
.info-row strong { color: var(--accent); }

.select-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }
.select-group { display: flex; flex-direction: column; gap: 6px; }
.select-group label { font-size: 0.85rem; color: var(--text-secondary); font-weight: 600; }
.styled-select {
  padding: 10px 14px; background: rgba(0,0,0,0.3); border: 1px solid var(--border-color);
  border-radius: 8px; color: var(--text-primary); font-size: 0.85rem;
}

.warn-banner { background: rgba(255,204,0,0.1); border: 1px solid rgba(255,204,0,0.3); border-radius: 8px; padding: 12px 16px; color: #ffcc00; font-size: 0.9rem; margin-bottom: 16px; }

.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
.kpi-card {
  background: linear-gradient(135deg, rgba(0,212,255,0.1), rgba(0,150,255,0.05));
  border: 1px solid var(--border-color); border-radius: 12px; padding: 20px; text-align: center;
}
.kpi-label { font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 8px; }
.kpi-value { font-size: 1.6rem; font-weight: 700; color: var(--text-primary); }
.kpi-delta { font-size: 0.85rem; margin-top: 4px; }
.down { color: #00ff88; }
.up { color: #ff6b6b; }

.chart-section { margin-top: 8px; }
.chart-section h3 { font-size: 1rem; color: var(--accent); margin-bottom: 12px; }
.chart-body { width: 100%; height: 350px; }
</style>
