<template>
  <header class="chart-title">
    <span>{{ title }}</span>
    <small v-if="english">/ {{ english }}</small>
    <slot />
  </header>
</template>

<script setup>
defineProps({ title: { type: String, required: true }, english: { type: String, default: '' } })
</script>

<style scoped>
.chart-title {
  min-height: 35px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  color: var(--color-text);
  border-left: 3px solid var(--color-accent);
  background: repeating-linear-gradient(115deg, rgba(20, 241, 190, .06) 0 2px, transparent 2px 10px);
  font-size: 13px;
  font-weight: 700;
}
.chart-title small { color: var(--color-muted); font-size: 9px; font-style: italic; }
</style>
