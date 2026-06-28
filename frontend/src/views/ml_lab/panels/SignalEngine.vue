<template>
  <div class="signal-engine">
    <div class="engine-header">
      <h2>Signal Engine</h2>
      <p class="desc">把 Model Prediction 转换成 Strategy Language — Prediction → Signal → Suggested Position</p>
    </div>

    <!-- 模板选择 -->
    <el-card class="section-card">
      <template #header>
        <div class="card-header">
          <span>模板选择</span>
          <el-button type="primary" :loading="running" @click="runEngine">
            <el-icon><VideoPlay /></el-icon>
            运行 Pipeline
          </el-button>
        </div>
      </template>
      <el-row :gutter="16">
        <el-col :span="12">
          <el-select v-model="selectedTemplate" placeholder="选择模板" @change="onTemplateChange" style="width:100%">
            <el-option v-for="t in templates" :key="t.name" :label="`${t.name} — ${t.description}`" :value="t.name" />
          </el-select>
        </el-col>
        <el-col :span="12">
          <el-input v-model="modelVersion" placeholder="模型版本 (可选)" />
        </el-col>
      </el-row>
    </el-card>

    <!-- 输入区 -->
    <el-card class="section-card">
      <template #header><span>输入 — Predictions (JSON)</span></template>
      <el-input
        v-model="predictionsJson"
        type="textarea"
        :rows="8"
        placeholder='[{"symbol":"BTC","datetime":"2026-01-01","value":0.05,"probability":0.8,"model_type":"lightgbm"}]'
      />
      <div class="hint">
        <el-button text @click="loadSamplePredictions">载入示例</el-button>
        <span class="hint-text">或通过 Prediction Adapter 转换原始模型输出</span>
      </div>
    </el-card>

    <!-- Pipeline 配置 -->
    <el-collapse class="config-collapse">
      <el-collapse-item title="Pipeline 配置（高级）" name="config">
        <el-row :gutter="16">
          <el-col :span="12">
            <div class="config-item">
              <label>Generator</label>
              <el-select v-model="config.generator.method" style="width:100%">
                <el-option v-for="m in generatorMethods" :key="m" :label="m" :value="m" />
              </el-select>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="config-item">
              <label>Calibrator</label>
              <el-select v-model="config.calibrator.method" style="width:100%">
                <el-option v-for="m in ['none','temperature','platt','isotonic']" :key="m" :label="m" :value="m" />
              </el-select>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="config-item">
              <label>Ranker</label>
              <el-select v-model="config.ranker.method" style="width:100%">
                <el-option v-for="m in ['none','topk','bottomk','topbottomk']" :key="m" :label="m" :value="m" />
              </el-select>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="config-item">
              <label>Scorer</label>
              <el-select v-model="config.scorer.method" style="width:100%">
                <el-option v-for="m in ['tanh','rank','zscore','quantile']" :key="m" :label="m" :value="m" />
              </el-select>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="config-item">
              <label>Allocator</label>
              <el-select v-model="config.allocator.method" style="width:100%">
                <el-option v-for="m in ['equal_weight','confidence_weight','kelly','volatility_scaling','risk_parity']" :key="m" :label="m" :value="m" />
              </el-select>
            </div>
          </el-col>
          <el-col :span="12">
            <div class="config-item">
              <label>Holding Period (days)</label>
              <el-input-number v-model="config.holding_period" :min="1" :max="60" style="width:100%" />
            </div>
          </el-col>
          <el-col :span="24">
            <el-checkbox v-model="config.save_to_registry">保存到 Registry</el-checkbox>
          </el-col>
        </el-row>
      </el-collapse-item>
    </el-collapse>

    <!-- 结果区 -->
    <el-card v-if="result" class="section-card result-card">
      <template #header>
        <div class="card-header">
          <span>结果 — SignalSet</span>
          <div class="summary-tags">
            <el-tag type="success">LONG: {{ result.summary.n_long }}</el-tag>
            <el-tag type="danger">SHORT: {{ result.summary.n_short }}</el-tag>
            <el-tag type="info">NEUTRAL: {{ result.summary.n_neutral }}</el-tag>
            <el-tag>Avg Score: {{ result.summary.avg_score.toFixed(2) }}</el-tag>
          </div>
        </div>
      </template>
      <el-table :data="result.signals" stripe max-height="500">
        <el-table-column prop="symbol" label="Symbol" width="120" />
        <el-table-column prop="direction" label="Direction" width="100">
          <template #default="{ row }">
            <el-tag :type="dirTagType(row.direction)" size="small">{{ row.direction }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="score" label="Score" width="100">
          <template #default="{ row }">{{ row.score.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="confidence" label="Confidence" width="110">
          <template #default="{ row }">{{ (row.confidence * 100).toFixed(1) }}%</template>
        </el-table-column>
        <el-table-column prop="expected_return" label="Expected Return" width="140">
          <template #default="{ row }">{{ (row.expected_return * 100).toFixed(2) }}%</template>
        </el-table-column>
        <el-table-column prop="suggested_weight" label="Weight" width="100">
          <template #default="{ row }">{{ (row.suggested_weight * 100).toFixed(2) }}%</template>
        </el-table-column>
        <el-table-column prop="holding_period" label="Hold Days" width="100" />
        <el-table-column prop="generator" label="Generator" width="120" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button text size="small" @click="explainSignal(row.signal_id)">解释</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="result.metadata.errors && result.metadata.errors.length" class="errors">
        <el-alert type="warning" :closable="false">
          <template #title>Pipeline 警告 ({{ result.metadata.errors.length }})</template>
          <pre>{{ result.metadata.errors }}</pre>
        </el-alert>
      </div>
    </el-card>

    <!-- 解释弹窗 -->
    <el-dialog v-model="explainVisible" title="Signal Explainability" width="80%">
      <div v-if="explainTrace" class="explain-trace">
        <el-timeline>
          <el-timeline-item v-for="(item, idx) in explainSteps" :key="idx" :timestamp="item.label" placement="top">
            <el-card>
              <pre>{{ item.data }}</pre>
            </el-card>
          </el-timeline-item>
        </el-timeline>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { VideoPlay } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import {
  runPipeline, getTemplates, explainSignal as explainSignalApi,
  type SignalTemplate, type SignalSet, type ExplainTrace,
} from '@/api/signalEngine'

const running = ref(false)
const templates = ref<SignalTemplate[]>([])
const selectedTemplate = ref('')
const modelVersion = ref('')
const predictionsJson = ref('')
const result = ref<SignalSet | null>(null)
const explainVisible = ref(false)
const explainTrace = ref<ExplainTrace | null>(null)

const config = reactive({
  generator: { method: 'threshold', long_threshold: 0.02, short_threshold: -0.02, use_short: false },
  calibrator: { method: 'none' },
  ranker: { method: 'none' },
  scorer: { method: 'tanh' },
  allocator: { method: 'equal_weight' },
  holding_period: 5,
  save_to_registry: false,
})

const generatorMethods = ['threshold', 'quantile', 'ranking', 'probability', 'classification', 'regression']

const explainSteps = computed(() => {
  if (!explainTrace.value) return []
  const t = explainTrace.value
  return [
    { label: 'Prediction', data: t.prediction },
    { label: 'After Calibration', data: t.after_calibration },
    { label: 'After Generator', data: t.after_generator },
    { label: 'After Filter', data: t.after_filter },
    { label: 'After Ranker', data: t.after_ranker },
    { label: 'After Scorer', data: t.after_scorer },
    { label: 'After Allocator', data: t.after_allocator },
    { label: 'Final Signal', data: t.final_signal },
  ].filter(s => Object.keys(s.data || {}).length > 0)
})

onMounted(async () => {
  await loadTemplates()
})

async function loadTemplates() {
  try {
    const res = await getTemplates()
    templates.value = res.templates
  } catch (e: any) {
    ElMessage.error('加载模板失败: ' + e.message)
  }
}

function onTemplateChange(name: string) {
  const t = templates.value.find(x => x.name === name)
  if (!t) return
  // 应用模板配置
  const pc = t.pipeline_config
  if (pc.generator) Object.assign(config.generator, pc.generator)
  if (pc.calibrator) Object.assign(config.calibrator, pc.calibrator)
  if (pc.ranker) Object.assign(config.ranker, pc.ranker)
  if (pc.scorer) Object.assign(config.scorer, pc.scorer)
  if (pc.allocator) Object.assign(config.allocator, pc.allocator)
  if (pc.holding_period) config.holding_period = pc.holding_period
  ElMessage.success(`已应用模板: ${t.name}`)
}

function loadSamplePredictions() {
  predictionsJson.value = JSON.stringify([
    { symbol: 'BTC', datetime: '2026-01-01', value: 0.05, probability: 0.85, model_type: 'lightgbm' },
    { symbol: 'ETH', datetime: '2026-01-01', value: 0.03, probability: 0.72, model_type: 'lightgbm' },
    { symbol: 'SOL', datetime: '2026-01-01', value: -0.02, probability: 0.45, model_type: 'lightgbm' },
    { symbol: 'AAPL', datetime: '2026-01-01', value: 0.04, probability: 0.78, model_type: 'lightgbm' },
    { symbol: 'TSLA', datetime: '2026-01-01', value: -0.01, probability: 0.48, model_type: 'lightgbm' },
  ], null, 2)
}

async function runEngine() {
  let predictions: any[]
  try {
    predictions = JSON.parse(predictionsJson.value || '[]')
  } catch {
    ElMessage.error('Predictions JSON 格式错误')
    return
  }
  if (!predictions.length) {
    ElMessage.warning('请输入 predictions')
    return
  }
  running.value = true
  try {
    const res = await runPipeline({
      predictions,
      config: { ...config },
      save_to_registry: config.save_to_registry,
      model_version: modelVersion.value,
    })
    result.value = res
    ElMessage.success(`生成 ${res.signals.length} 个信号`)
  } catch (e: any) {
    ElMessage.error('运行失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    running.value = false
  }
}

async function explainSignal(signalId: string) {
  try {
    const trace = await explainSignalApi(signalId)
    explainTrace.value = trace
    explainVisible.value = true
  } catch (e: any) {
    ElMessage.error('解释失败: ' + e.message)
  }
}

function dirTagType(dir: string) {
  if (dir === 'LONG') return 'success'
  if (dir === 'SHORT') return 'danger'
  return 'info'
}
</script>

<style scoped>
.signal-engine { padding: 16px; }
.engine-header h2 { margin: 0 0 4px 0; }
.engine-header .desc { color: #888; margin: 0 0 16px 0; font-size: 13px; }
.section-card { margin-bottom: 16px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.summary-tags { display: flex; gap: 8px; }
.hint { margin-top: 8px; display: flex; align-items: center; gap: 12px; }
.hint-text { color: #999; font-size: 12px; }
.config-collapse { margin-bottom: 16px; }
.config-item { margin-bottom: 12px; }
.config-item label { display: block; margin-bottom: 4px; font-size: 13px; color: #666; }
.result-card { margin-top: 16px; }
.errors { margin-top: 12px; }
.explain-trace pre { margin: 0; font-size: 12px; }
</style>
