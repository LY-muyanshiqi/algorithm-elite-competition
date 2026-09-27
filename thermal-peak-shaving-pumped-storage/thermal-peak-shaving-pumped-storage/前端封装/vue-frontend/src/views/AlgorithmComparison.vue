<template>
  <div class="algorithm-screen">
    <section class="control-band">
      <div class="control-title">
        <span>场景鲁棒优化实验</span>
        <small>全年代表场景 · 极端日 · CVaR · RLDE-F 个体自适应</small>
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
      <label>极端<input v-model.number="form.extreme_count" type="number" min="1" max="6" :disabled="running"></label>
      <label>α<input v-model.number="form.alpha" type="number" min="0.5" max="0.99" step="0.01" :disabled="running"></label>
      <label>β<input v-model.number="form.beta" type="number" min="0" max="2" step="0.1" :disabled="running"></label>
      <label>F步长<input v-model.number="form.f_delta" type="number" min="0.01" max="0.5" step="0.01" :disabled="running"></label>
      <label>温度<input v-model.number="form.rl_temperature" type="number" min="0.1" max="10" step="0.1" :disabled="running"></label>
      <label>RL率<input v-model.number="form.rl_alpha" type="number" min="0.001" max="1" step="0.01" :disabled="running"></label>
      <label>折扣<input v-model.number="form.rl_gamma" type="number" min="0" max="1" step="0.01" :disabled="running"></label>
      <button class="run-button" :disabled="running" @click="runOptimization">
        {{ running ? '计算中' : '运行四组对比' }}
      </button>
    </section>

    <section v-if="task && running" class="progress-band">
      <div><strong>{{ task.stage || '计算中' }}</strong><span>{{ progressPercent(task.progress) }}%</span></div>
      <div class="progress-track"><i :style="{ width: `${progressPercent(task.progress)}%` }"></i></div>
    </section>
    <section v-if="error" class="error-band">{{ error }}</section>

    <template v-if="result">
      <section class="summary-line">
        <span>{{ result.province_name }} · {{ result.capacity_mw }} MW</span>
        <span>{{ result.algorithm_version }}</span>
        <span>代表日 {{ result.scenario_days.length ? result.scenario_days.join('、') : '暂无' }}</span>
        <span>CVaR α={{ result.risk.alpha }} / β={{ result.risk.beta }}</span>
        <span>耗时 {{ format(result.runtime_seconds) }} s</span>
      </section>
      <section v-if="result.objective_definition" class="objective-note">
        {{ result.objective_definition }}
      </section>

      <template v-if="result.variants.length">
        <section class="kpi-grid">
          <article v-for="item in result.variants" :key="item.key" :class="['kpi-card', item.key]">
            <header><span>{{ item.label }}</span><b>{{ item.solutions }} 解</b></header>
            <div class="metric"><strong>{{ format(item.f1_best) }}</strong><small>鲁棒目标 f1（调峰）</small></div>
            <div class="metric"><strong>{{ format(item.f2_best) }}</strong><small>鲁棒目标 f2（碳排）</small></div>
            <footer>HV {{ compact(item.hv) }} · IGD {{ fixed(item.igd, 4) }}<br>
              <template v-if="item.rl">
                F̄ {{ fixed(item.rl.f_mean, 3) }} · Q更新 {{ item.rl.updates }}
                <span v-if="item.rl.action_counts.length"> · Δ/保持/增 {{ item.rl.action_counts.join('/') }}</span>
              </template>
              <template v-else>固定 F / 无 RLDE</template>
              <br>NFE {{ item.nfe }} · 启停 {{ fixed(item.dispatch_quality.starts, 1) }}
            </footer>
          </article>
        </section>

        <section class="visual-grid">
          <div class="panel wide"><h3>真实 Pareto 前沿</h3><div ref="paretoEl" class="chart"></div></div>
          <div class="panel"><h3>统一评价指标</h3><div ref="metricEl" class="chart"></div></div>
          <div class="panel"><h3>期望 / CVaR 风险目标</h3><div ref="riskEl" class="chart"></div></div>
          <div class="panel"><h3>调度质量</h3><div ref="qualityEl" class="chart"></div></div>
        </section>
      </template>
      <section v-else class="empty-panel">
        后端任务已完成，但没有返回可比较的有限 Pareto 解。请检查输入数据或增大种群与迭代次数后重试。
      </section>

      <section class="scenario-panel">
        <h3>代表场景构成</h3>
        <div v-if="result.scenario_days.length" class="scenario-list">
          <span v-for="(day, index) in result.scenario_days" :key="day">
            D{{ day }} · {{ labelName(result.scenario_labels[index]) }}
          </span>
        </div>
        <div v-else class="scenario-list scenario-empty">暂无代表场景信息</div>
      </section>
    </template>

    <section v-else-if="!running" class="empty-panel">
      设置实验参数并运行，系统将比较固定 NSLDE、场景鲁棒 NSLDE、RLDE-F 场景鲁棒和 RLDE-F 热启动。
    </section>
  </div>
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { fetchLatestRobustOptimization, fetchRobustOptimization, startRobustOptimization } from '../api'

const form = ref({ province: 'shaanxi', population: 24, generations: 20, scenario_count: 6, extreme_count: 2, beta: 0.3, alpha: 0.9, seed: 42, rl_alpha: 0.1, rl_gamma: 0.9, rl_temperature: 1.0, f_delta: 0.1 })
const task = ref(null)
const result = ref(null)
const running = ref(false)
const error = ref('')
const paretoEl = ref(null)
const metricEl = ref(null)
const qualityEl = ref(null)
const riskEl = ref(null)
let timer = null
let charts = []

const colors = ['#43e7c5', '#48a8ff', '#ffc857', '#ff6b8a']
const finiteNumber = (value, fallback = 0) => {
  if (value === null || value === undefined || value === '') return fallback
  const number = Number(value)
  return Number.isFinite(number) ? number : fallback
}
const format = value => finiteNumber(value).toLocaleString('zh-CN', { maximumFractionDigits: 1 })
const fixed = (value, digits = 2) => finiteNumber(value).toFixed(digits)
const compact = value => finiteNumber(value).toExponential(2)
const progressPercent = value => Math.min(100, Math.max(0, finiteNumber(value)))
const labelName = value => {
  if (!value) return '未标注场景'
  const label = String(value)
  return label === 'extreme_residual_load' ? '极端剩余负荷' : label.replace('cluster_', '典型簇 ')
}

const objectiveArray = value => {
  const source = Array.isArray(value) ? value : []
  return [finiteNumber(source[0]), finiteNumber(source[1])]
}

const paretoPoints = value => {
  if (!Array.isArray(value)) return []
  return value.reduce((points, point) => {
    if (!Array.isArray(point)) return points
    const x = Number(point[0]); const y = Number(point[1])
    if (Number.isFinite(x) && Number.isFinite(y)) points.push([x, y])
    return points
  }, [])
}

function normalizeVariant(raw, index) {
  const source = raw && typeof raw === 'object' ? raw : {}
  const metrics = source.metrics && typeof source.metrics === 'object' ? source.metrics : {}
  const dispatch = source.dispatch_quality || source.dispatchQuality || {}
  const rlCandidate = source.rl ?? source.rl_summary
  const rlSource = rlCandidate && typeof rlCandidate === 'object' ? rlCandidate : null
  const rl = rlSource ? {
    f_mean: finiteNumber(rlSource.f_mean),
    f_min: finiteNumber(rlSource.f_min),
    f_max: finiteNumber(rlSource.f_max),
    updates: Math.max(0, Math.round(finiteNumber(rlSource.updates))),
    temperature: finiteNumber(rlSource.temperature),
    action_counts: Array.isArray(rlSource.action_counts)
      ? rlSource.action_counts.map(value => Math.max(0, Math.round(finiteNumber(value))))
      : [],
  } : null
  const points = paretoPoints(source.pareto)
  const f1Fallback = points.length ? Math.min(...points.map(point => point[0])) : 0
  const f2Fallback = points.length ? Math.min(...points.map(point => point[1])) : 0
  return {
    ...source,
    key: String(source.key || `variant_${index + 1}`),
    label: String(source.label || source.name || `算法 ${index + 1}`),
    pareto: points,
    hv: finiteNumber(source.hv ?? metrics.hv),
    igd: finiteNumber(source.igd ?? metrics.igd),
    spacing: finiteNumber(source.spacing ?? metrics.spacing),
    f1_best: finiteNumber(source.f1_best, f1Fallback),
    f2_best: finiteNumber(source.f2_best, f2Fallback),
    solutions: Math.max(0, Math.round(finiteNumber(source.solutions))),
    expected_objectives: objectiveArray(source.expected_objectives ?? source.expected),
    cvar_objectives: objectiveArray(source.cvar_objectives ?? source.cvar),
    worst_objectives: objectiveArray(source.worst_objectives ?? source.worst),
    nfe: Math.max(0, Math.round(finiteNumber(source.nfe))),
    operator_use: Array.isArray(source.operator_use)
      ? source.operator_use.map(value => Math.max(0, Math.round(finiteNumber(value))))
      : [],
    dispatch_quality: {
      ramp_mw: finiteNumber(dispatch.ramp_mw),
      starts: finiteNumber(dispatch.starts),
      mode_switches: finiteNumber(dispatch.mode_switches),
      short_runs: finiteNumber(dispatch.short_runs),
    },
    rl,
  }
}

function normalizeResult(raw) {
  if (!raw || typeof raw !== 'object') return null
  // A few early task snapshots wrapped the payload in ``result``.  Accept
  // both shapes so a browser refresh does not break on an old cached run.
  const source = raw.result && !Array.isArray(raw.variants) ? raw.result : raw
  if (!source || typeof source !== 'object') return null
  const variantValues = Array.isArray(source.variants)
    ? source.variants
    : (source.variants && typeof source.variants === 'object' ? Object.values(source.variants) : [])
  const days = Array.isArray(source.scenario_days)
    ? source.scenario_days.map(day => Math.max(0, Math.round(finiteNumber(day))))
    : []
  const labels = Array.isArray(source.scenario_labels)
    ? source.scenario_labels.map(label => String(label || ''))
    : []
  const risk = source.risk && typeof source.risk === 'object' ? source.risk : {}
  return {
    ...source,
    province_name: String(source.province_name || source.province || '未知省份'),
    capacity_mw: finiteNumber(source.capacity_mw),
    algorithm_version: String(source.algorithm_version || 'NSLDE + 场景鲁棒优化'),
    objective_definition: String(source.objective_definition || ''),
    scenario_days: days,
    scenario_labels: labels,
    risk: {
      alpha: finiteNumber(risk.alpha ?? source.alpha, 0.9),
      beta: finiteNumber(risk.beta ?? source.beta, 0),
    },
    runtime_seconds: finiteNumber(source.runtime_seconds),
    variants: variantValues.map(normalizeVariant),
  }
}

function errorMessage(error, fallback = '请求失败') {
  const detail = error?.response?.data?.detail || error?.response?.data?.error || error?.message
  return typeof detail === 'string' ? detail : fallback
}

async function runOptimization() {
  error.value = ''
  if (Number(form.value.extreme_count) >= Number(form.value.scenario_count)) {
    error.value = '极端场景数量必须小于场景总数'
    return
  }
  result.value = null; running.value = true
  try {
    task.value = await startRobustOptimization(form.value)
    if (!task.value?.task_id) throw new Error('后端未返回优化任务编号')
    poll(task.value.task_id)
  } catch (e) {
    running.value = false
    error.value = errorMessage(e)
  }
}

function poll(taskId) {
  clearInterval(timer)
  const refresh = async () => {
    try {
      task.value = await fetchRobustOptimization(taskId)
      if (task.value.status === 'completed') {
        clearInterval(timer); running.value = false; result.value = normalizeResult(task.value.result)
        if (!result.value) { error.value = '后端返回的优化结果为空'; return }
        await nextTick(); renderCharts()
      } else if (task.value.status === 'failed') {
        clearInterval(timer); running.value = false; error.value = task.value.error || '优化失败'
      }
    } catch (e) { clearInterval(timer); running.value = false; error.value = errorMessage(e, '优化任务查询失败') }
  }
  refresh(); timer = window.setInterval(refresh, 1000)
}

function chart(dom, option) {
  if (!dom) return
  const instance = echarts.init(dom); instance.setOption(option); charts.push(instance)
}

function renderCharts() {
  charts.forEach(item => item.dispose()); charts = []
  const variants = result.value?.variants || []
  if (!variants.length) return
  const base = { textStyle: { color: '#9ab6c7' }, backgroundColor: 'transparent' }
  chart(paretoEl.value, { ...base, tooltip: { trigger: 'item' }, legend: { data: variants.map(v => v.label), textStyle: { color: '#9ab6c7' } }, grid: { left: 70, right: 25, top: 50, bottom: 55 }, xAxis: { name: '鲁棒目标 f1', splitLine: { lineStyle: { color: '#123344' } } }, yAxis: { name: '鲁棒目标 f2', splitLine: { lineStyle: { color: '#123344' } } }, series: variants.map((v, i) => ({ name: v.label, type: 'scatter', data: v.pareto, symbolSize: 7, itemStyle: { color: colors[i] } })) })
  chart(metricEl.value, { ...base, tooltip: { trigger: 'axis' }, legend: { data: ['IGD', 'Spacing'], textStyle: { color: '#9ab6c7' } }, grid: { left: 55, right: 20, top: 48, bottom: 60 }, xAxis: { type: 'category', data: variants.map(v => v.label), axisLabel: { rotate: 18 } }, yAxis: { splitLine: { lineStyle: { color: '#123344' } } }, series: [{ name: 'IGD', type: 'bar', data: variants.map(v => v.igd), itemStyle: { color: '#48a8ff' } }, { name: 'Spacing', type: 'line', data: variants.map(v => v.spacing), itemStyle: { color: '#ffc857' } }] })
  chart(riskEl.value, {
    ...base,
    tooltip: { trigger: 'axis' },
    legend: { data: ['期望 f1', 'CVaR f1', '期望 f2', 'CVaR f2'], textStyle: { color: '#9ab6c7' } },
    grid: { left: 65, right: 65, top: 48, bottom: 60 },
    xAxis: { type: 'category', data: variants.map(v => v.label), axisLabel: { rotate: 18 } },
    yAxis: [
      { name: 'f1', splitLine: { lineStyle: { color: '#123344' } } },
      { name: 'f2', splitLine: { show: false }, axisLabel: { color: '#8aa5b3' } },
    ],
    series: [
      { name: '期望 f1', type: 'bar', yAxisIndex: 0, data: variants.map(v => v.expected_objectives?.[0] ?? null), itemStyle: { color: '#43e7c5' } },
      { name: 'CVaR f1', type: 'line', yAxisIndex: 0, data: variants.map(v => v.cvar_objectives?.[0] ?? null), itemStyle: { color: '#ff6b8a' } },
      { name: '期望 f2', type: 'bar', yAxisIndex: 1, data: variants.map(v => v.expected_objectives?.[1] ?? null), itemStyle: { color: '#48a8ff' } },
      { name: 'CVaR f2', type: 'line', yAxisIndex: 1, data: variants.map(v => v.cvar_objectives?.[1] ?? null), itemStyle: { color: '#ffc857' } },
    ],
  })
  chart(qualityEl.value, { ...base, tooltip: { trigger: 'axis' }, legend: { data: ['启停', '切换', '短时运行'], textStyle: { color: '#9ab6c7' } }, grid: { left: 45, right: 20, top: 48, bottom: 60 }, xAxis: { type: 'category', data: variants.map(v => v.label), axisLabel: { rotate: 18 } }, yAxis: { splitLine: { lineStyle: { color: '#123344' } } }, series: ['starts', 'mode_switches', 'short_runs'].map((key, i) => ({ name: ['启停', '切换', '短时运行'][i], type: 'bar', data: variants.map(v => finiteNumber(v.dispatch_quality[key])), itemStyle: { color: colors[i] } })) })
}

function resize() { charts.forEach(item => item.resize()) }
onMounted(async () => {
  window.addEventListener('resize', resize)
  try {
    const latest = await fetchLatestRobustOptimization()
    if (latest.status === 'completed') { task.value = latest; result.value = normalizeResult(latest.result); await nextTick(); renderCharts() }
    else if (['queued', 'running'].includes(latest.status)) { task.value = latest; running.value = true; poll(latest.task_id) }
  } catch (e) {
    // The comparison page remains usable offline; make the missing API
    // explicit instead of leaving a silent blank state.
    error.value = errorMessage(e, '尚未连接鲁棒优化后端，请先启动 FastAPI')
  }
})
onBeforeUnmount(() => { clearInterval(timer); charts.forEach(item => item.dispose()); window.removeEventListener('resize', resize) })
</script>

<style scoped>
.algorithm-screen{min-height:100vh;padding:12px;color:#d9eef4;background:#020d15;letter-spacing:0}.control-band{display:grid;grid-template-columns:minmax(230px,1.5fr) repeat(11,minmax(70px,1fr)) 150px;gap:10px;align-items:end;padding:14px;border:1px solid #175064;background:#061923}.control-title{display:flex;flex-direction:column;gap:4px;color:#43e7c5;font-size:17px}.control-title small{color:#7897a6;font-size:11px}.control-band label{display:flex;flex-direction:column;gap:5px;color:#7fa4b4;font-size:11px}.control-band input,.control-band select{height:34px;padding:0 8px;color:#d9eef4;border:1px solid #1d5366;background:#04131c}.run-button{height:36px;color:#032019;border:1px solid #62f5d4;background:#43e7c5;font-weight:700;cursor:pointer}.run-button:disabled{opacity:.45;cursor:wait}.progress-band,.error-band,.summary-line,.objective-note{margin-top:10px;padding:11px 14px;border:1px solid #174659;background:#061923}.progress-band>div:first-child{display:flex;justify-content:space-between}.progress-track{height:4px;margin-top:8px;background:#0b2b38}.progress-track i{display:block;height:100%;background:#43e7c5;transition:width .3s}.error-band{color:#ff9dac;border-color:#713245}.summary-line{display:flex;flex-wrap:wrap;gap:22px;color:#99bac8;font-size:12px}.objective-note{color:#7897a6;font-size:11px;line-height:1.5}.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:10px}.kpi-card{padding:14px;border:1px solid #195064;background:#061923}.kpi-card header{display:flex;justify-content:space-between;color:#43e7c5}.kpi-card header b{color:#718f9b;font-size:10px}.metric{display:inline-flex;width:50%;flex-direction:column;margin-top:17px}.metric strong{font-size:20px}.metric small{margin-top:4px;color:#708f9d;font-size:10px}.kpi-card footer{margin-top:13px;color:#7d9dab;font-size:10px;line-height:1.7}.visual-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}.panel,.scenario-panel{border:1px solid #175064;background:#051720}.panel.wide{grid-column:1/-1}.panel h3,.scenario-panel h3{margin:0;padding:10px 13px;color:#9cc3d1;border-bottom:1px solid #123b4b;font-size:12px}.chart{height:340px}.scenario-panel{margin-top:10px}.scenario-list{display:flex;flex-wrap:wrap;gap:8px;padding:12px}.scenario-list span{padding:6px 9px;color:#9fc5d2;border:1px solid #1b4c5d;background:#08212c;font-size:11px}.empty-panel{margin-top:10px;padding:80px;text-align:center;color:#6f919f;border:1px dashed #1c4d5f}.error-band{color:#ff9aaa}@media(max-width:1400px){.control-band{grid-template-columns:repeat(4,1fr)}.control-title{grid-column:1/-1}}@media(max-width:1100px){.control-band{grid-template-columns:repeat(3,1fr)}.control-title{grid-column:1/-1}.kpi-grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:700px){.control-band,.kpi-grid,.visual-grid{grid-template-columns:1fr}.panel.wide{grid-column:auto}.summary-line{flex-direction:column;gap:7px}}
</style>
