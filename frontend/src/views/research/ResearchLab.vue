<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-header-row">
        <div>
          <h1 class="page-title">Research Lab</h1>
          <p class="page-desc">Parameter sweep, heatmap, walk-forward, robustness analysis</p>
        </div>
      </div>
    </div>

    <div class="page-content">
      <el-tabs v-model="activeTab" class="q-tabs">
        <!-- ==================== Parameter Sweep ==================== -->
        <el-tab-pane label="Parameter Sweep" name="sweep">
          <div class="sweep-layout">
            <!-- Left: Config -->
            <div class="sweep-config">
              <h3 class="section-title">Sweep Configuration</h3>

              <div class="form-group">
                <label>Strategy</label>
                <el-input v-model="sweepStrategyId" placeholder="e.g. ma_cross" />
              </div>

              <div class="form-group">
                <label>Dataset</label>
                <el-input v-model="sweepDatasetId" placeholder="default" />
              </div>

              <div class="form-group">
                <label>Parameters</label>
                <div v-for="(vals, key) in sweepParamSpace" :key="key" class="param-row">
                  <el-input :model-value="key" class="param-key" disabled />
                  <el-input
                    :model-value="vals.join(',')"
                    class="param-vals"
                    @update:model-value="(v: string) => updateParamSpace(key, v)"
                    placeholder="5,10,20"
                  />
                  <el-button :icon="Delete" circle size="small" @click="removeParam(key)" />
                </div>
                <div class="param-row">
                  <el-input v-model="newParamKey" placeholder="param name" class="param-key" />
                  <el-input v-model="newParamVals" placeholder="5,10,20" class="param-vals" />
                  <el-button :icon="Plus" circle size="small" type="primary" @click="addParam" />
                </div>
              </div>

              <el-button type="primary" :loading="sweepLoading" @click="runSweep" style="width:100%">
                Run Sweep
              </el-button>

              <!-- Sweep History -->
              <div v-if="sweepHistory.length" class="sweep-history">
                <h4 class="sub-title">Sweep History</h4>
                <div
                  v-for="s in sweepHistory"
                  :key="s.sweep_id"
                  class="sweep-item"
                  :class="{ active: currentSweepId === s.sweep_id }"
                  @click="selectSweep(s.sweep_id)"
                >
                  <span class="sweep-id">{{ s.sweep_id }}</span>
                  <span class="sweep-info">{{ s.strategy_id }} | {{ s.total_combos }} combos</span>
                </div>
              </div>
            </div>

            <!-- Right: Results -->
            <div class="sweep-results">
              <div v-if="sweepResult" class="results-content">
                <div class="stats-bar">
                  <div class="stat-item">
                    <span class="stat-label">Total</span>
                    <span class="stat-value">{{ sweepResult.total_combos }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Completed</span>
                    <span class="stat-value">{{ sweepResult.completed }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Best Sharpe</span>
                    <span class="stat-value highlight">{{ bestSharpe }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Avg Sharpe</span>
                    <span class="stat-value">{{ avgSharpe }}</span>
                  </div>
                </div>

                <!-- Results Table -->
                <el-table :data="sweepResult.results" stripe size="small" max-height="400" default-sort="{ prop: 'sharpe', order: descending }">
                  <el-table-column v-for="p in paramKeys" :key="p" :prop="'params.' + p" :label="p" width="100" sortable />
                  <el-table-column prop="sharpe" label="Sharpe" width="90" sortable>
                    <template #default="{ row }">
                      <span :class="row.sharpe > 1.5 ? 'text-green' : row.sharpe > 0 ? 'text-yellow' : 'text-red'">
                        {{ row.sharpe?.toFixed(2) }}
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="total_return" label="Return" width="90" sortable>
                    <template #default="{ row }">
                      <span :class="row.total_return > 0 ? 'text-green' : 'text-red'">
                        {{ (row.total_return * 100).toFixed(1) }}%
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="max_drawdown" label="MaxDD" width="90" sortable>
                    <template #default="{ row }">
                      {{ (row.max_drawdown * 100).toFixed(1) }}%
                    </template>
                  </el-table-column>
                  <el-table-column prop="trade_count" label="Trades" width="80" sortable />
                  <el-table-column prop="win_rate" label="WinRate" width="80" sortable>
                    <template #default="{ row }">
                      {{ (row.win_rate * 100).toFixed(0) }}%
                    </template>
                  </el-table-column>
                </el-table>
              </div>
              <div v-else class="tab-empty">Configure parameters and run a sweep to see results.</div>
            </div>
          </div>
        </el-tab-pane>

        <!-- ==================== Heatmap ==================== -->
        <el-tab-pane label="Heatmap" name="heatmap">
          <div v-if="currentSweepId" class="heatmap-section">
            <div class="tab-toolbar">
              <el-select v-model="heatmapXParam" placeholder="X Axis" style="width:160px;margin-right:8px" size="small">
                <el-option v-for="p in paramKeys" :key="p" :label="p" :value="p" />
              </el-select>
              <el-select v-model="heatmapYParam" placeholder="Y Axis" style="width:160px;margin-right:8px" size="small">
                <el-option v-for="p in paramKeys" :key="p" :label="p" :value="p" />
              </el-select>
              <el-select v-model="heatmapMetric" style="width:140px;margin-right:8px" size="small">
                <el-option value="sharpe" label="Sharpe" />
                <el-option value="total_return" label="Return" />
                <el-option value="max_drawdown" label="MaxDD" />
              </el-select>
              <el-button type="primary" size="small" :loading="heatmapLoading" @click="loadHeatmap">
                Generate Heatmap
              </el-button>
            </div>
            <div v-if="heatmapData" ref="heatmapChartRef" class="chart-box" style="height:420px"></div>
            <div v-else class="tab-empty">Select X/Y parameters and generate heatmap.</div>
          </div>
          <div v-else class="tab-empty">Run a parameter sweep first.</div>
        </el-tab-pane>

        <!-- ==================== Walk Forward ==================== -->
        <el-tab-pane label="Walk Forward" name="walkforward">
          <div class="wf-section">
            <div class="tab-toolbar">
              <el-select v-model="wfStrategyId" placeholder="Strategy" style="width:160px;margin-right:8px" size="small">
                <el-option value="ma_cross" label="MA Cross" />
                <el-option value="rsi_reversal" label="RSI Reversal" />
              </el-select>
              <el-input-number v-model="wfTrainYears" :min="1" :max="10" size="small" style="width:120px;margin-right:8px" />
              <span style="margin-right:4px;color:#8b949e">train yrs</span>
              <el-input-number v-model="wfTestYears" :min="1" :max="5" size="small" style="width:120px;margin-right:8px" />
              <span style="margin-right:8px;color:#8b949e">test yrs</span>
              <el-button type="primary" size="small" :loading="wfLoading" @click="runWalkForward">
                Run Walk Forward
              </el-button>
            </div>

            <div v-if="wfResult" class="wf-results">
              <div class="stats-bar">
                <div class="stat-item">
                  <span class="stat-label">Windows</span>
                  <span class="stat-value">{{ wfResult.n_windows }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">Avg OOS Sharpe</span>
                  <span class="stat-value highlight">{{ wfResult.avg_test_sharpe?.toFixed(2) }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">Avg OOS Return</span>
                  <span class="stat-value">{{ (wfResult.avg_test_return * 100).toFixed(1) }}%</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label">Stability</span>
                  <span class="stat-value" :class="wfResult.stability_score > 0.6 ? 'text-green' : 'text-yellow'">
                    {{ (wfResult.stability_score * 100).toFixed(0) }}%
                  </span>
                </div>
              </div>

              <el-table :data="wfResult.windows" stripe size="small">
                <el-table-column prop="window_id" label="#" width="50" />
                <el-table-column prop="train_period" label="Train" width="120" />
                <el-table-column prop="test_period" label="Test" width="80" />
                <el-table-column prop="train_sharpe" label="Train Sharpe" width="120" sortable>
                  <template #default="{ row }">{{ row.train_sharpe?.toFixed(2) }}</template>
                </el-table-column>
                <el-table-column prop="test_sharpe" label="Test Sharpe" width="120" sortable>
                  <template #default="{ row }">
                    <span :class="row.test_sharpe > 0 ? 'text-green' : 'text-red'">
                      {{ row.test_sharpe?.toFixed(2) }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="test_return" label="Test Return" width="110">
                  <template #default="{ row }">
                    <span :class="row.test_return > 0 ? 'text-green' : 'text-red'">
                      {{ (row.test_return * 100).toFixed(1) }}%
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="test_max_dd" label="MaxDD" width="90">
                  <template #default="{ row }">{{ (row.test_max_dd * 100).toFixed(1) }}%</template>
                </el-table-column>
                <el-table-column label="Best Params" min-width="160">
                  <template #default="{ row }">
                    <span v-for="(v, k) in row.best_params" :key="k" class="param-tag">
                      {{ k }}={{ v }}
                    </span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            <div v-else class="tab-empty">Configure and run a Walk Forward test.</div>
          </div>
        </el-tab-pane>

        <!-- ==================== Candidates ==================== -->
        <el-tab-pane label="Candidates" name="candidates">
          <div v-if="currentSweepId" class="candidate-section">
            <div class="tab-toolbar">
              <span style="color:#8b949e;margin-right:8px">Filter:</span>
              <el-input-number v-model="candMinSharpe" :step="0.1" :min="0" size="small" style="width:120px;margin-right:8px" />
              <span style="color:#8b949e;margin-right:4px">min Sharpe</span>
              <el-input-number v-model="candMaxDD" :step="0.05" :min="0" :max="1" size="small" style="width:120px;margin-right:8px" />
              <span style="color:#8b949e;margin-right:4px">max DD</span>
              <el-input-number v-model="candMinTrades" :step="10" :min="0" size="small" style="width:120px;margin-right:8px" />
              <span style="color:#8b949e;margin-right:8px">min trades</span>
              <el-button type="primary" size="small" :loading="candLoading" @click="loadCandidates">
                Find Candidates
              </el-button>
            </div>

            <div v-if="candidateResult">
              <div class="stats-bar">
                <div class="stat-item">
                  <span class="stat-label">Found</span>
                  <span class="stat-value highlight">{{ candidateResult.count }}</span>
                </div>
              </div>

              <el-table v-if="candidateResult.candidates.length" :data="candidateResult.candidates" stripe size="small">
                <el-table-column v-for="p in paramKeys" :key="'c'+p" :prop="'params.' + p" :label="p" width="100" />
                <el-table-column prop="sharpe" label="Sharpe" width="90" sortable>
                  <template #default="{ row }">
                    <span class="text-green">{{ row.sharpe?.toFixed(2) }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="total_return" label="Return" width="90">
                  <template #default="{ row }">{{ (row.total_return * 100).toFixed(1) }}%</template>
                </el-table-column>
                <el-table-column prop="max_drawdown" label="MaxDD" width="90">
                  <template #default="{ row }">{{ (row.max_drawdown * 100).toFixed(1) }}%</template>
                </el-table-column>
                <el-table-column prop="trade_count" label="Trades" width="80" />
                <el-table-column prop="win_rate" label="WinRate" width="80">
                  <template #default="{ row }">{{ (row.win_rate * 100).toFixed(0) }}%</template>
                </el-table-column>
              </el-table>
              <div v-else class="tab-empty">No candidates match the criteria. Try relaxing the filters.</div>
            </div>
            <div v-else class="tab-empty">Click "Find Candidates" to auto-filter strategies.</div>
          </div>
          <div v-else class="tab-empty">Run a parameter sweep first.</div>
        </el-tab-pane>

        <!-- ==================== Robustness ==================== -->
        <el-tab-pane label="Robustness" name="robustness">
          <div v-if="currentSweepId" class="robustness-section">
            <div class="tab-toolbar">
              <el-select v-model="robustnessMetric" style="width:140px;margin-right:8px" size="small">
                <el-option value="sharpe" label="Sharpe" />
                <el-option value="total_return" label="Return" />
              </el-select>
              <el-button type="primary" size="small" :loading="robLoading" @click="loadRobustness">
                Calculate Robustness
              </el-button>
            </div>

            <div v-if="robustnessData" class="robustness-results">
              <div class="robustness-grid">
                <div class="rob-card">
                  <div class="rob-label">Best Params</div>
                  <div class="rob-value">
                    <span v-for="(v, k) in robustnessData.best_params" :key="k" class="param-tag">
                      {{ k }}={{ v }}
                    </span>
                  </div>
                </div>
                <div class="rob-card">
                  <div class="rob-label">Best {{ robustnessMetric }}</div>
                  <div class="rob-value highlight">{{ robustnessData.best_metric }}</div>
                </div>
                <div class="rob-card">
                  <div class="rob-label">Neighbors</div>
                  <div class="rob-value">{{ robustnessData.neighbor_count }}</div>
                </div>
                <div class="rob-card">
                  <div class="rob-label">Neighbor Std</div>
                  <div class="rob-value">{{ robustnessData.neighbor_std }}</div>
                </div>
                <div class="rob-card big">
                  <div class="rob-label">Robustness Score</div>
                  <div class="rob-value" :class="robustnessData.robustness > 0.6 ? 'text-green' : robustnessData.robustness > 0.3 ? 'text-yellow' : 'text-red'">
                    {{ (robustnessData.robustness * 100).toFixed(0) }}%
                  </div>
                  <div class="rob-hint">
                    {{ robustnessData.robustness > 0.6 ? 'Stable - parameter changes have limited impact' :
                       robustnessData.robustness > 0.3 ? 'Moderate - some sensitivity to parameter changes' :
                       'Fragile - small parameter changes cause large performance shifts' }}
                  </div>
                </div>
              </div>

              <div v-if="robustnessData.neighbor_metrics" class="neighbor-chart">
                <h4 class="sub-title">Neighbor Performance Distribution</h4>
                <div ref="robustnessChartRef" class="chart-box" style="height:280px"></div>
              </div>
            </div>
            <div v-else class="tab-empty">Click "Calculate Robustness" to evaluate parameter stability.</div>
          </div>
          <div v-else class="tab-empty">Run a parameter sweep first.</div>
        </el-tab-pane>

        <!-- ==================== Report ==================== -->
        <el-tab-pane label="Report" name="report">
          <div v-if="currentSweepId" class="report-section">
            <div class="tab-toolbar">
              <el-button type="primary" :loading="reportLoading" @click="loadReport">
                Generate Report
              </el-button>
            </div>

            <div v-if="reportData" class="report-content">
              <div class="report-header">
                <h2>Research Report</h2>
                <p>{{ reportData.strategy_id }} | {{ reportData.dataset_id }} | {{ reportData.generated_at }}</p>
              </div>

              <div class="report-section-block">
                <h3>Overview</h3>
                <div class="stats-bar">
                  <div class="stat-item">
                    <span class="stat-label">Best Sharpe</span>
                    <span class="stat-value highlight">{{ reportData.overview.best_sharpe?.toFixed(2) }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Best Return</span>
                    <span class="stat-value">{{ (reportData.overview.best_return * 100).toFixed(1) }}%</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Avg Sharpe</span>
                    <span class="stat-value">{{ reportData.overview.avg_sharpe?.toFixed(2) }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Total Combos</span>
                    <span class="stat-value">{{ reportData.total_combos }}</span>
                  </div>
                </div>
              </div>

              <div v-if="reportData.robustness" class="report-section-block">
                <h3>Robustness</h3>
                <div class="stats-bar">
                  <div class="stat-item">
                    <span class="stat-label">Score</span>
                    <span class="stat-value" :class="reportData.robustness.robustness > 0.6 ? 'text-green' : 'text-yellow'">
                      {{ (reportData.robustness.robustness * 100).toFixed(0) }}%
                    </span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Neighbor Std</span>
                    <span class="stat-value">{{ reportData.robustness.neighbor_std }}</span>
                  </div>
                </div>
              </div>

              <div v-if="reportData.candidates" class="report-section-block">
                <h3>Candidates ({{ reportData.candidates.count }})</h3>
                <el-table v-if="reportData.candidates.top5.length" :data="reportData.candidates.top5" stripe size="small">
                  <el-table-column v-for="p in paramKeys" :key="'r'+p" :prop="'params.' + p" :label="p" width="100" />
                  <el-table-column prop="sharpe" label="Sharpe" width="90" />
                  <el-table-column prop="total_return" label="Return" width="90">
                    <template #default="{ row }">{{ (row.total_return * 100).toFixed(1) }}%</template>
                  </el-table-column>
                </el-table>
              </div>
            </div>
            <div v-else class="tab-empty">Click "Generate Report" to create a research report.</div>
          </div>
          <div v-else class="tab-empty">Run a parameter sweep first.</div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { Delete, Plus } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import {
  runSweep as apiRunSweep,
  listSweeps as apiListSweeps,
  getSweep as apiGetSweep,
  getHeatmap as apiGetHeatmap,
  getRobustness as apiGetRobustness,
  getCandidates as apiGetCandidates,
  runWalkForward as apiRunWalkForward,
  generateReport as apiGenerateReport,
  type SweepResult,
  type SweepSummary,
  type HeatmapData,
  type RobustnessResult,
  type CandidateResult,
  type WalkForwardResult,
  type ResearchReport,
} from '@/api/research'

// ---- State ----
const activeTab = ref('sweep')

// Sweep
const sweepStrategyId = ref('ma_cross')
const sweepDatasetId = ref('default')
const sweepParamSpace = ref<Record<string, number[]>>({
  fast_window: [5, 10, 20, 30],
  slow_window: [60, 120, 240],
})
const newParamKey = ref('')
const newParamVals = ref('')
const sweepLoading = ref(false)
const sweepResult = ref<SweepResult | null>(null)
const sweepHistory = ref<SweepSummary[]>([])
const currentSweepId = ref('')

// Heatmap
const heatmapXParam = ref('')
const heatmapYParam = ref('')
const heatmapMetric = ref('sharpe')
const heatmapLoading = ref(false)
const heatmapData = ref<HeatmapData | null>(null)
const heatmapChartRef = ref<HTMLElement>()

// Walk Forward
const wfStrategyId = ref('ma_cross')
const wfTrainYears = ref(3)
const wfTestYears = ref(1)
const wfLoading = ref(false)
const wfResult = ref<WalkForwardResult | null>(null)

// Candidates
const candMinSharpe = ref(1.5)
const candMaxDD = ref(0.2)
const candMinTrades = ref(50)
const candLoading = ref(false)
const candidateResult = ref<CandidateResult | null>(null)

// Robustness
const robustnessMetric = ref('sharpe')
const robLoading = ref(false)
const robustnessData = ref<RobustnessResult | null>(null)
const robustnessChartRef = ref<HTMLElement>()

// Report
const reportLoading = ref(false)
const reportData = ref<ResearchReport | null>(null)

// ---- Computed ----
const paramKeys = computed(() => {
  if (sweepResult.value) {
    const first = sweepResult.value.results[0]
    if (first) return Object.keys(first.params)
  }
  return Object.keys(sweepParamSpace.value)
})

const bestSharpe = computed(() => {
  if (!sweepResult.value?.results.length) return '-'
  return Math.max(...sweepResult.value.results.map(r => r.sharpe)).toFixed(2)
})

const avgSharpe = computed(() => {
  if (!sweepResult.value?.results.length) return '-'
  const avg = sweepResult.value.results.reduce((s, r) => s + r.sharpe, 0) / sweepResult.value.results.length
  return avg.toFixed(2)
})

// ---- Param Space Management ----
function updateParamSpace(key: string, valStr: string) {
  const vals = valStr.split(',').map(v => Number(v.trim())).filter(v => !isNaN(v))
  sweepParamSpace.value[key] = vals
}

function addParam() {
  if (!newParamKey.value || !newParamVals.value) return
  const vals = newParamVals.value.split(',').map(v => Number(v.trim())).filter(v => !isNaN(v))
  if (vals.length) {
    sweepParamSpace.value[newParamKey.value] = vals
    newParamKey.value = ''
    newParamVals.value = ''
  }
}

function removeParam(key: string) {
  delete sweepParamSpace.value[key]
  sweepParamSpace.value = { ...sweepParamSpace.value }
}

// ---- API Calls ----
async function runSweep() {
  sweepLoading.value = true
  try {
    const result = await apiRunSweep(
      sweepStrategyId.value,
      sweepParamSpace.value,
      sweepDatasetId.value,
      true,
    )
    sweepResult.value = result
    currentSweepId.value = result.sweep_id
    // Set default heatmap params
    const keys = Object.keys(sweepParamSpace.value)
    if (keys.length >= 2) {
      heatmapXParam.value = keys[0]
      heatmapYParam.value = keys[1]
    }
    await loadSweepHistory()
  } catch (e: any) {
    console.error('Sweep failed:', e)
  } finally {
    sweepLoading.value = false
  }
}

async function loadSweepHistory() {
  try {
    sweepHistory.value = await apiListSweeps()
  } catch { /* ignore */ }
}

async function selectSweep(sweepId: string) {
  currentSweepId.value = sweepId
  try {
    sweepResult.value = await apiGetSweep(sweepId)
    const keys = Object.keys(sweepResult.value.param_space || {})
    if (keys.length >= 2) {
      heatmapXParam.value = keys[0]
      heatmapYParam.value = keys[1]
    }
  } catch { /* ignore */ }
}

async function loadHeatmap() {
  if (!currentSweepId.value || !heatmapXParam.value || !heatmapYParam.value) return
  heatmapLoading.value = true
  try {
    heatmapData.value = await apiGetHeatmap(
      currentSweepId.value,
      heatmapXParam.value,
      heatmapYParam.value,
      heatmapMetric.value,
    )
    await nextTick()
    renderHeatmap()
  } catch (e: any) {
    console.error('Heatmap failed:', e)
  } finally {
    heatmapLoading.value = false
  }
}

async function runWalkForward() {
  wfLoading.value = true
  try {
    wfResult.value = await apiRunWalkForward(
      wfStrategyId.value,
      sweepParamSpace.value,
      sweepDatasetId.value,
      wfTrainYears.value,
      wfTestYears.value,
    )
  } catch (e: any) {
    console.error('Walk Forward failed:', e)
  } finally {
    wfLoading.value = false
  }
}

async function loadCandidates() {
  if (!currentSweepId.value) return
  candLoading.value = true
  try {
    candidateResult.value = await apiGetCandidates(
      currentSweepId.value,
      candMinSharpe.value,
      candMaxDD.value,
      candMinTrades.value,
    )
  } catch (e: any) {
    console.error('Candidates failed:', e)
  } finally {
    candLoading.value = false
  }
}

async function loadRobustness() {
  if (!currentSweepId.value) return
  robLoading.value = true
  try {
    robustnessData.value = await apiGetRobustness(
      currentSweepId.value,
      paramKeys.value,
      robustnessMetric.value,
    )
    await nextTick()
    renderRobustnessChart()
  } catch (e: any) {
    console.error('Robustness failed:', e)
  } finally {
    robLoading.value = false
  }
}

async function loadReport() {
  if (!currentSweepId.value) return
  reportLoading.value = true
  try {
    reportData.value = await apiGenerateReport(currentSweepId.value)
  } catch (e: any) {
    console.error('Report failed:', e)
  } finally {
    reportLoading.value = false
  }
}

// ---- Charts ----
let heatmapChart: echarts.ECharts | null = null
let robChart: echarts.ECharts | null = null

function renderHeatmap() {
  if (!heatmapChartRef.value || !heatmapData.value) return
  if (!heatmapChart) {
    heatmapChart = echarts.init(heatmapChartRef.value)
  }

  const hm = heatmapData.value
  const seriesData: [number, number, number | null][] = []
  let minVal = Infinity, maxVal = -Infinity
  for (let yi = 0; yi < hm.y_values.length; yi++) {
    for (let xi = 0; xi < hm.x_values.length; xi++) {
      const v = hm.matrix[yi][xi]
      seriesData.push([xi, yi, v])
      if (v !== null) {
        minVal = Math.min(minVal, v)
        maxVal = Math.max(maxVal, v)
      }
    }
  }

  heatmapChart.setOption({
    tooltip: {
      formatter: (p: any) => {
        const d = p.data
        return `${hm.x_label}=${hm.x_values[d[0]]}<br/>${hm.y_label}=${hm.y_values[d[1]]}<br/>${hm.metric}=${d[2]}`
      },
    },
    grid: { top: 30, right: 80, bottom: 60, left: 80 },
    xAxis: {
      type: 'category',
      data: hm.x_values.map(String),
      name: hm.x_label,
      splitArea: { show: true },
    },
    yAxis: {
      type: 'category',
      data: hm.y_values.map(String),
      name: hm.y_label,
      splitArea: { show: true },
    },
    visualMap: {
      min: minVal,
      max: maxVal,
      calculable: true,
      orient: 'vertical',
      right: 10,
      top: 'center',
      inRange: {
        color: ['#313695', '#4575b4', '#74add1', '#abd9e9', '#e0f3f8',
                '#ffffbf', '#fee090', '#fdae61', '#f46d43', '#d73027', '#a50026'],
      },
    },
    series: [{
      type: 'heatmap',
      data: seriesData,
      label: { show: true, fontSize: 11 },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.5)' } },
    }],
  })
}

function renderRobustnessChart() {
  if (!robustnessChartRef.value || !robustnessData.value?.neighbor_metrics) return
  if (!robChart) {
    robChart = echarts.init(robustnessChartRef.value)
  }

  const metrics = robustnessData.value.neighbor_metrics
  const best = robustnessData.value.best_metric

  robChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { top: 20, right: 20, bottom: 30, left: 50 },
    xAxis: { type: 'category', data: metrics.map((_, i) => `N${i + 1}`) },
    yAxis: { type: 'value', name: robustnessMetric.value },
    series: [
      {
        type: 'bar',
        data: metrics.map(m => ({
          value: m,
          itemStyle: { color: m > 0 ? '#67c23a' : '#f56c6c' },
        })),
      },
      {
        type: 'line',
        data: metrics.map(() => best),
        lineStyle: { color: '#409eff', type: 'dashed' },
        symbol: 'none',
        markLine: {
          data: [{ yAxis: best, name: 'Best' }],
          lineStyle: { color: '#409eff', type: 'dashed' },
        },
      },
    ],
  })
}

// ---- Lifecycle ----
onMounted(() => {
  loadSweepHistory()
})

watch(activeTab, (tab) => {
  if (tab === 'heatmap' && heatmapData.value) {
    nextTick(() => renderHeatmap())
  }
  if (tab === 'robustness' && robustnessData.value?.neighbor_metrics) {
    nextTick(() => renderRobustnessChart())
  }
})
</script>

<style scoped>
.page-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.page-header {
  padding: 16px 20px 0;
}
.page-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.page-title {
  font-size: 20px;
  font-weight: 600;
  margin: 0;
}
.page-desc {
  font-size: 13px;
  color: #8b949e;
  margin: 4px 0 0;
}
.page-content {
  flex: 1;
  padding: 12px 20px 20px;
  overflow: auto;
}

/* Sweep Layout */
.sweep-layout {
  display: flex;
  gap: 20px;
  min-height: 500px;
}
.sweep-config {
  width: 320px;
  flex-shrink: 0;
  padding: 16px;
  background: var(--el-bg-color-overlay, #161b22);
  border-radius: 8px;
  border: 1px solid #30363d;
}
.sweep-results {
  flex: 1;
  min-width: 0;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 12px;
}
.sub-title {
  font-size: 13px;
  font-weight: 600;
  margin: 16px 0 8px;
  color: #8b949e;
}

.form-group {
  margin-bottom: 12px;
}
.form-group label {
  display: block;
  font-size: 12px;
  color: #8b949e;
  margin-bottom: 4px;
}

.param-row {
  display: flex;
  gap: 6px;
  margin-bottom: 6px;
  align-items: center;
}
.param-key {
  width: 110px;
}
.param-vals {
  flex: 1;
}
.param-tag {
  display: inline-block;
  padding: 2px 6px;
  margin: 0 2px;
  background: #30363d;
  border-radius: 3px;
  font-size: 11px;
  font-family: monospace;
}

/* Sweep History */
.sweep-history {
  margin-top: 16px;
  border-top: 1px solid #30363d;
  padding-top: 12px;
}
.sweep-item {
  padding: 6px 8px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  margin-bottom: 4px;
  transition: background 0.15s;
}
.sweep-item:hover {
  background: #30363d;
}
.sweep-item.active {
  background: #1f6feb33;
  border: 1px solid #1f6feb;
}
.sweep-id {
  font-family: monospace;
  color: #58a6ff;
}
.sweep-info {
  color: #8b949e;
  margin-left: 8px;
}

/* Stats Bar */
.stats-bar {
  display: flex;
  gap: 20px;
  margin-bottom: 16px;
  padding: 12px;
  background: var(--el-bg-color-overlay, #161b22);
  border-radius: 8px;
  border: 1px solid #30363d;
}
.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.stat-label {
  font-size: 11px;
  color: #8b949e;
}
.stat-value {
  font-size: 18px;
  font-weight: 600;
  font-family: monospace;
}
.stat-value.highlight {
  color: #58a6ff;
}

/* Tab Toolbar */
.tab-toolbar {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 4px;
}

/* Chart */
.chart-box {
  width: 100%;
  min-height: 300px;
}

/* Tab Empty */
.tab-empty {
  text-align: center;
  padding: 60px 20px;
  color: #8b949e;
  font-size: 14px;
}

/* Text Colors */
.text-green { color: #67c23a; }
.text-yellow { color: #e6a23c; }
.text-red { color: #f56c6c; }

/* Robustness */
.robustness-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.rob-card {
  padding: 12px;
  background: var(--el-bg-color-overlay, #161b22);
  border-radius: 8px;
  border: 1px solid #30363d;
  text-align: center;
}
.rob-card.big {
  grid-column: span 4;
}
.rob-label {
  font-size: 11px;
  color: #8b949e;
  margin-bottom: 4px;
}
.rob-value {
  font-size: 20px;
  font-weight: 600;
  font-family: monospace;
}
.rob-hint {
  font-size: 12px;
  color: #8b949e;
  margin-top: 4px;
}

/* Report */
.report-content {
  max-width: 900px;
}
.report-header h2 {
  font-size: 18px;
  margin: 0 0 4px;
}
.report-header p {
  font-size: 13px;
  color: #8b949e;
  margin: 0 0 16px;
}
.report-section-block {
  margin-bottom: 24px;
  padding: 16px;
  background: var(--el-bg-color-overlay, #161b22);
  border-radius: 8px;
  border: 1px solid #30363d;
}
.report-section-block h3 {
  font-size: 14px;
  margin: 0 0 12px;
  color: #58a6ff;
}
</style>
