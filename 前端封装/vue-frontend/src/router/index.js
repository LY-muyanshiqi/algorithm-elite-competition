import { createRouter, createWebHistory } from 'vue-router'
import SchedulingEditor from '../views/SchedulingEditor.vue'
import SimulationView from '../views/SimulationView.vue'

const routes = [
  { path: '/', redirect: '/dashboard' },

  { path: '/dashboard',
    name: 'Dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { title: '系统总览', icon: '📊' },
  },

  { path: '/scheduling',
    name: 'Scheduling',
    component: SchedulingEditor,
    meta: { title: '抽水蓄能调度编辑器', navTitle: '调度编辑', icon: '🏭' },
  },

  { path: '/renewable',
    name: 'Renewable',
    component: () => import('../views/RenewableEnergy.vue'),
    meta: { title: '新能源数据', icon: '🌤️' },
  },

  { path: '/carbon',
    name: 'Carbon',
    component: () => import('../views/CarbonAnalysis.vue'),
    meta: { title: '碳减排分析', icon: '💨' },
  },

  { path: '/simulation',
    name: 'Simulation',
    component: SimulationView,
    meta: { title: '实时仿真', icon: '🔬' },
  },

  { path: '/heatmap',
    name: 'Heatmap',
    component: () => import('../views/HeatmapView.vue'),
    meta: { title: '热力图分析', icon: '🔥' },
  },

  { path: '/statistics',
    name: 'Statistics',
    component: () => import('../views/StatisticsView.vue'),
    meta: { title: '统计分析', icon: '📊' },
  },

  { path: '/algorithm-compare',
    name: 'AlgorithmCompare',
    component: () => import('../views/AlgorithmComparison.vue'),
    meta: { title: '算法对比', navTitle: '算法对比', icon: '⚔️' },
  },

  { path: '/history',
    name: 'History',
    component: () => import('../views/HistoryComparison.vue'),
    meta: { title: '历史对比', navTitle: '历史对比', icon: '📜' },
  },

  { path: '/seasonal',
    name: 'Seasonal',
    component: () => import('../views/SeasonalAnalysis.vue'),
    meta: { title: '四季分析', navTitle: '四季分析', icon: '🍃' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
