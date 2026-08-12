<template>
  <div class="experiment-page">
    <h2>NSLDE 消融实验分析</h2>
    <p class="subtitle">7组配置对比 - 每模块独立贡献验证</p>

    <!-- 指标总览表格 -->
    <section class="section">
      <h3>消融实验指标对比</h3>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>配置</th>
              <th>初始化</th>
              <th>交叉/变异</th>
              <th>可行率</th>
              <th>f1均值</th>
              <th>f2均值</th>
              <th>HV</th>
              <th>IGD</th>
              <th>Spacing</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in ablationData" :key="row.name"
                :class="{ 'highlight': row.name === 'A4_NSLDE' }">
              <td><strong>{{ row.name }}</strong></td>
              <td>{{ row.init }}</td>
              <td>{{ row.operators }}</td>
              <td>{{ row.feasibility_rate }}</td>
              <td>{{ row.f1_mean }}</td>
              <td>{{ row.f2_mean }}</td>
              <td>{{ row.hv }}</td>
              <td>{{ row.igd }}</td>
              <td>{{ row.spacing }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 统计显著性 -->
    <section class="section">
      <h3>统计显著性检验 (Wilcoxon + Friedman)</h3>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>对比</th>
              <th>f1 p-value</th>
              <th>f2 p-value</th>
              <th>可行性 p-value</th>
              <th>Cohen's d</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in statsData" :key="row.comparison">
              <td>{{ row.comparison }}</td>
              <td :class="sigClass(row.p_f1)">{{ row.p_f1 }}</td>
              <td :class="sigClass(row.p_f2)">{{ row.p_f2 }}</td>
              <td :class="sigClass(row.p_feas)">{{ row.p_feas }}</td>
              <td>{{ row.cohens_d }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- 图表区 -->
    <section class="section">
      <h3>Pareto前沿对比</h3>
      <div ref="paretoChart" class="chart"></div>
    </section>

    <section class="section">
      <h3>收敛曲线 (HV vs 代数)</h3>
      <div ref="convergeChart" class="chart"></div>
    </section>

    <p class="note">
      数据说明: 真实数据请先在MATLAB运行 run_ablation(1, 'shaanxi', 5)，然后通过 experiment_runner.py 加载。
    </p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import * as echarts from 'echarts'

const ablationData = ref([
  { name: 'A0_NSGAII_baseline', init: 'random', operators: 'SBX+PM', feasibility_rate: '-', f1_mean: '-', f2_mean: '-', hv: '-', igd: '-', spacing: '-' },
  { name: 'A1_chaos_only', init: 'logistic', operators: 'SBX+PM', feasibility_rate: '-', f1_mean: '-', f2_mean: '-', hv: '-', igd: '-', spacing: '-' },
  { name: 'A2_de_only', init: 'random', operators: 'DE/rand/1+PM', feasibility_rate: '-', f1_mean: '-', f2_mean: '-', hv: '-', igd: '-', spacing: '-' },
  { name: 'A3_levy_only', init: 'random', operators: 'SBX+Levy', feasibility_rate: '-', f1_mean: '-', f2_mean: '-', hv: '-', igd: '-', spacing: '-' },
  { name: 'A4_NSLDE', init: 'logistic', operators: 'DE/rand/1+Levy', feasibility_rate: '-', f1_mean: '-', f2_mean: '-', hv: '-', igd: '-', spacing: '-' },
  { name: 'A5_QLearning', init: 'logistic', operators: 'Q-Learn自适应', feasibility_rate: '-', f1_mean: '-', f2_mean: '-', hv: '-', igd: '-', spacing: '-' },
  { name: 'A6_NSLDE_full', init: 'logistic', operators: '全7算子', feasibility_rate: '-', f1_mean: '-', f2_mean: '-', hv: '-', igd: '-', spacing: '-' },
])

const statsData = ref([
  { comparison: 'A1 vs A0 (混沌)', p_f1: '-', p_f2: '-', p_feas: '-', cohens_d: '-' },
  { comparison: 'A2 vs A0 (DE)', p_f1: '-', p_f2: '-', p_feas: '-', cohens_d: '-' },
  { comparison: 'A3 vs A0 (Levy)', p_f1: '-', p_f2: '-', p_feas: '-', cohens_d: '-' },
  { comparison: 'A4 vs A0 (NSLDE)', p_f1: '-', p_f2: '-', p_feas: '-', cohens_d: '-' },
  { comparison: 'A5 vs A4 (Q-Learn)', p_f1: '-', p_f2: '-', p_feas: '-', cohens_d: '-' },
  { comparison: 'A6 vs A4 (Full)', p_f1: '-', p_f2: '-', p_feas: '-', cohens_d: '-' },
])

const paretoChart = ref(null)
const convergeChart = ref(null)

function sigClass(val) {
  if (val === '-') return ''
  const n = parseFloat(val)
  if (n < 0.001) return 'sig-high'
  if (n < 0.01) return 'sig-mid'
  if (n < 0.05) return 'sig-low'
  return ''
}

onMounted(() => {
  // Pareto对比图
  const pChart = echarts.init(paretoChart.value)
  pChart.setOption({
    tooltip: { trigger: 'item' },
    legend: { data: ['A0 (NSGA-II)', 'A4 (NSLDE)', 'A5 (Q-Learning)'], textStyle: { color: '#ccc' } },
    xAxis: { name: 'f1 (火电调峰, MW)', nameTextStyle: { color: '#999' }, axisLine: { lineStyle: { color: '#444' } } },
    yAxis: { name: 'f2 (碳排放, kg)', nameTextStyle: { color: '#999' }, axisLine: { lineStyle: { color: '#444' } } },
    backgroundColor: '#1a1a2e',
    series: [
      { name: 'A0 (NSGA-II)', type: 'scatter', data: [], itemStyle: { color: '#e74c3c' } },
      { name: 'A4 (NSLDE)', type: 'scatter', data: [], itemStyle: { color: '#2ecc71' } },
      { name: 'A5 (Q-Learning)', type: 'scatter', data: [], itemStyle: { color: '#3498db' } },
    ]
  })

  // 收敛曲线图
  const cChart = echarts.init(convergeChart.value)
  cChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['A0', 'A1', 'A2', 'A3', 'A4', 'A5', 'A6'], textStyle: { color: '#ccc' } },
    xAxis: { name: '代数', nameTextStyle: { color: '#999' }, axisLine: { lineStyle: { color: '#444' } } },
    yAxis: { name: 'HV', nameTextStyle: { color: '#999' }, axisLine: { lineStyle: { color: '#444' } } },
    backgroundColor: '#1a1a2e',
    series: Array.from({ length: 7 }, (_, i) => ({
      name: 'A' + i, type: 'line', data: [], smooth: true,
      lineStyle: { width: i === 4 ? 3 : 1.5 },
    }))
  })
})
</script>

<style scoped>
.experiment-page {
  padding: 24px;
  color: #e0e0e0;
}
.subtitle { color: #888; margin-bottom: 24px; }
.section { margin-bottom: 32px; }
.section h3 { color: #ccc; margin-bottom: 12px; border-left: 3px solid #2ecc71; padding-left: 8px; }
.table-wrapper { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #333; }
th { background: #16213e; color: #999; position: sticky; top: 0; }
tr:hover { background: rgba(46, 204, 113, 0.1); }
.highlight { background: rgba(46, 204, 113, 0.15); }
.sig-high { color: #2ecc71; font-weight: bold; }
.sig-mid { color: #3498db; }
.sig-low { color: #f39c12; }
.chart { width: 100%; height: 400px; }
.note { margin-top: 32px; padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px; color: #666; font-size: 12px; }
</style>
