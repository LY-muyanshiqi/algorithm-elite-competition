<template><div class="loading-overlay"><i></i><span>{{ text }}</span></div></template>
<script setup>defineProps({ text: { type: String, default: '正在加载调度数据…' } })</script>
<style scoped>
.loading-overlay { position: absolute; inset: 0; z-index: 20; display: grid; place-content: center; gap: 12px; text-align: center; color: var(--color-muted); background: rgba(2, 13, 20, .78); backdrop-filter: blur(3px); }
.loading-overlay i { width: 38px; height: 38px; margin: auto; border: 2px solid rgba(20,241,190,.15); border-top-color: var(--color-accent); border-radius: 50%; animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
