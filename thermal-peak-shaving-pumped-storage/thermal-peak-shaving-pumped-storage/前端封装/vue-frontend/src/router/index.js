import { createRouter, createWebHistory } from 'vue-router'
import SchedulingEditor from '../views/SchedulingEditor.vue'
import SimulationView from '../views/SimulationView.vue'

const routes = [
  { path: '/', redirect: '/dashboard' },

  { path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { title: '系统总览', navTitle: '系统总览', icon: '📊', order: 1, fullScreen: true,
      screenTitle: '西北零碳虚拟电厂智能调度系统',
      screenSubtitle: '陕西 · 甘肃 · 青海 · 宁夏 · 新疆 / 新能源消纳与抽水蓄能协同优化' },
  },

  { path: '/scheduling',
    name: 'Scheduling',
    component: SchedulingEditor,
    meta: { title: '抽水蓄能调度编辑器', navTitle: '调度编辑', icon: '🏭', order: 2, fullScreen: true,
      screenTitle: '抽水蓄能智能调度控制中心',
      screenSubtitle: '西北电网 · 日内调度 · 曲线拖拽 · 碳减排反馈' },
  },

  { path: '/renewable',
    name: 'Renewable',
    component: () => import('../views/RenewableEnergy.vue'),
    meta: { title: '新能源数据', navTitle: '新能源', icon: '🌤️', order: 3, fullScreen: true,
      screenTitle: '西北五省区新能源资源分析',
      screenSubtitle: '风电 · 光伏 · 水电 / 365天 × 24小时出力监测' },
  },

  { path: '/carbon',
    name: 'Carbon',
    component: () => import('../views/CarbonAnalysis.vue'),
    meta: { title: '碳减排分析', navTitle: '碳分析', icon: '💨', order: 4, fullScreen: true,
      screenTitle: '西北五省区碳减排监测中心',
      screenSubtitle: '抽水蓄能协同调峰 · 碳排趋势 · 减排贡献分析' },
  },

  { path: '/simulation',
    name: 'Simulation',
    component: SimulationView,
    meta: { title: '实时仿真', icon: '🔬', order: 5,
      screenTitle: '实时仿真推演中心', screenSubtitle: '多场景参数推演 · 实时反馈' },
  },

  { path: '/heatmap',
    name: 'Heatmap',
    component: () => import('../views/HeatmapView.vue'),
    meta: { title: '热力图分析', icon: '🔥', primary: false },
  },

  { path: '/statistics',
    name: 'Statistics',
    component: () => import('../views/StatisticsView.vue'),
    meta: { title: '统计分析', icon: '📊', primary: false },
  },

  { path: '/algorithm-compare',
    name: 'AlgorithmCompare',
    component: () => import('../views/AlgorithmComparison.vue'),
    meta: { title: '算法对比', navTitle: '算法对比', icon: '⚔️', order: 6, fullScreen: true,
      screenTitle: '多目标优化算法对比中心',
      screenSubtitle: 'NSLDE · NSGA-II · MOEA/D / Pareto前沿与收敛性能' },
  },

  { path: '/history',
    name: 'History',
    component: () => import('../views/HistoryComparison.vue'),
    meta: { title: '历史对比', navTitle: '历史对比', icon: '📜', primary: false },
  },

  { path: '/seasonal',
    name: 'Seasonal',
    component: () => import('../views/SeasonalAnalysis.vue'),
    meta: { title: '四季分析', navTitle: '四季分析', icon: '🍃', primary: false },
  },

  { path: '/storage-compare',
    name: 'StorageCompare',
    component: () => import('../views/StorageComparison.vue'),
    meta: { title: '储能对比', navTitle: '储能对比', icon: '🔋', primary: false },
  },

  { path: '/experiments',
    name: 'Experiments',
    component: () => import('../views/ExperimentResults.vue'),
    meta: { title: '实验分析', navTitle: '实验分析', icon: '🧪',
      screenTitle: 'NSLDE 消融实验分析中心', screenSubtitle: '消融实验 · 显著性检验 · 收敛性能' },
  },

  { path: '/strategy',
    name: 'Strategy',
    component: () => import('../views/StrategyContributions.vue'),
    meta: { title: '策略贡献', navTitle: '策略贡献', icon: '🎯',
      screenTitle: 'Q-Learning 策略贡献分析中心', screenSubtitle: '自适应算子选择 · 奖励追踪' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
