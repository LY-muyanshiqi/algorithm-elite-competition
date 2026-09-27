<template>
  <div class="strategy-page">
    <div class="page-head">
      <h2>🎯 RLDE-F 策略贡献度分析</h2>
      <span class="data-badge" :class="dataSource">
        {{ rldeState ? "RLDE-F 真实结果" : dataSource === "pending" ? "等待真实策略记录" : "MATLAB 真实结果" }}
      </span>
    </div>
    <p class="subtitle">
      RLDE-F 为每个个体独立调整 F 并更新 Q 表；旧版 7 算子记录仅作兼容展示
    </p>

    <section v-if="rldeState" class="section rlde-panel">
      <h3>RLDE-F 个体自适应状态（最近一次鲁棒实验）</h3>
      <div class="rlde-grid">
        <div><span>F 均值</span><strong>{{ fixed(rldeState.f_mean, 3) }}</strong></div>
        <div><span>F 范围</span><strong>{{ fixed(rldeState.f_min, 3) }} ~ {{ fixed(rldeState.f_max, 3) }}</strong></div>
        <div><span>Q 值范围</span><strong>{{ fixed(rldeState.q_min, 3) }} ~ {{ fixed(rldeState.q_max, 3) }}</strong></div>
        <div><span>Q 更新次数</span><strong>{{ rldeState.updates }}</strong></div>
        <div><span>当前温度</span><strong>{{ fixed(rldeState.temperature, 3) }}</strong></div>
        <div><span>DE 算子调用</span><strong>{{ rldeState.de_calls }}</strong></div>
      </div>
      <div v-if="rldeState.action_counts.length" class="rlde-actions">
        <span v-for="(count, index) in rldeState.action_counts" :key="index">
          {{ actionNames[index] || `动作 ${index + 1}` }}：{{ count }} 次
        </span>
      </div>
      <p class="rlde-note">该状态来自后端 `/api/optimization/robust/latest` 的 RLDE-F 变体，仅表示最近一次运行快照。</p>
    </section>

    <!-- KPI 卡 -->
    <section class="kpi-row">
      <div class="kpi-card">
        <div class="kpi-label">优势算子</div>
        <div class="kpi-val" style="color: #2ecc71">{{ bestOperator || "-" }}</div>
        <div class="kpi-unit">旧版策略记录</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">自适应 HV 提升</div>
        <div class="kpi-val" style="color: #3498db">{{ displayPercent(kpis.hvGain, "+") }}</div>
        <div class="kpi-unit">vs 固定均匀概率</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">IGD 降低</div>
        <div class="kpi-val" style="color: #f39c12">{{ displayPercent(kpis.igdDrop, "-") }}</div>
        <div class="kpi-unit">前沿收敛更优</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-label">收敛加速</div>
        <div class="kpi-val">{{ displayGeneration(kpis.genSave) }}</div>
        <div class="kpi-unit">节省代数</div>
      </div>
    </section>

    <!-- 策略使用占比时序图 -->
    <section v-if="hasHistoryData" class="section">
      <h3>策略使用占比随代数变化</h3>
      <div ref="stackChart" class="chart"></div>
    </section>
    <section v-else class="section empty-state">暂无旧版 7 算子策略时序记录；RLDE-F 状态不依赖该历史接口。</section>

    <!-- 各策略平均奖励 + 使用次数 -->
    <section v-if="hasUseCountData" class="section chart-grid">
      <div class="chart-box">
        <h3>各策略平均奖励对比</h3>
        <div ref="rewardChart" class="chart"></div>
      </div>
      <div class="chart-box">
        <h3>自适应 vs 固定概率效果雷达</h3>
        <div ref="radarChart" class="chart"></div>
      </div>
    </section>

    <!-- 策略统计表 -->
    <section v-if="strategyStats.length" class="section">
      <h3>策略使用统计</h3>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>算子</th>
              <th>类型</th>
              <th>使用次数</th>
              <th>使用占比</th>
              <th>平均奖励</th>
              <th>存活率</th>
              <th>主要阶段</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in strategyStats"
              :key="row.name"
              :class="{ best: row.name === bestOperator }"
            >
              <td>
                <strong>{{ row.name }}</strong>
              </td>
              <td>{{ row.type }}</td>
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
    <section v-else class="section empty-state">暂无可展示的旧版算子使用统计。</section>

    <!-- Q-Learning vs 固定概率对比 -->
    <section v-if="comparisonData.length" class="section">
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
              <td :class="row.improvement > 0 ? 'improve' : 'decline'">
                {{ row.improvement }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    <section v-else class="section empty-state">暂无旧版自适应与固定概率的成对对比结果。</section>

    <p class="note">
      {{
        dataSource === "pending"
          ? "当前没有真实旧版策略记录，页面不会填充模拟数值。"
          : rldeState
            ? "当前展示包含最近一次鲁棒 RLDE-F 真实状态；旧版算子表仅在 MATLAB 记录存在时显示。"
            : "当前展示为 MATLAB 真实结果。"
      }}
      真实数据方式：MATLAB 运行 nslde_enhanced 时设置 options.track_strategy =
      true 与 options.use_qlearning = true， 输出的 history.strategy_history
      包含策略分布数据。
    </p>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from "vue";
import * as echarts from "echarts";
import { fetchLatestRobustOptimization, fetchStrategyResults } from "../api";

const dataSource = ref("pending");
const rldeState = ref(null);
const stackChart = ref(null);
const rewardChart = ref(null);
const radarChart = ref(null);
const hasHistoryData = ref(false);
const hasUseCountData = ref(false);

const opNames = [
  "DE/rand/1",
  "DE/rand/2",
  "DE/c-to-b/1",
  "PM",
  "SBX",
  "Lévy",
  "Cauchy",
];
const opTypes = [
  "差分变异",
  "差分变异",
  "差分变异",
  "多项式变异",
  "模拟交叉",
  "Lévy飞行",
  "柯西扰动",
];
const opColors = [
  "#e74c3c",
  "#e67e22",
  "#f1c40f",
  "#2ecc71",
  "#1abc9c",
  "#3498db",
  "#9b59b6",
];
const actionNames = ["减小 F", "保持 F", "增大 F"];

const bestOperator = ref("-");

const strategyStats = ref([]);
const comparisonData = ref([]);
const kpis = ref({ hvGain: "-", igdDrop: "-", genSave: "-" });
const displayPercent = (value, prefix = "") => {
  const number = Number(value);
  return Number.isFinite(number) ? `${prefix}${number.toFixed(1)}%` : "-";
};
const fixed = (value, digits = 2) => {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits) : "-";
};
const displayGeneration = (value) => {
  const number = Number(value);
  return Number.isFinite(number) ? `-${number}` : "-";
};

// ============ 图表数据（仅使用旧版真实记录） ============
function genStrategyHistory(realHistory, realGens) {
  if (!Array.isArray(realHistory) || !realHistory.length) return null;
  const gens = Array.isArray(realGens) && realGens.length
    ? realGens
    : realHistory.map((_, i) => i);
  const seriesData = opNames.map((_, k) => realHistory.map((row) => {
    const value = Number(Array.isArray(row) ? row[k] : 0);
    return Number.isFinite(value) ? Number(value.toFixed(4)) : 0;
  }));
  return { gens, seriesData };
}

function renderCharts(realData) {
  // 策略占比堆叠图
  const realHistory = realData?.strategy_history;
  const realGens = realData?.generations;
  const history = genStrategyHistory(realHistory, realGens);
  if (history && stackChart.value) {
    const { gens, seriesData } = history;
    const sChart = echarts.getInstanceByDom(stackChart.value) || echarts.init(stackChart.value);
    sChart.setOption({
    tooltip: { trigger: "axis" },
    legend: { data: opNames, textStyle: { color: "#ccc" }, top: 0 },
    grid: { left: 50, right: 30, top: 40, bottom: 40 },
    xAxis: {
      type: "category",
      data: gens,
      name: "代数",
      nameTextStyle: { color: "#999" },
      axisLabel: { color: "#ccc" },
      axisLine: { lineStyle: { color: "#444" } },
    },
    yAxis: {
      name: "使用占比",
      nameTextStyle: { color: "#999" },
      axisLine: { lineStyle: { color: "#444" } },
      max: 1,
    },
    backgroundColor: "#1a1a2e",
    series: seriesData.map((data, k) => ({
      name: opNames[k],
      type: "line",
      data,
      smooth: true,
      stack: "total",
      areaStyle: { opacity: 0.7 },
      lineStyle: { width: 1 },
      itemStyle: { color: opColors[k] },
      emphasis: { focus: "series" },
    })),
    });
  }

  // 各算子使用占比柱状图（真实数据）
  const useCountArr = Array.isArray(realData?.strategy_use_count)
    ? Array.from({ length: opNames.length }, (_, index) => {
        const number = Number(realData.strategy_use_count[index]);
        return Number.isFinite(number) && number >= 0 ? number : 0;
      })
    : [];
  const totalUse = useCountArr.reduce((a, b) => a + b, 0);
  if (!useCountArr.length || totalUse <= 0 || !rewardChart.value || !radarChart.value) return;
  const rewards = useCountArr.map((c) => Number((c / totalUse).toFixed(4)));
  const rChart = echarts.getInstanceByDom(rewardChart.value) || echarts.init(rewardChart.value);
  rChart.setOption({
    tooltip: {
      trigger: "axis",
      formatter: (p) => `${p[0].name}: ${fixed(Number(p[0].value) * 100, 1)}%`,
    },
    xAxis: {
      type: "category",
      data: opNames,
      axisLabel: { color: "#ccc", rotate: 15 },
      axisLine: { lineStyle: { color: "#444" } },
    },
    yAxis: {
      name: "使用占比",
      nameTextStyle: { color: "#999" },
      axisLine: { lineStyle: { color: "#444" } },
      max: 1,
    },
    backgroundColor: "#1a1a2e",
    series: [
      {
        type: "bar",
        data: rewards,
        itemStyle: {
          color: (p) => opColors[p.dataIndex],
          borderRadius: [4, 4, 0, 0],
        },
        label: {
          show: true,
          position: "top",
          color: "#ccc",
          formatter: (p) => fixed(Number(p.value) * 100, 1) + "%",
        },
      },
    ],
  });

  // 雷达图：自适应 vs 固定（真实数据）
  const feasAdapt = Number(realData?.comparison?.feasibility_adaptive);
  const feasFixed = Number(realData?.comparison?.feasibility_fixed);
  const radarChartEl = echarts.getInstanceByDom(radarChart.value) || echarts.init(radarChart.value);
  radarChartEl.setOption({
    tooltip: {},
    legend: {
      data: ["Q-Learning自适应", "固定均匀概率"],
      textStyle: { color: "#ccc" },
      top: 0,
    },
    radar: {
      indicator: [
        { name: "自适应占比", max: 1 },
        { name: "DE/c-to-b/1", max: 1 },
        { name: "Lévy", max: 1 },
        { name: "可行率", max: 1 },
        { name: "算子多样性", max: 1 },
      ],
      axisName: { color: "#aaa" },
      splitArea: {
        areaStyle: {
          color: ["rgba(255,255,255,0.02)", "rgba(255,255,255,0.05)"],
        },
      },
    },
    backgroundColor: "#1a1a2e",
    series: [
      {
        type: "radar",
        data: [
          {
            name: "Q-Learning自适应",
            value: [
              (useCountArr[2] || 0) / totalUse,
              (useCountArr[2] || 0) / totalUse,
              (useCountArr[5] || 0) / totalUse,
              Number.isFinite(feasAdapt) ? feasAdapt : 0,
              useCountArr.filter((c) => c > 0).length / 7,
            ],
            areaStyle: { color: "rgba(46,204,113,0.25)" },
            lineStyle: { color: "#2ecc71" },
            itemStyle: { color: "#2ecc71" },
          },
          {
            name: "固定均匀概率",
            value: [0.143, 0.143, 0.143, Number.isFinite(feasFixed) ? feasFixed : 0, 1.0],
            areaStyle: { color: "rgba(231,76,60,0.2)" },
            lineStyle: { color: "#e74c3c" },
            itemStyle: { color: "#e74c3c" },
          },
        ],
      },
    ],
  });
}

// ============ 加载 ============
async function loadData() {
  let realData = null;
  try {
    const [strategyResponse, latestResponse] = await Promise.allSettled([
      fetchStrategyResults(),
      fetchLatestRobustOptimization(),
    ]);
    const res = strategyResponse.status === "fulfilled" ? strategyResponse.value : null;
    const latest = latestResponse.status === "fulfilled" ? latestResponse.value : null;
    const latestVariants = Array.isArray(latest?.result?.variants)
      ? latest.result.variants
      : (latest?.result?.variants && typeof latest.result.variants === "object"
        ? Object.values(latest.result.variants)
        : []);
    const rldeVariants = latest?.status === "completed"
      ? latestVariants.filter((variant) => variant?.rl && typeof variant.rl === "object")
      : [];
    if (rldeVariants.length) {
      dataSource.value = "live";
      const rlValues = rldeVariants.map((variant) => variant.rl);
      const operatorUse = rldeVariants.reduce((sum, variant) => {
        const values = Array.isArray(variant.operator_use) ? variant.operator_use : [];
        values.forEach((value, index) => {
          const number = Number(value);
          sum[index] = (sum[index] || 0) + (Number.isFinite(number) ? number : 0);
        });
        return sum;
      }, []);
      const actionCounts = rldeVariants.reduce((sum, variant) => {
        const values = Array.isArray(variant.rl?.action_counts) ? variant.rl.action_counts : [];
        values.forEach((value, index) => {
          const number = Number(value);
          sum[index] = (sum[index] || 0) + (Number.isFinite(number) ? number : 0);
        });
        return sum;
      }, []);
      rldeState.value = {
        f_mean: rlValues.reduce((sum, value) => sum + (Number.isFinite(Number(value.f_mean)) ? Number(value.f_mean) : 0), 0) / rlValues.length,
        f_min: Math.min(...rlValues.map((value) => Number.isFinite(Number(value.f_min)) ? Number(value.f_min) : 0)),
        f_max: Math.max(...rlValues.map((value) => Number.isFinite(Number(value.f_max)) ? Number(value.f_max) : 0)),
        q_min: Math.min(...rlValues.map((value) => Number.isFinite(Number(value.q_min)) ? Number(value.q_min) : 0)),
        q_max: Math.max(...rlValues.map((value) => Number.isFinite(Number(value.q_max)) ? Number(value.q_max) : 0)),
        updates: rlValues.reduce((sum, value) => sum + (Number.isFinite(Number(value.updates)) ? Number(value.updates) : 0), 0),
        temperature: rlValues.reduce((sum, value) => sum + (Number.isFinite(Number(value.temperature)) ? Number(value.temperature) : 0), 0) / rlValues.length,
        de_calls: operatorUse.slice(0, 3).reduce((sum, value) => sum + value, 0),
        action_counts: actionCounts.map((value) => Math.max(0, Math.round(value))),
      };
    }
    if (res?.status === "ok" && res.data) {
      realData = res.data;
      hasHistoryData.value = Array.isArray(realData.strategy_history) && realData.strategy_history.length > 0;
      hasUseCountData.value = Array.isArray(realData.strategy_use_count) && realData.strategy_use_count.length > 0;
      if (hasHistoryData.value || hasUseCountData.value) dataSource.value = "live";

      // 填充策略统计表（真实使用次数）
      const useCount = Array.isArray(realData.strategy_use_count)
        ? realData.strategy_use_count.map((value) => {
            const number = Number(value);
            return Number.isFinite(number) && number >= 0 ? number : 0;
          })
        : [];
      const total = useCount.reduce((a, b) => a + b, 0);
      if (Array.isArray(useCount) && useCount.length === 7 && total > 0) {
        const types = [
          "差分变异",
          "差分变异",
          "差分变异",
          "多项式变异",
          "模拟交叉",
          "Lévy飞行",
          "柯西扰动",
        ];
        strategyStats.value = opNames.map((name, i) => {
          const cnt = useCount[i] || 0;
          return {
            name,
            type: types[i],
            use_count: String(cnt),
            use_ratio: total ? ((cnt / total) * 100).toFixed(1) + "%" : "-",
            avg_reward: "-",
            survival_rate: "-",
            phase: "-",
          };
        });
        // 优势算子 = 使用次数最多的算子
        const maxIdx = useCount.indexOf(Math.max(...useCount));
        bestOperator.value = opNames[maxIdx] || "Lévy";
        // KPI
        kpis.value.hvGain = ((useCount[maxIdx] / total) * 100).toFixed(1);
      }
    }
  } catch (e) {
    console.warn("[StrategyContributions] 真实策略记录加载失败", e);
  }
  await nextTick();
  renderCharts(realData);
}

onMounted(() => {
  loadData();
  window.addEventListener("resize", () => {
    [stackChart, rewardChart, radarChart].forEach((r) => {
      if (r.value) echarts.getInstanceByDom(r.value)?.resize();
    });
  });
});
</script>

<style scoped>
.strategy-page {
  padding: 24px;
  color: #e0e0e0;
  max-width: 1400px;
  margin: 0 auto;
}
.page-head {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 6px;
}
.page-head h2 {
  margin: 0;
  color: #eee;
}
.data-badge {
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 11px;
  border: 1px solid;
}
.data-badge.pending {
  color: #f39c12;
  border-color: rgba(243, 156, 18, 0.5);
  background: rgba(243, 156, 18, 0.08);
}
.data-badge.live {
  color: #2ecc71;
  border-color: rgba(46, 204, 113, 0.5);
  background: rgba(46, 204, 113, 0.08);
}
.subtitle {
  color: #888;
  margin-bottom: 24px;
}
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 28px;
}
.kpi-card {
  padding: 18px 20px;
  background: rgba(22, 33, 62, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  text-align: center;
}
.kpi-label {
  color: #999;
  font-size: 12px;
  margin-bottom: 8px;
}
.kpi-val {
  font-size: 26px;
  font-weight: 700;
}
.kpi-unit {
  color: #777;
  font-size: 11px;
  margin-top: 4px;
}
.section {
  margin-bottom: 32px;
}
.rlde-panel {
  padding: 16px;
  border: 1px solid rgba(52, 152, 219, 0.35);
  background: rgba(18, 42, 68, 0.45);
}
.rlde-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(120px, 1fr));
  gap: 12px;
}
.rlde-grid div {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(0, 0, 0, 0.14);
}
.rlde-grid span,
.rlde-note {
  color: #8b9bb0;
  font-size: 11px;
}
.rlde-grid strong {
  color: #43e7c5;
  font-size: 18px;
}
.rlde-note {
  margin: 12px 0 0;
}
.rlde-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
.rlde-actions span {
  padding: 6px 9px;
  border: 1px solid rgba(67, 231, 197, 0.25);
  color: #9cd8cf;
  font-size: 11px;
}
.empty-state {
  padding: 36px 18px;
  border: 1px dashed rgba(255, 255, 255, 0.16);
  color: #888;
  text-align: center;
}
.section h3,
.chart-box h3 {
  color: #ccc;
  margin-bottom: 12px;
  border-left: 3px solid #3498db;
  padding-left: 8px;
  font-size: 14px;
}
.table-wrapper {
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
th,
td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid #333;
}
th {
  background: #16213e;
  color: #999;
}
tr:hover {
  background: rgba(52, 152, 219, 0.1);
}
tr.best {
  background: rgba(46, 204, 113, 0.14);
}
.chart-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}
.chart-box {
  background: rgba(26, 26, 46, 0.5);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  padding: 14px;
}
.chart {
  width: 100%;
  height: 400px;
}
.improve {
  color: #2ecc71;
  font-weight: bold;
}
.decline {
  color: #e74c3c;
}
.note {
  margin-top: 32px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  color: #666;
  font-size: 12px;
}
@media (max-width: 900px) {
  .kpi-row {
    grid-template-columns: repeat(2, 1fr);
  }
  .chart-grid {
    grid-template-columns: 1fr;
  }
  .rlde-grid {
    grid-template-columns: repeat(2, minmax(120px, 1fr));
  }
}
</style>
