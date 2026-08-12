<template>
  <header class="screen-header">
    <div class="screen-brand">
      <span class="screen-brand__mark">ϟ</span>
      <div>
        <h1>{{ displayTitle }}</h1>
        <p>{{ displaySubtitle }}</p>
      </div>
    </div>

    <nav class="screen-nav" aria-label="大屏导航">
      <i></i>
      <router-link
        v-for="route in primaryRoutes"
        :key="route.path"
        :to="route.path"
        active-class="screen-nav__link--active"
        class="screen-nav__link"
      >
        {{ route.meta.navTitle || route.meta.title }}
      </router-link>
      <details v-if="secondaryRoutes.length" class="more-nav">
        <summary>更多</summary>
        <div>
          <router-link
            v-for="route in secondaryRoutes"
            :key="route.path"
            :to="route.path"
          >
            {{ route.meta.navTitle || route.meta.title }}
          </router-link>
        </div>
      </details>
      <i></i>
    </nav>

    <div class="screen-tools">
      <StatusIndicator :status="status" :label="statusLabel" />
      <a href="http://localhost:8501" target="_blank" rel="noopener noreferrer"
        >Streamlit</a
      >
      <div class="weather">
        <span>●</span>
        <div><strong>实时天气</strong><small>WEATHER</small></div>
      </div>
      <RealtimeClock />
    </div>
  </header>
</template>

<script setup>
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import RealtimeClock from "./RealtimeClock.vue";
import StatusIndicator from "./StatusIndicator.vue";

const router = useRouter();
const route = useRoute();
const namedRoutes = computed(() =>
  router.getRoutes().filter((route) => route.name),
);
const primaryRoutes = computed(() =>
  namedRoutes.value
    .filter((route) => route.meta.primary !== false)
    .sort((a, b) => (a.meta.order ?? 99) - (b.meta.order ?? 99)),
);
const secondaryRoutes = computed(() =>
  namedRoutes.value.filter((route) => route.meta.primary === false),
);

const props = defineProps({
  title: { type: String, default: "" },
  subtitle: { type: String, default: "" },
  status: { type: String, default: "online" },
  statusLabel: { type: String, default: "调度系统在线" },
});

const displayTitle = computed(
  () => props.title || route.meta.screenTitle || route.meta.title || "智蓄减碳",
);
const displaySubtitle = computed(
  () =>
    props.subtitle ||
    route.meta.screenSubtitle ||
    "新型电力系统下抽水蓄能减碳效益优化系统",
);
</script>

<style scoped>
.screen-header {
  height: 86px;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 20px;
  padding: 8px 24px;
  background: linear-gradient(90deg, #063f40 0%, #073739 48%, #063a3c 100%);
  border: 1px solid rgba(20, 241, 190, 0.55);
  border-bottom: 2px solid rgba(20, 241, 190, 0.48);
  box-shadow:
    0 8px 30px rgba(0, 0, 0, 0.35),
    inset 0 -1px 20px rgba(20, 241, 190, 0.06);
}
.screen-brand {
  display: flex;
  align-items: center;
  gap: 13px;
  min-width: 0;
}
.screen-brand__mark {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  color: #24f7c1;
  border: 1px solid rgba(36, 247, 193, 0.45);
  border-radius: 10px;
  background: rgba(3, 25, 35, 0.35);
  font-size: 28px;
  font-weight: 800;
  box-shadow: inset 0 0 15px rgba(36, 247, 193, 0.08);
}
.screen-brand h1 {
  margin: 0;
  font-size: clamp(18px, 1.55vw, 27px);
  font-weight: 500;
  letter-spacing: 0.12em;
  white-space: nowrap;
}
.screen-brand p {
  margin: 4px 0 0;
  color: #73aaa8;
  font-size: 10px;
  font-style: italic;
  font-weight: 700;
  letter-spacing: 0.06em;
}
.screen-nav {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  color: #16eeb7;
}
.screen-nav > i {
  display: block;
  width: 48px;
  height: 1px;
  margin: 0 8px;
  background: linear-gradient(90deg, transparent, #10b994);
}
.screen-nav > i:last-child {
  transform: scaleX(-1);
}
.screen-nav__link,
.more-nav summary {
  padding: 10px 8px 8px;
  color: #79aaa5;
  border-bottom: 2px solid transparent;
  text-decoration: none;
  font-size: 11px;
  white-space: nowrap;
  cursor: pointer;
  list-style: none;
  transition: 160ms ease;
}
.screen-nav__link:hover,
.screen-nav__link--active {
  color: #20f3bd;
  border-bottom-color: #14f1be;
  background: linear-gradient(180deg, transparent, rgba(20, 241, 190, 0.07));
}
.more-nav {
  position: relative;
}
.more-nav summary::-webkit-details-marker {
  display: none;
}
.more-nav[open] summary {
  color: #20f3bd;
}
.more-nav > div {
  position: absolute;
  z-index: 30;
  top: 38px;
  right: 0;
  min-width: 126px;
  display: grid;
  padding: 6px;
  background: rgba(2, 20, 28, 0.98);
  border: 1px solid rgba(20, 241, 190, 0.34);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.45);
}
.more-nav a {
  padding: 8px 10px;
  color: #8fb4b0;
  text-decoration: none;
  font-size: 11px;
}
.more-nav a:hover {
  color: #20f3bd;
  background: rgba(20, 241, 190, 0.08);
}
.screen-tools {
  justify-self: end;
  display: flex;
  align-items: center;
  gap: 20px;
}
.screen-tools > a {
  padding: 5px 8px;
  color: #72dcca;
  border: 1px solid rgba(20, 241, 190, 0.22);
  text-decoration: none;
  font-size: 10px;
}
.weather {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-left: 16px;
  border-left: 1px solid rgba(119, 170, 168, 0.18);
}
.weather > span {
  color: #aaffdf;
  text-shadow: 0 0 10px #65ffd1;
}
.weather strong,
.weather small {
  display: block;
}
.weather strong {
  font-size: 11px;
}
.weather small {
  color: #6e9897;
  font-size: 8px;
}
@media (max-width: 1450px) {
  .screen-nav > i {
    display: none;
  }
  .screen-nav__link {
    padding-inline: 6px;
  }
  .screen-tools > :first-child,
  .weather {
    display: none;
  }
}
@media (max-width: 800px) {
  .screen-header {
    grid-template-columns: 1fr auto;
    height: 76px;
    padding: 7px 12px;
  }
  .screen-nav {
    display: none;
  }
  .screen-tools > a {
    display: none;
  }
  .screen-brand p {
    display: none;
  }
}
</style>
