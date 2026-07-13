<template>
  <div class="seasonal">
    <div class="page-header">
      <h2>🍃 四季对比分析</h2>
      <p class="page-desc">Spring / Summer / Autumn / Winter 各季节的新能源消纳、碳减排和调度指标对比</p>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>计算四季数据...</p>
    </div>

    <template v-if="!loading && seasonalData">
      <!-- KPI 表格 -->
      <div class="table-wrap">
        <table class="season-table">
          <thead>
            <tr>
              <th>季节</th>
              <th>新能源消纳率 (%)</th>
              <th>碳减排量 (万吨)</th>
              <th>抽水小时</th>
              <th>发电小时</th>
              <th>总负荷 (亿kWh)</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in seasonalData.rows" :key="row.season">
              <td>
                <span class="season-badge" :style="{ color: row.color }">{{ row.icon }} {{ row.season }}</span>
              </td>
              <td>{{ row.renewable_ratio.toFixed(1) }}%</td>
              <td>{{ row.carbon_reduction.toFixed(2) }}</td>
              <td>{{ row.pump_hours }}</td>
              <td>{{ row.gen_hours }}</td>
              <td>{{ row.total_load.toFixed(2) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 图表 -->
      <div class="chart-section">
        <h3>四季新能源消纳率对比</h3>
        <div ref="renewableChart" class="chart-body"></div>
      </div>

      <div class="chart-section">
        <h3>四季碳减排量对比</h3>
        <div ref="carbonChart" class="chart-body"></div>
      </div>

      <div class="chart-section">
        <h3>四季抽蓄调度统计</h3>
        <div ref="pumpChart" class="chart-body"></div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { fetchAllData } from '../api'

const loading = ref(true)
const seasonalData = ref(null)
const renewableChart = ref(null)
const carbonChart = ref(null)
const pumpChart = ref(null)
let rInstance = null, cInstance = null, pInstance = null

function computeSeasonal(data) {
  const z = data.z_gain || []
  const fh = data.fh || []
  const wind = data.wind || []
  const solar = data.solar || []
  const hydro = data.hydro || []
  const np = data.np_raw || []
  const Nt = data.Nt || []
  const Nt2 = data.Nt2 || []

  const seasons = [
    { name: 'Spring', icon: '🌸', color: '#00ff88', range: [0, 90] },
    { name: 'Summer', icon: '☀️', color: '#00d4ff', range: [90, 181] },
    { name: 'Autumn', icon: '🍂', color: '#ff9800', range: [181, 273] },
    { name: 'Winter', icon: '❄️', color: '#ff6b6b', range: [273, 365] },
  ]

  const rows = seasons.map(s => {
    const [start, end] = s.range
    const slice = (arr) => arr.slice(start, end)

    const windSum = slice(wind).flat().reduce((a, b) => a + b, 0)
    const solarSum = slice(solar).flat().reduce((a, b) => a + b, 0)
    const hydroSum = slice(hydro).flat().reduce((a, b) => a + b, 0)
    const fhSum = slice(fh).flat().reduce((a, b) => a + b, 0)
    const renewableRatio = (windSum + solarSum + hydroSum) / (fhSum + windSum + solarSum + hydroSum) * 100

    const carbonReduction = slice(Nt).flat().reduce((a, b, i) => a + Math.abs(b - slice(Nt2).flat()[i] || 0), 0) / 1e4

    const pumpHours = slice(np).flat().filter(v => v < 0).length
    const genHours = slice(np).flat().filter(v => v > 0).length
    const totalLoad = fhSum / 1e4

    return { ...s, renewable_ratio: renewableRatio, carbon_reduction: carbonReduction, pump_hours: pumpHours, gen_hours: genHours, total_load: totalLoad }
  })

  return { rows }
}

function initCharts() {
  if (!seasonalData.value) return

  const rows = seasonalData.value.rows
  const names = rows.map(r => r.season)
  const colors = rows.map(r => r.color)

  // Renewable chart
  if (renewableChart.value) {
    if (rInstance) rInstance.dispose()
    rInstance = echarts.init(renewableChart.value)
    rInstance.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 70, right: 40, top: 30, bottom: 50 },
      xAxis: { type: 'category', data: names, axisLabel: { color: '#8ba4c4' } },
      yAxis: { name: '%', axisLabel: { color: '#8ba4c4' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } } },
      series: [{
        type: 'bar', data: rows.map(r => +r.renewable_ratio.toFixed(1)),
        itemStyle: { color: (p) => colors[p.dataIndex] },
        label: { show: true, position: 'top', color: '#e0e6ed', formatter: '{c}%' },
      }],
    })
  }

  // Carbon chart
  if (carbonChart.value) {
    if (cInstance) cInstance.dispose()
    cInstance = echarts.init(carbonChart.value)
    cInstance.setOption({
      tooltip: { trigger: 'axis' },
      grid: { left: 80, right: 40, top: 30, bottom: 50 },
      xAxis: { type: 'category', data: names, axisLabel: { color: '#8ba4c4' } },
      yAxis: { name: '万吨', axisLabel: { color: '#8ba4c4' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } } },
      series: [{
        type: 'bar', data: rows.map(r => +r.carbon_reduction.toFixed(2)),
        itemStyle: { color: (p) => colors[p.dataIndex] },
        label: { show: true, position: 'top', color: '#e0e6ed' },
      }],
    })
  }

  // Pump schedule chart
  if (pumpChart.value) {
    if (pInstance) pInstance.dispose()
    pInstance = echarts.init(pumpChart.value)
    pInstance.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['抽水小时', '发电小时'], textStyle: { color: '#8ba4c4' }, top: 10 },
      grid: { left: 70, right: 40, top: 60, bottom: 50 },
      xAxis: { type: 'category', data: names, axisLabel: { color: '#8ba4c4' } },
      yAxis: { axisLabel: { color: '#8ba4c4' }, splitLine: { lineStyle: { color: 'rgba(255,255,255,0.05)' } } },
      series: [
        { name: '抽水小时', type: 'bar', data: rows.map(r => r.pump_hours), itemStyle: { color: '#00d4ff' }, barGap: '10%' },
        { name: '发电小时', type: 'bar', data: rows.map(r => r.gen_hours), itemStyle: { color: '#ffcc00' }, barGap: '10%' },
      ],
    })
  }
}

onMounted(async () => {
  try {
    const data = await fetchAllData()
    seasonalData.value = computeSeasonal(data)
  } catch (e) {
    console.error('加载失败:', e)
  }
  loading.value = false
  await nextTick()
  initCharts()
})

onBeforeUnmount(() => {
  rInstance?.dispose(); cInstance?.dispose(); pInstance?.dispose()
})
</script>

<style scoped>
.seasonal { animation: fadeIn 0.3s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

.page-header { margin-bottom: 24px; }
.page-header h2 { font-size: 1.5rem; color: var(--accent); margin-bottom: 8px; }
.page-desc { color: var(--text-secondary); font-size: 0.9rem; }

.loading-state { display: flex; flex-direction: column; align-items: center; padding: 80px 0; color: var(--text-secondary); }
.spinner { width: 40px; height: 40px; border: 3px solid rgba(0,212,255,0.2); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; margin-bottom: 16px; }
@keyframes spin { to { transform: rotate(360deg); } }

.table-wrap { overflow-x: auto; margin-bottom: 24px; }
.season-table { width: 100%; border-collapse: collapse; }
.season-table th, .season-table td { padding: 12px 16px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.05); }
.season-table th { color: var(--text-secondary); font-size: 0.85rem; background: rgba(0,212,255,0.05); }
.season-table td { font-size: 0.9rem; }
.season-badge { font-weight: 600; }
.season-table tr:hover td { background: rgba(0,212,255,0.03); }

.chart-section { margin-bottom: 24px; }
.chart-section h3 { font-size: 1rem; color: var(--accent); margin-bottom: 12px; }
.chart-body { width: 100%; height: 350px; }
</style>
