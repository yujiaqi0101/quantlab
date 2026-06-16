<template>
  <div class="workspace-container">
    <div class="workspace-header">
      <h1 class="page-title">Backtest Workspace</h1>
      <p class="page-desc">Select strategy, dataset, and parameters to run a backtest</p>
    </div>

    <div class="workspace-layout">
      <!-- Left: Config Panel -->
      <div class="config-panel">
        <!-- Strategy -->
        <div class="config-section">
          <h3 class="section-label">Strategy</h3>
          <el-select
            v-model="selectedStrategyId"
            placeholder="Select strategy..."
            class="full-select"
            @change="onStrategyChange"
          >
            <el-option
              v-for="s in strategyStore.items"
              :key="s.id"
              :label="s.name"
              :value="s.id"
            />
          </el-select>
        </div>

        <!-- Dataset -->
        <div class="config-section">
          <h3 class="section-label">Dataset</h3>
          <el-select
            v-model="selectedDatasetId"
            placeholder="Select dataset..."
            class="full-select"
            @change="onDatasetChange"
          >
            <el-option
              v-for="d in datasetStore.items"
              :key="d.dataset_id"
              :label="d.name"
              :value="d.dataset_id"
            />
          </el-select>
        </div>

        <!-- Dynamic Parameters -->
        <div v-if="currentParams.length > 0" class="config-section">
          <h3 class="section-label">Parameters</h3>
          <div class="params-form">
            <div v-for="param in currentParams" :key="param.name" class="param-field">
              <label class="param-label">
                {{ param.name }}
                <span v-if="param.description" class="param-hint">{{ param.description }}</span>
              </label>

              <!-- Bool -->
              <el-switch
                v-if="param.type === 'bool'"
                v-model="paramValues[param.name]"
              />

              <!-- Select -->
              <el-select
                v-else-if="param.choices && param.choices.length > 0"
                v-model="paramValues[param.name]"
                class="full-select"
              >
                <el-option
                  v-for="c in param.choices"
                  :key="c"
                  :label="String(c)"
                  :value="c"
                />
              </el-select>

              <!-- Number -->
              <el-input-number
                v-else-if="param.type === 'int' || param.type === 'float'"
                v-model="paramValues[param.name]"
                :min="param.min_value ?? undefined"
                :max="param.max_value ?? undefined"
                :step="param.type === 'int' ? 1 : 0.1"
                :precision="param.type === 'float' ? 2 : 0"
                controls-position="right"
                class="full-input"
              />

              <!-- String fallback -->
              <el-input
                v-else
                v-model="paramValues[param.name]"
                class="full-input"
              />
            </div>
          </div>
        </div>

        <!-- Advanced Options -->
        <div class="config-section">
          <h3 class="section-label" @click="showAdvanced = !showAdvanced" style="cursor: pointer">
            Advanced
            <el-icon :size="12" style="margin-left: 4px">
              <ArrowDown v-if="!showAdvanced" />
              <ArrowUp v-else />
            </el-icon>
          </h3>
          <div v-if="showAdvanced" class="advanced-form">
            <div class="param-field">
              <label class="param-label">Initial Cash</label>
              <el-input-number v-model="advanced.initial_cash" :min="1000" :step="10000" controls-position="right" class="full-input" />
            </div>
            <div class="param-field">
              <label class="param-label">Commission (bps)</label>
              <el-input-number v-model="advanced.commission_bps" :min="0" :step="0.5" :precision="1" controls-position="right" class="full-input" />
            </div>
            <div class="param-field">
              <label class="param-label">Slippage (bps)</label>
              <el-input-number v-model="advanced.slippage_bps" :min="0" :step="0.5" :precision="1" controls-position="right" class="full-input" />
            </div>
          </div>
        </div>

        <!-- Run Button -->
        <div class="run-section">
          <el-button
            type="primary"
            size="large"
            class="run-btn"
            :loading="btStore.running"
            :disabled="!canRun"
            @click="onRunBacktest"
          >
            {{ btStore.running ? 'Running...' : 'Run Backtest' }}
          </el-button>

          <!-- Progress -->
          <div v-if="btStore.running" class="progress-section">
            <el-progress
              :percentage="btStore.taskProgress"
              :stroke-width="4"
              color="#58a6ff"
              :show-text="true"
            />
            <span class="progress-status">{{ btStore.taskStatus }}</span>
          </div>

          <!-- Error -->
          <div v-if="btStore.error" class="error-msg">
            {{ btStore.error }}
          </div>

          <!-- Success -->
          <div v-if="btStore.experimentId" class="success-msg">
            Backtest completed!
            <el-button type="primary" link @click="goToExperiment">
              View Experiment →
            </el-button>
          </div>
        </div>
      </div>

      <!-- Right: Preview Panel -->
      <div class="preview-panel">
        <div v-if="!selectedDatasetId" class="empty-preview">
          <el-icon :size="48" color="#1b2332"><DataLine /></el-icon>
          <p>Select a dataset to preview</p>
        </div>

        <template v-else>
          <!-- K-line Chart -->
          <div v-if="datasetPreview && selectedDataset?.is_ohlcv" class="preview-section">
            <h3 class="section-label">Price Chart</h3>
            <CandlestickChart :preview="datasetPreview" />
          </div>

          <!-- Dataset Info -->
          <div v-if="selectedDataset" class="preview-section">
            <h3 class="section-label">Dataset Info</h3>
            <div class="info-grid-compact">
              <div class="info-item">
                <span class="info-key">Symbol</span>
                <span class="info-val">{{ selectedDataset.symbol }}</span>
              </div>
              <div class="info-item">
                <span class="info-key">Rows</span>
                <span class="info-val">{{ formatNumber(selectedDataset.rows) }}</span>
              </div>
              <div class="info-item">
                <span class="info-key">Range</span>
                <span class="info-val">{{ formatDate(selectedDataset.start_time) }} ~ {{ formatDate(selectedDataset.end_time) }}</span>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useStrategyStore } from '@/stores/strategy'
import { useDatasetStore } from '@/stores/dataset'
import { useBacktestStore } from '@/stores/backtest'
import { getDatasetPreview, type PreviewData } from '@/api/dataset'
import { DataLine, ArrowDown, ArrowUp } from '@element-plus/icons-vue'
import CandlestickChart from '@/components/charts/CandlestickChart.vue'

const router = useRouter()
const strategyStore = useStrategyStore()
const datasetStore = useDatasetStore()
const btStore = useBacktestStore()

const selectedStrategyId = ref('')
const selectedDatasetId = ref('')
const paramValues = ref<Record<string, any>>({})
const showAdvanced = ref(false)
const datasetPreview = ref<PreviewData | null>(null)

const advanced = ref({
  initial_cash: 100000,
  commission_bps: 1.0,
  slippage_bps: 1.0,
})

const currentParams = computed(() => {
  if (!selectedStrategyId.value) return []
  const s = strategyStore.items.find((s) => s.id === selectedStrategyId.value)
  return s?.parameters || []
})

const selectedDataset = computed(() => {
  if (!selectedDatasetId.value) return null
  return datasetStore.items.find((d) => d.dataset_id === selectedDatasetId.value) || null
})

const canRun = computed(() => {
  return selectedStrategyId.value && selectedDatasetId.value && !btStore.running
})

function onStrategyChange(id: string) {
  const s = strategyStore.items.find((s) => s.id === id)
  if (!s) return
  // Reset params to defaults
  paramValues.value = {}
  for (const p of s.parameters || []) {
    paramValues.value[p.name] = p.default
  }
}

async function onDatasetChange(id: string) {
  datasetPreview.value = null
  if (!id) return
  try {
    datasetPreview.value = await getDatasetPreview(id, 200)
  } catch (e) {
    console.error('[BacktestWorkspace] preview error:', e)
  }
}

async function onRunBacktest() {
  if (!canRun.value) return

  await btStore.runBacktest({
    strategy: selectedStrategyId.value,
    parameters: { ...paramValues.value },
    dataset: selectedDatasetId.value,
    initial_cash: advanced.value.initial_cash,
    commission_bps: advanced.value.commission_bps,
    slippage_bps: advanced.value.slippage_bps,
    save_experiment: true,
  })
}

function goToExperiment() {
  if (btStore.experimentId) {
    router.push(`/experiments/${btStore.experimentId}`)
  }
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(2) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return String(n)
}

function formatDate(dt: string): string {
  if (!dt) return '-'
  return dt.split(' ')[0]
}

onMounted(() => {
  strategyStore.load()
  datasetStore.load()
})
</script>

<style scoped>
.workspace-container {
  max-width: 1200px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #e6edf3;
  margin: 0 0 4px 0;
  letter-spacing: -0.5px;
}

.page-desc {
  font-size: 14px;
  color: #484f58;
  margin: 0 0 24px 0;
}

.workspace-layout {
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 24px;
  align-items: start;
}

/* Left Panel */
.config-panel {
  background: #0d1117;
  border: 1px solid #1b2332;
  border-radius: 10px;
  padding: 20px;
}

.config-section {
  margin-bottom: 20px;
}

.section-label {
  font-size: 12px;
  font-weight: 600;
  color: #8b949e;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 8px 0;
  display: flex;
  align-items: center;
}

.full-select {
  width: 100%;
}

.full-select :deep(.el-input__wrapper) {
  background: #161b22;
  border: 1px solid #1b2332;
  box-shadow: none;
}

.full-select :deep(.el-input__inner) {
  color: #e6edf3;
}

.full-input {
  width: 100%;
}

.full-input :deep(.el-input__wrapper) {
  background: #161b22;
  border: 1px solid #1b2332;
  box-shadow: none;
}

.full-input :deep(.el-input__inner) {
  color: #e6edf3;
}

/* Params Form */
.params-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.param-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.param-label {
  font-size: 13px;
  color: #c9d1d9;
  font-weight: 500;
}

.param-hint {
  font-size: 11px;
  color: #484f58;
  margin-left: 6px;
  font-weight: 400;
}

/* Advanced */
.advanced-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* Run Section */
.run-section {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #1b2332;
}

.run-btn {
  width: 100%;
  height: 44px;
  font-size: 15px;
  font-weight: 600;
  background: #1f6feb;
  border-color: #1f6feb;
}

.run-btn:hover {
  background: #388bfd;
  border-color: #388bfd;
}

.run-btn:disabled {
  background: #1b2332;
  border-color: #1b2332;
}

.progress-section {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-status {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 12px;
  color: #8b949e;
}

.error-msg {
  margin-top: 8px;
  padding: 8px 12px;
  background: rgba(248, 81, 73, 0.1);
  border: 1px solid rgba(248, 81, 73, 0.3);
  border-radius: 6px;
  color: #f85149;
  font-size: 13px;
}

.success-msg {
  margin-top: 8px;
  padding: 8px 12px;
  background: rgba(63, 185, 80, 0.1);
  border: 1px solid rgba(63, 185, 80, 0.3);
  border-radius: 6px;
  color: #3fb950;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* Right Panel */
.preview-panel {
  min-height: 400px;
}

.empty-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 120px 0;
  color: #484f58;
  font-size: 14px;
  gap: 8px;
  background: #0d1117;
  border: 1px solid #1b2332;
  border-radius: 10px;
}

.preview-section {
  margin-bottom: 20px;
}

.info-grid-compact {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.info-key {
  font-size: 11px;
  color: #484f58;
  text-transform: uppercase;
}

.info-val {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  color: #c9d1d9;
}
</style>
