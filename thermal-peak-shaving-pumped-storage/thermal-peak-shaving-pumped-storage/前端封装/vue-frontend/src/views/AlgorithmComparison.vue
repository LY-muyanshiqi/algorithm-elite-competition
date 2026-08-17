<template>
  <div class="algorithm-screen">
    <section class="control-band">
      <div class="control-title">
        <span>场景鲁棒优化实验</span>
        <small>全年代表场景 · 极端日 · CVaR · 跨日经验迁移</small>
      </div>
      <label>省份
        <select v-model="form.province" :disabled="running">
          <option value="shaanxi">陕西</option><option value="gansu">甘肃</option>
          <option value="qinghai">青海</option><option value="ningxia">宁夏</option>
        </select>
      </label>
      <label>种群<input v-model.number="form.population" type="number" min="8" max="100" :disabled="running"></label>
      <label>代数<input v-model.number="form.generations" type="number" min="1" max="500" :disabled="running"></label>
      <label>场景<input v-model.number="form.scenario_count" type="number" min="2" max="16" :disabled="running"></label>
      <label>β<input v-model.number="form.beta" type="number" min="0" max="2" step="0.1" :disabled="running"></label>
      <button class="run-button" :disabled="running" @click="runOptimization">
        {{ running ? '计算中' : '运行四组对比' }}
      </button>
    </section>

    <section v-if="task && running" class="progress-band">
      <div><strong>{{ task.stage }}</strong><span>{{ task.progress }}%</span></div>
      <div class="progress-track"><i :style="{ width: `${task.progress}%` }"></i></div>
    </section>
    <section v-if="error" class="error-band">{{ error }}</section>

    <template v-if="result">
      <section class="summary-line">
        <span>{{ result.province_name }} · {{ result.capacity_mw }} MW</span>
        <span>代表日 {{ result.scenario_days.join('、') }}</span>
        <span>CVaR α={{ result.risk.alpha }} / β={{ result.risk.beta }}</span>
        <span>耗时 {{ result.runtime_seconds }} s</span>
      </section>

      <section class="kpi-grid">
        <article v-for="item in result.variants" :key="item.key" :class="['kpi-card', item.key]">
          <header><span>{{ item.label }}</span><b>{{ item.solutions }} 解</b></header>
          <div class="metric"><strong>{{ format(item.f1_best) }}</strong><small>最小调峰容量</small></div>
          <div class="metric"><strong>{{ format(item.f2_best) }}</strong><small>最小碳排放</small></div>
          <footer>HV {{ compact(item.hv) }} · IGD {{ item.igd.toFixed(4) }}</footer>
        </article>
      </section>

      <section class="visual-grid">
        <div class="panel wide"><h3>真实 Pareto 前沿</h3><div ref="paretoEl" class="chart"></div></div>
        <div class="panel"><h3>统一评价指标</h3><div ref="metricEl" class="chart"></div></div>
        <div class="panel"><h3>调度质量</h3><div ref="qualityEl" class="chart"></div></div>
      </section>

      <section class="scenario-panel">
        <h3>代表场景构成</h3>
        <div class="scenario-list">
          <span v-for="(day, index) in result.scenario_days" :key="day">
            D{{ day }} · {{ labelName(result.scenario_labels[index]) }}
          </span>
        </div>
      </section>
    </template>

    <section v-else-if="!running" class="empty-panel">
      设置实验参数并运行，系统将比较原始 NSLDE、场景鲁棒、经验热启动和组合算法。
    </section>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { fetchLatestRobustOptimization, fetchRobustOptimization, startRobustOptimization } from '../api'

const form = ref({ province: 'shaanxi', population: 24, generations: 20, scenario_count: 6, extreme_count: 2, beta: 0.3, alpha: 0.9, seed: 42 })
const task = ref(null)
const result = ref(null)
const running = ref(false)
const error = ref('')
const paretoEl = ref(null)
const metricEl = ref(null)
const qualityEl = ref(null)
let timer = null
let charts = []

const colors = ['#43e7c5', '#48a8ff', '#ffc857', '#ff6b8a']
const format = value => Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 1 })
const compact = value => Number(value).toExponential(2)
const labelName = value => value === 'extreme_residual_load' ? '极端剩余负荷' : value.replace('cluster_', '典型簇 ')

async function runOptimization() {
  error.value = ''; result.value = null; running.value = true
  try {
    task.value = await startRobustOptimization(form.value)
    poll(task.value.task_id)
  } catch (e) {
    running.value = false
    error.value = e.response?.data?.detail || e.message
  }
}

function poll(taskId) {
  clearInterval(timer)
  const refresh = async () => {
    try {
      task.value = await fetchRobustOptimization(taskId)
      if (task.value.status === 'completed') {
        clearInterval(timer); running.value = false; result.value = task.value.result
        await nextTick(); renderCharts()
      } else if (task.value.status === 'failed') {
        clearInterval(timer); running.value = false; error.value = task.value.error || '优化失败'
      }
    } catch (e) { clearInterval(timer); running.value = false; error.value = e.message }
  }
  refresh(); timer = window.setInterval(refresh, 1000)
}

function chart(dom, option) {
  const instance = echarts.init(dom); instance.setOption(option); charts.push(instance)
}

function renderCharts() {
  charts.forEach(item => item.dispose()); charts = []
  const variants = result.value.variants
  const base = { textStyle: { color: '#9ab6c7' }, backgroundColor: 'transparent' }
  chart(paretoEl.value, { ...base, tooltip: { trigger: 'item' }, legend: { data: variants.map(v => v.label), textStyle: { color: '#9ab6c7' } }, grid: { left: 70, right: 25, top: 50, bottom: 55 }, xAxis: { name: '调峰容量', splitLine: { lineStyle: { color: '#123344' } } }, yAxis: { name: '碳排放', splitLine: { lineStyle: { color: '#123344' } } }, series: variants.map((v, i) => ({ name: v.label, type: 'scatter', data: v.pareto, symbolSize: 7, itemStyle: { color: colors[i] } })) })
  chart(metricEl.value, { ...base, tooltip: { trigger: 'axis' }, legend: { data: ['IGD', 'Spacing'], textStyle: { color: '#9ab6c7' } }, grid: { left: 55, right: 20, top: 48, bottom: 60 }, xAxis: { type: 'category', data: variants.map(v => v.label), axisLabel: { rotate: 18 } }, yAxis: { splitLine: { lineStyle: { color: '#123344' } } }, series: [{ name: 'IGD', type: 'bar', data: variants.map(v => v.igd), itemStyle: { color: '#48a8ff' } }, { name: 'Spacing', type: 'line', data: variants.map(v => v.spacing), itemStyle: { color: '#ffc857' } }] })
  chart(qualityEl.value, { ...base, tooltip: { trigger: 'axis' }, legend: { data: ['启停', '切换', '短时运行'], textStyle: { color: '#9ab6c7' } }, grid: { left: 45, right: 20, top: 48, bottom: 60 }, xAxis: { type: 'category', data: variants.map(v => v.label), axisLabel: { rotate: 18 } }, yAxis: { splitLine: { lineStyle: { color: '#123344' } } }, series: ['starts', 'mode_switches', 'short_runs'].map((key, i) => ({ name: ['启停', '切换', '短时运行'][i], type: 'bar', data: variants.map(v => v.dispatch_quality[key]), itemStyle: { color: colors[i] } })) })
}

function resize() { charts.forEach(item => item.resize()) }
onMounted(async () => {
  window.addEventListener('resize', resize)
  try {
    const latest = await fetchLatestRobustOptimization()
    if (latest.status === 'completed') { task.value = latest; result.value = latest.result; await nextTick(); renderCharts() }
    else if (['queued', 'running'].includes(latest.status)) { task.value = latest; running.value = true; poll(latest.task_id) }
  } catch { /* No previous task. */ }
})
onBeforeUnmount(() => { clearInterval(timer); charts.forEach(item => item.dispose()); window.removeEventListener('resize', resize) })
</script>

<style scoped>
.algorithm-screen{min-height:100vh;padding:12px;color:#d9eef4;background:#020d15;letter-spacing:0}.control-band{display:grid;grid-template-columns:minmax(230px,1fr) repeat(5,minmax(72px,110px)) 150px;gap:10px;align-items:end;padding:14px;border:1px solid #175064;background:#061923}.control-title{display:flex;flex-direction:column;gap:4px;color:#43e7c5;font-size:17px}.control-title small{color:#7897a6;font-size:11px}.control-band label{display:flex;flex-direction:column;gap:5px;color:#7fa4b4;font-size:11px}.control-band input,.control-band select{height:34px;padding:0 8px;color:#d9eef4;border:1px solid #1d5366;background:#04131c}.run-button{height:36px;color:#032019;border:1px solid #62f5d4;background:#43e7c5;font-weight:700;cursor:pointer}.run-button:disabled{opacity:.45;cursor:wait}.progress-band,.error-band,.summary-line{margin-top:10px;padding:11px 14px;border:1px solid #174659;background:#061923}.progress-band>div:first-child{display:flex;justify-content:space-between}.progress-track{height:4px;margin-top:8px;background:#0b2b38}.progress-track i{display:block;height:100%;background:#43e7c5;transition:width .3s}.error-band{color:#ff9dac;border-color:#713245}.summary-line{display:flex;flex-wrap:wrap;gap:22px;color:#99bac8;font-size:12px}.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:10px}.kpi-card{padding:14px;border:1px solid #195064;background:#061923}.kpi-card header{display:flex;justify-content:space-between;color:#43e7c5}.kpi-card header b{color:#718f9b;font-size:10px}.metric{display:inline-flex;width:50%;flex-direction:column;margin-top:17px}.metric strong{font-size:20px}.metric small{margin-top:4px;color:#708f9d;font-size:10px}.kpi-card footer{margin-top:13px;color:#7d9dab;font-size:10px}.visual-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}.panel,.scenario-panel{border:1px solid #175064;background:#051720}.panel.wide{grid-column:1/-1}.panel h3,.scenario-panel h3{margin:0;padding:10px 13px;color:#9cc3d1;border-bottom:1px solid #123b4b;font-size:12px}.chart{height:340px}.scenario-panel{margin-top:10px}.scenario-list{display:flex;flex-wrap:wrap;gap:8px;padding:12px}.scenario-list span{padding:6px 9px;color:#9fc5d2;border:1px solid #1b4c5d;background:#08212c;font-size:11px}.empty-panel{margin-top:10px;padding:80px;text-align:center;color:#6f919f;border:1px dashed #1c4d5f}.error-band{color:#ff9aaa}@media(max-width:1100px){.control-band{grid-template-columns:repeat(3,1fr)}.control-title{grid-column:1/-1}.kpi-grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:700px){.control-band,.kpi-grid,.visual-grid{grid-template-columns:1fr}.panel.wide{grid-column:auto}.summary-line{flex-direction:column;gap:7px}}
</style>
