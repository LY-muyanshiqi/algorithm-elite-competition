<template>
  <div class="clock">
    <strong>{{ time }}</strong>
    <span>{{ date }}</span>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

const time = ref('00:00:00')
const date = ref('----/--/--')
let timer

function updateClock() {
  const now = new Date()
  time.value = now.toLocaleTimeString('zh-CN', { hour12: false })
  date.value = now.toLocaleDateString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit', weekday: 'short',
  })
}

onMounted(() => {
  updateClock()
  timer = window.setInterval(updateClock, 1000)
})
onBeforeUnmount(() => window.clearInterval(timer))
</script>

<style scoped>
.clock { text-align: right; line-height: 1.1; }
.clock strong { display: block; color: var(--color-accent); font: 700 20px/1 monospace; }
.clock span { display: block; margin-top: 5px; color: var(--color-muted); font-size: 10px; }
</style>
