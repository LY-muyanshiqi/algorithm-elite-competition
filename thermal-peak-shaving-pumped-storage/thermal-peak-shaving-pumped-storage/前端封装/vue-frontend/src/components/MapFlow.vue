<template><div ref="chartElement" class="map-flow" aria-label="广东省零碳虚拟电厂调度地图"></div></template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import shaanxi from '../assets/shaanxi.json'
import gansu from '../assets/gansu.json'
import qinghai from '../assets/qinghai.json'
import ningxia from '../assets/ningxia.json'
import xinjiang from '../assets/xinjiang.json'

const props = defineProps({ intensity: { type: Number, default: 1 } })
const chartElement = ref(null)
let chart
let resizeObserver

const northwestGeoJson = {
  type: 'FeatureCollection',
  features: [shaanxi, gansu, qinghai, ningxia, xinjiang].flatMap((item) => item.features),
}
echarts.registerMap('northwest-zero-carbon', northwestGeoJson)

const cityPoints = [
  ['西安调度中心',108.94,34.34,230],['榆林风光基地',109.73,38.29,196],['延安能源基地',109.49,36.59,154],
  ['宝鸡抽蓄电站',107.24,34.36,136],['兰州负荷中心',103.84,36.06,178],['酒泉新能源基地',98.49,39.73,208],
  ['西宁调度中心',101.78,36.62,142],['格尔木光伏基地',94.90,36.41,188],['银川负荷中心',106.23,38.49,152],
  ['中卫新能源基地',105.20,37.50,166],['乌鲁木齐中心',87.62,43.82,184],['哈密风电基地',93.51,42.82,214],
  ['克拉玛依能源站',84.89,45.58,126],['喀什储能节点',75.99,39.47,112],
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
    map:'northwest-zero-carbon', roam:false, silent:!top, zlevel,
    layoutCenter:['49%',`${50+offset}%`], layoutSize:'96%', aspectScale:.92,
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
.map-flow { width:100%; height:100%; min-height:480px; background:radial-gradient(ellipse at 49% 52%,rgba(71,137,190,.22),transparent 48%),linear-gradient(180deg,rgba(3,13,22,.18),rgba(2,12,23,.58)),repeating-linear-gradient(0deg,rgba(86,217,255,.025) 0 1px,transparent 1px 34px),repeating-linear-gradient(90deg,rgba(86,217,255,.02) 0 1px,transparent 1px 34px); }
</style>
