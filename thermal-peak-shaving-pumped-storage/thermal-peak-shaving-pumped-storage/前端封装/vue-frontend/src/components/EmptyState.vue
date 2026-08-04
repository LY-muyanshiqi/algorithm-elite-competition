<template>
  <div class="empty-state"><span>◇</span><strong>{{ title }}</strong><p>{{ description }}</p><button v-if="action" type="button" @click="$emit('action')">{{ action }}</button></div>
</template>
<script setup>
defineProps({ title: { type: String, default: '暂无数据' }, description: { type: String, default: '请检查数据源后重试' }, action: { type: String, default: '' } })
defineEmits(['action'])
</script>
<style scoped>
.empty-state { min-height: 180px; display: grid; place-content: center; justify-items: center; color: var(--color-muted); text-align: center; }
.empty-state > span { color: var(--color-accent); font-size: 30px; }.empty-state strong { color: var(--color-text); }.empty-state p { margin: 6px 0 12px; font-size: 12px; }
.empty-state button { padding: 6px 14px; color: var(--color-accent); border: 1px solid var(--color-border-strong); background: transparent; cursor: pointer; }
</style>
