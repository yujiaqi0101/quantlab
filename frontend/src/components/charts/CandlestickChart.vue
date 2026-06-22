<template>
  <div class="chart-container">
    <v-chart :option="chartOption" autoresize class="chart" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CandlestickChart as EchartsCandlestick, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, DataZoomComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { PreviewData } from '@/api/dataset'

use([EchartsCandlestick, BarChart, GridComponent, TooltipComponent, DataZoomComponent, CanvasRenderer])

const props = defineProps<{
  preview: PreviewData
  activeSymbol?: string
}>()

const chartOption = computed(() => {
  if (!props.preview?.symbols?.length) return {}

  const sym = props.activeSymbol && props.preview.preview[props.activeSymbol]
    ? props.activeSymbol
    : props.preview.symbols[0]
  const symData = props.preview.preview[sym]
  if (!symData) return {}

  const dates = symData.index
  const rows = symData.rows

  // Find OHLCV column indices
  const cols = symData.columns
  const oi = cols.indexOf('open')
  const hi = cols.indexOf('high')
  const li = cols.indexOf('low')
  const ci = cols.indexOf('close')
  const vi = cols.indexOf('volume')

  if (oi < 0 || hi < 0 || li < 0 || ci < 0) return {}

  const ohlcData = rows.map((r: any[]) => [r[oi], r[ci], r[li], r[hi]])
  const volumes = vi >= 0 ? rows.map((r: any[]) => r[vi]) : []

  return {
    backgroundColor: 'transparent',
    animation: false,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      backgroundColor: '#161b22',
      borderColor: '#1b2332',
      textStyle: { color: '#e6edf3', fontSize: 12, fontFamily: 'SF Mono, Cascadia Code, monospace' },
      formatter: (params: any) => {
        const d = params[0]
        if (!d) return ''
        const idx = d.dataIndex
        const row = rows[idx]
        if (!row) return ''
        const date = dates[idx]
        let html = `<div style="font-weight:600;margin-bottom:4px">${date}</div>`
        html += `O: ${row[oi]?.toFixed(2)}  H: ${row[hi]?.toFixed(2)}<br/>`
        html += `L: ${row[li]?.toFixed(2)}  C: ${row[ci]?.toFixed(2)}`
        if (vi >= 0 && row[vi]) html += `<br/>Vol: ${row[vi]?.toLocaleString()}`
        return html
      },
    },
    grid: [
      { left: 60, right: 20, top: 10, bottom: vi >= 0 ? 120 : 60 },
      ...(vi >= 0 ? [{ left: 60, right: 20, top: '72%', bottom: 60 }] : []),
    ],
    xAxis: [
      {
        type: 'category',
        data: dates,
        axisLine: { lineStyle: { color: '#1b2332' } },
        axisLabel: { color: '#484f58', fontSize: 10, fontFamily: 'SF Mono, Cascadia Code, monospace' },
        splitLine: { show: false },
        gridIndex: 0,
      },
      ...(vi >= 0 ? [{
        type: 'category',
        data: dates,
        gridIndex: 1,
        axisLine: { lineStyle: { color: '#1b2332' } },
        axisLabel: { show: false },
        splitLine: { show: false },
      }] : []),
    ],
    yAxis: [
      {
        type: 'value',
        scale: true,
        axisLine: { show: false },
        axisLabel: { color: '#484f58', fontSize: 10, fontFamily: 'SF Mono, Cascadia Code, monospace' },
        splitLine: { lineStyle: { color: '#1b2332', type: 'dashed' } },
        gridIndex: 0,
      },
      ...(vi >= 0 ? [{
        type: 'value',
        scale: true,
        gridIndex: 1,
        axisLine: { show: false },
        axisLabel: { show: false },
        splitLine: { show: false },
      }] : []),
    ],
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: [0],
        start: 0,
        end: 100,
      },
      {
        type: 'slider',
        xAxisIndex: [0],
        bottom: 10,
        height: 20,
        borderColor: '#1b2332',
        fillerColor: 'rgba(88,166,255,0.1)',
        handleStyle: { color: '#58a6ff' },
        textStyle: { color: '#484f58', fontSize: 10 },
        dataBackground: {
          lineStyle: { color: '#1b2332' },
          areaStyle: { color: '#161b22' },
        },
      },
    ],
    series: [
      {
        name: sym,
        type: 'candlestick',
        data: ohlcData,
        xAxisIndex: 0,
        yAxisIndex: 0,
        itemStyle: {
          color: '#3fb950',
          color0: '#f85149',
          borderColor: '#3fb950',
          borderColor0: '#f85149',
        },
      },
      ...(vi >= 0 ? [{
        name: 'Volume',
        type: 'bar',
        data: volumes.map((v: number, i: number) => ({
          value: v,
          itemStyle: {
            color: rows[i][ci] >= rows[i][oi] ? 'rgba(63,185,80,0.3)' : 'rgba(248,81,73,0.3)',
          },
        })),
        xAxisIndex: 1,
        yAxisIndex: 1,
      }] : []),
    ],
  }
})
</script>

<style scoped>
.chart-container {
  background: #0d1117;
  border: 1px solid #1b2332;
  border-radius: 8px;
  padding: 12px;
}

.chart {
  width: 100%;
  height: 400px;
}
</style>
