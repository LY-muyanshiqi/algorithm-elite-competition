<template>
  <div class="app-shell">
    <div v-if="runtimeError" class="global-error" role="alert">
      <span>页面运行异常：{{ runtimeError }}</span>
      <button type="button" @click="reloadPage">重新加载</button>
    </div>

    <header v-if="!isFullScreen" class="app-header">
      <router-link to="/dashboard" class="brand" aria-label="返回系统总览">
        <span class="brand-mark">⚡</span>
        <span>
          <strong>智蓄减碳</strong>
          <small>NSLDE · PUMPED STORAGE</small>
        </span>
      </router-link>

      <nav class="main-nav" aria-label="主导航">
        <router-link
          v-for="route in primaryRoutes"
          :key="route.path"
          :to="route.path"
          class="nav-link"
          active-class="nav-link--active"
        >
          {{ route.meta.navTitle || route.meta.title }}
        </router-link>
        <a
          href="http://localhost:8501"
          class="nav-link nav-link--streamlit"
          target="_blank"
          rel="noopener noreferrer"
          title="打开 Streamlit 调试仪表盘"
        >
          Streamlit 仪表盘
        </a>
      </nav>

      <StatusIndicator
        :status="apiOnline ? 'online' : 'offline'"
        :label="apiOnline ? '数据服务在线' : '数据服务离线'"
      />
    </header>

    <div v-if="!isFullScreen && !apiOnline" class="offline-banner">
      FastAPI 暂未连接，页面将显示演示数据；启动后端后会自动恢复实时数据。
    </div>

    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onErrorCaptured, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { checkHealth } from './api'
import StatusIndicator from './components/StatusIndicator.vue'

const router = useRouter()
const route = useRoute()
const apiOnline = ref(false)
const runtimeError = ref('')
const isFullScreen = computed(() => route.meta.fullScreen === true)
let healthTimer

const primaryRoutes = computed(() =>
  router
    .getRoutes()
    .filter((route) => route.name && route.meta?.primary !== false)
    .sort((a, b) => (a.meta.order ?? 99) - (b.meta.order ?? 99)),
)

async function refreshHealth() {
  const health = await checkHealth()
  apiOnline.value = health.status === 'ok'
}

function reloadPage() {
  window.location.reload()
}

onErrorCaptured((error) => {
  runtimeError.value = error?.message || '未知错误'
  return false
})

onMounted(() => {
  refreshHealth()
  healthTimer = window.setInterval(refreshHealth, 30000)
})

onBeforeUnmount(() => window.clearInterval(healthTimer))
</script>

<style>
@import './styles/theme.css';

.app-shell {
  min-height: 100vh;
  background: var(--color-bg);
}

.app-header {
  position: sticky;
  top: 0;
  z-index: 100;
  min-height: 62px;
  display: grid;
  grid-template-columns: minmax(230px, 1fr) auto minmax(190px, 1fr);
  align-items: center;
  gap: 20px;
  padding: 8px clamp(16px, 2vw, 36px);
  background: rgba(3, 20, 31, 0.94);
  border-bottom: 1px solid var(--color-border-strong);
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.28);
  backdrop-filter: blur(16px);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--color-text);
  text-decoration: none;
}

.brand-mark {
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  color: var(--color-accent);
  border: 1px solid var(--color-border-strong);
  border-radius: 10px;
  background: rgba(20, 241, 190, 0.08);
}

.brand strong,
.brand small {
  display: block;
}

.brand strong {
  font-size: 17px;
  letter-spacing: 0.16em;
}

.brand small {
  margin-top: 2px;
  color: var(--color-muted);
  font-size: 9px;
  letter-spacing: 0.12em;
}

.main-nav {
  display: flex;
  justify-content: center;
  gap: 4px;
}

.nav-link {
  padding: 8px 11px;
  color: var(--color-muted);
  border-bottom: 2px solid transparent;
  text-decoration: none;
  font-size: 13px;
  white-space: nowrap;
  transition: 180ms ease;
}

.nav-link:hover,
.nav-link--active {
  color: var(--color-accent);
  border-bottom-color: var(--color-accent);
  background: linear-gradient(180deg, transparent, rgba(20, 241, 190, 0.08));
}

.nav-link--streamlit {
  margin-left: 6px;
  color: var(--color-cyan);
  border: 1px solid rgba(86, 217, 255, 0.2);
  border-radius: 3px;
}

.nav-link--streamlit:hover {
  color: #d9f8ff;
  border-color: rgba(86, 217, 255, 0.55);
  background: rgba(86, 217, 255, 0.1);
}

.app-header > :last-child {
  justify-self: end;
}

.offline-banner,
.global-error {
  padding: 8px 24px;
  text-align: center;
  font-size: 12px;
}

.offline-banner {
  color: #ffd27a;
  background: rgba(255, 170, 44, 0.12);
  border-bottom: 1px solid rgba(255, 170, 44, 0.25);
}

.global-error {
  position: relative;
  z-index: 200;
  color: #ffd3d3;
  background: #501c27;
}

.global-error button {
  margin-left: 12px;
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.35);
  border-radius: 4px;
  background: transparent;
  cursor: pointer;
}

.app-main {
  min-height: calc(100vh - 62px);
}

@media (max-width: 1180px) {
  .app-header {
    grid-template-columns: 1fr auto;
  }

  .main-nav {
    grid-column: 1 / -1;
    justify-content: flex-start;
    overflow-x: auto;
    order: 3;
  }
}
</style>
