<template>
  <div class="risk-workspace">
    <template v-if="!store.currentSessionId">
      <el-empty description="请先创建会话" :image-size="120" />
    </template>
    <template v-else>
      <!-- 指标卡 -->
      <div class="metrics-grid">
        <el-card v-for="m in metrics" :key="m.label" class="metric-card" shadow="never">
          <div class="metric-label">{{ m.label }}</div>
          <div class="metric-value" :class="m.valueClass">{{ m.value }}</div>
          <div class="metric-sub" v-if="m.sub">{{ m.sub }}</div>
        </el-card>
      </div>

      <!-- 图表区 -->
      <div class="charts-grid">
        <el-card class="chart-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span class="card-title">Drawdown 曲线</span>
              <span class="card-sub">{{ equityCurve.length }} points</span>
            </div>
          </template>
          <v-chart :option="drawdownOption" autoresize class="chart" />
        </el-card>

        <el-card class="chart-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span class="card-title">风险雷达 Risk Radar</span>
              <span class="card-sub">5 dimensions</span>
            </div>
          </template>
          <v-chart :option="radarOption" autoresize class="chart" />
        </el-card>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, RadarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, RadarComponent } from 'echarts/components'
import { useTradingStore } from '@/stores/trading'
import { tradingApi, type RiskData, type EquityPoint } from '@/api/trading'

use([CanvasRenderer, LineChart, RadarChart, GridComponent, TooltipComponent, LegendComponent, RadarComponent])

const store = useTradingStore()

const risk = ref<RiskData | null>(null)
const equityCurve = ref<EquityPoint[]>([])

// ---- 格式化 ----
function formatPct(v: number | undefined | null): string {
  if (v == null) return '-'
  return (v * 100).toFixed(2) + '%'
}

// ---- 指标卡 ----
const metrics = computed(() => {
  const r = risk.value
  return [
    {
      label: 'VaR(95%)',
      value: formatPct(r?.var_95),
      sub: '95% 置信',
      valueClass: dangerClass(r?.var_95, 0.05),
    },
    {
      label: 'Max Drawdown',
      value: formatPct(r?.max_drawdown),
      sub: '历史最大回撤',
      valueClass: dangerClass(r?.max_drawdown, 0.15),
    },
    {
      label: 'Current Drawdown',
      value: formatPct(r?.current_drawdown),
      sub: '当前回撤',
      valueClass: dangerClass(r?.current_drawdown, 0.1),
    },
    {
      label: 'Turnover',
      value: formatPct(r?.turnover),
      sub: '换手率',
      valueClass: warningClass(r?.turnover, 0.5),
    },
    {
      label: 'Concentration',
      value: formatPct(r?.concentration),
      sub: '集中度',
      valueClass: warningClass(r?.concentration, 0.3),
    },
    {
      label: 'Exposure',
      value: formatPct(r?.exposure),
      sub: '风险敞口',
      valueClass: exposureClass(r?.exposure),
    },
  ]
})

function dangerClass(v: number | undefined | null, threshold: number): string {
  if (v == null) return ''
  if (Math.abs(v) > threshold) return 'text-danger'
  if (Math.abs(v) > threshold * 0.6) return 'text-warning'
  return 'text-success'
}
function warningClass(v: number | undefined | null, threshold: number): string {
  if (v == null) return ''
  if (v > threshold) return 'text-warning'
  if (v > threshold * 1.5) return 'text-danger'
  return 'text-success'
}
function exposureClass(v: number | undefined | null): string {
  if (v == null) return ''
  if (v > 1) return 'text-danger'
  if (v > 0.8) return 'text-warning'
  return 'text-success'
}

// ---- Drawdown 曲线 ----
const drawdownOption = computed(() => {
  const curve = equityCurve.value
  if (!curve.length) return {}
  const times = curve.map(p => p.time)
  const drawdowns = curve.map(p => (p.max_drawdown ?? 0) * 100)

  return {
    backgroundColor: 'transparent',
    animation: false,
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#161b22',
      borderColor: '#21262d',
      textStyle: { color: '#e6edf3', fontSize: 12, fontFamily: 'SF Mono, monospace' },
      formatter: (params: any) => {
        if (!params?.length) return ''
        const idx = params[0].dataIndex
        const point = curve[idx]
        let html = `<div style="font-weight:600;margin-bottom:4px">${point.time}</div>`
        html += `<span style="color:#f85149">●</span> Drawdown: ${params[0].value.toFixed(2)}%`
        return html
      },
    },
    grid: { left: 60, right: 20, top: 30, bottom: 40 },
    xAxis: {
      type: 'category',
      data: times,
      axisLine: { lineStyle: { color: '#21262d' } },
      axisLabel: { color: '#8b949e', fontSize: 10, fontFamily: 'SF Mono, monospace' },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisLabel: {
        color: '#8b949e',
        fontSize: 10,
        fontFamily: 'SF Mono, monospace',
        formatter: (v: number) => v.toFixed(1) + '%',
      },
      splitLine: { lineStyle: { color: '#21262d', type: 'dashed' } },
    },
    series: [
      {
        name: 'Drawdown',
        type: 'line',
        data: drawdowns,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#f85149', width: 1.5 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(248,81,73,0)' },
              { offset: 1, color: 'rgba(248,81,73,0.25)' },
            ],
          },
        },
      },
    ],
  }
})

// ---- 雷达图 ----
const radarOption = computed(() => {
  const r = risk.value
  if (!r) return {}

  // 将各指标归一化到 0-100，便于在雷达图上比较
  const drawdown = Math.min(Math.abs(r.current_drawdown ?? 0) * 1000, 100)
  const concentration = Math.min(Math.abs(r.concentration ?? 0) * 100, 100)
  const exposure = Math.min(Math.abs(r.exposure ?? 0) * 100, 100)
  const turnover = Math.min(Math.abs(r.turnover ?? 0) * 100, 100)
  const beta = Math.min(Math.abs(r.beta ?? 0) * 50, 100)

  return {
    backgroundColor: 'transparent',
    animation: false,
    tooltip: {
      backgroundColor: '#161b22',
      borderColor: '#21262d',
      textStyle: { color: '#e6edf3', fontSize: 12, fontFamily: 'SF Mono, monospace' },
    },
    radar: {
      indicator: [
        { name: 'Drawdown', max: 100 },
        { name: 'Concentration', max: 100 },
        { name: 'Exposure', max: 100 },
        { name: 'Turnover', max: 100 },
        { name: 'Beta', max: 100 },
      ],
      center: ['50%', '55%'],
      radius: '65%',
      axisName: {
        color: '#8b949e',
        fontSize: 11,
        fontFamily: 'SF Mono, monospace',
      },
      splitLine: { lineStyle: { color: '#21262d' } },
      splitArea: {
        areaStyle: {
          color: ['rgba(22,27,34,0.3)', 'rgba(22,27,34,0.6)'],
        },
      },
      axisLine: { lineStyle: { color: '#21262d' } },
    },
    series: [
      {
        name: 'Risk',
        type: 'radar',
        data: [
          {
            value: [drawdown, concentration, exposure, turnover, beta],
            name: 'Current Risk',
            areaStyle: { color: 'rgba(248,81,73,0.2)' },
            lineStyle: { color: '#f85149', width: 2 },
            itemStyle: { color: '#f85149' },
          },
        ],
      },
    ],
  }
})

// ---- 数据加载 ----
async function loadRisk() {
  if (!store.currentSessionId) return
  try {
    risk.value = await tradingApi.getRisk(store.currentSessionId)
  } catch (e) {
    console.error('loadRisk error', e)
  }
}

async function loadEquityCurve() {
  if (!store.currentSessionId) return
  try {
    const res = await tradingApi.getEquityCurve(store.currentSessionId)
    equityCurve.value = res.curve || []
  } catch (e) {
    console.error('loadEquityCurve error', e)
  }
}

async function loadAll() {
  await Promise.all([loadRisk(), loadEquityCurve()])
}

onMounted(() => {
  loadAll()
})
</script>

<style scoped>
.risk-workspace {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 12px;
  font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', 'JetBrains Mono', ui-monospace, monospace;
}

/* 指标卡 */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 12px;
  flex-shrink: 0;
}
.metric-card {
  background: var(--q-bg-secondary, #0d1117);
  border: 1px solid var(--q-border, #21262d);
  border-radius: 6px;
}
.metric-card :deep(.el-card__body) {
  padding: 14px 16px;
}
.metric-label {
  font-size: 11px;
  color: var(--q-text-muted, #8b949e);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}
.metric-value {
  font-size: 18px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--q-text-primary, #e6edf3);
}
.metric-sub {
  font-size: 11px;
  color: var(--q-text-muted, #8b949e);
  margin-top: 4px;
}

/* 图表网格 */
.charts-grid {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 12px;
  flex: 1;
  min-height: 0;
}
.chart-card {
  background: var(--q-bg-secondary, #0d1117);
  border: 1px solid var(--q-border, #21262d);
  border-radius: 6px;
  overflow: hidden;
}
.chart-card :deep(.el-card__header) {
  padding: 10px 14px;
  background: var(--q-bg-tertiary, #161b22);
  border-bottom: 1px solid var(--q-border, #21262d);
}
.chart-card :deep(.el-card__body) {
  padding: 12px;
  height: calc(100% - 42px);
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-title {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: var(--q-text-primary, #e6edf3);
}
.card-sub {
  font-size: 11px;
  color: var(--q-text-muted, #8b949e);
}
.chart {
  width: 100%;
  height: 100%;
  min-height: 320px;
}

/* 颜色 */
.text-success { color: #3fb950; }
.text-danger { color: #f85149; }
.text-warning { color: #d29922; }
.text-info { color: #58a6ff; }

/* 响应式 */
@media (max-width: 1400px) {
  .metrics-grid {
    grid-template-columns: repeat(3, 1fr);
  }
  .charts-grid {
    grid-template-columns: 1fr;
  }
}
</style>
