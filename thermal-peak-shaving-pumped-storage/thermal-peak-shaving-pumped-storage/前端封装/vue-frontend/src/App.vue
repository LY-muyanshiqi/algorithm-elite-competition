<template>
  <div class="app-container">
    <!-- 顶部导航栏 -->
    <header class="app-header">
      <div class="header-left">
        <span class="logo">⚡</span>
        <h1 class="title">抽水蓄能减碳效益优化系统</h1>
      </div>
      <nav class="header-nav">
        <router-link
          v-for="route in routes"
          :key="route.path"
          :to="route.path"
          class="nav-link"
          active-class="nav-link--active"
        >
          <span class="nav-icon">{{ route.meta.icon }}</span>
          <span class="nav-text">{{
            route.meta.navTitle || route.meta.title
          }}</span>
        </router-link>
        <a
          href="http://localhost:8501"
          class="nav-link nav-link--back"
          target="_blank"
          title="返回 Streamlit 仪表盘"
        >
          <span class="nav-icon">📊</span>
          <span class="nav-text">返回仪表盘</span>
        </a>
      </nav>
      <div class="header-right">
        <span
          class="api-status"
          :class="apiOnline ? 'status-online' : 'status-offline'"
        >
          {{ apiOnline ? "API 已连接" : "API 断开" }}
        </span>
      </div>
    </header>

    <!-- 主内容 -->
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from "vue";
import { useRouter } from "vue-router";
import { checkHealth } from "./api";

const router = useRouter();
const routes = router.getRoutes().filter((r) => r.name);
const apiOnline = ref(false);
const _healthTimer = ref(null);

onMounted(async () => {
  const health = await checkHealth();
  apiOnline.value = health.status === "ok";
  _healthTimer.value = setInterval(async () => {
    const h = await checkHealth();
    apiOnline.value = h.status === "ok";
  }, 30000);
});

onBeforeUnmount(() => {
  if (_healthTimer.value) clearInterval(_healthTimer.value);
});
</script>

<style>
/* ========== 全局样式（深色科技风） ========== */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

:root {
  --bg-primary: #0a1628;
  --bg-secondary: #0d1f3c;
  --bg-card: rgba(0, 212, 255, 0.08);
  --border-color: rgba(0, 212, 255, 0.25);
  --text-primary: #e0e6ed;
  --text-secondary: #8ba4c4;
  --accent: #00d4ff;
  --accent2: #00ff88;
  --danger: #ff6b6b;
  --warning: #ffcc00;
}

body {
  font-family:
    "Microsoft YaHei",
    -apple-system,
    sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  min-height: 100vh;
}

.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* ========== 顶部导航 ========== */
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 24px;
  background: linear-gradient(
    135deg,
    rgba(0, 212, 255, 0.1),
    rgba(0, 150, 255, 0.05)
  );
  border-bottom: 1px solid var(--border-color);
  backdrop-filter: blur(10px);
  position: sticky;
  top: 0;
  z-index: 100;
  flex-wrap: nowrap;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.logo {
  font-size: 1.4rem;
  line-height: 1;
}

.title {
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: 1px;
  white-space: nowrap;
  background: linear-gradient(90deg, var(--accent), #0096ff);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}

.header-nav {
  display: flex;
  gap: 4px;
  align-items: center;
  flex: 1;
  justify-content: center;
  padding: 0 16px;
  min-width: 0;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 7px 14px;
  border-radius: 8px;
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 0.85rem;
  font-weight: 500;
  letter-spacing: 0.5px;
  transition: all 0.2s;
  border: 1px solid transparent;
  white-space: nowrap;
}

.nav-link:hover {
  background: rgba(0, 212, 255, 0.1);
  color: var(--text-primary);
}

.nav-link--active {
  background: rgba(0, 212, 255, 0.15);
  color: var(--accent);
  border-color: rgba(0, 212, 255, 0.3);
}

.nav-link--back {
  flex-shrink: 0;
  margin-left: 8px;
  border-color: rgba(255, 255, 255, 0.1);
  font-size: 0.8rem;
  padding: 7px 12px;
}

.nav-icon {
  font-size: 1rem;
  line-height: 1;
}

.nav-text {
  font-size: 0.85rem;
}

.header-right {
  display: flex;
  align-items: center;
}

.api-status {
  font-size: 0.75rem;
  padding: 4px 12px;
  border-radius: 12px;
}

.status-online {
  background: rgba(0, 255, 136, 0.15);
  color: var(--accent2);
  border: 1px solid rgba(0, 255, 136, 0.3);
}

.status-offline {
  background: rgba(255, 107, 107, 0.15);
  color: var(--danger);
  border: 1px solid rgba(255, 107, 107, 0.3);
}

/* ========== 主内容 ========== */
.app-main {
  flex: 1;
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}
</style>
