<template>
  <div class="feature-importance">
    <div class="panel-header">
      <h2>特征重要性 Feature Importance</h2>
    </div>

    <el-card>
      <el-form :model="form" label-width="120px" inline>
        <el-form-item label="数据集 Dataset">
          <el-select v-model="form.dataset_id" placeholder="选择数据集 Select dataset" style="width: 200px" @change="onDatasetChange">
            <el-option v-for="d in datasets" :key="d.dataset_id" :label="d.name" :value="d.dataset_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="特征集 FeatureSet">
          <el-select v-model="form.feature_set_id" placeholder="选择特征集 Select feature set" style="width: 200px" @change="onFeatureSetChange">
            <el-option v-for="f in featureSets" :key="f.name" :label="f.name" :value="f.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签集 LabelSet">
          <el-select v-model="form.label_set_id" placeholder="选择标签集 Select label set" style="width: 200px">
            <el-option v-for="l in labelSets" :key="l.name" :label="l.name" :value="l.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="模型 Model">
          <el-select v-model="form.model_type" style="width: 160px">
            <el-option label="线性回归 Linear" value="LINEAR_REGRESSION" />
            <el-option label="随机森林 Random Forest" value="RANDOM_FOREST" />
            <el-option label="LightGBM" value="LIGHTGBM" />
            <el-option label="XGBoost" value="XGBOOST" />
          </el-select>
        </el-form-item>
        <el-form-item label="方法 Methods">
          <el-checkbox-group v-model="form.methods">
            <el-checkbox label="gain">增益 Gain</el-checkbox>
            <el-checkbox label="permutation">置换 Permutation</el-checkbox>
            <el-checkbox label="shap">SHAP</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="训练任务 Job">
          <el-select v-model="selectedJobId" placeholder="选择训练任务（按时间倒序）" style="width: 320px" @change="onJobChange" clearable>
            <el-option
              v-for="j in availableJobs"
              :key="j.job_id"
              :label="formatJobLabel(j)"
              :value="j.job_id"
            />
          </el-select>
        </el-form-item>
      </el-form>

      <div style="margin-top: 16px; text-align: right">
        <el-button type="primary" :loading="running" @click="runAnalysis">计算重要性 Compute</el-button>
      </div>
    </el-card>

    <!-- 结果 -->
    <el-card v-if="results || selectedJob" style="margin-top: 16px">
      <div v-if="jobSource" class="job-source">
        <el-tag type="info" size="small">结果来源 Source</el-tag>
        <span class="source-text">{{ jobSource }}</span>
      </div>
      <el-tabs v-model="activeMethod">
        <el-tab-pane
          v-for="method in Object.keys(results || {})"
          :key="method"
          :label="method.toUpperCase()"
          :name="method"
        >
          <div v-if="results && results[method]">
            <el-table :data="results[method].details" border size="small">
              <el-table-column prop="rank" label="排名 Rank" width="80" sortable />
              <el-table-column prop="feature" label="特征 Feature" />
              <el-table-column label="重要性 Importance" width="160" sortable :sort-by="'importance'">
                <template #default="{ row }">
                  {{ row.importance.toFixed(6) }}
                </template>
              </el-table-column>
              <el-table-column label="归一化 Normalized" width="180">
                <template #default="{ row }">
                  <el-progress :percentage="row.normalized * 100" :stroke-width="10" />
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { http } from '@/api/http'
import {
  getMLDatasets,
  getFeatureSets,
  getLabelSets,
  type MLDataset,
  type MLFeatureSet,
  type MLLabelSet,
} from '@/api/ml'

const datasets = ref<MLDataset[]>([])
const featureSets = ref<MLFeatureSet[]>([])
const labelSets = ref<MLLabelSet[]>([])
const running = ref(false)
const results = ref<Record<string, any> | null>(null)
const activeMethod = ref('')

const allJobs = ref<any[]>([])
const selectedJobId = ref<string>('')

const form = ref({
  dataset_id: '',
  feature_set_id: '',
  label_set_id: '',
  model_type: 'LIGHTGBM',
  methods: ['gain', 'permutation'] as string[],
})

// 当前 dataset 下所有 COMPLETED job，按 created_at 倒序
const availableJobs = computed(() => {
  return allJobs.value
    .filter((j: any) => j.status === 'COMPLETED' && j.dataset_id === form.value.dataset_id)
    .sort((a: any, b: any) => (b.created_at || '').localeCompare(a.created_at || ''))
})

const selectedJob = computed(() =>
  allJobs.value.find((j: any) => j.job_id === selectedJobId.value) || null
)

const jobSource = computed(() => {
  const j = selectedJob.value
  if (!j) return ''
  const time = (j.created_at || '').replace('T', ' ').slice(0, 19)
  const methods = (j.methods || []).join(', ') || '(none)'
  return `${j.name} | ${time} | 模型 ${j.model_type} | 方法 ${methods} | job_id=${j.job_id}`
})

function formatJobLabel(j: any): string {
  const time = (j.created_at || '').replace('T', ' ').slice(5, 16) // MM-DD HH:MM
  const methods = (j.methods || ['gain']).join('+')
  return `${time} | ${j.model_type} | methods: ${methods} | ${j.name}`
}

async function loadOptions() {
  const [ds, fs, ls, jobsResp] = await Promise.all([
    getMLDatasets(),
    getFeatureSets(),
    getLabelSets(),
    http.get('/ml/training/jobs'),
  ])
  datasets.value = ds.datasets
  featureSets.value = fs.sets
  labelSets.value = ls.sets
  allJobs.value = jobsResp.data?.jobs || []

  await autoLoadFromJob()
}

async function autoLoadFromJob() {
  try {
    // 优先用 quick 分析
    const quickResp = await http.get('/ml/feature-analysis/quick')
    const quickResults = quickResp.data?.results || []
    if (quickResults.length > 0 && quickResults.some((r: any) => r.importance !== undefined)) {
      const details = quickResults
        .filter((r: any) => r.importance !== undefined)
        .sort((a: any, b: any) => (b.importance || 0) - (a.importance || 0))
        .map((r: any, i: number) => ({
          rank: i + 1,
          feature: r.feature_name,
          importance: r.importance || 0,
          normalized: r.importance_pct ? r.importance_pct / 100 : (r.importance || 0) / (quickResults.reduce((s: number, x: any) => s + (x.importance || 0), 0) || 1),
        }))
      if (details.length > 0) {
        results.value = { gain: { details, model_type: 'Auto', n_features: details.length } }
        activeMethod.value = 'gain'
        return
      }
    }

    // 找该 dataset 下的最新 job 并选中
    if (availableJobs.value.length > 0) {
      selectedJobId.value = availableJobs.value[0].job_id
      await loadJobResults(selectedJobId.value)
    }
  } catch (e: any) {
    // 静默失败
  }
}

async function loadJobResults(jobId: string) {
  if (!jobId) return
  try {
    const resp = await http.get(`/ml/feature-importance/from-job/${jobId}`)
    if (resp.data) {
      results.value = resp.data
      const methods = Object.keys(resp.data)
      if (methods.length > 0) activeMethod.value = methods[0]
    }
  } catch (e: any) {
    // 静默失败
  }
}

function onDatasetChange() {
  // dataset 切换时重置 job 选择，自动选最新
  selectedJobId.value = ''
  results.value = null
  if (availableJobs.value.length > 0) {
    selectedJobId.value = availableJobs.value[0].job_id
    loadJobResults(selectedJobId.value)
  }
}

function onJobChange(jobId: string) {
  if (jobId) loadJobResults(jobId)
}

function onFeatureSetChange() {}

async function runAnalysis() {
  if (!form.value.dataset_id || !form.value.feature_set_id || !form.value.label_set_id) {
    ElMessage.warning('请选择数据集、特征集和标签集 Please select dataset, FeatureSet, and LabelSet')
    return
  }
  // 若已选 job，直接重新加载
  if (selectedJobId.value) {
    running.value = true
    try {
      await loadJobResults(selectedJobId.value)
    } finally {
      running.value = false
    }
    return
  }
  // fallback：找最新匹配 job
  if (availableJobs.value.length === 0) {
    ElMessage.info('未找到该数据集的已完成训练任务，请先训练模型 No completed training job found for this dataset.')
    return
  }
  selectedJobId.value = availableJobs.value[0].job_id
  running.value = true
  try {
    await loadJobResults(selectedJobId.value)
  } finally {
    running.value = false
  }
}

onMounted(loadOptions)
</script>

<style scoped>
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.panel-header h2 {
  margin: 0;
}
.job-source {
  padding: 8px 12px;
  margin-bottom: 12px;
  background: rgba(64, 158, 255, 0.08);
  border-left: 3px solid #409eff;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #909399;
}
.job-source .source-text {
  color: #303133;
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  word-break: break-all;
}
</style>
