<template>
  <div class="portfolio-workspace">
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
              <span class="card-title">持仓权重 Allocation</span>
              <span class="card-sub">{{ portfolio?.n_positions ?? 0 }} positions</span>
            </div>
          </template>
          <v-chart :option="pieOption" autoresize class="chart" />
        </el-card>

        <el-card class="chart-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span class="card-title">净值曲线 Equity Curve</span>
              <span class="card-sub">{{ equityCurve.length }} points</span>
            </div>
          </template>
          <v-chart :option="equityOption" autoresize class="chart" />
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
import { LineChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { useTradingStore } from '@/stores/trading'
import { tradingApi, type PortfolioData, type EquityPoint } from '@/api/trading'

use([CanvasRenderer, LineChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const store = useTradingStore()

const portfolio = ref<PortfolioData | null>(null)
const equityCurve = ref<EquityPoint[]>([])

// ---- 格式化 ----
function formatNum(v: number | undefined | null): string {
  if (v == null) return '-'
  return Number(v).toLocaleString('en-US', { maximumFractionDigits: 2 })
}
function formatPct(v: number | undefined | null): string {
  if (v == null) return '-'
  return (v * 100).toFixed(2) + '%'
}

// ---- 指标卡 ----
const metrics = computed(() => {
  const p = portfolio.value
  return [
    {
      label: 'Total Equity',
      value: formatNum(p?.total_equity),
      sub: '总权益',
      valueClass: '',
    },
    {
      label: 'Cash',
      value: formatNum(p?.cash),
      sub: '可用现金',
      valueClass: 'text-info',
    },
    {
      label: 'Invested',
      value: formatNum(p?.invested),
      sub: '已投资',
      valueClass: 'text-info',
    },
    {
      label: 'Exposure',
      value: formatPct(p?.exposure),
      sub: '风险敞口',
      valueClass: exposureClass(p?.exposure),
    },
    {
      label: 'Leverage',
      value: formatPct(p?.leverage),
      sub: '杠杆',
      valueClass: leverageClass(p?.leverage),
    },
  ]
})

function exposureClass(v: number | undefined | null): string {
  if (v == null) return ''
  if (v > 1) return 'text-danger'
  if (v > 0.8) return 'text-warning'
  return 'text-success'
}
function leverageClass(v: number | undefined | null): string {
  if (v == null) return ''
  if (v > 2) return 'text-danger'
  if (v > 1) return 'text-warning'
  return 'text-success'
}

// ---- 饼图 ----
const pieOption = computed(() => {
  const weights = portfolio.value?.weights || []
  const data = weights.map(w => ({
    name: w.symbol,
    value: Number(w.weight.toFixed(4)),
  }))
  return {
    backgroundColor: 'transparent',
    animation: false,
    tooltip: {
      trigger: 'item',
      backgroundColor: '#161b22',
      borderColor: '#21262d',
      textStyle: { color: '#e6edf3', fontSize: 12, fontFamily: 'SF Mono, monospace' },
      formatter: (p: any) => {
        const mv = weights[p.dataIndex]?.market_value
        return `${p.name}<br/>权重: ${p.percent}%<br/>市值: ${formatNum(mv)}`
      },
    },
    legend: {
      type: 'scroll',
      orient: 'vertical',
      right: 10,
      top: 'center',
      textStyle: { color: '#8b949e', fontSize: 11, fontFamily: 'SF Mono, monospace' },
      pageTextStyle: { color: '#8b949e' },
    },
    series: [
      {
        name: 'Weights',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['40%', '50%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderColor: '#0d1117',
          borderWidth: 2,
        },
        label: {
          show: true,
          formatter: '{b}\n{d}%',
          color: '#e6edf3',
          fontSize: 10,
          fontFamily: 'SF Mono, monospace',
        },
        labelLine: { lineStyle: { color: '#8b949e' } },
        data,
        color: ['#58a6ff', '#3fb950', '#d29922', '#f85149', '#a371f7', '#ff7b72', '#7ee787', '#ffa657'],
      },
    ],
  }
})

// ---- 净值曲线 ----
const equityOption = computed(() => {
  const curve = equityCurve.value
  if (!curve.length) return {}
  const times = curve.map(p => p.time)
  const equity = curve.map(p => p.total_value)
  const cash = curve.map(p => p.cash)

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
        for (const p of params) {
          const color = p.seriesName === 'Equity' ? '#58a6ff' : '#3fb950'
          const val = p.value.toLocaleString('en-US', { maximumFractionDigits: 2 })
          html += `<span style="color:${color}">●</span> ${p.seriesName}: ${val}<br/>`
        }
        if (point.daily_return != null) {
          html += `Return: ${(point.daily_return * 100).toFixed(2)}%`
        }
        return html
      },
    },
    legend: {
      data: ['Equity', 'Cash'],
      textStyle: { color: '#8b949e', fontSize: 11 },
      top: 4,
      right: 20,
    },
    grid: { left: 60, right: 20, top: 40, bottom: 40 },
    xAxis: {
      type: 'category',
      data: times,
      axisLine: { lineStyle: { color: '#21262d' } },
      axisLabel: { color: '#8b949e', fontSize: 10, fontFamily: 'SF Mono, monospace' },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      scale: true,
      axisLine: { show: false },
      axisLabel: {
        color: '#8b949e',
        fontSize: 10,
        fontFamily: 'SF Mono, monospace',
        formatter: (v: number) => {
          if (Math.abs(v) >= 1_000_000) return (v / 1_000_000).toFixed(1) + 'M'
          if (Math.abs(v) >= 1_000) return (v / 1_000).toFixed(0) + 'K'
          return String(v)
        },
      },
      splitLine: { lineStyle: { color: '#21262d', type: 'dashed' } },
    },
    series: [
      {
        name: 'Equity',
        type: 'line',
        data: equity,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#58a6ff', width: 1.5 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(88,166,255,0.2)' },
              { offset: 1, color: 'rgba(88,166,255,0)' },
            ],
          },
        },
      },
      {
        name: 'Cash',
        type: 'line',
        data: cash,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#3fb950', width: 1, type: 'dashed' },
      },
    ],
  }
})

// ---- 数据加载 ----
async function loadPortfolio() {
  if (!store.currentSessionId) return
  try {
    portfolio.value = await tradingApi.getPortfolio(store.currentSessionId)
  } catch (e) {
    console.error('loadPortfolio error', e)
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
  await Promise.all([loadPortfolio(), loadEquityCurve()])
}

onMounted(() => {
  loadAll()
})
</script>

<style scoped>
.portfolio-workspace {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 12px;
  font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', 'JetBrains Mono', ui-monospace, monospace;
}

/* 指标卡 */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
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
  font-size: 20px;
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
  grid-template-columns: 1fr 1.4fr;
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
@media (max-width: 1200px) {
  .metrics-grid {
    grid-template-columns: repeat(3, 1fr);
  }
  .charts-grid {
    grid-template-columns: 1fr;
  }
}
</style>
