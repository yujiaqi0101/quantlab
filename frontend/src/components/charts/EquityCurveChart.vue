<template>
  <div class="chart-container">
    <v-chart :option="chartOption" autoresize class="chart" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([LineChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, CanvasRenderer])

import type { EquityData } from '@/api/experiment'

const props = defineProps<{
  equity: EquityData
  showDrawdown?: boolean
}>()

const chartOption = computed(() => {
  if (!props.equity?.equity?.length) return {}

  const timestamps = props.equity.timestamps
  const equity = props.equity.equity
  const initial = equity[0] || 100000

  // Compute drawdown
  const drawdown: number[] = []
  let peak = equity[0]
  for (const v of equity) {
    if (v > peak) peak = v
    drawdown.push(((v - peak) / peak) * 100)
  }

  const series: any[] = [
    {
      name: 'Equity',
      type: 'line',
      data: equity,
      xAxisIndex: 0,
      yAxisIndex: 0,
      smooth: true,
      symbol: 'none',
      lineStyle: { color: '#58a6ff', width: 1.5 },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(88,166,255,0.15)' },
            { offset: 1, color: 'rgba(88,166,255,0)' },
          ],
        },
      },
    },
  ]

  const yAxis: any[] = [
    {
      type: 'value',
      scale: true,
      axisLine: { show: false },
      axisLabel: {
        color: '#484f58',
        fontSize: 10,
        fontFamily: 'SF Mono, Cascadia Code, monospace',
        formatter: (v: number) => {
          if (v >= 1_000_000) return (v / 1_000_000).toFixed(1) + 'M'
          if (v >= 1_000) return (v / 1_000).toFixed(0) + 'K'
          return String(v)
        },
      },
      splitLine: { lineStyle: { color: '#1b2332', type: 'dashed' } },
      gridIndex: 0,
    },
  ]

  const grid: any[] = [
    { left: 70, right: 20, top: 30, bottom: props.showDrawdown ? 120 : 60 },
  ]

  if (props.showDrawdown) {
    series.push({
      name: 'Drawdown',
      type: 'line',
      data: drawdown,
      xAxisIndex: 1,
      yAxisIndex: 1,
      smooth: true,
      symbol: 'none',
      lineStyle: { color: '#f85149', width: 1 },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(248,81,73,0)' },
            { offset: 1, color: 'rgba(248,81,73,0.15)' },
          ],
        },
      },
    })
    yAxis.push({
      type: 'value',
      scale: true,
      gridIndex: 1,
      axisLine: { show: false },
      axisLabel: {
        color: '#484f58',
        fontSize: 10,
        fontFamily: 'SF Mono, Cascadia Code, monospace',
        formatter: (v: number) => v.toFixed(0) + '%',
      },
      splitLine: { show: false },
    })
    grid.push({ left: 70, right: 20, top: '72%', bottom: 60 })
  }

  return {
    backgroundColor: 'transparent',
    animation: false,
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#161b22',
      borderColor: '#1b2332',
      textStyle: { color: '#e6edf3', fontSize: 12, fontFamily: 'SF Mono, Cascadia Code, monospace' },
      formatter: (params: any) => {
        if (!params?.length) return ''
        const idx = params[0].dataIndex
        const date = timestamps[idx]
        let html = `<div style="font-weight:600;margin-bottom:4px">${date}</div>`
        for (const p of params) {
          const color = p.seriesName === 'Drawdown' ? '#f85149' : '#58a6ff'
          const val = p.seriesName === 'Drawdown'
            ? p.value.toFixed(2) + '%'
            : p.value.toLocaleString(undefined, { maximumFractionDigits: 0 })
          html += `<span style="color:${color}">●</span> ${p.seriesName}: ${val}<br/>`
        }
        return html
      },
    },
    legend: {
      show: props.showDrawdown,
      data: ['Equity', 'Drawdown'],
      textStyle: { color: '#8b949e', fontSize: 11 },
      top: 4,
      right: 20,
    },
    grid,
    xAxis: [
      {
        type: 'category',
        data: timestamps,
        axisLine: { lineStyle: { color: '#1b2332' } },
        axisLabel: { color: '#484f58', fontSize: 10, fontFamily: 'SF Mono, Cascadia Code, monospace' },
        splitLine: { show: false },
        gridIndex: 0,
      },
      ...(props.showDrawdown ? [{
        type: 'category',
        data: timestamps,
        gridIndex: 1,
        axisLine: { lineStyle: { color: '#1b2332' } },
        axisLabel: { show: false },
        splitLine: { show: false },
      }] : []),
    ],
    yAxis,
    dataZoom: [
      { type: 'inside', xAxisIndex: [0], start: 0, end: 100 },
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
    series,
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
  height: 380px;
}
</style>
