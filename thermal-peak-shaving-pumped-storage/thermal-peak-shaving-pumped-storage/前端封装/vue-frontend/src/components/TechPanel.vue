<template>
  <section class="tech-panel">
    <ChartTitle v-if="title" :title="title" :english="english" />
    <div class="tech-panel__body" :class="bodyClass"><slot /></div>
  </section>
</template>

<script setup>
import ChartTitle from './ChartTitle.vue'
defineProps({
  title: { type: String, default: '' },
  english: { type: String, default: '' },
  bodyClass: { type: String, default: '' },
})
</script>

<style scoped>
.tech-panel {
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  background: linear-gradient(145deg, rgba(5, 32, 43, .88), rgba(2, 16, 25, .92));
  border: 1px solid var(--color-border);
  border-radius: var(--panel-radius);
  box-shadow: inset 0 0 28px rgba(13, 162, 141, .035);
}
.tech-panel__body { min-height: 0; padding: 10px; }
</style>
