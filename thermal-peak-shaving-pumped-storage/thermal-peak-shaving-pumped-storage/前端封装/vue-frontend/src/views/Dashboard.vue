<template>
  <div class="dashboard-screen">
    <LoadingOverlay v-if="loading" />
    <ScreenHeader title="零碳虚拟电厂智能调度系统" subtitle="广东区域 · 新能源消纳与抽水蓄能协同优化" :status="usingDemoData ? 'warning' : 'online'" :status-label="usingDemoData ? '演示数据模式' : '实时调度在线'" />

    <div v-if="errorMessage" class="data-warning">{{ errorMessage }}<button type="button" @click="loadDashboard">重新连接</button></div>

    <section class="dashboard-grid">
      <div class="left-column">
        <TechPanel title="实时碳排放" english="REAL-TIME CARBON">
          <div class="carbon-gauge"><div ref="carbonGaugeRef" class="chart chart--gauge"></div><dl><div><dt>当前减排</dt><dd>{{ metrics.carbonReduction }} 万吨</dd></div><div><dt>剩余碳配额</dt><dd>{{ metrics.carbonQuota }} tCO₂</dd></div></dl></div>
        </TechPanel>
        <TechPanel title="碳排放趋势" english="CARBON TREND"><div ref="carbonTrendRef" class="chart"></div></TechPanel>
        <TechPanel title="减排贡献" english="CARBON REDUCTION"><div ref="contributionRef" class="chart"></div></TechPanel>
      </div>

      <div class="center-column">
        <TechPanel body-class="map-panel">
          <div class="map-caption"><span>广东省能源协同网络</span><small>ENERGY COORDINATION NETWORK</small></div>
          <MapFlow :intensity="flowIntensity" />
          <div class="map-legend"><span><i class="legend-dot"></i>抽蓄电站</span><span><i class="legend-dot legend-dot--cyan"></i>负荷中心</span><span><i class="legend-line"></i>实时能量流</span></div>
        </TechPanel>
        <div class="kpi-strip">
          <KpiCard label="今日碳减排" :value="metrics.todayCarbon" unit="tCO₂" trend="↓ 3.2%" />
          <KpiCard label="绿电消纳率" :value="metrics.renewableRate" unit="%" trend="↑ 1.8%" tone="cyan" />
          <KpiCard label="虚拟电厂收益" :value="metrics.revenue" unit="万元" trend="↑ 5.6%" />
          <KpiCard label="剩余碳配额" :value="metrics.carbonQuota" unit="tCO₂" trend="↓ 12.4%" tone="warning" />
          <KpiCard label="抽发综合效率" :value="metrics.efficiency" unit="%" tone="cyan" />
        </div>
      </div>

      <div class="right-column">
        <TechPanel title="实时电力负荷" english="REAL-TIME LOAD"><div ref="loadBarRef" class="chart"></div></TechPanel>
        <TechPanel title="负荷预测曲线" english="LOAD FORECAST"><div ref="forecastRef" class="chart"></div></TechPanel>
        <TechPanel title="分时电价调度建议" english="TOU PRICING">
          <div class="dispatch-table-wrap"><table class="dispatch-table"><thead><tr><th>时段</th><th>时间范围</th><th>电价</th><th>调度建议</th></tr></thead><tbody><tr v-for="item in dispatchAdvice" :key="item.period"><td>{{ item.period }}</td><td>{{ item.time }}</td><td>{{ item.price }}</td><td>{{ item.action }}</td></tr></tbody></table></div>
        </TechPanel>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import * as echarts from 'echarts'
import { fetchDashboard } from '../api'
import KpiCard from '../components/KpiCard.vue'
import LoadingOverlay from '../components/LoadingOverlay.vue'
import MapFlow from '../components/MapFlow.vue'
import ScreenHeader from '../components/ScreenHeader.vue'
import TechPanel from '../components/TechPanel.vue'

const loading = ref(true)
const usingDemoData = ref(false)
const errorMessage = ref('')
const dashboardData = ref(null)
const carbonGaugeRef = ref(null)
const carbonTrendRef = ref(null)
const contributionRef = ref(null)
const loadBarRef = ref(null)
const forecastRef = ref(null)
const chartInstances = []
let resizeObserver

const demoData = {
  total_wind: 1860, total_solar: 1240, total_hydro: 890, total_fh: 2840,
  Nt_first30: Array.from({ length: 168 }, (_, i) => 510 + Math.sin(i / 10) * 82 + Math.sin(i / 3) * 15),
  daily_carbon: Array.from({ length: 30 }, (_, i) => 1320 - i * 4 + Math.sin(i / 2) * 22),
  carbon_result: { carbon_change: 119.5 },
  ps_stats: { efficiency: 82.5, generating_hours: 2410, pumping_hours: 2120 },
}

const metrics = reactive({ carbonReduction: '119.50', carbonQuota: '2,340', todayCarbon: '1,195', renewableRate: '82.5', revenue: '157', efficiency: '82.5' })
const flowIntensity = computed(() => Math.max(0.7, Number(metrics.renewableRate) / 80))
const dispatchAdvice = [
  { period: '尖峰', time: '11:00–15:00', price: '1.28', action: '储能放电 · 削峰增效' },
  { period: '高峰', time: '08:00–11:00', price: '0.96', action: '优先放电 · 负荷跟踪' },
  { period: '平段', time: '06:00–08:00', price: '0.58', action: '维持水位 · 灵活响应' },
  { period: '低谷', time: '22:00–06:00', price: '0.28', action: '抽水蓄能 · 消纳绿电' },
]
const chartBase = { textStyle: { color: '#779aa0', fontFamily: 'Microsoft YaHei' }, tooltip: { trigger: 'axis', className: 'chart-tooltip' }, grid: { left: 42, right: 12, top: 26, bottom: 30 } }

function createChart(element, option) {
  if (!element) return
  const instance = echarts.init(element)
  instance.setOption(option)
  chartInstances.push(instance)
}

function categoryAxis(data = []) { return { type: 'category', data, axisLine: { lineStyle: { color: '#16454b' } }, axisLabel: { color: '#6f9298', fontSize: 9 } } }
function valueAxis() { return { type: 'value', axisLine: { show: false }, splitLine: { lineStyle: { color: 'rgba(78,150,151,.13)' } }, axisLabel: { color: '#6f9298', fontSize: 9 } } }

function renderCharts() {
  chartInstances.splice(0).forEach((chart) => chart.dispose())
  const data = dashboardData.value
  const trend = (data.daily_carbon || demoData.daily_carbon).slice(-7)
  const thermal = (data.Nt_first30 || demoData.Nt_first30).slice(0, 24)
  const mixTotal = data.total_wind + data.total_solar + data.total_hydro + data.total_fh
  const renewable = data.total_wind + data.total_solar + data.total_hydro
  metrics.renewableRate = ((renewable / Math.max(1, mixTotal)) * 100).toFixed(1)

  createChart(carbonGaugeRef.value, { series: [{ type: 'gauge', startAngle: 90, endAngle: -270, radius: '88%', progress: { show: true, roundCap: true, width: 16, itemStyle: { color: '#14f1be' } }, axisLine: { lineStyle: { width: 16, color: [[1, 'rgba(20,241,190,.1)']] } }, pointer: { show: false }, axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false }, detail: { formatter: '{value}%', color: '#e8fff9', fontSize: 24, offsetCenter: [0, '2%'] }, title: { offsetCenter: [0, '28%'], color: '#779aa0', fontSize: 9 }, data: [{ value: Number(metrics.renewableRate), name: '绿电消纳率' }] }] })
  createChart(carbonTrendRef.value, { ...chartBase, xAxis: categoryAxis(['07-29','07-30','07-31','08-01','08-02','08-03','08-04']), yAxis: valueAxis(), series: [{ type: 'line', smooth: true, symbolSize: 5, data: trend, lineStyle: { color: '#14f1be', width: 2 }, itemStyle: { color: '#54ffd4' }, areaStyle: { color: new echarts.graphic.LinearGradient(0,0,0,1,[{ offset:0,color:'rgba(20,241,190,.28)'},{ offset:1,color:'rgba(20,241,190,0)' }]) } }] })
  createChart(contributionRef.value, { ...chartBase, grid: { left: 64, right: 24, top: 10, bottom: 20 }, xAxis: valueAxis(), yAxis: { ...categoryAxis(['光伏消纳','储能削峰','负荷优化']), axisLine: { show: false }, axisLabel: { color: '#d5ebe7', fontSize: 10 } }, series: [{ type: 'bar', data: [data.total_solar, data.ps_stats?.pumping_hours || 1240, Math.round(renewable / 4)], barWidth: 12, itemStyle: { color: '#14f1be', borderRadius: [0,5,5,0] }, label: { show: true, position: 'right', color: '#d8fdf4', fontSize: 9 } }] })
  createChart(loadBarRef.value, { ...chartBase, grid: { left: 52, right: 35, top: 10, bottom: 20 }, xAxis: valueAxis(), yAxis: { ...categoryAxis(['A公司','B公司','C公司']), axisLine: { show: false }, axisLabel: { color: '#d5ebe7', fontSize: 10 } }, series: [{ type: 'bar', data: [284,196,147], barWidth: 13, itemStyle: { color: new echarts.graphic.LinearGradient(0,0,1,0,[{ offset:0,color:'#09cfa2'},{ offset:1,color:'#54ffd4'}]), borderRadius: [0,2,2,0] }, label: { show: true, position: 'right', formatter: '{c} MW', color: '#d8fdf4', fontSize: 9 } }] })
  createChart(forecastRef.value, { ...chartBase, xAxis: categoryAxis(Array.from({length:24},(_,i)=>String(i).padStart(2,'0'))), yAxis: valueAxis(), series: [{ type: 'line', smooth: true, symbol: 'none', data: thermal, lineStyle: { color: '#14f1be', width: 2 }, areaStyle: { color: new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(20,241,190,.24)'},{offset:1,color:'rgba(20,241,190,0)'}]) } }] })
}

function applyMetrics(data) {
  const carbon = Math.abs(Number(data.carbon_result?.carbon_change || 119.5))
  metrics.carbonReduction = carbon.toFixed(2)
  metrics.todayCarbon = Math.round(carbon * 10).toLocaleString('zh-CN')
  metrics.efficiency = Number(data.ps_stats?.efficiency || 82.5).toFixed(1)
  metrics.revenue = Math.round(carbon * 1.31).toLocaleString('zh-CN')
}

async function loadDashboard() {
  loading.value = true
  errorMessage.value = ''
  try {
    dashboardData.value = await fetchDashboard()
    usingDemoData.value = false
  } catch (error) {
    dashboardData.value = demoData
    usingDemoData.value = true
    errorMessage.value = '实时接口暂不可用，当前使用内置演示数据。'
    console.warn('Dashboard API unavailable, using demo data.', error)
  }
  applyMetrics(dashboardData.value)
  loading.value = false
  await nextTick()
  renderCharts()
}

onMounted(async () => {
  await loadDashboard()
  resizeObserver = new ResizeObserver(() => chartInstances.forEach((chart) => chart.resize()))
  resizeObserver.observe(document.querySelector('.dashboard-grid'))
})
onBeforeUnmount(() => { resizeObserver?.disconnect(); chartInstances.forEach((chart) => chart.dispose()) })
</script>

<style scoped>
.dashboard-screen { position: relative; min-height: calc(100vh - 62px); padding: 10px; background: linear-gradient(rgba(2,12,18,.3),rgba(2,12,18,.86)),repeating-linear-gradient(0deg,rgba(20,241,190,.018) 0 1px,transparent 1px 28px); }
.data-warning { display:flex; justify-content:center; gap:12px; padding:6px; color:var(--color-warning); font-size:11px; background:rgba(255,170,44,.08); }
.data-warning button { color:inherit; border:0; border-bottom:1px solid currentColor; background:transparent; cursor:pointer; }
.dashboard-grid { height:clamp(760px,calc(100vh - 164px),1000px); display:grid; grid-template-columns:minmax(220px,22%) minmax(480px,1fr) minmax(240px,23%); gap:9px; margin-top:9px; }
.left-column,.right-column,.center-column { min-width:0; min-height:0; display:grid; gap:9px; }
.left-column { grid-template-rows:1.02fr .98fr .9fr; }.right-column { grid-template-rows:.9fr 1.05fr 1.05fr; }.center-column { grid-template-rows:minmax(0,1fr) auto; }
.chart { width:100%; height:100%; min-height:155px; }.chart--gauge { min-height:145px; }
.carbon-gauge { height:100%; display:grid; grid-template-columns:58% 42%; align-items:center; }.carbon-gauge dl { margin:0; padding-left:8px; border-left:1px solid var(--color-border); }.carbon-gauge dl div+div { margin-top:18px; }.carbon-gauge dt { color:var(--color-muted); font-size:9px; }.carbon-gauge dd { margin:4px 0 0; color:var(--color-accent); font:700 12px monospace; }
:deep(.map-panel) { position:relative; height:100%; padding:0; }.map-caption { position:absolute; z-index:5; top:16px; left:18px; display:grid; gap:3px; }.map-caption span { font-size:13px; font-weight:700; letter-spacing:.1em; }.map-caption small { color:var(--color-muted); font-size:8px; letter-spacing:.12em; }
.map-legend { position:absolute; z-index:5; bottom:14px; left:18px; display:flex; gap:15px; padding:7px 10px; color:var(--color-muted); background:rgba(2,13,20,.72); font-size:9px; }.map-legend span { display:flex; align-items:center; gap:5px; }.legend-dot { width:6px; height:6px; border-radius:50%; background:var(--color-accent); box-shadow:0 0 8px currentColor; }.legend-dot--cyan { color:var(--color-cyan); background:currentColor; }.legend-line { width:14px; height:1px; background:var(--color-cyan); }
.kpi-strip { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:7px; }.dispatch-table-wrap { height:100%; overflow:auto; }.dispatch-table { width:100%; border-collapse:collapse; table-layout:fixed; font-size:9px; }.dispatch-table th,.dispatch-table td { padding:8px 5px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; text-align:left; border-bottom:1px solid rgba(119,154,160,.16); }.dispatch-table th { color:var(--color-muted); background:rgba(119,154,160,.08); }.dispatch-table td:first-child { color:var(--color-accent); font-weight:700; }.dispatch-table th:nth-child(1){width:15%}.dispatch-table th:nth-child(2){width:25%}.dispatch-table th:nth-child(3){width:14%}
@media(max-width:1100px){.dashboard-grid{height:auto;grid-template-columns:1fr 1fr}.center-column{grid-column:1/-1;grid-row:1;min-height:620px}.left-column,.right-column{min-height:720px}}
@media(max-width:720px){.dashboard-screen{padding:6px}.dashboard-grid{grid-template-columns:1fr}.center-column,.left-column,.right-column{grid-column:1;min-height:720px}.kpi-strip{grid-template-columns:repeat(2,minmax(0,1fr))}}
</style>
