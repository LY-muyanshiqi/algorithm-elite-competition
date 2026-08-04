<template>
  <span class="status-indicator" :class="`status-indicator--${status}`">
    <i aria-hidden="true"></i>
    <span>{{ label }}</span>
  </span>
</template>

<script setup>
defineProps({
  status: { type: String, default: 'online' },
  label: { type: String, required: true },
})
</script>

<style scoped>
.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--color-muted);
  font-size: 12px;
  white-space: nowrap;
}

.status-indicator i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 12px currentColor;
}

.status-indicator--online { color: var(--color-accent); }
.status-indicator--offline { color: var(--color-danger); }
.status-indicator--warning { color: var(--color-warning); }
</style>
