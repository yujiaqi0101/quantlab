<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-header-row">
        <div>
          <h1 class="page-title">策略构建器 Strategy Builder</h1>
          <p class="page-desc">可视化构建策略 Build strategies visually — no code required</p>
        </div>
      </div>
    </div>

    <div class="page-content">
      <el-tabs v-model="activeTab" class="q-tabs">
        <!-- ==================== Builder ==================== -->
        <el-tab-pane label="构建器 Builder" name="builder">
          <div class="builder-layout">
            <!-- Left: Config -->
            <div class="builder-config">
              <h3 class="section-title">策略配置 Strategy Configuration</h3>

              <!-- Name -->
              <div class="form-group">
                <label>策略名称 Strategy Name</label>
                <el-input v-model="form.name" placeholder="e.g. RSI_Momentum_Strategy" />
              </div>

              <div class="form-group">
                <label>描述 Description</label>
                <el-input v-model="form.description" type="textarea" :rows="2" placeholder="Optional description" />
              </div>

              <!-- Signal Rules -->
              <div class="form-group">
                <label>信号规则 Signal Rules</label>
                <div v-for="(rule, idx) in form.signals" :key="idx" class="rule-card">
                  <div class="rule-header">
                    <span class="rule-index">信号 Signal {{ idx + 1 }}</span>
                    <el-button :icon="Delete" circle size="small" @click="removeSignal(idx)" />
                  </div>
                  <div class="rule-body">
                    <el-select v-model="rule.type" style="width:120px;margin-right:6px" size="small" @change="onRuleTypeChange(rule)">
                      <el-option value="threshold" label="Threshold" />
                      <el-option value="crossover" label="Crossover" />
                      <el-option value="zero_cross" label="Zero Cross" />
                    </el-select>

                    <template v-if="rule.type === 'threshold'">
                      <el-select v-model="rule.factor" placeholder="Factor" filterable style="width:100px;margin-right:6px" size="small">
                        <el-option v-for="f in factorOptions" :key="f" :label="f" :value="f" />
                      </el-select>
                      <el-select v-model="rule.op" style="width:70px;margin-right:6px" size="small">
                        <el-option v-for="op in ['<', '<=', '>', '>=', '==']" :key="op" :label="op" :value="op" />
                      </el-select>
                      <el-input-number v-model="rule.value" :step="1" size="small" style="width:100px;margin-right:6px" />
                      <el-select v-model="rule.direction" style="width:80px" size="small">
                        <el-option value="long" label="Long" />
                        <el-option value="short" label="Short" />
                        <el-option value="both" label="Both" />
                      </el-select>
                    </template>

                    <template v-else-if="rule.type === 'crossover'">
                      <el-select v-model="rule.fast_factor" placeholder="Fast" filterable style="width:90px;margin-right:6px" size="small">
                        <el-option v-for="f in factorOptions" :key="f" :label="f" :value="f" />
                      </el-select>
                      <span style="color:#8b949e;margin-right:6px">crosses</span>
                      <el-select v-model="rule.slow_factor" placeholder="Slow" filterable style="width:90px" size="small">
                        <el-option v-for="f in factorOptions" :key="f" :label="f" :value="f" />
                      </el-select>
                    </template>

                    <template v-else>
                      <el-select v-model="rule.factor" placeholder="Factor" filterable style="width:120px" size="small">
                        <el-option v-for="f in factorOptions" :key="f" :label="f" :value="f" />
                      </el-select>
                    </template>
                  </div>
                </div>

                <el-button type="primary" size="small" :icon="Plus" @click="addSignal" style="width:100%">
                  Add Signal 添加信号
                </el-button>
              </div>

              <!-- Signal Logic -->
              <div class="form-group">
                <label>信号逻辑 Signal Logic</label>
                <el-select v-model="form.signalLogic" style="width:100%">
                  <el-option value="AND" label="AND (all signals agree)" />
                  <el-option value="OR" label="OR (any signal triggers)" />
                  <el-option value="MAJORITY" label="MAJORITY (most signals agree)" />
                </el-select>
              </div>

              <!-- Position -->
              <div class="form-group">
                <label>持仓 Position</label>
                <div class="pos-row">
                  <el-select v-model="form.position.type" style="width:140px;margin-right:8px" size="small">
                    <el-option value="target" label="Target" />
                    <el-option value="equal_weight" label="Equal Weight" />
                  </el-select>
                  <el-input-number v-model="form.position.value" :min="0" :max="2" :step="0.1" size="small" style="width:110px" />
                </div>
              </div>

              <!-- Risk -->
              <div class="form-group">
                <label>风控 Risk Control</label>
                <div class="risk-grid">
                  <div class="risk-item">
                    <span class="risk-label">止损 Stop Loss</span>
                    <el-input-number v-model="form.risk.stop_loss" :min="0" :max="1" :step="0.01" size="small" style="width:100px" />
                  </div>
                  <div class="risk-item">
                    <span class="risk-label">止盈 Take Profit</span>
                    <el-input-number v-model="form.risk.take_profit" :min="0" :max="1" :step="0.01" size="small" style="width:100px" />
                  </div>
                  <div class="risk-item">
                    <span class="risk-label">最大回撤 Max DD</span>
                    <el-input-number v-model="form.risk.max_drawdown" :min="0" :max="1" :step="0.01" size="small" style="width:100px" />
                  </div>
                </div>
              </div>

              <!-- Actions -->
              <div class="action-buttons">
                <el-button type="primary" :loading="createLoading" @click="createStrategy">
                  创建策略 Create Strategy
                </el-button>
                <el-button @click="resetForm">Reset</el-button>
              </div>
            </div>

            <!-- Right: Preview -->
            <div class="builder-preview">
              <div v-if="previewData" class="preview-content">
                <h3 class="section-title">策略预览 Strategy Preview</h3>

                <!-- Strategy Graph -->
                <div class="strategy-graph">
                  <div class="graph-node signal" v-for="(rule, idx) in form.signals" :key="'g'+idx">
                    <div class="node-icon">S{{ idx + 1 }}</div>
                    <div class="node-label">
                      {{ rule.type === 'crossover' ? `${rule.fast_factor || '?'} x ${rule.slow_factor || '?'}` :
                         rule.type === 'zero_cross' ? `${rule.factor || '?'} > 0` :
                         `${rule.factor || '?'} ${rule.op || '<'} ${rule.value ?? 0}` }}
                    </div>
                  </div>
                  <div class="graph-arrow">&#8595;</div>
                  <div class="graph-node logic">
                    <div class="node-icon">{{ form.signalLogic }}</div>
                    <div class="node-label">信号逻辑 Signal Logic</div>
                  </div>
                  <div class="graph-arrow">&#8595;</div>
                  <div class="graph-node position">
                    <div class="node-icon">P</div>
                    <div class="node-label">持仓 Position {{ (form.position.value * 100).toFixed(0) }}%</div>
                  </div>
                </div>

                <!-- Stats -->
                <div class="stats-bar">
                  <div class="stat-item">
                    <span class="stat-label">总K线 Total Bars</span>
                    <span class="stat-value">{{ previewData.total_bars }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Long</span>
                    <span class="stat-value text-green">{{ previewData.long_pct }}%</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Short</span>
                    <span class="stat-value text-red">{{ previewData.short_pct }}%</span>
                  </div>
                </div>

                <!-- Timeline -->
                <div class="timeline-section">
                  <h4 class="sub-title">信号时间线 Signal Timeline</h4>
                  <div class="signal-timeline">
                    <span
                      v-for="(sig, i) in previewData.signal_timeline"
                      :key="i"
                      class="timeline-bar"
                      :class="{ long: sig === 1, short: sig === -1, neutral: sig === 0 }"
                      :title="`Bar ${i}: ${sig === 1 ? 'Long' : sig === -1 ? 'Short' : 'Neutral'}`"
                    ></span>
                  </div>
                  <div class="timeline-legend">
                    <span class="legend-item"><span class="legend-dot long"></span> Long</span>
                    <span class="legend-item"><span class="legend-dot short"></span> Short</span>
                    <span class="legend-item"><span class="legend-dot neutral"></span> Neutral</span>
                  </div>
                </div>
              </div>
              <div v-else class="tab-empty">Create a strategy to see the preview.</div>
            </div>
          </div>
        </el-tab-pane>

        <!-- ==================== Templates ==================== -->
        <el-tab-pane label="模板 Templates" name="templates">
          <div class="templates-grid">
            <div
              v-for="tmpl in templates"
              :key="tmpl.key"
              class="template-card"
              @click="applyTemplate(tmpl)"
            >
              <div class="template-name">{{ tmpl.name }}</div>
              <div class="template-desc">{{ tmpl.description }}</div>
              <div class="template-meta">
                <el-tag size="small" effect="dark">{{ tmpl.signal_logic }}</el-tag>
                <el-tag size="small" type="info" effect="dark">{{ tmpl.signals.length }} signals</el-tag>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- ==================== My Strategies ==================== -->
        <el-tab-pane label="我的策略 My Strategies" name="list">
          <div class="tab-toolbar">
            <el-button :icon="Refresh" circle @click="loadSpecs" :loading="listLoading" />
          </div>

          <div v-if="specs.length" class="specs-grid">
            <div
              v-for="spec in specs"
              :key="spec.spec_id"
              class="spec-card"
            >
              <div class="spec-header">
                <span class="spec-name">{{ spec.name }}</span>
                <el-tag size="small" effect="dark">{{ spec.signal_logic }}</el-tag>
              </div>
              <div class="spec-desc">{{ spec.description || '无描述 No description' }}</div>
              <div class="spec-meta">
                <span>{{ spec.signal_count }} 信号 signals</span>
                <span>持仓 Position: {{ (spec.position_value * 100).toFixed(0) }}%</span>
              </div>
              <div class="spec-actions">
                <el-button size="small" type="primary" @click="compileSpec(spec.spec_id)">
                  编译 Compile
                </el-button>
                <el-button size="small" @click="previewSpec(spec.spec_id)">
                  预览 Preview
                </el-button>
                <el-button size="small" type="danger" @click="deleteSpec(spec.spec_id)">
                  删除 Delete
                </el-button>
              </div>
            </div>
          </div>
          <div v-else class="tab-empty">No strategies yet. Create one in the Builder tab.</div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Delete, Plus, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  listTemplates as apiListTemplates,
  createStrategy as apiCreateStrategy,
  listSpecs as apiListSpecs,
  deleteSpec as apiDeleteSpec,
  compileStrategy as apiCompileStrategy,
  previewStrategy as apiPreviewStrategy,
  type StrategyTemplate,
  type StrategySpecSummary,
  type PreviewResult,
  type SignalRuleData,
} from '@/api/strategyBuilder'

// ---- State ----
const activeTab = ref('builder')
const createLoading = ref(false)
const listLoading = ref(false)
const templates = ref<StrategyTemplate[]>([])
const specs = ref<StrategySpecSummary[]>([])
const previewData = ref<PreviewResult | null>(null)

const factorOptions = [
  'RSI14', 'RSI6', 'RSI28',
  'Momentum10', 'Momentum20', 'Momentum60',
  'MA5', 'MA10', 'MA20', 'MA60', 'MA120', 'MA240',
  'EMA12', 'EMA26',
  'MACD', 'MACD_Signal',
  'BB_Upper', 'BB_Lower', 'BB_Middle',
  'ATR14', 'Volatility20',
  'Volume', 'VolumeRank',
  'VWAP',
]

const defaultSignal = (): SignalRuleData => ({
  type: 'threshold',
  factor: 'RSI14',
  op: '<',
  value: 30,
  direction: 'long',
  fast_factor: 'MA5',
  slow_factor: 'MA20',
})

const form = reactive({
  name: '',
  description: '',
  signals: [defaultSignal()] as SignalRuleData[],
  signalLogic: 'AND',
  position: {
    type: 'target',
    value: 1.0,
    max_position: 1.0,
    min_position: 0.0,
  },
  risk: {
    stop_loss: 0,
    take_profit: 0,
    max_drawdown: 0,
    trailing_stop: 0,
  },
})

// ---- Signal Management ----
function addSignal() {
  form.signals.push(defaultSignal())
}

function removeSignal(idx: number) {
  form.signals.splice(idx, 1)
}

function onRuleTypeChange(rule: SignalRuleData) {
  if (rule.type === 'crossover') {
    rule.fast_factor = 'MA5'
    rule.slow_factor = 'MA20'
  } else if (rule.type === 'zero_cross') {
    rule.factor = 'MACD'
  }
}

// ---- API Calls ----
async function createStrategy() {
  if (!form.name) {
    ElMessage.warning('Please enter a strategy name')
    return
  }
  if (!form.signals.length) {
    ElMessage.warning('Please add at least one signal rule')
    return
  }

  createLoading.value = true
  try {
    const spec = await apiCreateStrategy(
      form.name,
      form.signals,
      form.signalLogic,
      form.position,
      form.risk,
      form.description,
    )
    ElMessage.success(`Strategy "${spec.name}" created!`)

    // Auto preview
    previewData.value = await apiPreviewStrategy(spec.spec_id)
    await loadSpecs()
  } catch (e: any) {
    ElMessage.error('Failed to create strategy')
  } finally {
    createLoading.value = false
  }
}

async function loadSpecs() {
  listLoading.value = true
  try {
    specs.value = await apiListSpecs()
  } catch { /* ignore */ }
  finally {
    listLoading.value = false
  }
}

async function compileSpec(specId: string) {
  try {
    const result = await apiCompileStrategy(specId)
    ElMessage.success(result.message)
  } catch (e: any) {
    ElMessage.error('Compilation failed')
  }
}

async function previewSpec(specId: string) {
  try {
    previewData.value = await apiPreviewStrategy(specId)
    activeTab.value = 'builder'
  } catch { /* ignore */ }
}

async function deleteSpec(specId: string) {
  try {
    await apiDeleteSpec(specId)
    ElMessage.success('Strategy deleted')
    await loadSpecs()
  } catch { /* ignore */ }
}

function applyTemplate(tmpl: StrategyTemplate) {
  form.name = tmpl.name
  form.description = tmpl.description
  form.signals = tmpl.signals.map(s => ({ ...s }))
  form.signalLogic = tmpl.signal_logic
  form.position = { ...tmpl.position }
  form.risk = { ...tmpl.risk }
  activeTab.value = 'builder'
  ElMessage.info(`Template "${tmpl.name}" applied`)
}

function resetForm() {
  form.name = ''
  form.description = ''
  form.signals = [defaultSignal()]
  form.signalLogic = 'AND'
  form.position = { type: 'target', value: 1.0, max_position: 1.0, min_position: 0.0 }
  form.risk = { stop_loss: 0, take_profit: 0, max_drawdown: 0, trailing_stop: 0 }
  previewData.value = null
}

// ---- Lifecycle ----
onMounted(async () => {
  try {
    templates.value = await apiListTemplates()
  } catch { /* ignore */ }
  await loadSpecs()
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

/* Builder Layout */
.builder-layout {
  display: flex;
  gap: 20px;
  min-height: 500px;
}
.builder-config {
  width: 400px;
  flex-shrink: 0;
  padding: 16px;
  background: var(--el-bg-color-overlay, #161b22);
  border-radius: 8px;
  border: 1px solid #30363d;
}
.builder-preview {
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
  margin-bottom: 14px;
}
.form-group label {
  display: block;
  font-size: 12px;
  color: #8b949e;
  margin-bottom: 4px;
}

/* Rule Card */
.rule-card {
  padding: 10px;
  margin-bottom: 8px;
  background: #0d1117;
  border-radius: 6px;
  border: 1px solid #30363d;
}
.rule-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.rule-index {
  font-size: 12px;
  font-weight: 600;
  color: #58a6ff;
}
.rule-body {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

/* Position & Risk */
.pos-row {
  display: flex;
  align-items: center;
}
.risk-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.risk-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.risk-label {
  font-size: 11px;
  color: #8b949e;
}

/* Action Buttons */
.action-buttons {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}

/* Strategy Graph */
.strategy-graph {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px;
  margin-bottom: 16px;
  background: var(--el-bg-color-overlay, #161b22);
  border-radius: 8px;
  border: 1px solid #30363d;
}
.graph-node {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-radius: 8px;
  min-width: 200px;
}
.graph-node.signal {
  background: #1f2937;
  border: 1px solid #30363d;
}
.graph-node.logic {
  background: #1f2937;
  border: 1px solid #1f6feb;
}
.graph-node.position {
  background: #1f2937;
  border: 1px solid #238636;
}
.node-icon {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 12px;
  color: #fff;
  flex-shrink: 0;
}
.signal .node-icon { background: #1f6feb; }
.logic .node-icon { background: #8b5cf6; }
.position .node-icon { background: #238636; }
.node-label {
  font-size: 13px;
  font-family: monospace;
}
.graph-arrow {
  font-size: 20px;
  color: #8b949e;
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
.stat-value.highlight { color: #58a6ff; }

/* Signal Timeline */
.timeline-section {
  padding: 16px;
  background: var(--el-bg-color-overlay, #161b22);
  border-radius: 8px;
  border: 1px solid #30363d;
}
.signal-timeline {
  display: flex;
  gap: 2px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.timeline-bar {
  width: 8px;
  height: 24px;
  border-radius: 2px;
}
.timeline-bar.long { background: #238636; }
.timeline-bar.short { background: #da3633; }
.timeline-bar.neutral { background: #30363d; }
.timeline-legend {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #8b949e;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
}
.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 2px;
}
.legend-dot.long { background: #238636; }
.legend-dot.short { background: #da3633; }
.legend-dot.neutral { background: #30363d; }

/* Templates */
.templates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px;
}
.template-card {
  padding: 16px;
  background: var(--el-bg-color-overlay, #161b22);
  border-radius: 8px;
  border: 1px solid #30363d;
  cursor: pointer;
  transition: border-color 0.2s;
}
.template-card:hover {
  border-color: #58a6ff;
}
.template-name {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 6px;
}
.template-desc {
  font-size: 12px;
  color: #8b949e;
  margin-bottom: 10px;
}
.template-meta {
  display: flex;
  gap: 6px;
}

/* Specs */
.specs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}
.spec-card {
  padding: 16px;
  background: var(--el-bg-color-overlay, #161b22);
  border-radius: 8px;
  border: 1px solid #30363d;
}
.spec-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.spec-name {
  font-size: 14px;
  font-weight: 600;
}
.spec-desc {
  font-size: 12px;
  color: #8b949e;
  margin-bottom: 8px;
}
.spec-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #8b949e;
  margin-bottom: 12px;
}
.spec-actions {
  display: flex;
  gap: 6px;
}

/* Tab Toolbar */
.tab-toolbar {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
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
.text-red { color: #f56c6c; }

/* Preview Content */
.preview-content {
  padding: 16px;
  background: var(--el-bg-color-overlay, #161b22);
  border-radius: 8px;
  border: 1px solid #30363d;
}
</style>
