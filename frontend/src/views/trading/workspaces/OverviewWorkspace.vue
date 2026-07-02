<template>
  <div class="overview-workspace">
    <template v-if="!store.currentSessionId">
      <el-empty description="请先创建会话" :image-size="120" />
    </template>
    <template v-else>
      <!-- 指标卡 2行3列 -->
      <div class="metrics-grid">
        <el-card v-for="m in metrics" :key="m.label" class="metric-card" shadow="never">
          <div class="metric-label">{{ m.label }}</div>
          <div class="metric-value" :class="m.valueClass">{{ m.value }}</div>
          <div class="metric-sub">{{ m.sub }}</div>
        </el-card>
      </div>

      <!-- 图表区：权益曲线 + PnL 构成 -->
      <div class="charts-grid">
        <el-card class="chart-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span class="card-title">权益曲线 Equity Curve</span>
              <div class="card-actions">
                <span class="card-sub">{{ equityCurve.length }} points</span>
                <el-button text size="small" :icon="Refresh" @click="refreshAll" :loading="loading">刷新</el-button>
              </div>
            </div>
          </template>
          <v-chart v-if="equityCurve.length" :option="equityOption" autoresize class="chart" />
          <el-empty v-else description="暂无权益曲线数据" :image-size="80" />
        </el-card>

        <el-card class="chart-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span class="card-title">今日 PnL 构成</span>
              <span class="card-sub">已实现 / 未实现</span>
            </div>
          </template>
          <v-chart v-if="hasPnlData" :option="pnlOption" autoresize class="chart" />
          <el-empty v-else description="暂无 PnL 数据" :image-size="80" />
        </el-card>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { useTradingStore } from '@/stores/trading'
import { tradingApi, type EquityPoint } from '@/api/trading'

use([CanvasRenderer, LineChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const store = useTradingStore()
const ov = computed(() => store.overview)
const loading = computed(() => store.loading)
const equityCurve = ref<EquityPoint[]>([])
let pollTimer: ReturnType<typeof setInterval> | null = null

// ---- 格式化 ----
function formatNum(v: number | undefined | null): string {
  if (v == null) return '-'
  return Number(v).toLocaleString('en-US', { maximumFractionDigits: 2 })
}
function formatPct(v: number | undefined | null): string {
  if (v == null) return '-'
  return (v * 100).toFixed(2) + '%'
}
function pnlClass(v: number | undefined | null): string {
  if (v == null || v === 0) return ''
  return v > 0 ? 'text-success' : 'text-danger'
}

// ---- 指标卡 ----
const metrics = computed(() => {
  const o = ov.value
  return [
    {
      label: "Today's Return",
      value: formatPct(o?.today_return),
      sub: '今日收益率',
      valueClass: pnlClass(o?.today_return),
    },
    {
      label: "Today's PnL",
      value: formatNum(o?.today_pnl),
      sub: '今日盈亏',
      valueClass: pnlClass(o?.today_pnl),
    },
    {
      label: 'Cash',
      value: formatNum(o?.cash),
      sub: '可用现金',
      valueClass: 'text-info',
    },
    {
      label: 'Exposure',
      value: formatPct(o?.exposure),
      sub: '风险敞口',
      valueClass: '',
    },
    {
      label: 'Sharpe',
      value: formatNum(o?.sharpe),
      sub: '夏普比率',
      valueClass: '',
    },
    {
      label: 'Max Drawdown',
      value: formatPct(o?.max_drawdown),
      sub: '最大回撤',
      valueClass: 'text-danger',
    },
  ]
})

// ---- PnL 构成判断 ----
const hasPnlData = computed(() => {
  const r = ov.value?.realized_pnl ?? 0
  const u = ov.value?.unrealized_pnl ?? 0
  return Math.abs(r) + Math.abs(u) > 0
})

// ---- 权益曲线 ----
const equityOption = computed(() => {
  const curve = equityCurve.value
  if (!curve.length) return {}
  const times = curve.map(p => p.time)
  const values = curve.map(p => p.total_value)

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
        html += `<span style="color:#58a6ff">●</span> Equity: ${Number(params[0].value).toLocaleString('en-US', { maximumFractionDigits: 2 })}`
        if (point.daily_return != null) {
          html += `<br/><span style="color:#8b949e">Return:</span> ${(point.daily_return * 100).toFixed(2)}%`
        }
        return html
      },
    },
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'category',
      data: times,
      boundaryGap: false,
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
        data: values,
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
    ],
  }
})

// ---- PnL 构成饼图 ----
const pnlOption = computed(() => {
  const r = ov.value?.realized_pnl ?? 0
  const u = ov.value?.unrealized_pnl ?? 0
  return {
    backgroundColor: 'transparent',
    animation: false,
    tooltip: {
      trigger: 'item',
      backgroundColor: '#161b22',
      borderColor: '#21262d',
      textStyle: { color: '#e6edf3', fontSize: 12, fontFamily: 'SF Mono, monospace' },
      formatter: (p: any) => {
        const real = p.data.realValue
        const sign = real >= 0 ? '+' : ''
        return `${p.name}<br/>实际值: ${sign}${formatNum(real)}<br/>占比: ${p.percent}%`
      },
    },
    legend: {
      bottom: 0,
      textStyle: { color: '#8b949e', fontSize: 11, fontFamily: 'SF Mono, monospace' },
      data: ['已实现 Realized', '未实现 Unrealized'],
    },
    series: [
      {
        name: 'PnL',
        type: 'pie',
        radius: ['45%', '70%'],
        center: ['50%', '45%'],
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
        data: [
          { name: '已实现 Realized', value: Math.abs(r), realValue: r, itemStyle: { color: '#58a6ff' } },
          { name: '未实现 Unrealized', value: Math.abs(u), realValue: u, itemStyle: { color: '#3fb950' } },
        ],
      },
    ],
  }
})

// ---- 数据加载 ----
async function loadEquityCurve() {
  if (!store.currentSessionId) return
  try {
    const res = await tradingApi.getEquityCurve(store.currentSessionId)
    equityCurve.value = res.curve || []
  } catch (e) {
    console.error('loadEquityCurve error', e)
  }
}

async function refreshAll() {
  await Promise.all([store.fetchOverview(), loadEquityCurve()])
}

onMounted(() => {
  refreshAll()
  // 每 5 秒刷新 overview
  pollTimer = setInterval(() => {
    if (store.currentSessionId) store.fetchOverview()
  }, 5000)
})

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
</script>

<style scoped>
.overview-workspace {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 12px;
  font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', 'JetBrains Mono', ui-monospace, monospace;
}

/* 指标卡 */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
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
  font-size: 22px;
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
  grid-template-columns: 1.6fr 1fr;
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
.card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.chart {
  width: 100%;
  height: 100%;
  min-height: 300px;
}

/* 颜色 */
.text-success { color: #3fb950; }
.text-danger { color: #f85149; }
.text-warning { color: #d29922; }
.text-info { color: #58a6ff; }

/* 响应式 */
@media (max-width: 1200px) {
  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .charts-grid {
    grid-template-columns: 1fr;
  }
}
</style>
