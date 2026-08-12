<template>
  <div class="app-shell">
    <div v-if="runtimeError" class="global-error" role="alert">
      <span>页面运行异常：{{ runtimeError }}</span>
      <button type="button" @click="reloadPage">重新加载</button>
    </div>

    <ScreenHeader
      :status="apiOnline ? 'online' : 'offline'"
      :status-label="apiOnline ? '数据服务在线' : '数据服务离线'"
    />

    <div v-if="!apiOnline" class="offline-banner">
      FastAPI 暂未连接，页面将显示演示数据；启动后端后会自动恢复实时数据。
    </div>

    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import {
  computed,
  onBeforeUnmount,
  onErrorCaptured,
  onMounted,
  ref,
} from "vue";
import { checkHealth } from "./api";
import ScreenHeader from "./components/ScreenHeader.vue";

const apiOnline = ref(false);
const runtimeError = ref("");

let healthTimer;

async function refreshHealth() {
  const health = await checkHealth();
  apiOnline.value = health.status === "ok";
}

function reloadPage() {
  window.location.reload();
}

onErrorCaptured((error) => {
  runtimeError.value = error?.message || "未知错误";
  return false;
});

onMounted(() => {
  refreshHealth();
  healthTimer = window.setInterval(refreshHealth, 30000);
});

onBeforeUnmount(() => window.clearInterval(healthTimer));
</script>

<style>
@import "./styles/theme.css";

.app-shell {
  min-height: 100vh;
  background: var(--color-bg);
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
  min-height: calc(100vh - 86px);
}
</style>
