<template>
  <div class="validation-center">
    <div class="panel-header">
      <h2>验证中心 Validation Center</h2>
      <p class="hint">质量控制中心 — Raw Model → Validation Pipeline → Model Package → Registry</p>
    </div>

    <el-alert type="warning" :closable="false" show-icon style="margin-bottom: 16px">
      时间序列切勿使用 train_test_split()，请始终使用滚动前进验证。Never use train_test_split() for time series. Always use Walk Forward validation.
    </el-alert>

    <el-tabs v-model="activeSubTab" type="border-card">
      <!-- Gate 配置 -->
      <el-tab-pane label="Gate 配置 Gate Config" name="config">
        <el-table :data="gateConfigs" border style="width: 100%">
          <el-table-column prop="name" label="Gate 名称" width="150" />
          <el-table-column prop="level" label="级别 Level" width="120" />
          <el-table-column prop="description" label="描述" />
          <el-table-column label="启用 Enabled" width="100">
            <template #default="{ row }">
              <el-switch v-model="row.enabled" @change="updateGateConfig(row)" />
            </template>
          </el-table-column>
          <el-table-column label="权重 Weight" width="120">
            <template #default="{ row }">
              <el-input-number v-model="row.weight" :min="0" :max="100" :step="5" size="small" @change="updateGateConfig(row)" />
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- 运行验证 -->
      <el-tab-pane label="运行验证 Run Pipeline" name="run">
        <el-form :model="runForm" label-width="160px" style="max-width: 800px">
          <!-- 方式1：从 Experiment 加载（推荐） -->
          <el-divider content-position="left">选择实验 Select Experiment（推荐）</el-divider>
          <el-form-item label="实验 Experiment">
            <el-select
              v-model="selectedExperimentId"
              filterable
              clearable
              placeholder="选择已训练的实验（Training Center 产出）"
              style="width: 100%"
              @change="onExperimentChange"
            >
              <el-option
                v-for="exp in experiments"
                :key="exp.experiment_id"
                :label="`${exp.name} (${exp.experiment_id})`"
                :value="exp.experiment_id"
              />
            </el-select>
          </el-form-item>
          <el-form-item v-if="selectedExperiment" label="实验信息">
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="数据集">{{ selectedExperiment.dataset_id }}</el-descriptions-item>
              <el-descriptions-item label="特征集">{{ selectedExperiment.feature_set_id }}</el-descriptions-item>
              <el-descriptions-item label="标签集">{{ selectedExperiment.label_set_id }}</el-descriptions-item>
              <el-descriptions-item label="模型类型">{{ selectedExperiment.model_type }}</el-descriptions-item>
              <el-descriptions-item label="Raw Model">
                <el-tag v-if="selectedExperiment.model_version_id" type="warning" size="small">
                  {{ selectedExperiment.model_version_id }}
                </el-tag>
                <span v-else style="color: #f56c6c;">无（需重新训练）</span>
              </el-descriptions-item>
              <el-descriptions-item label="状态">
                <el-tag :type="selectedExperiment.status === 'COMPLETED' ? 'success' : 'danger'" size="small">
                  {{ selectedExperiment.status }}
                </el-tag>
              </el-descriptions-item>
            </el-descriptions>
          </el-form-item>
          <el-alert
            v-if="selectedExperiment && !selectedExperiment.model_version_id"
            type="error"
            :closable="false"
            show-icon
            style="margin-bottom: 12px"
          >
            该实验没有关联的 Raw Model（可能是旧实验），请在 Training Center 重新训练后再验证。
          </el-alert>

          <!-- Walk Forward 配置 -->
          <el-divider content-position="left">Walk Forward 配置</el-divider>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="折数 Splits">
                <el-input-number v-model="runForm.n_splits" :min="2" :max="20" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="间隔 Gap">
                <el-input-number v-model="runForm.gap" :min="0" />
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="训练大小 Train">
                <el-input-number v-model="runForm.train_size" :min="30" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="测试大小 Test">
                <el-input-number v-model="runForm.test_size" :min="10" />
              </el-form-item>
            </el-col>
          </el-row>

          <el-form-item label="FAIL 时停止">
            <el-switch v-model="runForm.stop_on_fail" />
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              :loading="running"
              :disabled="!selectedExperimentId || (selectedExperiment && !selectedExperiment.model_version_id)"
              @click="runPipeline"
            >
              运行验证流水线 Run Pipeline
            </el-button>
          </el-form-item>

          <!-- 高级模式：手动输入数据 -->
          <el-collapse>
            <el-collapse-item title="高级模式：手动输入数据 Advanced: Manual Data Input" name="advanced">
              <el-form-item label="模型类型 Model">
                <el-select v-model="runForm.model_type" style="width: 100%">
                  <el-option label="线性回归 Linear" value="LINEAR_REGRESSION" />
                  <el-option label="随机森林 Random Forest" value="RANDOM_FOREST" />
                  <el-option label="LightGBM" value="LIGHTGBM" />
                  <el-option label="XGBoost" value="XGBOOST" />
                </el-select>
              </el-form-item>
              <el-form-item label="分类器 Classifier">
                <el-switch v-model="runForm.is_classifier" />
              </el-form-item>
              <el-form-item label="特征数据 Feature Data">
                <el-input v-model="featureDataText" type="textarea" :rows="6" placeholder='JSON 格式: {"f1": [1,2,3], "f2": [4,5,6]}' />
              </el-form-item>
              <el-form-item label="标签数据 Label Data">
                <el-input v-model="labelDataText" type="textarea" :rows="3" placeholder='JSON 格式: [0.1, 0.2, 0.3]' />
              </el-form-item>
              <el-form-item label="时间索引 Index (可选)">
                <el-input v-model="indexText" type="textarea" :rows="2" placeholder='JSON 格式: ["2024-01-01", "2024-01-02"]' />
              </el-form-item>
              <el-form-item>
                <el-button :loading="running" @click="runPipelineManual">手动模式运行</el-button>
              </el-form-item>
            </el-collapse-item>
          </el-collapse>
        </el-form>
      </el-tab-pane>

      <!-- 验证结果 Dashboard -->
      <el-tab-pane label="验证结果 Results" name="results">
        <div v-if="pipelineResult">
          <!-- Overall Score -->
          <el-card style="margin-bottom: 16px">
            <el-row :gutter="16" align="middle">
              <el-col :span="6">
                <div class="score-display">
                  <div class="score-label">Overall Score</div>
                  <div :class="['score-value', `grade-${pipelineResult.overall_grade}`]">
                    {{ pipelineResult.overall_score.toFixed(1) }}
                    <span class="score-grade">({{ pipelineResult.overall_grade }})</span>
                  </div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="score-display">
                  <div class="score-label">Status</div>
                  <el-tag :type="statusTagType(pipelineResult.overall_status)" size="large">
                    {{ pipelineResult.overall_status }}
                  </el-tag>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="score-display">
                  <div class="score-label">Passed</div>
                  <el-tag :type="pipelineResult.passed ? 'success' : 'danger'" size="large">
                    {{ pipelineResult.passed ? 'YES' : 'NO' }}
                  </el-tag>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="score-display">
                  <div class="score-label">Execution Time</div>
                  <div class="score-value">{{ pipelineResult.total_execution_time.toFixed(2) }}s</div>
                </div>
              </el-col>
            </el-row>
            <div v-if="pipelineResult.stopped_at" style="margin-top: 12px; color: #f56c6c;">
              Pipeline stopped at gate: {{ pipelineResult.stopped_at }}
            </div>
          </el-card>

          <!-- Gate Results -->
          <el-card>
            <template #header>Gate Results — 逐项验证结果</template>
            <el-table :data="pipelineResult.gate_results" border>
              <el-table-column prop="level" label="级别" width="120" />
              <el-table-column prop="gate_name" label="Gate" width="150" />
              <el-table-column label="状态 Status" width="100">
                <template #default="{ row }">
                  <el-tag :type="statusTagType(row.status)" size="small">{{ row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="Score" width="100">
                <template #default="{ row }">
                  <span :class="`grade-${row.grade}`">{{ row.score.toFixed(1) }} ({{ row.grade }})</span>
                </template>
              </el-table-column>
              <el-table-column prop="summary" label="摘要 Summary" />
              <el-table-column label="耗时" width="80">
                <template #default="{ row }">
                  {{ row.execution_time.toFixed(2) }}s
                </template>
              </el-table-column>
              <el-table-column label="详情" width="80">
                <template #default="{ row }">
                  <el-button size="small" text @click="showGateDetail(row)">详情</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>
        <el-empty v-else description="请运行验证流水线查看结果 Run pipeline to see results" />
      </el-tab-pane>

      <!-- Champion Challenge -->
      <el-tab-pane label="Champion 挑战" name="challenge">
        <el-form :model="challengeForm" label-width="160px" style="max-width: 800px">
          <el-form-item label="Candidate ID">
            <el-input v-model="challengeForm.candidate_id" placeholder="MV-xxx" />
          </el-form-item>
          <el-form-item label="Family 模型族">
            <el-input v-model="challengeForm.family" placeholder="LGBM_Momentum" />
          </el-form-item>
          <el-form-item label="Candidate 指标">
            <el-input v-model="candidateMetricsText" type="textarea" :rows="4" placeholder='{"walk_forward_ic": 0.08, "sharpe": 1.2, "overall_score": 85}' />
          </el-form-item>
          <el-form-item label="Champion 指标 (可选)">
            <el-input v-model="championMetricsText" type="textarea" :rows="4" placeholder='{"walk_forward_ic": 0.06, "sharpe": 1.0, "overall_score": 75}' />
          </el-form-item>
          <el-form-item label="对比维度 Metrics">
            <el-select v-model="challengeForm.metrics" multiple style="width: 100%">
              <el-option label="WalkForward IC" value="walk_forward_ic" />
              <el-option label="WalkForward Rank IC" value="walk_forward_rank_ic" />
              <el-option label="Sharpe" value="sharpe" />
              <el-option label="Max Drawdown" value="max_drawdown" />
              <el-option label="Robustness Score" value="robustness_score" />
              <el-option label="Benchmark Score" value="benchmark_score" />
              <el-option label="IC Stability" value="ic_stability" />
              <el-option label="Overall Score" value="overall_score" />
            </el-select>
          </el-form-item>
          <el-form-item label="胜出阈值 Win Threshold">
            <el-input-number v-model="challengeForm.win_threshold" :min="0" :max="1" :step="0.1" :precision="2" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="challenging" @click="runChallenge">发起挑战 Run Challenge</el-button>
          </el-form-item>
        </el-form>

        <el-card v-if="challengeResult" style="margin-top: 16px">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span>挑战结果 Challenge Result</span>
              <el-tag :type="decisionTagType(challengeResult.decision)" size="large">{{ challengeResult.decision }}</el-tag>
            </div>
          </template>
          <el-descriptions :column="3" border>
            <el-descriptions-item label="Challenge ID">{{ challengeResult.challenge_id }}</el-descriptions-item>
            <el-descriptions-item label="Candidate">{{ challengeResult.candidate_id }}</el-descriptions-item>
            <el-descriptions-item label="Champion">{{ challengeResult.champion_id || 'None' }}</el-descriptions-item>
            <el-descriptions-item label="Wins">{{ challengeResult.n_wins }} / {{ challengeResult.n_total }}</el-descriptions-item>
            <el-descriptions-item label="Win Ratio">{{ (challengeResult.win_ratio * 100).toFixed(0) }}%</el-descriptions-item>
            <el-descriptions-item label="Reason">{{ challengeResult.reason }}</el-descriptions-item>
          </el-descriptions>

          <el-table :data="challengeResult.comparisons" border style="margin-top: 12px">
            <el-table-column prop="metric" label="指标 Metric" width="200" />
            <el-table-column label="Candidate" width="120">
              <template #default="{ row }">{{ row.candidate_value.toFixed(4) }}</template>
            </el-table-column>
            <el-table-column label="Champion" width="120">
              <template #default="{ row }">{{ row.champion_value.toFixed(4) }}</template>
            </el-table-column>
            <el-table-column label="Delta" width="120">
              <template #default="{ row }">
                <span :style="{ color: row.delta > 0 ? '#67c23a' : '#f56c6c' }">
                  {{ row.delta > 0 ? '+' : '' }}{{ row.delta.toFixed(4) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="Winner" width="120">
              <template #default="{ row }">
                <el-tag :type="row.candidate_wins ? 'success' : 'info'" size="small">
                  {{ row.candidate_wins ? 'CANDIDATE' : 'CHAMPION' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- Gate Detail Dialog -->
    <el-dialog v-model="showDetail" title="Gate 详情" width="700px">
      <div v-if="currentGate">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="Gate">{{ currentGate.gate_name }}</el-descriptions-item>
          <el-descriptions-item label="Level">{{ currentGate.level }}</el-descriptions-item>
          <el-descriptions-item label="Status">{{ currentGate.status }}</el-descriptions-item>
          <el-descriptions-item label="Score">{{ currentGate.score }} ({{ currentGate.grade }})</el-descriptions-item>
          <el-descriptions-item label="Summary" :span="2">{{ currentGate.summary }}</el-descriptions-item>
          <el-descriptions-item label="Execution Time">{{ currentGate.execution_time?.toFixed(4) }}s</el-descriptions-item>
        </el-descriptions>
        <h4>Details</h4>
        <pre>{{ JSON.stringify(currentGate.details, null, 2) }}</pre>
        <div v-if="currentGate.error">
          <h4 style="color: #f56c6c">Error</h4>
          <pre style="color: #f56c6c">{{ currentGate.error }}</pre>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  listGates,
  runValidationPipeline,
  runChampionChallenge,
  getExperiments,
  type GateConfig,
  type PipelineResult,
  type ChallengeResult,
  type MLExperiment,
} from '@/api/ml'

const activeSubTab = ref('config')
const gateConfigs = ref<GateConfig[]>([])

// Experiment 选择（方式1：推荐）
const experiments = ref<MLExperiment[]>([])
const selectedExperimentId = ref('')
const selectedExperiment = computed(() =>
  experiments.value.find(e => e.experiment_id === selectedExperimentId.value)
)

// Run form
const running = ref(false)
const featureDataText = ref('')
const labelDataText = ref('')
const indexText = ref('')
const runForm = ref({
  model_type: 'LIGHTGBM',
  is_classifier: false,
  n_splits: 5,
  train_size: 252,
  test_size: 63,
  gap: 0,
  stop_on_fail: true,
})
const pipelineResult = ref<PipelineResult | null>(null)

// Challenge form
const challenging = ref(false)
const candidateMetricsText = ref('')
const championMetricsText = ref('')
const challengeForm = ref({
  candidate_id: '',
  family: '',
  metrics: ['walk_forward_ic', 'sharpe', 'overall_score'],
  win_threshold: 0.6,
})
const challengeResult = ref<ChallengeResult | null>(null)

// Gate detail
const showDetail = ref(false)
const currentGate = ref<any>(null)

async function loadGates() {
  try {
    const resp = await listGates()
    gateConfigs.value = resp.gates
  } catch (e: any) {
    ElMessage.error(e.message || '加载 Gate 列表失败')
  }
}

async function loadExperiments() {
  try {
    const resp = await getExperiments({ status: 'COMPLETED' })
    experiments.value = resp.experiments
  } catch (e: any) {
    ElMessage.error(e.message || '加载实验列表失败')
  }
}

function onExperimentChange() {
  // 切换实验时清空之前的结果
  pipelineResult.value = null
}

async function updateGateConfig(row: GateConfig) {
  // 实时更新 Gate 配置（前端状态，实际更新通过 API）
  ElMessage.success(`Gate ${row.name} 配置已更新`)
}

async function runPipeline() {
  if (!selectedExperimentId.value) {
    ElMessage.warning('请先选择实验')
    return
  }

  running.value = true
  try {
    const result = await runValidationPipeline({
      experiment_id: selectedExperimentId.value,
      n_splits: runForm.value.n_splits,
      train_size: runForm.value.train_size,
      test_size: runForm.value.test_size,
      gap: runForm.value.gap,
      stop_on_fail: runForm.value.stop_on_fail,
    })
    pipelineResult.value = result
    activeSubTab.value = 'results'
    ElMessage.success(`验证完成: Score ${result.overall_score.toFixed(1)} (${result.overall_grade})`)
  } catch (e: any) {
    ElMessage.error(e.message || '验证流水线运行失败')
  } finally {
    running.value = false
  }
}

async function runPipelineManual() {
  let feature_data: Record<string, number[]>
  let label_data: number[]
  let index: string[] | undefined

  try {
    feature_data = JSON.parse(featureDataText.value)
    label_data = JSON.parse(labelDataText.value)
    if (indexText.value) index = JSON.parse(indexText.value)
  } catch (e: any) {
    ElMessage.error('JSON 解析失败: ' + e.message)
    return
  }

  running.value = true
  try {
    const result = await runValidationPipeline({
      feature_data,
      label_data,
      index,
      model_type: runForm.value.model_type,
      is_classifier: runForm.value.is_classifier,
      n_splits: runForm.value.n_splits,
      train_size: runForm.value.train_size,
      test_size: runForm.value.test_size,
      gap: runForm.value.gap,
      stop_on_fail: runForm.value.stop_on_fail,
    })
    pipelineResult.value = result
    activeSubTab.value = 'results'
    ElMessage.success(`验证完成: Score ${result.overall_score.toFixed(1)} (${result.overall_grade})`)
  } catch (e: any) {
    ElMessage.error(e.message || '验证流水线运行失败')
  } finally {
    running.value = false
  }
}

async function runChallenge() {
  let candidate_metrics: Record<string, number>
  let champion_metrics: Record<string, number> | undefined

  try {
    candidate_metrics = JSON.parse(candidateMetricsText.value)
    if (championMetricsText.value) {
      champion_metrics = JSON.parse(championMetricsText.value)
    }
  } catch (e: any) {
    ElMessage.error('JSON 解析失败: ' + e.message)
    return
  }

  challenging.value = true
  try {
    const result = await runChampionChallenge({
      candidate_id: challengeForm.value.candidate_id,
      family: challengeForm.value.family,
      candidate_metrics,
      champion_metrics,
      metrics: challengeForm.value.metrics,
      win_threshold: challengeForm.value.win_threshold,
    })
    challengeResult.value = result
    ElMessage.success(`挑战完成: ${result.decision}`)
  } catch (e: any) {
    ElMessage.error(e.message || '挑战运行失败')
  } finally {
    challenging.value = false
  }
}

function showGateDetail(row: any) {
  currentGate.value = row
  showDetail.value = true
}

function statusTagType(status: string): any {
  const map: Record<string, string> = {
    PASS: 'success',
    WARNING: 'warning',
    FAIL: 'danger',
    SKIP: 'info',
    ERROR: 'danger',
  }
  return map[status] || 'info'
}

function decisionTagType(decision: string): any {
  const map: Record<string, string> = {
    PROMOTE: 'success',
    REJECT: 'danger',
    INCONCLUSIVE: 'warning',
  }
  return map[decision] || 'info'
}

onMounted(() => {
  loadGates()
  loadExperiments()
})
</script>

<style scoped>
.panel-header {
  margin-bottom: 16px;
}
.panel-header h2 {
  margin: 0 0 8px 0;
}
.hint {
  color: #909399;
  font-size: 13px;
  margin: 0;
}
.score-display {
  text-align: center;
}
.score-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 8px;
}
.score-value {
  font-size: 36px;
  font-weight: bold;
}
.score-grade {
  font-size: 20px;
  margin-left: 4px;
}
.grade-A { color: #67c23a; }
.grade-B { color: #409eff; }
.grade-C { color: #e6a23c; }
.grade-D { color: #f56c6c; }
.grade-F { color: #f56c6c; }
pre {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  max-height: 300px;
  overflow: auto;
}
</style>
