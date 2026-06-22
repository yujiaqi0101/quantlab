<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-header-row">
        <div>
          <h1 class="page-title">信号研究 Signal Research</h1>
          <p class="page-desc">构建、可视化和分析交易信号 Build, visualize, and analyze trading signals</p>
        </div>
        <div class="page-actions">
          <el-select v-model="selectedDataset" placeholder="数据集 Dataset" class="filter-select" @change="onDatasetChange">
            <el-option v-for="ds in datasets" :key="ds.dataset_id" :label="ds.name" :value="ds.dataset_id" />
          </el-select>
          <el-select v-model="selectedSymbol" placeholder="标的 Symbol" clearable class="filter-select" style="width:140px">
            <el-option v-for="s in symbols" :key="s" :label="s" :value="s" />
          </el-select>
          <el-button :icon="Refresh" circle @click="loadSignals" :loading="loading" />
        </div>
      </div>
    </div>

    <div class="page-content two-col">
      <!-- Left: Signal Builder + List -->
      <div class="left-panel">
        <!-- Signal Builder -->
        <div class="builder-card">
          <div class="card-title">信号构建器 Signal Builder</div>

          <el-tabs v-model="builderTab" class="q-tabs">
            <!-- Threshold Builder -->
            <el-tab-pane label="阈值 Threshold" name="threshold">
              <div class="builder-form">
                <el-select v-model="buildFactor" placeholder="因子 Factor" filterable class="builder-input">
                  <el-option v-for="f in factorList" :key="f.name" :label="f.name" :value="f.name" />
                </el-select>
                <el-select v-model="buildOperator" placeholder="Op" class="builder-input" style="width:90px">
                  <el-option v-for="op in thresholdOps" :key="op" :label="op" :value="op" />
                </el-select>
                <el-input-number v-model="buildValue" :step="1" class="builder-input" style="width:120px" />
                <el-select v-model="buildDirection" class="builder-input" style="width:100px">
                  <el-option label="Long" value="long" />
                  <el-option label="Short" value="short" />
                </el-select>
                <el-button type="primary" size="small" @click="buildThreshold" :loading="buildLoading">构建 Build</el-button>
              </div>
            </el-tab-pane>

            <!-- Crossover Builder -->
            <el-tab-pane label="交叉 Crossover" name="crossover">
              <div class="builder-form">
                <el-select v-model="buildFastFactor" placeholder="快线 Fast" filterable class="builder-input">
                  <el-option v-for="f in factorList" :key="f.name" :label="f.name" :value="f.name" />
                </el-select>
                <span class="builder-label">交叉 crosses</span>
                <el-select v-model="buildSlowFactor" placeholder="慢线 Slow" filterable class="builder-input">
                  <el-option v-for="f in factorList" :key="f.name" :label="f.name" :value="f.name" />
                </el-select>
                <el-button type="primary" size="small" @click="buildCrossover" :loading="buildLoading">构建 Build</el-button>
              </div>
            </el-tab-pane>

            <!-- Combine Builder -->
            <el-tab-pane label="Combine" name="combine">
              <div class="builder-form">
                <el-select v-model="combineSignals_" multiple placeholder="Select signals" class="builder-input" style="width:300px">
                  <el-option v-for="s in signals" :key="s.name" :label="s.name" :value="s.name" />
                </el-select>
                <el-select v-model="combineLogic" class="builder-input" style="width:120px">
                  <el-option label="AND" value="AND" />
                  <el-option label="OR" value="OR" />
                  <el-option label="MAJORITY" value="MAJORITY" />
                </el-select>
                <el-button type="primary" size="small" @click="buildCombine" :loading="buildLoading" :disabled="combineSignals_.length < 2">Combine</el-button>
              </div>
            </el-tab-pane>
          </el-tabs>
        </div>

        <!-- Signal List -->
        <div class="signal-list-card">
          <div class="card-title">Signals ({{ signals.length }})</div>
          <div class="signal-list">
            <div
              v-for="s in signals"
              :key="s.name"
              class="signal-item"
              :class="{ active: selectedSignal === s.name }"
              @click="selectSignal(s.name)"
            >
              <div class="signal-item-header">
                <span class="signal-item-name">{{ s.name }}</span>
                <el-tag size="small" effect="dark" :type="signalTypeColor(s.type)">{{ s.type }}</el-tag>
              </div>
              <div class="signal-item-desc">{{ s.description || '-' }}</div>
            </div>
            <div v-if="signals.length === 0" class="list-empty">No signals. Use the builder above to create one.</div>
          </div>
        </div>
      </div>

      <!-- Right: Signal Detail -->
      <div class="right-panel">
        <div v-if="!selectedSignal" class="empty-detail">
          <p>Select a signal to explore</p>
        </div>

        <div v-else class="detail-content">
          <el-tabs v-model="detailTab" class="q-tabs">
            <!-- Preview & Coverage -->
            <el-tab-pane label="Coverage" name="coverage">
              <div class="tab-toolbar">
                <el-button type="primary" size="small" :loading="previewLoading" @click="loadPreview">Analyze</el-button>
              </div>
              <div v-if="previewData" class="coverage-grid">
                <div class="cov-card">
                  <div class="cov-label">Total Bars</div>
                  <div class="cov-value">{{ previewData.total_bars }}</div>
                </div>
                <div class="cov-card cov-long">
                  <div class="cov-label">Long Signals</div>
                  <div class="cov-value">{{ previewData.long_count }} ({{ (previewData.long_pct * 100).toFixed(1) }}%)</div>
                </div>
                <div class="cov-card cov-short">
                  <div class="cov-label">Short Signals</div>
                  <div class="cov-value">{{ previewData.short_count }} ({{ (previewData.short_pct * 100).toFixed(1) }}%)</div>
                </div>
                <div class="cov-card cov-neutral">
                  <div class="cov-label">Neutral</div>
                  <div class="cov-value">{{ previewData.neutral_count }}</div>
                </div>
                <div class="cov-card cov-coverage">
                  <div class="cov-label">Coverage</div>
                  <div class="cov-value">{{ (previewData.coverage * 100).toFixed(1) }}%</div>
                </div>
              </div>
              <div v-else class="tab-empty">Click Analyze to compute signal coverage.</div>
            </el-tab-pane>

            <!-- Visualization -->
            <el-tab-pane label="Visualization" name="visualize">
              <div class="tab-toolbar">
                <el-button type="primary" size="small" :loading="vizLoading" @click="loadVisualization">Load Chart</el-button>
              </div>
              <div v-if="vizData" class="chart-container">
                <div ref="priceChartRef" class="chart-box"></div>
                <div ref="signalChartRef" class="chart-box signal-chart"></div>
              </div>
              <div v-else class="tab-empty">Click Load Chart to visualize the signal.</div>
            </el-tab-pane>

            <!-- Forward Return -->
            <el-tab-pane label="Forward Return" name="forward">
              <div class="tab-toolbar">
                <el-button type="primary" size="small" :loading="fwdLoading" @click="loadForwardReturn">Run Analysis</el-button>
              </div>
              <div v-if="fwdData" class="fwd-results">
                <el-table :data="fwdTableData" class="q-table" size="small">
                  <el-table-column prop="period" label="Period" width="80" />
                  <el-table-column prop="long_mean" label="Long Mean" width="100">
                    <template #default="{ row }">
                      <span :class="retColor(row.long_mean)">{{ fmtPct(row.long_mean) }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="long_wr" label="Long WR" width="90">
                    <template #default="{ row }">
                      <span>{{ (row.long_wr * 100).toFixed(1) }}%</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="short_mean" label="Short Mean" width="100">
                    <template #default="{ row }">
                      <span :class="retColor(row.short_mean)">{{ fmtPct(row.short_mean) }}</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="short_wr" label="Short WR" width="90">
                    <template #default="{ row }">
                      <span>{{ (row.short_wr * 100).toFixed(1) }}%</span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="count" label="Count" width="80" />
                </el-table>
              </div>
              <div v-else class="tab-empty">Click Run Analysis to compute forward returns.</div>
            </el-tab-pane>
          </el-tabs>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import {
  getSignalList,
  buildThresholdSignal,
  buildCrossoverSignal,
  combineSignals,
  previewSignal,
  visualizeSignal,
  getForwardReturn,
  type SignalInfo,
  type SignalPreview,
  type SignalVisualizeResult,
  type ForwardReturnResult,
} from '@/api/signal'
import { getFactorList, type FactorInfo } from '@/api/factor'
import { http } from '@/api/http'

// ---- State ----
const loading = ref(false)
const signals = ref<SignalInfo[]>([])
const factorList = ref<FactorInfo[]>([])
const selectedSignal = ref('')

// Dataset / Symbol
const datasets = ref<any[]>([])
const selectedDataset = ref('')
const symbols = ref<string[]>([])
const selectedSymbol = ref('')

// Builder
const builderTab = ref('threshold')
const buildLoading = ref(false)
// Threshold
const buildFactor = ref('')
const buildOperator = ref('<')
const buildValue = ref(30)
const buildDirection = ref('long')
const thresholdOps = ['<', '<=', '>', '>=', '==']
// Crossover
const buildFastFactor = ref('')
const buildSlowFactor = ref('')
// Combine
const combineSignals_ = ref<string[]>([])
const combineLogic = ref('AND')

// Detail
const detailTab = ref('coverage')

// Preview
const previewLoading = ref(false)
const previewData = ref<SignalPreview | null>(null)

// Visualization
const vizLoading = ref(false)
const vizData = ref<SignalVisualizeResult | null>(null)
const priceChartRef = ref<HTMLElement>()
const signalChartRef = ref<HTMLElement>()
let priceChart: echarts.ECharts | null = null
let signalChart: echarts.ECharts | null = null

// Forward Return
const fwdLoading = ref(false)
const fwdData = ref<ForwardReturnResult | null>(null)
const fwdTableData = ref<any[]>([])

// ---- Load ----
async function loadSignals() {
  loading.value = true
  try {
    signals.value = await getSignalList()
  } catch (e) {
    console.error('Failed to load signals', e)
  } finally {
    loading.value = false
  }
}

async function loadFactors() {
  try {
    factorList.value = await getFactorList()
  } catch (e) {
    console.error('Failed to load factors', e)
  }
}

async function loadDatasets() {
  try {
    const resp = await http.get('/datasets')
    datasets.value = resp.data
    if (datasets.value.length > 0 && !selectedDataset.value) {
      selectedDataset.value = datasets.value[0].dataset_id
      await onDatasetChange()
    }
  } catch (e) {
    console.error('Failed to load datasets', e)
  }
}

async function onDatasetChange() {
  if (!selectedDataset.value) return
  try {
    const resp = await http.get(`/datasets/${selectedDataset.value}/symbols`)
    symbols.value = resp.data
    if (symbols.value.length > 0 && !selectedSymbol.value) {
      selectedSymbol.value = symbols.value[0]
    }
  } catch (e) {
    symbols.value = []
  }
}

// ---- Select ----
function selectSignal(name: string) {
  selectedSignal.value = name
  previewData.value = null
  vizData.value = null
  fwdData.value = null
}

function signalTypeColor(type: string): string {
  const map: Record<string, string> = {
    ThresholdSignal: '', CrossoverSignal: 'success', ZeroCrossoverSignal: 'warning',
    AndSignal: 'info', OrSignal: 'info', MajoritySignal: 'danger',
  }
  return map[type] || ''
}

// ---- Builder ----
async function buildThreshold() {
  if (!buildFactor.value) return
  buildLoading.value = true
  try {
    await buildThresholdSignal(buildFactor.value, buildOperator.value, buildValue.value, buildDirection.value)
    await loadSignals()
  } catch (e) {
    console.error('Build error', e)
  } finally {
    buildLoading.value = false
  }
}

async function buildCrossover() {
  if (!buildFastFactor.value || !buildSlowFactor.value) return
  buildLoading.value = true
  try {
    await buildCrossoverSignal(buildFastFactor.value, buildSlowFactor.value)
    await loadSignals()
  } catch (e) {
    console.error('Build error', e)
  } finally {
    buildLoading.value = false
  }
}

async function buildCombine() {
  if (combineSignals_.value.length < 2) return
  buildLoading.value = true
  try {
    await combineSignals(
      combineSignals_.value,
      combineLogic.value,
      undefined,
      selectedDataset.value,
      selectedSymbol.value,
    )
    await loadSignals()
  } catch (e) {
    console.error('Combine error', e)
  } finally {
    buildLoading.value = false
  }
}

// ---- Preview ----
async function loadPreview() {
  if (!selectedSignal.value || !selectedDataset.value) return
  previewLoading.value = true
  try {
    previewData.value = await previewSignal(selectedSignal.value, selectedDataset.value, selectedSymbol.value)
  } catch (e) {
    console.error('Preview error', e)
  } finally {
    previewLoading.value = false
  }
}

// ---- Visualization ----
async function loadVisualization() {
  if (!selectedSignal.value || !selectedDataset.value) return
  vizLoading.value = true
  try {
    vizData.value = await visualizeSignal(selectedSignal.value, selectedDataset.value, selectedSymbol.value)
    await nextTick()
    renderVizCharts()
  } catch (e) {
    console.error('Viz error', e)
    vizData.value = null
  } finally {
    vizLoading.value = false
  }
}

function renderVizCharts() {
  if (!vizData.value) return

  // Price chart
  if (priceChartRef.value) {
    priceChart = echarts.init(priceChartRef.value)
    const d = vizData.value
    const dates = d.candles.map(c => c.t.slice(0, 10))
    priceChart.setOption({
      backgroundColor: 'transparent',
      animation: false,
      tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
      grid: { left: 60, right: 20, top: 30, bottom: 30 },
      xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 10, color: '#8b949e' }, axisLine: { lineStyle: { color: '#1b2332' } } },
      yAxis: { scale: true, splitLine: { lineStyle: { color: '#1b2332' } }, axisLabel: { fontSize: 10, color: '#8b949e' } },
      series: [{
        type: 'candlestick',
        data: d.candles.map(c => [c.o, c.c, c.l, c.h]),
        itemStyle: { color: '#3fb950', color0: '#f85149', borderColor: '#3fb950', borderColor0: '#f85149' },
      }],
      title: { text: `${d.symbol} Price`, left: 'center', textStyle: { color: '#c9d1d9', fontSize: 13 } },
    })
  }

  // Signal timeline chart
  if (signalChartRef.value) {
    signalChart = echarts.init(signalChartRef.value)
    const d = vizData.value
    const dates = d.signal.map(s => s.t.slice(0, 10))
    const vals = d.signal.map(s => s.v)

    // 分离 long/short 区域
    const longVals = vals.map(v => v === 1 ? 1 : null as any)
    const shortVals = vals.map(v => v === -1 ? -1 : null as any)

    signalChart.setOption({
      backgroundColor: 'transparent',
      animation: false,
      tooltip: { trigger: 'axis' },
      legend: { data: ['Long', 'Short'], top: 5, textStyle: { color: '#8b949e', fontSize: 11 } },
      grid: { left: 60, right: 20, top: 40, bottom: 30 },
      xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 10, color: '#8b949e' }, axisLine: { lineStyle: { color: '#1b2332' } } },
      yAxis: { min: -1.5, max: 1.5, splitLine: { lineStyle: { color: '#1b2332' } }, axisLabel: { fontSize: 10, color: '#8b949e' } },
      series: [
        {
          name: 'Long',
          type: 'bar',
          data: longVals,
          itemStyle: { color: '#3fb950' },
          barWidth: 3,
        },
        {
          name: 'Short',
          type: 'bar',
          data: shortVals,
          itemStyle: { color: '#f85149' },
          barWidth: 3,
        },
      ],
      title: { text: d.signal_name, left: 'center', textStyle: { color: '#c9d1d9', fontSize: 13 } },
    })
  }
}

// ---- Forward Return ----
async function loadForwardReturn() {
  if (!selectedSignal.value || !selectedDataset.value) return
  fwdLoading.value = true
  try {
    fwdData.value = await getForwardReturn(selectedSignal.value, selectedDataset.value, selectedSymbol.value)
    buildFwdTable()
  } catch (e) {
    console.error('Forward return error', e)
    fwdData.value = null
  } finally {
    fwdLoading.value = false
  }
}

function buildFwdTable() {
  if (!fwdData.value) return
  const rows: any[] = []
  for (const [key, val] of Object.entries(fwdData.value.forward_returns)) {
    const period = key.replace('fwd_', '')
    rows.push({
      period: `${period} bar${parseInt(period) > 1 ? 's' : ''}`,
      long_mean: val.long.mean,
      long_wr: val.long.win_rate,
      short_mean: val.short.mean,
      short_wr: val.short.win_rate,
      count: val.all.count,
    })
  }
  fwdTableData.value = rows
}

function fmtPct(val: number): string {
  if (val === 0) return '0.00%'
  return (val * 100).toFixed(4) + '%'
}

function retColor(val: number): string {
  if (val > 0) return 'fwd-positive'
  if (val < 0) return 'fwd-negative'
  return ''
}

// ---- Lifecycle ----
onMounted(async () => {
  await Promise.all([loadSignals(), loadFactors(), loadDatasets()])
})

window.addEventListener('resize', () => {
  priceChart?.resize()
  signalChart?.resize()
})
</script>

<style scoped>
.page-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.page-header {
  margin-bottom: 16px;
}

.page-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--q-text-primary);
  margin: 0;
}

.page-desc {
  font-size: 13px;
  color: var(--q-text-muted);
  margin: 4px 0 0;
}

.page-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.filter-select {
  width: 160px;
}

.two-col {
  display: flex;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

.left-panel {
  width: 420px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.right-panel {
  flex: 1;
  min-width: 0;
}

.builder-card,
.signal-list-card {
  background: var(--q-bg-secondary);
  border: 1px solid var(--q-border);
  border-radius: 8px;
  padding: 16px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--q-text-primary);
  margin-bottom: 12px;
}

.builder-form {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.builder-input {
  flex-shrink: 0;
}

.builder-label {
  color: var(--q-text-muted);
  font-size: 13px;
}

.signal-list {
  max-height: 400px;
  overflow-y: auto;
}

.signal-item {
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
  border: 1px solid transparent;
}

.signal-item:hover {
  background: var(--q-bg-tertiary);
}

.signal-item.active {
  background: rgba(88, 166, 255, 0.08);
  border-color: var(--q-accent);
}

.signal-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.signal-item-name {
  font-weight: 600;
  font-size: 13px;
  color: var(--q-text-primary);
}

.signal-item-desc {
  font-size: 11px;
  color: var(--q-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.list-empty {
  text-align: center;
  color: var(--q-text-muted);
  padding: 24px;
  font-size: 13px;
}

.empty-detail {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 400px;
  background: var(--q-bg-secondary);
  border: 1px solid var(--q-border);
  border-radius: 8px;
  color: var(--q-text-muted);
}

.detail-content {
  background: var(--q-bg-secondary);
  border: 1px solid var(--q-border);
  border-radius: 8px;
  padding: 20px;
  min-height: 500px;
}

.tab-toolbar {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.tab-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  color: var(--q-text-muted);
  font-size: 13px;
}

/* Coverage */
.coverage-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 10px;
}

.cov-card {
  background: var(--q-bg-primary);
  border: 1px solid var(--q-border);
  border-radius: 6px;
  padding: 12px;
  text-align: center;
}

.cov-label {
  font-size: 11px;
  color: var(--q-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.cov-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--q-text-primary);
}

.cov-long .cov-value { color: #3fb950; }
.cov-short .cov-value { color: #f85149; }
.cov-neutral .cov-value { color: var(--q-text-muted); }
.cov-coverage .cov-value { color: #58a6ff; }

/* Charts */
.chart-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chart-box {
  height: 300px;
  width: 100%;
  border: 1px solid var(--q-border);
  border-radius: 6px;
}

.signal-chart {
  height: 200px;
}

/* Forward Return */
.fwd-positive {
  color: #3fb950;
  font-weight: 600;
}

.fwd-negative {
  color: #f85149;
  font-weight: 600;
}
</style>
