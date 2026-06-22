<template>
  <div class="compare-page">
    <!-- Header -->
    <div class="compare-header">
      <div class="compare-header-left">
        <h1 class="compare-title">对比实验 Compare Experiments</h1>
        <p class="compare-sub">{{ compareData.experiments?.length || 0 }} 个实验已选择 experiments selected</p>
      </div>
      <div class="compare-header-right">
        <el-button @click="router.push('/experiments')">返回实验 Back to Experiments</el-button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-state">
      <el-icon class="is-loading" :size="24"><Loading /></el-icon>
      <span>加载对比中 Loading comparison...</span>
    </div>

    <!-- Error -->
    <div v-else-if="error" class="error-state">
      <el-icon :size="24" color="#f85149"><CircleCloseFilled /></el-icon>
      <p>{{ error }}</p>
    </div>

    <template v-else-if="compareData.experiments?.length">
      <!-- Equity Curve Comparison -->
      <div class="section">
        <div class="section-header">
          <span class="section-title">资金曲线对比 Equity Curve Comparison</span>
        </div>
        <div class="section-body">
          <div class="chart-container">
            <v-chart :option="equityChartOption" autoresize class="chart" />
          </div>
        </div>
      </div>

      <!-- Metrics Comparison Table -->
      <div class="section">
        <div class="section-header">
          <span class="section-title">指标对比 Metrics Comparison</span>
        </div>
        <div class="section-body">
          <el-table
            :data="metricsTable"
            class="q-table"
            :header-cell-style="{ background: '#161b22', color: '#8b949e', borderBottom: '1px solid #1b2332' }"
            :cell-style="{ borderBottom: '1px solid #1b2332' }"
          >
            <el-table-column prop="name" label="实验 Experiment" min-width="160">
              <template #default="{ row }">
                <div class="cell-exp-name">
                  <span class="dot" :style="{ background: row._color }"></span>
                  <span>{{ row.name || row.id }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="strategy" label="策略 Strategy" width="140">
              <template #default="{ row }">
                <span class="cell-strategy">{{ row.strategy }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="total_return" label="收益 Return" width="100" align="right" sortable>
              <template #default="{ row }">
                <span :class="row.total_return >= 0 ? 'cell-positive' : 'cell-negative'">
                  {{ row.total_return >= 0 ? '+' : '' }}{{ row.total_return?.toFixed(2) }}%
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="sharpe" label="夏普 Sharpe" width="90" align="right" sortable>
              <template #default="{ row }">
                <span class="cell-num">{{ row.sharpe?.toFixed(3) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="max_drawdown" label="回撤 MaxDD" width="90" align="right" sortable>
              <template #default="{ row }">
                <span class="cell-negative">{{ row.max_drawdown?.toFixed(2) }}%</span>
              </template>
            </el-table-column>
            <el-table-column prop="win_rate" label="Win%" width="80" align="right">
              <template #default="{ row }">
                <span class="cell-num">{{ row.win_rate?.toFixed(1) }}%</span>
              </template>
            </el-table-column>
            <el-table-column prop="trade_count" label="Trades" width="80" align="right">
              <template #default="{ row }">
                <span class="cell-num">{{ row.trade_count }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="final_equity" label="Final Equity" width="120" align="right">
              <template #default="{ row }">
                <span class="cell-num">${{ (row.final_equity || 0).toLocaleString(undefined, { maximumFractionDigits: 0 }) }}</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- Param Diff -->
      <div v-if="paramDiffKeys.length" class="section">
        <div class="section-header">
          <span class="section-title">Parameter Differences</span>
        </div>
        <div class="section-body">
          <el-table
            :data="paramDiffRows"
            class="q-table"
            :header-cell-style="{ background: '#161b22', color: '#8b949e', borderBottom: '1px solid #1b2332' }"
            :cell-style="{ borderBottom: '1px solid #1b2332' }"
          >
            <el-table-column prop="key" label="Parameter" width="160">
              <template #default="{ row }">
                <span class="cell-param-key">{{ row.key }}</span>
              </template>
            </el-table-column>
            <el-table-column
              v-for="exp in compareData.experiments"
              :key="exp.id"
              :label="exp.name || exp.id"
              min-width="120"
            >
              <template #default="{ row }">
                <span :class="{ 'cell-diff': !row.same }" class="cell-param-val">
                  {{ row.values[exp.id] ?? '-' }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </template>

    <!-- Empty -->
    <div v-else class="empty-state">
      <p>Select at least 2 experiments from the Experiments page to compare.</p>
      <el-button type="primary" @click="router.push('/experiments')">Go to Experiments</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { compareExperiments, type CompareResult } from '@/api/experiment'
import { Loading, CircleCloseFilled } from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([LineChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, CanvasRenderer])

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const error = ref<string | null>(null)
const compareData = ref<CompareResult>({
  experiments: [],
  equity_curves: {},
  param_diff: {},
  metrics_comparison: {},
})

const COLORS = ['#58a6ff', '#3fb950', '#f85149', '#bc8cff', '#e3b341', '#79c0ff', '#d2a8ff', '#ffa657']

const metricsTable = computed(() => {
  const exps = compareData.value.experiments || []
  return exps.map((exp: any, i: number) => ({
    ...exp,
    _color: COLORS[i % COLORS.length],
  }))
})

const paramDiffKeys = computed(() => {
  return Object.keys(compareData.value.param_diff || {})
})

const paramDiffRows = computed(() => {
  const diff = compareData.value.param_diff || {}
  return Object.entries(diff).map(([key, val]: [string, any]) => ({
    key,
    values: val.values || {},
    same: val.same,
  }))
})

const equityChartOption = computed(() => {
  const curves = compareData.value.equity_curves || {}
  const entries = Object.entries(curves)
  if (!entries.length) return {}

  const series = entries.map(([eid, curve]: [string, any], i: number) => ({
    name: curve.name || eid,
    type: 'line',
    data: curve.values,
    smooth: true,
    symbol: 'none',
    lineStyle: { color: COLORS[i % COLORS.length], width: 1.5 },
  }))

  // 统一 x 轴（取最长的）
  let maxLen = 0
  let xData: string[] = []
  for (const [, curve] of entries) {
    if (curve.timestamps?.length > maxLen) {
      maxLen = curve.timestamps.length
      xData = curve.timestamps
    }
  }

  return {
    backgroundColor: 'transparent',
    animation: false,
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#161b22',
      borderColor: '#1b2332',
      textStyle: { color: '#e6edf3', fontSize: 12, fontFamily: 'SF Mono, Cascadia Code, monospace' },
    },
    legend: {
      show: true,
      textStyle: { color: '#8b949e', fontSize: 11 },
      top: 4,
      right: 20,
    },
    grid: { left: 70, right: 20, top: 40, bottom: 60 },
    xAxis: {
      type: 'category',
      data: xData,
      axisLine: { lineStyle: { color: '#1b2332' } },
      axisLabel: { color: '#484f58', fontSize: 10, fontFamily: 'SF Mono, Cascadia Code, monospace' },
      splitLine: { show: false },
    },
    yAxis: {
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
    },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      {
        type: 'slider',
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

onMounted(async () => {
  const idsStr = route.query.ids as string
  if (!idsStr) return

  const ids = idsStr.split(',').filter(Boolean)
  if (ids.length < 2) {
    error.value = 'Please select at least 2 experiments to compare.'
    return
  }

  loading.value = true
  try {
    compareData.value = await compareExperiments(ids, true, false)
  } catch (e: any) {
    error.value = e.message || 'Failed to load comparison data'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.compare-page {
  max-width: 1200px;
}

.compare-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.compare-title {
  font-size: 24px;
  font-weight: 700;
  color: #e6edf3;
  margin: 0 0 4px 0;
  letter-spacing: -0.5px;
}

.compare-sub {
  font-size: 14px;
  color: #484f58;
  margin: 0;
}

.loading-state,
.error-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  color: #8b949e;
  font-size: 14px;
  gap: 12px;
}

.section {
  margin-bottom: 24px;
}

.section-header {
  margin-bottom: 12px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #8b949e;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.section-body {
  min-height: 0;
}

.chart-container {
  background: #0d1117;
  border: 1px solid #1b2332;
  border-radius: 8px;
  padding: 12px;
}

.chart {
  width: 100%;
  height: 420px;
}

.q-table {
  --el-table-bg-color: #0d1117;
  --el-table-tr-bg-color: #0d1117;
  --el-table-row-hover-bg-color: #161b22;
  --el-table-text-color: #e6edf3;
  --el-table-border-color: #1b2332;
  --el-table-header-text-color: #8b949e;
}

.cell-exp-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  color: #e6edf3;
  font-size: 13px;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.cell-strategy {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 12px;
  color: #58a6ff;
}

.cell-positive {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  color: #3fb950;
  font-weight: 600;
}

.cell-negative {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  color: #f85149;
}

.cell-num {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  color: #c9d1d9;
}

.cell-param-key {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  color: #8b949e;
}

.cell-param-val {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  color: #c9d1d9;
}

.cell-diff {
  color: #e3b341 !important;
  font-weight: 600;
}
</style>
