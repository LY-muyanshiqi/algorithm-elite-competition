<template>
  <article class="kpi-card" :class="`kpi-card--${tone}`">
    <span>{{ label }}</span>
    <strong>{{ value }} <small>{{ unit }}</small></strong>
    <em v-if="trend">{{ trend }}</em>
  </article>
</template>

<script setup>
defineProps({
  label: { type: String, required: true }, value: { type: [String, Number], required: true },
  unit: { type: String, default: '' }, trend: { type: String, default: '' }, tone: { type: String, default: 'green' },
})
</script>

<style scoped>
.kpi-card {
  position: relative;
  min-width: 0;
  padding: 10px 13px;
  background: rgba(3, 24, 34, .92);
  border: 1px solid var(--color-border);
  border-left: 2px solid var(--color-accent);
}
.kpi-card span { display: block; color: var(--color-muted); font-size: 10px; }
.kpi-card strong { display: block; margin-top: 5px; color: var(--color-accent); font: 700 clamp(15px, 1.25vw, 22px)/1 monospace; white-space: nowrap; }
.kpi-card small { font-size: 9px; font-weight: 400; }
.kpi-card em { position: absolute; top: 9px; right: 10px; color: var(--color-accent-soft); font-size: 9px; font-style: normal; }
.kpi-card--cyan { border-left-color: var(--color-cyan); }
.kpi-card--cyan strong { color: var(--color-cyan); }
.kpi-card--warning { border-left-color: var(--color-warning); }
.kpi-card--warning strong { color: var(--color-warning); }
</style>
