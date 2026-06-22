<template>
  <div class="detail-container">
    <!-- Back -->
    <div class="detail-back" @click="router.push('/experiments')">
      <el-icon :size="14"><ArrowLeft /></el-icon>
      <span>返回实验 Back to Experiments</span>
    </div>

    <!-- Loading -->
    <div v-if="store.loading && !exp" class="loading-state">
      <el-icon class="is-loading" :size="24"><Loading /></el-icon>
      <span>加载实验中 Loading experiment...</span>
    </div>

    <!-- Error -->
    <div v-else-if="store.error" class="error-state">
      <el-icon :size="24" color="#f85149"><CircleCloseFilled /></el-icon>
      <p>{{ store.error }}</p>
    </div>

    <!-- Content -->
    <template v-else-if="exp">
      <!-- Header -->
      <div class="detail-header">
        <div>
          <h1 class="detail-title">{{ exp.name || exp.id }}</h1>
          <p class="detail-sub">
            <span class="detail-id">{{ exp.id }}</span>
            <span class="detail-sep">|</span>
            <span class="detail-strategy">{{ exp.strategy }}</span>
            <span v-if="exp.dataset_id" class="detail-sep">|</span>
            <span v-if="exp.dataset_id" class="detail-dataset">{{ exp.dataset_id }}</span>
          </p>
        </div>
        <div class="detail-meta">
          <span class="detail-date">{{ formatDate(exp.created_at) }}</span>
          <el-tag v-if="exp.tag" effect="dark" class="source-tag">{{ exp.tag }}</el-tag>
          <el-tag
            v-if="exp.status && exp.status !== 'normal'"
            :type="statusTagType(exp.status)"
            effect="dark"
            size="small"
          >{{ exp.status }}</el-tag>
        </div>
      </div>

      <!-- Tabs -->
      <el-tabs v-model="activeTab" class="detail-tabs">
        <!-- ==================== Tab 1: Overview ==================== -->
        <el-tab-pane label="概览 Overview" name="overview">
          <div class="metrics-grid">
            <div class="metric-cell" v-for="m in overviewCards" :key="m.key">
              <span class="metric-label">{{ m.label }}</span>
              <span class="metric-value" :class="m.tone">{{ m.value }}</span>
              <span v-if="m.hint" class="metric-hint">{{ m.hint }}</span>
            </div>
          </div>

          <!-- Parameters -->
          <div v-if="exp.params && Object.keys(exp.params).length > 0" class="section-block">
            <div class="section-title">参数 Parameters</div>
            <div class="params-grid">
              <div v-for="(val, key) in exp.params" :key="key" class="param-row">
                <span class="param-key">{{ key }}</span>
                <span class="param-val">{{ JSON.stringify(val) }}</span>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- ==================== Tab 2: Performance ==================== -->
        <el-tab-pane label="绩效 Performance" name="performance">
          <!-- Equity + Drawdown -->
          <div class="section-block">
            <div class="section-title">资金曲线与回撤 Equity Curve & Drawdown</div>
            <div class="chart-box">
              <v-chart :option="equityDrawdownOption" autoresize class="chart" />
            </div>
          </div>

          <!-- Monthly Returns Heatmap -->
          <div class="section-block" v-if="hasMonthly">
            <div class="section-title">Monthly Returns (%)</div>
            <div class="chart-box chart-sm">
              <v-chart :option="monthlyHeatmapOption" autoresize class="chart" />
            </div>
          </div>

          <!-- Annual Returns -->
          <div class="section-block" v-if="hasAnnual">
            <div class="section-title">Annual Returns (%)</div>
            <div class="chart-box chart-xs">
              <v-chart :option="annualBarOption" autoresize class="chart" />
            </div>
          </div>
        </el-tab-pane>

        <!-- ==================== Tab 3: Trades ==================== -->
        <el-tab-pane label="Trades" name="trades">
          <!-- Trade Table -->
          <div class="section-block">
            <div class="section-title">Trade Records <span class="section-sub">{{ store.trades.length }} trades</span></div>
            <TradesWidget :trades="store.trades" />
          </div>

          <!-- PnL Distribution -->
          <div class="section-block" v-if="hasPnlDist">
            <div class="section-title">PnL Distribution</div>
            <div class="chart-box chart-sm">
              <v-chart :option="pnlDistOption" autoresize class="chart" />
            </div>
          </div>

          <!-- Holding Stats -->
          <div class="section-block" v-if="hasHolding">
            <div class="section-title">Holding Time</div>
            <div class="holding-grid">
              <div class="holding-cell" v-for="h in holdingCards" :key="h.label">
                <span class="holding-val">{{ h.value }}</span>
                <span class="holding-label">{{ h.label }}</span>
              </div>
            </div>
          </div>

          <!-- Top Winners / Losers -->
          <div class="top-grid" v-if="hasTopTrades">
            <div class="section-block">
              <div class="section-title">Top Winners</div>
              <div class="top-list">
                <div v-for="(t, i) in topWinners" :key="'w'+i" class="top-row positive">
                  <span class="top-rank">{{ i + 1 }}</span>
                  <span class="top-symbol">{{ t.symbol }}</span>
                  <span class="top-pnl">+{{ formatPrice(t.pnl) }}</span>
                </div>
              </div>
            </div>
            <div class="section-block">
              <div class="section-title">Top Losers</div>
              <div class="top-list">
                <div v-for="(t, i) in topLosers" :key="'l'+i" class="top-row negative">
                  <span class="top-rank">{{ i + 1 }}</span>
                  <span class="top-symbol">{{ t.symbol }}</span>
                  <span class="top-pnl">{{ formatPrice(t.pnl) }}</span>
                </div>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- ==================== Tab 4: Risk ==================== -->
        <el-tab-pane label="Risk" name="risk">
          <!-- Rolling Sharpe -->
          <div class="section-block" v-if="hasRolling">
            <div class="section-title">Rolling Sharpe (60d)</div>
            <div class="chart-box chart-sm">
              <v-chart :option="rollingSharpeOption" autoresize class="chart" />
            </div>
          </div>

          <!-- Rolling Drawdown -->
          <div class="section-block" v-if="hasRolling">
            <div class="section-title">Rolling Max Drawdown (60d)</div>
            <div class="chart-box chart-sm">
              <v-chart :option="rollingDDOption" autoresize class="chart" />
            </div>
          </div>

          <!-- Rolling Volatility -->
          <div class="section-block" v-if="hasRolling">
            <div class="section-title">Rolling Volatility (60d)</div>
            <div class="chart-box chart-sm">
              <v-chart :option="rollingVolOption" autoresize class="chart" />
            </div>
          </div>

          <div v-if="!hasRolling" class="empty-state">
            <p>Not enough data for rolling analysis (need 60+ bars)</p>
          </div>
        </el-tab-pane>

        <!-- ==================== Tab 5: Journal ==================== -->
        <el-tab-pane label="Journal" name="journal">
          <!-- Status Pipeline -->
          <div class="section-block">
            <div class="section-title">Candidate Pipeline</div>
            <div class="pipeline-bar">
              <div
                v-for="s in pipelineStages"
                :key="s.key"
                class="pipeline-stage"
                :class="{ active: currentStatus === s.key, passed: pipelineIndex(s.key) < pipelineIndex(currentStatus) }"
                @click="changeStatus(s.key)"
              >
                <span class="pipeline-dot"></span>
                <span class="pipeline-label">{{ s.label }}</span>
              </div>
            </div>
          </div>

          <!-- Bookmark -->
          <div class="section-block">
            <div class="section-title">Bookmark</div>
            <div class="bookmark-row">
              <span
                class="bookmark-star"
                :class="{ active: exp.favorite === 1 }"
                @click="toggleFav"
              >{{ exp.favorite === 1 ? '★' : '☆' }}</span>
              <span class="bookmark-text">{{ exp.favorite === 1 ? 'Bookmarked' : 'Not bookmarked' }}</span>
            </div>
          </div>

          <!-- Research Note -->
          <div class="section-block">
            <div class="section-title">Research Notes</div>
            <el-input
              v-model="noteText"
              type="textarea"
              :rows="6"
              placeholder="Record your findings, hypotheses, and observations..."
              resize="vertical"
              class="note-input"
            />
            <div class="note-actions">
              <el-button type="primary" size="small" @click="saveNote" :disabled="noteText === exp.note">Save Note</el-button>
              <span v-if="noteSaved" class="note-saved">Saved</span>
            </div>
          </div>

          <!-- Tags -->
          <div class="section-block">
            <div class="section-title">Tags</div>
            <div class="tags-row">
              <el-tag
                v-for="t in currentTags"
                :key="t"
                closable
                effect="dark"
                size="small"
                class="journal-tag"
                @close="removeTag(t)"
              >{{ t }}</el-tag>
              <el-input
                v-if="tagInputVisible"
                ref="tagInputRef"
                v-model="tagInputVal"
                size="small"
                class="tag-input"
                @keyup.enter="addTag"
                @blur="addTag"
              />
              <el-button v-else size="small" @click="showTagInput">+ Tag</el-button>
            </div>
          </div>

          <!-- Lineage (Family Tree) -->
          <div class="section-block">
            <div class="section-title">Experiment Lineage</div>
            <div class="lineage-section">
              <!-- Set Parent -->
              <div class="lineage-setter">
                <span class="lineage-label">Parent:</span>
                <span v-if="exp.parent_id" class="lineage-parent" @click="router.push(`/experiments/${exp.parent_id}`)">{{ exp.parent_id }}</span>
                <span v-else class="lineage-none">None</span>
                <el-input
                  v-model="parentIdInput"
                  size="small"
                  placeholder="Set parent experiment ID"
                  class="parent-input"
                  @keyup.enter="setParent"
                >
                  <template #append>
                    <el-button @click="setParent" :disabled="!parentIdInput">Set</el-button>
                  </template>
                </el-input>
              </div>
              <!-- Family Tree -->
              <div v-if="store.lineage?.family" class="family-tree">
                <LineageTreeNode :node="store.lineage.family" :current-id="exp.id" @navigate="router.push(`/experiments/${$event}`)" />
              </div>
              <div v-else class="lineage-empty">No lineage data. Set a parent experiment to build the family tree.</div>
            </div>
          </div>

          <!-- Activity Log -->
          <div class="section-block" v-if="store.activity.length > 0">
            <div class="section-title">Activity Log</div>
            <div class="activity-list">
              <div v-for="act in store.activity" :key="act.id" class="activity-item">
                <span class="activity-action">{{ act.action }}</span>
                <span v-if="act.detail" class="activity-detail">{{ act.detail }}</span>
                <span class="activity-time">{{ formatDateTime(act.created_at) }}</span>
              </div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useExperimentStore } from '@/stores/experiment'
import { addExperimentTag, removeExperimentTag } from '@/api/experiment'
import { ArrowLeft, Loading, CircleCloseFilled } from '@element-plus/icons-vue'
import TradesWidget from '@/widgets/trades/TradesWidget.vue'
import LineageTreeNode from './LineageTreeNode.vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import {
  LineChart, BarChart, HeatmapChart,
} from 'echarts/charts'
import {
  GridComponent, TooltipComponent, LegendComponent,
  DataZoomComponent, VisualMapComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { buildBaseOption, COLORS } from '@/charts/baseOption'

use([LineChart, BarChart, HeatmapChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, VisualMapComponent, CanvasRenderer])

const route = useRoute()
const router = useRouter()
const store = useExperimentStore()
const activeTab = ref('overview')

const exp = computed(() => store.current)
const an = computed(() => store.analytics)

function formatDate(dt: string): string {
  if (!dt) return '-'
  return dt.split('T')[0]
}

function formatPrice(v?: number): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '-'
  return v.toFixed(2)
}

function statusTagType(s: string): string {
  if (s === 'candidate') return 'warning'
  if (s === 'production') return 'success'
  return 'info'
}

// ==================== Overview ====================
function fmtPct(v?: number): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '-'
  const sign = v >= 0 ? '+' : ''
  return `${sign}${v.toFixed(2)}%`
}

function fmtNum(v?: number, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '-'
  return v.toFixed(digits)
}

const overviewCards = computed(() => {
  const m: any = exp.value || {}
  const em: any = an.value?.extended_metrics || {}
  return [
    { key: 'return', label: 'Total Return', value: fmtPct(m.total_return), tone: (m.total_return ?? 0) >= 0 ? 'positive' : 'negative', hint: '' },
    { key: 'sharpe', label: 'Sharpe', value: fmtNum(m.sharpe, 3), tone: (m.sharpe ?? 0) >= 1 ? 'positive' : '', hint: '' },
    { key: 'sortino', label: 'Sortino', value: fmtNum(em.sortino, 3), tone: '', hint: '' },
    { key: 'calmar', label: 'Calmar', value: fmtNum(em.calmar, 3), tone: '', hint: '' },
    { key: 'winrate', label: 'Win Rate', value: fmtPct(m.win_rate), tone: '', hint: '' },
    { key: 'pf', label: 'Profit Factor', value: fmtNum(em.profit_factor ?? m.profit_factor, 2), tone: '', hint: '' },
    { key: 'maxdd', label: 'Max Drawdown', value: fmtPct(m.max_drawdown), tone: 'negative', hint: '' },
    { key: 'vol', label: 'Volatility', value: em.volatility ? fmtPct(em.volatility) : '-', tone: '', hint: '' },
  ]
})

// ==================== Performance ====================
const hasMonthly = computed(() => an.value?.monthly_returns && Object.keys(an.value.monthly_returns).length > 0)
const hasAnnual = computed(() => an.value?.annual_returns && Object.keys(an.value.annual_returns).length > 0)

const equityDrawdownOption = computed(() => {
  const eq = store.equity
  if (!eq?.equity?.length) return {}
  const equity = eq.equity
  const timestamps = eq.timestamps
  const dd = an.value?.drawdown_curve || []

  const series: any[] = [
    {
      name: 'Equity', type: 'line', data: equity, xAxisIndex: 0, yAxisIndex: 0,
      smooth: true, symbol: 'none',
      lineStyle: { color: COLORS.blue, width: 1.5 },
      areaStyle: {
        color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [
          { offset: 0, color: 'rgba(88,166,255,0.18)' },
          { offset: 1, color: 'rgba(88,166,255,0)' },
        ] },
      },
    },
  ]
  const grid: any[] = [{ left: 70, right: 20, top: 30, bottom: dd.length ? 120 : 60 }]
  const yAxis: any[] = [{
    type: 'value', scale: true, gridIndex: 0,
    axisLine: { show: false },
    axisLabel: { color: '#484f58', fontSize: 10, fontFamily: 'SF Mono, Cascadia Code, monospace' },
    splitLine: { lineStyle: { color: '#1b2332', type: 'dashed' } },
  }]
  const xAxis: any[] = [{
    type: 'category', data: timestamps, gridIndex: 0,
    axisLine: { lineStyle: { color: '#1b2332' } },
    axisLabel: { color: '#484f58', fontSize: 10, fontFamily: 'SF Mono, Cascadia Code, monospace' },
  }]

  if (dd.length) {
    series.push({
      name: 'Drawdown', type: 'line', data: dd, xAxisIndex: 1, yAxisIndex: 1,
      smooth: true, symbol: 'none',
      lineStyle: { color: COLORS.red, width: 1 },
      areaStyle: {
        color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [
          { offset: 0, color: 'rgba(248,81,73,0)' },
          { offset: 1, color: 'rgba(248,81,73,0.18)' },
        ] },
      },
    })
    yAxis.push({
      type: 'value', scale: true, gridIndex: 1,
      axisLine: { show: false },
      axisLabel: { color: '#484f58', fontSize: 10, formatter: (v: number) => v.toFixed(0) + '%' },
      splitLine: { show: false },
    })
    xAxis.push({ type: 'category', data: timestamps, gridIndex: 1, axisLabel: { show: false }, axisLine: { lineStyle: { color: '#1b2332' } } })
    grid.push({ left: 70, right: 20, top: '72%', bottom: 60 })
  }

  return {
    ...buildBaseOption(),
    legend: { show: dd.length > 0, data: ['Equity', 'Drawdown'], textStyle: { color: '#8b949e', fontSize: 11 }, top: 4, right: 20 },
    tooltip: { trigger: 'axis', backgroundColor: '#161b22', borderColor: '#1b2332', textStyle: { color: '#e6edf3', fontSize: 12, fontFamily: 'SF Mono, Cascadia Code, monospace' } },
    grid, xAxis, yAxis,
    dataZoom: [
      { type: 'inside', xAxisIndex: [0], start: 0, end: 100 },
      { type: 'slider', xAxisIndex: [0], bottom: 10, height: 18, borderColor: '#1b2332', fillerColor: 'rgba(88,166,255,0.1)', handleStyle: { color: '#58a6ff' }, textStyle: { color: '#484f58', fontSize: 10 } },
    ],
    series,
  }
})

const monthlyHeatmapOption = computed(() => {
  const mr = an.value?.monthly_returns
  if (!mr) return {}
  const years = Object.keys(mr).sort()
  const months = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']
  const data: number[][] = []
  let minVal = 0, maxVal = 0
  for (let yi = 0; yi < years.length; yi++) {
    for (let mi = 0; mi < 12; mi++) {
      const v = mr[years[yi]][months[mi]]
      if (v !== undefined) {
        data.push([mi, yi, v])
        if (v < minVal) minVal = v
        if (v > maxVal) maxVal = v
      }
    }
  }
  return {
    ...buildBaseOption(),
    tooltip: {
      backgroundColor: '#161b22', borderColor: '#1b2332',
      textStyle: { color: '#e6edf3', fontSize: 12, fontFamily: 'SF Mono, Cascadia Code, monospace' },
      formatter: (p: any) => {
        if (!p.data) return ''
        const [mi, yi, v] = p.data
        return `${years[yi]}-${months[mi]}: ${v >= 0 ? '+' : ''}${v.toFixed(2)}%`
      },
    },
    grid: { left: 60, right: 40, top: 10, bottom: 40 },
    xAxis: { type: 'category', data: months, axisLine: { lineStyle: { color: '#1b2332' } }, axisLabel: { color: '#8b949e', fontSize: 10 } },
    yAxis: { type: 'category', data: years, axisLine: { lineStyle: { color: '#1b2332' } }, axisLabel: { color: '#8b949e', fontSize: 10 } },
    visualMap: {
      min: minVal, max: maxVal, calculable: true, orient: 'horizontal', left: 'center', bottom: 0,
      inRange: { color: ['#f85149', '#161b22', '#3fb950'] },
      textStyle: { color: '#8b949e', fontSize: 10 },
      itemHeight: 10, itemWidth: 120,
    },
    series: [{
      type: 'heatmap', data, label: {
        show: true,
        formatter: (p: any) => p.data[2] !== undefined ? p.data[2].toFixed(1) : '',
        color: '#e6edf3', fontSize: 9, fontFamily: 'SF Mono, Cascadia Code, monospace',
      },
    }],
  }
})

const annualBarOption = computed(() => {
  const ar = an.value?.annual_returns
  if (!ar) return {}
  const years = Object.keys(ar).sort()
  const values = years.map(y => ar[y])
  return {
    ...buildBaseOption(),
    tooltip: { trigger: 'axis', backgroundColor: '#161b22', borderColor: '#1b2332', textStyle: { color: '#e6edf3', fontSize: 12, fontFamily: 'SF Mono, Cascadia Code, monospace' } },
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: years, axisLine: { lineStyle: { color: '#1b2332' } }, axisLabel: { color: '#8b949e', fontSize: 11 } },
    yAxis: { type: 'value', axisLine: { show: false }, axisLabel: { color: '#484f58', fontSize: 10, formatter: (v: number) => v.toFixed(0) + '%' }, splitLine: { lineStyle: { color: '#1b2332', type: 'dashed' } } },
    series: [{
      type: 'bar', data: values.map(v => ({
        value: v,
        itemStyle: { color: v >= 0 ? COLORS.green : COLORS.red },
      })),
      barWidth: '40%',
      label: { show: true, position: 'top', color: '#8b949e', fontSize: 10, fontFamily: 'SF Mono, Cascadia Code, monospace', formatter: (p: any) => p.value.toFixed(1) + '%' },
    }],
  }
})

// ==================== Trades ====================
const hasPnlDist = computed(() => (an.value?.pnl_distribution?.counts?.length ?? 0) > 0)
const hasHolding = computed(() => !!an.value?.holding_stats?.avg_days)
const hasTopTrades = computed(() => (an.value?.top_winners?.length ?? 0) > 0 || (an.value?.top_losers?.length ?? 0) > 0)
const topWinners = computed(() => an.value?.top_winners || [])
const topLosers = computed(() => an.value?.top_losers || [])

const pnlDistOption = computed(() => {
  const dist = an.value?.pnl_distribution
  if (!dist?.counts?.length) return {}
  const edges = dist.edges
  const labels = edges.slice(0, -1).map((e, i) => `${e.toFixed(0)}~${edges[i + 1].toFixed(0)}`)
  return {
    ...buildBaseOption(),
    tooltip: { trigger: 'axis', backgroundColor: '#161b22', borderColor: '#1b2332', textStyle: { color: '#e6edf3', fontSize: 12 } },
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: labels, axisLine: { lineStyle: { color: '#1b2332' } }, axisLabel: { color: '#8b949e', fontSize: 9, rotate: 30 } },
    yAxis: { type: 'value', axisLine: { show: false }, axisLabel: { color: '#484f58', fontSize: 10 }, splitLine: { lineStyle: { color: '#1b2332', type: 'dashed' } } },
    series: [{
      type: 'bar', data: dist.counts,
      itemStyle: { color: COLORS.blue },
      barWidth: '60%',
    }],
  }
})

const holdingCards = computed(() => {
  const h = an.value?.holding_stats
  if (!h) return []
  return [
    { label: 'Avg', value: `${h.avg_days}d` },
    { label: 'Median', value: `${h.median_days}d` },
    { label: 'Max', value: `${h.max_days}d` },
    { label: 'Min', value: `${h.min_days}d` },
  ]
})

// ==================== Risk ====================
const hasRolling = computed(() => (an.value?.rolling_sharpe?.length ?? 0) > 0)

function rollingXAxis() {
  const eq = store.equity
  const startIdx = an.value?.rolling_start_index ?? 0
  if (!eq?.timestamps) return []
  return eq.timestamps.slice(startIdx)
}

const rollingSharpeOption = computed(() => {
  const rs = an.value?.rolling_sharpe
  if (!rs?.length) return {}
  const ts = rollingXAxis()
  return {
    ...buildBaseOption(),
    tooltip: { trigger: 'axis', backgroundColor: '#161b22', borderColor: '#1b2332', textStyle: { color: '#e6edf3', fontSize: 12 } },
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: ts, axisLine: { lineStyle: { color: '#1b2332' } }, axisLabel: { color: '#484f58', fontSize: 10 } },
    yAxis: { type: 'value', axisLine: { show: false }, axisLabel: { color: '#484f58', fontSize: 10 }, splitLine: { lineStyle: { color: '#1b2332', type: 'dashed' } } },
    series: [{
      type: 'line', data: rs, smooth: true, symbol: 'none',
      lineStyle: { color: COLORS.purple, width: 1.5 },
      areaStyle: {
        color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [
          { offset: 0, color: 'rgba(188,140,255,0.15)' },
          { offset: 1, color: 'rgba(188,140,255,0)' },
        ] },
      },
      markLine: { silent: true, data: [{ yAxis: 0, lineStyle: { color: '#484f58', type: 'dashed' } }] },
    }],
    dataZoom: [{ type: 'inside', start: 0, end: 100 }],
  }
})

const rollingDDOption = computed(() => {
  const rd = an.value?.rolling_drawdown
  if (!rd?.length) return {}
  const ts = rollingXAxis()
  return {
    ...buildBaseOption(),
    tooltip: { trigger: 'axis', backgroundColor: '#161b22', borderColor: '#1b2332', textStyle: { color: '#e6edf3', fontSize: 12 } },
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: ts, axisLine: { lineStyle: { color: '#1b2332' } }, axisLabel: { color: '#484f58', fontSize: 10 } },
    yAxis: { type: 'value', axisLine: { show: false }, axisLabel: { color: '#484f58', fontSize: 10, formatter: (v: number) => v.toFixed(0) + '%' }, splitLine: { lineStyle: { color: '#1b2332', type: 'dashed' } } },
    series: [{
      type: 'line', data: rd, smooth: true, symbol: 'none',
      lineStyle: { color: COLORS.red, width: 1.5 },
      areaStyle: {
        color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [
          { offset: 0, color: 'rgba(248,81,73,0)' },
          { offset: 1, color: 'rgba(248,81,73,0.15)' },
        ] },
      },
    }],
    dataZoom: [{ type: 'inside', start: 0, end: 100 }],
  }
})

const rollingVolOption = computed(() => {
  const rv = an.value?.rolling_volatility
  if (!rv?.length) return {}
  const ts = rollingXAxis()
  return {
    ...buildBaseOption(),
    tooltip: { trigger: 'axis', backgroundColor: '#161b22', borderColor: '#1b2332', textStyle: { color: '#e6edf3', fontSize: 12 } },
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: ts, axisLine: { lineStyle: { color: '#1b2332' } }, axisLabel: { color: '#484f58', fontSize: 10 } },
    yAxis: { type: 'value', axisLine: { show: false }, axisLabel: { color: '#484f58', fontSize: 10, formatter: (v: number) => v.toFixed(0) + '%' }, splitLine: { lineStyle: { color: '#1b2332', type: 'dashed' } } },
    series: [{
      type: 'line', data: rv, smooth: true, symbol: 'none',
      lineStyle: { color: COLORS.orange, width: 1.5 },
      areaStyle: {
        color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [
          { offset: 0, color: 'rgba(255,140,66,0.15)' },
          { offset: 1, color: 'rgba(255,140,66,0)' },
        ] },
      },
    }],
    dataZoom: [{ type: 'inside', start: 0, end: 100 }],
  }
})

// ==================== Journal ====================
const pipelineStages = [
  { key: 'normal', label: 'Research' },
  { key: 'candidate', label: 'Candidate' },
  { key: 'paper_trading', label: 'Paper Trading' },
  { key: 'production', label: 'Production' },
]

const currentStatus = computed(() => exp.value?.status || 'normal')

function pipelineIndex(key: string): number {
  return pipelineStages.findIndex(s => s.key === key)
}

async function changeStatus(status: string) {
  if (!exp.value) return
  await store.updateStatus(exp.value.id, status)
}

async function toggleFav() {
  if (!exp.value) return
  await store.updateFavorite(exp.value.id, exp.value.favorite !== 1)
}

// Note
const noteText = ref('')
const noteSaved = ref(false)

function initNote() {
  noteText.value = exp.value?.note || ''
  noteSaved.value = false
}

async function saveNote() {
  if (!exp.value) return
  await store.updateNote(exp.value.id, noteText.value)
  noteSaved.value = true
  setTimeout(() => { noteSaved.value = false }, 2000)
}

// Tags
const currentTags = computed(() => {
  try {
    const raw = exp.value?.tags_json
    if (!raw) return []
    return JSON.parse(raw)
  } catch {
    return [] as string[]
  }
})

const tagInputVisible = ref(false)
const tagInputVal = ref('')
const tagInputRef = ref<any>(null)

function showTagInput() {
  tagInputVisible.value = true
  tagInputVal.value = ''
  nextTick(() => tagInputRef.value?.focus())
}

async function addTag() {
  const tag = tagInputVal.value.trim()
  if (!tag || !exp.value) return
  const newTags = await addExperimentTag(exp.value.id, tag)
  if (exp.value) exp.value.tags_json = JSON.stringify(newTags)
  tagInputVisible.value = false
  tagInputVal.value = ''
}

async function removeTag(tag: string) {
  if (!exp.value) return
  const newTags = await removeExperimentTag(exp.value.id, tag)
  exp.value.tags_json = JSON.stringify(newTags)
}

// Lineage
const parentIdInput = ref('')

async function setParent() {
  const pid = parentIdInput.value.trim()
  if (!pid || !exp.value) return
  await store.updateParent(exp.value.id, pid)
  parentIdInput.value = ''
}

function formatDateTime(dt: string): string {
  if (!dt) return '-'
  return dt.replace('T', ' ').substring(0, 19)
}

onMounted(() => {
  const id = route.params.id as string
  if (id) {
    store.loadDetail(id).then(() => initNote())
  }
})
</script>

<style scoped>
.detail-container {
  max-width: 1200px;
}

.detail-back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #58a6ff;
  font-size: 13px;
  cursor: pointer;
  margin-bottom: 20px;
  transition: color 0.2s;
}

.detail-back:hover {
  color: #79c0ff;
}

.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  color: var(--q-text-secondary);
  font-size: 14px;
  gap: 12px;
}

/* Header */
.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.detail-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--q-text-primary);
  margin: 0 0 4px 0;
  letter-spacing: -0.5px;
}

.detail-sub {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  margin: 0;
}

.detail-id {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  color: var(--q-text-muted);
}

.detail-sep {
  color: var(--q-border);
}

.detail-strategy {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  color: var(--q-accent);
}

.detail-dataset {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  color: var(--q-text-secondary);
}

.detail-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.detail-date {
  font-size: 13px;
  color: var(--q-text-muted);
}

.source-tag {
  background: var(--q-bg-tertiary);
  border-color: var(--q-border);
  color: var(--q-text-secondary);
  font-size: 11px;
}

/* Tabs */
.detail-tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
}

.detail-tabs :deep(.el-tabs__item) {
  color: #8b949e;
  font-size: 13px;
  font-weight: 500;
}

.detail-tabs :deep(.el-tabs__item.is-active) {
  color: #58a6ff;
}

.detail-tabs :deep(.el-tabs__active-bar) {
  background: #58a6ff;
}

.detail-tabs :deep(.el-tabs__nav-wrap::after) {
  background: #1b2332;
}

/* Overview metrics grid */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 20px;
}

@media (max-width: 900px) {
  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.metric-cell {
  background: #0d1117;
  border: 1px solid #1b2332;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  transition: border-color 0.2s;
}

.metric-cell:hover {
  border-color: #30363d;
}

.metric-label {
  font-size: 11px;
  color: #484f58;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 500;
}

.metric-value {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 20px;
  font-weight: 700;
  color: #e6edf3;
  line-height: 1.2;
}

.metric-value.positive {
  color: #3fb950;
}

.metric-value.negative {
  color: #f85149;
}

.metric-hint {
  font-size: 10px;
  color: #484f58;
  margin-top: 2px;
}

/* Section blocks */
.section-block {
  margin-bottom: 20px;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: #8b949e;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-sub {
  font-size: 11px;
  color: #484f58;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-weight: 400;
  text-transform: none;
}

/* Chart boxes */
.chart-box {
  background: #0d1117;
  border: 1px solid #1b2332;
  border-radius: 8px;
  padding: 8px;
}

.chart-box .chart {
  width: 100%;
  height: 360px;
}

.chart-sm .chart {
  height: 280px;
}

.chart-xs .chart {
  height: 200px;
}

/* Parameters */
.params-grid {
  background: #0d1117;
  border: 1px solid #1b2332;
  border-radius: 8px;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.param-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  border-bottom: 1px solid #1b2332;
}

.param-row:last-child {
  border-bottom: none;
}

.param-key {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  color: #8b949e;
}

.param-val {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  color: #79c0ff;
}

/* Holding grid */
.holding-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}

.holding-cell {
  background: #0d1117;
  border: 1px solid #1b2332;
  border-radius: 8px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.holding-val {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 18px;
  font-weight: 700;
  color: #e6edf3;
}

.holding-label {
  font-size: 11px;
  color: #484f58;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Top winners/losers */
.top-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.top-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.top-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  background: #0d1117;
  border: 1px solid #1b2332;
  border-radius: 6px;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 12px;
}

.top-row.positive .top-pnl {
  color: #3fb950;
}

.top-row.negative .top-pnl {
  color: #f85149;
}

.top-rank {
  color: #484f58;
  width: 16px;
  text-align: center;
}

.top-symbol {
  color: #58a6ff;
  flex: 1;
}

.top-pnl {
  font-weight: 600;
}

/* Empty state */
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  color: #484f58;
  font-size: 13px;
}

/* Journal Tab */
.pipeline-bar {
  display: flex;
  align-items: center;
  gap: 0;
  background: #0d1117;
  border: 1px solid #1b2332;
  border-radius: 8px;
  padding: 12px 16px;
}

.pipeline-stage {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px;
  cursor: pointer;
  transition: all 0.2s;
  border-radius: 4px;
  position: relative;
}

.pipeline-stage:not(:last-child)::after {
  content: '→';
  margin-left: 12px;
  color: #484f58;
  font-size: 12px;
}

.pipeline-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #484f58;
  transition: background 0.2s;
}

.pipeline-stage.active .pipeline-dot {
  background: #58a6ff;
  box-shadow: 0 0 6px rgba(88, 166, 255, 0.4);
}

.pipeline-stage.passed .pipeline-dot {
  background: #3fb950;
}

.pipeline-label {
  font-size: 12px;
  color: #484f58;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.pipeline-stage.active .pipeline-label {
  color: #58a6ff;
}

.pipeline-stage.passed .pipeline-label {
  color: #3fb950;
}

.pipeline-stage:hover {
  background: #161b22;
}

/* Bookmark */
.bookmark-row {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #0d1117;
  border: 1px solid #1b2332;
  border-radius: 8px;
  padding: 10px 16px;
}

.bookmark-star {
  font-size: 20px;
  color: #484f58;
  cursor: pointer;
  transition: color 0.2s;
  user-select: none;
}

.bookmark-star.active {
  color: #e3b341;
}

.bookmark-star:hover {
  color: #e3b341;
}

.bookmark-text {
  font-size: 13px;
  color: #8b949e;
}

/* Note */
.note-input :deep(.el-textarea__inner) {
  background: #0d1117;
  border-color: #1b2332;
  color: #e6edf3;
  font-size: 13px;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  line-height: 1.6;
}

.note-input :deep(.el-textarea__inner:focus) {
  border-color: #58a6ff;
}

.note-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.note-saved {
  font-size: 12px;
  color: #3fb950;
}

/* Tags */
.tags-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.journal-tag {
  background: #161b22;
  border-color: #30363d;
  color: #79c0ff;
}

.tag-input {
  width: 120px;
}

.tag-input :deep(.el-input__inner) {
  background: #0d1117;
  border-color: #1b2332;
  color: #e6edf3;
}

/* Lineage */
.lineage-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.lineage-setter {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.lineage-label {
  font-size: 12px;
  color: #8b949e;
  font-weight: 500;
}

.lineage-parent {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 12px;
  color: #58a6ff;
  cursor: pointer;
  text-decoration: underline;
}

.lineage-parent:hover {
  color: #79c0ff;
}

.lineage-none {
  font-size: 12px;
  color: #484f58;
}

.parent-input {
  width: 280px;
}

.parent-input :deep(.el-input__inner) {
  background: #0d1117;
  border-color: #1b2332;
  color: #e6edf3;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 12px;
}

.family-tree {
  background: #0d1117;
  border: 1px solid #1b2332;
  border-radius: 8px;
  padding: 16px;
}

.lineage-empty {
  color: #484f58;
  font-size: 13px;
  padding: 12px 0;
}

/* Activity */
.activity-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.activity-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  background: #0d1117;
  border: 1px solid #1b2332;
  border-radius: 6px;
  font-size: 12px;
}

.activity-action {
  font-weight: 500;
  color: #58a6ff;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  font-size: 11px;
}

.activity-detail {
  color: #8b949e;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 11px;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.activity-time {
  color: #484f58;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 11px;
  flex-shrink: 0;
}
</style>
