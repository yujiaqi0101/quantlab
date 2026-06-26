<template>
  <div class="page-container">
    <el-alert
      type="warning"
      :closable="false"
      class="deprecated-banner"
      title="此页面已迁移至 Research Graph Studio"
      description="Factor Studio 已被 Research OS 替代。请使用新的 Research Graph Studio 进行因子研究、编译与执行。"
      show-icon
    >
      <template #default>
        <div class="deprecated-content">
          <div class="deprecated-text">
            <strong>Factor Studio 已迁移</strong> · 此页面为只读兼容模式，新功能请使用 Research Graph Studio。
          </div>
          <el-button type="primary" size="small" @click="$router.push('/research-graph')">
            前往 Research Graph Studio →
          </el-button>
        </div>
      </template>
    </el-alert>
    <div class="page-header">
      <div class="page-header-row">
        <div>
          <h1 class="page-title">因子工作室 Factor Studio <span class="deprecated-tag">DEPRECATED</span></h1>
          <p class="page-desc">研究、可视化和分析因子 Research, visualize, and analyze factors</p>
        </div>
        <div class="page-actions">
          <el-select v-model="selectedCategory" placeholder="分类 Category" clearable class="filter-select" @change="loadFactors">
            <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
          </el-select>
          <el-select v-model="selectedDataset" placeholder="数据集 Dataset" class="filter-select" @change="onDatasetChange">
            <el-option v-for="ds in datasets" :key="ds.dataset_id" :label="ds.name" :value="ds.dataset_id" />
          </el-select>
          <el-select v-model="selectedSymbol" placeholder="标的 Symbol" clearable class="filter-select" style="width:140px">
            <el-option v-for="s in symbols" :key="s" :label="s" :value="s" />
          </el-select>
          <el-button :icon="Refresh" circle @click="loadFactors" :loading="loading" />
        </div>
      </div>
    </div>

    <div class="page-content">
      <!-- Factor List -->
      <div class="factor-grid">
        <div
          v-for="f in factors"
          :key="f.name"
          class="factor-card"
          :class="{ active: selectedFactor === f.name }"
          @click="selectFactor(f.name)"
        >
          <div class="factor-card-header">
            <span class="factor-name">{{ f.name }}</span>
            <el-tag size="small" :type="categoryType(f.category)" effect="dark">{{ f.category }}</el-tag>
          </div>
          <div class="factor-desc">{{ f.description || '-' }}</div>
        </div>
      </div>

      <!-- Factor Detail Panel -->
      <div v-if="selectedFactor" class="detail-panel">
        <el-tabs v-model="activeTab" class="q-tabs">
          <!-- Visualization Tab -->
          <el-tab-pane label="可视化 Visualization" name="visualize">
            <div class="tab-toolbar">
              <el-button type="primary" size="small" :loading="vizLoading" :disabled="!selectedDatasetHasData" @click="loadVisualization">
                加载图表 Load Chart
              </el-button>
              <span v-if="!selectedDatasetHasData" class="no-data-tip">数据集无数据，请先加载数据</span>
            </div>
            <div v-if="vizData" class="chart-container">
              <div ref="priceChartRef" class="chart-box"></div>
              <div ref="factorChartRef" class="chart-box factor-chart"></div>
            </div>
            <div v-else class="tab-empty">选择数据集并点击加载图表来可视化因子 Select a dataset and click Load Chart to visualize the factor.</div>
          </el-tab-pane>

          <!-- IC Analysis Tab -->
          <el-tab-pane label="IC分析 IC Analysis" name="ic">
            <div class="tab-toolbar">
              <el-select v-model="icForwardPeriod" style="width:160px;margin-right:8px" size="small">
                <el-option :value="1" label="Forward 1 bar" />
                <el-option :value="5" label="Forward 5 bars" />
                <el-option :value="10" label="Forward 10 bars" />
                <el-option :value="20" label="Forward 20 bars" />
              </el-select>
              <el-button type="primary" size="small" :loading="icLoading" :disabled="!selectedDatasetHasData" @click="loadIC">
                Run IC Analysis
              </el-button>
              <span v-if="!selectedDatasetHasData" class="no-data-tip">数据集无数据，请先加载数据</span>
            </div>
            <div v-if="icData" class="ic-results">
              <div class="ic-stats-grid">
                <div class="ic-stat-card">
                  <div class="ic-stat-label">Mean IC</div>
                  <div class="ic-stat-value" :class="icColor(icData.ic_stats.mean_ic)">{{ icData.ic_stats.mean_ic }}</div>
                </div>
                <div class="ic-stat-card">
                  <div class="ic-stat-label">IC IR</div>
                  <div class="ic-stat-value" :class="icColor(icData.ic_stats.ic_ir)">{{ icData.ic_stats.ic_ir }}</div>
                </div>
                <div class="ic-stat-card">
                  <div class="ic-stat-label">IC > 0</div>
                  <div class="ic-stat-value">{{ (icData.ic_stats.ic_positive * 100).toFixed(1) }}%</div>
                </div>
                <div class="ic-stat-card">
                  <div class="ic-stat-label">Mean Rank IC</div>
                  <div class="ic-stat-value" :class="icColor(icData.rank_ic_stats.mean_ic)">{{ icData.rank_ic_stats.mean_ic }}</div>
                </div>
                <div class="ic-stat-card">
                  <div class="ic-stat-label">Rank IC IR</div>
                  <div class="ic-stat-value" :class="icColor(icData.rank_ic_stats.ic_ir)">{{ icData.rank_ic_stats.ic_ir }}</div>
                </div>
                <div class="ic-stat-card">
                  <div class="ic-stat-label">Turnover</div>
                  <div class="ic-stat-value">{{ icData.turnover }}</div>
                </div>
                <div class="ic-stat-card">
                  <div class="ic-stat-label">Coverage</div>
                  <div class="ic-stat-value">{{ (icData.coverage * 100).toFixed(1) }}%</div>
                </div>
                <div class="ic-stat-card">
                  <div class="ic-stat-label">Periods</div>
                  <div class="ic-stat-value">{{ icData.ic_stats.count }}</div>
                </div>
              </div>
              <div ref="icChartRef" class="chart-box ic-chart"></div>
            </div>
            <div v-else class="tab-empty">Click Run IC Analysis to compute Information Coefficient.</div>
          </el-tab-pane>

          <!-- Correlation Tab -->
          <el-tab-pane label="Correlation" name="correlation">
            <div class="tab-toolbar">
              <el-select v-model="corrFactors" multiple placeholder="Select factors" class="corr-select" size="small">
                <el-option v-for="f in factors" :key="f.name" :label="f.name" :value="f.name" />
              </el-select>
              <el-button type="primary" size="small" :loading="corrLoading" @click="loadCorrelation" :disabled="corrFactors.length < 2 || !selectedDatasetHasData">
                Compute Correlation
              </el-button>
              <span v-if="!selectedDatasetHasData" class="no-data-tip">数据集无数据，请先加载数据</span>
            </div>
            <div v-if="corrData" class="corr-container">
              <div ref="corrChartRef" class="chart-box corr-chart"></div>
            </div>
            <div v-else class="tab-empty">Select at least 2 factors and compute correlation.</div>
          </el-tab-pane>
        </el-tabs>
      </div>

      <!-- Empty State -->
      <div v-if="!selectedFactor && factors.length > 0" class="empty-detail">
        <p>Select a factor to explore</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import {
  getFactorList,
  getFactorCategories,
  type FactorInfo,
  type VisualizeResult,
  type ICResult,
  type CorrelationResult,
  visualizeFactor,
  getFactorIC,
  getFactorCorrelation,
} from '@/api/factor'
import { http } from '@/api/http'

// ---- State ----
const loading = ref(false)
const factors = ref<FactorInfo[]>([])
const categories = ref<string[]>([])
const selectedCategory = ref('')
const selectedFactor = ref('')
const activeTab = ref('visualize')

// Dataset / Symbol
const datasets = ref<any[]>([])
const selectedDataset = ref('')
const symbols = ref<string[]>([])
const selectedSymbol = ref('')

// 当前选中的数据集是否有数据（无数据时禁用分析类按钮，避免触发 400）
const selectedDatasetHasData = computed(() => {
  if (!selectedDataset.value) return false
  const ds = datasets.value.find(d => d.dataset_id === selectedDataset.value)
  return !!(ds && ds.has_data)
})

// Visualization
const vizLoading = ref(false)
const vizData = ref<VisualizeResult | null>(null)
const priceChartRef = ref<HTMLElement>()
const factorChartRef = ref<HTMLElement>()
let priceChart: echarts.ECharts | null = null
let factorChart: echarts.ECharts | null = null

// IC Analysis
const icLoading = ref(false)
const icData = ref<ICResult | null>(null)
const icForwardPeriod = ref(1)
const icChartRef = ref<HTMLElement>()
let icChart: echarts.ECharts | null = null

// Correlation
const corrLoading = ref(false)
const corrData = ref<CorrelationResult | null>(null)
const corrFactors = ref<string[]>([])
const corrChartRef = ref<HTMLElement>()
let corrChart: echarts.ECharts | null = null

// ---- Load Factors ----
async function loadFactors() {
  loading.value = true
  try {
    factors.value = await getFactorList(selectedCategory.value || undefined)
  } catch (e) {
    console.error('Failed to load factors', e)
  } finally {
    loading.value = false
  }
}

async function loadCategories() {
  try {
    categories.value = await getFactorCategories()
  } catch (e) {
    console.error('Failed to load categories', e)
  }
}

// ---- Dataset ----
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

// ---- Select Factor ----
function selectFactor(name: string) {
  selectedFactor.value = name
  vizData.value = null
  icData.value = null
  corrData.value = null
  // Auto-add to correlation selection
  if (!corrFactors.value.includes(name)) {
    corrFactors.value.push(name)
  }
}

// ---- Category tag type ----
function categoryType(cat: string): string {
  const map: Record<string, string> = {
    trend: '', momentum: 'success', volatility: 'warning',
    volume: 'info', cross_sectional: 'danger', fundamental: '',
    composite: 'info',
  }
  return map[cat] || ''
}

// ---- IC color ----
function icColor(val: number): string {
  if (val > 0.03) return 'ic-positive'
  if (val < -0.03) return 'ic-negative'
  return 'ic-neutral'
}

// ---- Visualization ----
async function loadVisualization() {
  if (!selectedFactor.value || !selectedDataset.value) return
  vizLoading.value = true
  try {
    vizData.value = await visualizeFactor(
      selectedFactor.value,
      selectedDataset.value,
      selectedSymbol.value,
    )
    await nextTick()
    renderVizCharts()
  } catch (e: any) {
    console.error('Viz error', e)
    vizData.value = null
  } finally {
    vizLoading.value = false
  }
}

function renderVizCharts() {
  if (!vizData.value) return

  // Price chart (candlestick)
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

  // Factor chart
  if (factorChartRef.value) {
    factorChart = echarts.init(factorChartRef.value)
    const d = vizData.value
    const dates = d.factor.map(f => f.t.slice(0, 10))
    const vals = d.factor.map(f => f.v)
    factorChart.setOption({
      backgroundColor: 'transparent',
      animation: false,
      tooltip: { trigger: 'axis' },
      grid: { left: 60, right: 20, top: 30, bottom: 30 },
      xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 10, color: '#8b949e' }, axisLine: { lineStyle: { color: '#1b2332' } } },
      yAxis: { splitLine: { lineStyle: { color: '#1b2332' } }, axisLabel: { fontSize: 10, color: '#8b949e' } },
      series: [{
        type: 'line',
        data: vals,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#58a6ff', width: 1.5 },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(88,166,255,0.25)' },
          { offset: 1, color: 'rgba(88,166,255,0.02)' },
        ]) },
      }],
      title: { text: d.factor_name, left: 'center', textStyle: { color: '#c9d1d9', fontSize: 13 } },
    })
  }
}

// ---- IC Analysis ----
async function loadIC() {
  if (!selectedFactor.value || !selectedDataset.value) return
  icLoading.value = true
  try {
    icData.value = await getFactorIC(
      selectedFactor.value,
      selectedDataset.value,
      selectedSymbol.value,
      icForwardPeriod.value,
    )
    await nextTick()
    renderICChart()
  } catch (e) {
    console.error('IC error', e)
    icData.value = null
  } finally {
    icLoading.value = false
  }
}

function renderICChart() {
  if (!icData.value || !icChartRef.value) return
  icChart = echarts.init(icChartRef.value)
  const d = icData.value
  const dates = d.ic_series.map(x => x.t.slice(0, 10))
  const icVals = d.ic_series.map(x => x.v)
  const rankIcVals = d.rank_ic_series.map(x => x.v)

  icChart.setOption({
    backgroundColor: 'transparent',
    animation: false,
    tooltip: { trigger: 'axis' },
    legend: { data: ['IC', 'Rank IC'], top: 5, textStyle: { color: '#8b949e', fontSize: 11 } },
    grid: { left: 60, right: 20, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 10, color: '#8b949e' }, axisLine: { lineStyle: { color: '#1b2332' } } },
    yAxis: { splitLine: { lineStyle: { color: '#1b2332' } }, axisLabel: { fontSize: 10, color: '#8b949e' } },
    series: [
      {
        name: 'IC',
        type: 'bar',
        data: icVals,
        itemStyle: { color: (p: any) => p.value >= 0 ? '#3fb950' : '#f85149' },
      },
      {
        name: 'Rank IC',
        type: 'line',
        data: rankIcVals,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#58a6ff', width: 1.5 },
      },
    ],
  })
}

// ---- Correlation ----
async function loadCorrelation() {
  if (corrFactors.value.length < 2 || !selectedDataset.value) return
  corrLoading.value = true
  try {
    corrData.value = await getFactorCorrelation(
      corrFactors.value,
      selectedDataset.value,
      selectedSymbol.value,
    )
    await nextTick()
    renderCorrChart()
  } catch (e) {
    console.error('Correlation error', e)
    corrData.value = null
  } finally {
    corrLoading.value = false
  }
}

function renderCorrChart() {
  if (!corrData.value || !corrChartRef.value) return
  corrChart = echarts.init(corrChartRef.value)
  const d = corrData.value
  const labels = d.labels
  const matrix = d.matrix

  // Build heatmap data
  const heatData: any[] = []
  let minVal = 1, maxVal = -1
  for (let i = 0; i < labels.length; i++) {
    for (let j = 0; j < labels.length; j++) {
      const v = matrix[i][j] ?? 0
      heatData.push([j, i, v])
      if (i !== j) {
        minVal = Math.min(minVal, v)
        maxVal = Math.max(maxVal, v)
      }
    }
  }

  corrChart.setOption({
    backgroundColor: 'transparent',
    animation: false,
    tooltip: {
      formatter: (p: any) => {
        const [x, y, v] = p.data
        return `${labels[y]} vs ${labels[x]}: ${v.toFixed(4)}`
      },
    },
    grid: { left: 100, right: 40, top: 10, bottom: 60 },
    xAxis: { type: 'category', data: labels, axisLabel: { fontSize: 10, color: '#8b949e', rotate: 30 }, axisLine: { lineStyle: { color: '#1b2332' } } },
    yAxis: { type: 'category', data: labels, axisLabel: { fontSize: 10, color: '#8b949e' }, axisLine: { lineStyle: { color: '#1b2332' } } },
    visualMap: {
      min: -1, max: 1,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      inRange: { color: ['#f85149', '#1b2332', '#3fb950'] },
      textStyle: { color: '#8b949e' },
    },
    series: [{
      type: 'heatmap',
      data: heatData,
      label: {
        show: true,
        formatter: (p: any) => p.data[2].toFixed(2),
        fontSize: 10,
        color: '#c9d1d9',
      },
    }],
  })
}

// ---- Lifecycle ----
onMounted(async () => {
  await Promise.all([loadFactors(), loadCategories(), loadDatasets()])
})

// Resize
window.addEventListener('resize', () => {
  priceChart?.resize()
  factorChart?.resize()
  icChart?.resize()
  corrChart?.resize()
})
</script>

<style scoped>
.deprecated-banner {
  margin-bottom: 16px;
}

.deprecated-content {
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
}

.deprecated-text { flex: 1; }

.deprecated-tag {
  display: inline-block;
  padding: 2px 8px;
  background: #e6a23c;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1px;
  border-radius: 2px;
  margin-left: 8px;
  vertical-align: middle;
}

.page-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.page-header {
  margin-bottom: 20px;
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

.factor-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

.factor-card {
  background: var(--q-bg-secondary);
  border: 1px solid var(--q-border);
  border-radius: 8px;
  padding: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.factor-card:hover {
  border-color: var(--q-accent);
}

.factor-card.active {
  border-color: var(--q-accent);
  background: rgba(88, 166, 255, 0.08);
}

.factor-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.factor-name {
  font-weight: 600;
  font-size: 14px;
  color: var(--q-text-primary);
}

.factor-desc {
  font-size: 12px;
  color: var(--q-text-muted);
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-panel {
  background: var(--q-bg-secondary);
  border: 1px solid var(--q-border);
  border-radius: 8px;
  padding: 20px;
  min-height: 400px;
}

.tab-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.no-data-tip {
  color: #f85149;
  font-size: 12px;
}

.tab-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  color: var(--q-text-muted);
  font-size: 14px;
}

.empty-detail {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  color: var(--q-text-muted);
}

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

.factor-chart {
  height: 250px;
}

.ic-chart {
  height: 300px;
}

.corr-chart {
  height: 400px;
}

.corr-select {
  width: 400px;
}

.ic-stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.ic-stat-card {
  background: var(--q-bg-primary);
  border: 1px solid var(--q-border);
  border-radius: 6px;
  padding: 12px;
  text-align: center;
}

.ic-stat-label {
  font-size: 11px;
  color: var(--q-text-muted);
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.ic-stat-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--q-text-primary);
}

.ic-positive {
  color: #3fb950 !important;
}

.ic-negative {
  color: #f85149 !important;
}

.ic-neutral {
  color: var(--q-text-secondary) !important;
}
</style>
