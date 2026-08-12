<template>
  <div class="strategy-page">
    <h2>Q-Learning 策略贡献度分析</h2>
    <p class="subtitle">7种算子在进化过程中的使用分布与奖励追踪</p>

    <!-- 策略使用占比时序图 -->
    <section class="section">
      <h3>策略使用占比随代数变化</h3>
      <div ref="stackChart" class="chart"></div>
    </section>

    <!-- 各策略平均奖励 -->
    <section class="section">
      <h3>各策略平均奖励对比</h3>
      <div ref="rewardChart" class="chart"></div>
    </section>

    <!-- 策略统计表 -->
    <section class="section">
      <h3>策略使用统计</h3>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>算子</th>
              <th>使用次数</th>
              <th>使用占比</th>
              <th>平均奖励</th>
              <th>存活率</th>
              <th>主要阶段</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in strategyStats" :key="row.name">
              <td><strong>{{ row.name }}</strong></td>
              <td>{{ row.use_count }}</td>
              <td>{{ row.use_ratio }}</td>
              <td>{{ row.avg_reward }}</td>
              <td>{{ row.survival_rate }}</td>
              <td>{{ row.phase }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Q-Learning vs 固定概率对比 -->
    <section class="section">
      <h3>自适应 vs 固定概率效果对比</h3>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>指标</th>
              <th>Q-Learning自适应</th>
              <th>固定均匀概率</th>
              <th>提升</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in comparisonData" :key="row.metric">
              <td>{{ row.metric }}</td>
              <td>{{ row.adaptive }}</td>
              <td>{{ row.fixed }}</td>
              <td :class="row.improvement > 0 ? 'improve' : 'decline'">{{ row.improvement }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <p class="note">
      数据说明: 在MATLAB中运行 nslde_enhanced 时设置 options.track_strategy = true 和 options.use_qlearning = true，
      输出的 history.strategy_history 包含策略分布数据。
    </p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import * as echarts from 'echarts'

const stackChart = ref(null)
const rewardChart = ref(null)

const opNames = ['DE/rand/1', 'DE/rand/2', 'DE/c-to-b/1', 'PM', 'SBX', 'Levy', 'Cauchy']

const strategyStats = ref([
  { name: 'DE/rand/1', use_count: '-', use_ratio: '-', avg_reward: '-', survival_rate: '-', phase: '-' },
  { name: 'DE/rand/2', use_count: '-', use_ratio: '-', avg_reward: '-', survival_rate: '-', phase: '-' },
  { name: 'DE/c-to-b/1', use_count: '-', use_ratio: '-', avg_reward: '-', survival_rate: '-', phase: '-' },
  { name: 'PM', use_count: '-', use_ratio: '-', avg_reward: '-', survival_rate: '-', phase: '-' },
  { name: 'SBX', use_count: '-', use_ratio: '-', avg_reward: '-', survival_rate: '-', phase: '-' },
  { name: 'Levy', use_count: '-', use_ratio: '-', avg_reward: '-', survival_rate: '-', phase: '-' },
  { name: 'Cauchy', use_count: '-', use_ratio: '-', avg_reward: '-', survival_rate: '-', phase: '-' },
])

const comparisonData = ref([
  { metric: 'HV', adaptive: '-', fixed: '-', improvement: 0 },
  { metric: 'IGD', adaptive: '-', fixed: '-', improvement: 0 },
  { metric: 'Spacing', adaptive: '-', fixed: '-', improvement: 0 },
  { metric: '可行率', adaptive: '-', fixed: '-', improvement: 0 },
  { metric: '收敛速度(代数)', adaptive: '-', fixed: '-', improvement: 0 },
])

onMounted(() => {
  const sChart = echarts.init(stackChart.value)
  sChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: opNames, textStyle: { color: '#ccc' }, top: 0 },
    grid: { left: 50, right: 30, top: 40, bottom: 40 },
    xAxis: { name: '代数', nameTextStyle: { color: '#999' }, axisLine: { lineStyle: { color: '#444' } } },
    yAxis: { name: '使用占比', nameTextStyle: { color: '#999' }, axisLine: { lineStyle: { color: '#444' } }, max: 1 },
    backgroundColor: '#1a1a2e',
    series: opNames.map(name => ({ name, type: 'line', data: [], smooth: true, stack: 'total', areaStyle: {} })),
  })

  const rChart = echarts.init(rewardChart.value)
  rChart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: opNames, axisLabel: { color: '#ccc', rotate: 15 }, axisLine: { lineStyle: { color: '#444' } } },
    yAxis: { name: '平均奖励', nameTextStyle: { color: '#999' }, axisLine: { lineStyle: { color: '#444' } } },
    backgroundColor: '#1a1a2e',
    series: [{ type: 'bar', data: [], itemStyle: { color: '#3498db', borderRadius: [4,4,0,0] } }],
  })
})
</script>

<style scoped>
.strategy-page { padding: 24px; color: #e0e0e0; }
.subtitle { color: #888; margin-bottom: 24px; }
.section { margin-bottom: 32px; }
.section h3 { color: #ccc; margin-bottom: 12px; border-left: 3px solid #3498db; padding-left: 8px; }
.table-wrapper { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #333; }
th { background: #16213e; color: #999; }
tr:hover { background: rgba(52, 152, 219, 0.1); }
.chart { width: 100%; height: 400px; }
.improve { color: #2ecc71; font-weight: bold; }
.decline { color: #e74c3c; }
.note { margin-top: 32px; padding: 12px; background: rgba(255,255,255,0.05); border-radius: 8px; color: #666; font-size: 12px; }
</style>
