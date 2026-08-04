<template><div ref="chartElement" class="map-flow" aria-label="广东省零碳虚拟电厂调度地图"></div></template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import guangdong from '../assets/guangdong.json'

const props = defineProps({ intensity: { type: Number, default: 1 } })
const chartElement = ref(null)
let chart
let resizeObserver

echarts.registerMap('guangdong-zero-carbon', guangdong)

const cityPoints = [
  ['广州',113.27,23.13,196],['深圳',114.06,22.55,178],['珠海',113.58,22.27,96],
  ['佛山',113.12,23.02,147],['东莞',113.75,23.02,155],['惠州',114.42,23.11,124],
  ['河源',114.70,23.74,157],['韶关',113.60,24.81,108],['清远',113.06,23.68,118],
  ['湛江',110.36,21.27,132],['阳江',111.98,21.86,126],['汕头',116.68,23.35,114],
  ['梅州',116.12,24.29,88],['肇庆',112.47,23.05,105],['江门',113.08,22.58,111],
]
const center = cityPoints[0]
const stations = cityPoints.map(([name,lng,lat,value], index) => ({ name, value:[lng,lat,value], symbolSize:index===0?15:Math.max(5,Math.min(10,value/18)) }))
const routes = cityPoints.slice(1).map(([name,lng,lat]) => ({ name:`${name} → 广州`, coords:[[lng,lat],[center[1],center[2]]] }))
const warmPoints = cityPoints.flatMap(([name,lng,lat,value], index) => [
  { name, value:[lng,lat,value], symbolSize:Math.max(9,value/7) },
  { value:[lng+.09*((index%3)-1),lat+.07*((index%2)?1:-1),value*.6], symbolSize:Math.max(6,value/10) },
])

function geoLayer(offset, zlevel, top = false) {
  return {
    map:'guangdong-zero-carbon', roam:false, silent:!top, zlevel,
    layoutCenter:['50%',`${51+offset}%`], layoutSize:'91%', aspectScale:.92,
    itemStyle: top
      ? { areaColor:'rgba(25,62,88,.83)', borderColor:'#a8ddff', borderWidth:1.25, shadowBlur:22, shadowColor:'rgba(99,184,255,.48)' }
      : { areaColor:`rgba(9,37,70,${.78-offset*.07})`, borderColor:'rgba(61,134,205,.7)', borderWidth:1, shadowBlur:8, shadowColor:'#071b37' },
    emphasis:{ disabled:true },
    label: top ? { show:true, color:'rgba(202,232,244,.54)', fontSize:8 } : { show:false },
  }
}

function render() {
  if (!chartElement.value) return
  chart ??= echarts.init(chartElement.value)
  chart.setOption({
    backgroundColor:'transparent',
    tooltip:{ trigger:'item', className:'chart-tooltip', formatter:(p)=>p.value?.[2] ? `${p.name}<br/>实时调度功率：${Math.round(p.value[2])} MW` : p.name },
    geo:[geoLayer(0,5,true),geoLayer(1.4,4),geoLayer(2.7,3),geoLayer(4,2),geoLayer(5.3,1)],
    series:[
      { type:'effectScatter', coordinateSystem:'geo', geoIndex:0, zlevel:8, data:warmPoints, silent:true, rippleEffect:{ scale:5, brushType:'fill', period:3.5 }, symbol:'circle', itemStyle:{ color:'#ffbb53', opacity:.8, shadowBlur:22, shadowColor:'#ffc85d' } },
      { type:'lines', coordinateSystem:'geo', geoIndex:0, zlevel:9, data:routes, effect:{ show:true, period:Math.max(2.4,4/props.intensity), trailLength:.42, symbol:'circle', symbolSize:5, color:'#dcf8ff' }, lineStyle:{ color:'#b7ebff', width:1.6, opacity:.76, curveness:.25, shadowBlur:8, shadowColor:'#8de3ff' } },
      { type:'effectScatter', coordinateSystem:'geo', geoIndex:0, zlevel:10, data:stations, rippleEffect:{ scale:3, brushType:'stroke', period:2.8 }, itemStyle:{ color:'#72eaff', shadowBlur:18, shadowColor:'#8fefff' }, label:{ show:true, formatter:'{b}', position:'right', color:'#d9f7ff', fontSize:8, textShadowBlur:3, textShadowColor:'#00131f' } },
    ],
  }, true)
}

onMounted(() => { render(); resizeObserver=new ResizeObserver(()=>chart?.resize()); resizeObserver.observe(chartElement.value) })
watch(()=>props.intensity,render)
onBeforeUnmount(()=>{ resizeObserver?.disconnect(); chart?.dispose() })
</script>

<style scoped>
.map-flow { width:100%; height:100%; min-height:480px; background:radial-gradient(ellipse at 50% 54%,rgba(71,137,190,.2),transparent 46%),linear-gradient(180deg,rgba(3,13,22,.18),rgba(2,12,23,.58)),repeating-linear-gradient(0deg,rgba(86,217,255,.025) 0 1px,transparent 1px 34px),repeating-linear-gradient(90deg,rgba(86,217,255,.02) 0 1px,transparent 1px 34px); }
</style>
