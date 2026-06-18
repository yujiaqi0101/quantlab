<template>
  <div class="training-center">
    <div class="panel-header">
      <h2>Training Center</h2>
      <el-button type="primary" @click="showTrainDialog = true">Start Training</el-button>
    </div>

    <!-- 状态卡片 -->
    <el-row :gutter="16" v-if="status" style="margin-bottom: 16px">
      <el-col :span="6">
        <el-card><div class="stat"><div class="label">Total</div><div class="value">{{ status.total }}</div></div></el-card>
      </el-col>
      <el-col :span="6">
        <el-card><div class="stat"><div class="label">Completed</div><div class="value success">{{ status.completed }}</div></div></el-card>
      </el-col>
      <el-col :span="6">
        <el-card><div class="stat"><div class="label">Failed</div><div class="value danger">{{ status.failed }}</div></div></el-card>
      </el-col>
      <el-col :span="6">
        <el-card><div class="stat"><div class="label">Running</div><div class="value warning">{{ status.running }}</div></div></el-card>
      </el-col>
    </el-row>

    <!-- 任务列表 -->
    <el-table :data="jobs" v-loading="loading" border>
      <el-table-column prop="job_id" label="Job ID" width="120" />
      <el-table-column prop="dataset_id" label="Dataset" width="120" />
      <el-table-column prop="feature_ids" label="Features" width="200">
        <template #default="{ row }">
          <el-tag v-for="f in row.feature_ids" :key="f" size="small" style="margin-right: 4px">{{ f }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="label_id" label="Label" width="150" />
      <el-table-column prop="model_type" label="Model" width="150" />
      <el-table-column prop="status" label="Status" width="120">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Metrics" v-if="jobs.length > 0 && jobs[0].metrics">
        <template #default="{ row }">
          <span v-if="row.metrics">IC: {{ row.metrics.ic?.toFixed(4) }}, RMSE: {{ row.metrics.rmse?.toFixed(4) }}</span>
        </template>
      </el-table-column>
    </el-table>

    <!-- 训练对话框 -->
    <el-dialog v-model="showTrainDialog" title="Start Training" width="600px">
      <el-form :model="trainForm" label-width="120px">
        <el-form-item label="Dataset">
          <el-select v-model="trainForm.dataset_id" placeholder="Select dataset" style="width: 100%">
            <el-option v-for="ds in datasets" :key="ds.dataset_id" :label="ds.name" :value="ds.dataset_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Features">
          <el-select v-model="trainForm.feature_ids" multiple placeholder="Select features" style="width: 100%">
            <el-option v-for="f in features" :key="f.feature_id" :label="f.name" :value="f.feature_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Label">
          <el-select v-model="trainForm.label_id" placeholder="Select label" style="width: 100%">
            <el-option v-for="l in labels" :key="l.label_id" :label="l.name" :value="l.label_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Model">
          <el-select v-model="trainForm.model_type" style="width: 100%">
            <el-option v-for="m in models" :key="m.type" :label="m.name" :value="m.type" />
          </el-select>
        </el-form-item>
        <el-form-item label="Classifier">
          <el-switch v-model="trainForm.is_classifier" />
        </el-form-item>
        <el-form-item label="Train Ratio">
          <el-slider v-model="trainForm.train_ratio" :min="0.5" :max="0.9" :step="0.05" show-input />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showTrainDialog = false">Cancel</el-button>
        <el-button type="primary" :loading="training" @click="startTraining">Train</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getTrainingJobs, submitTraining,
  getMLDatasets, getMLFeatures, getMLLabels, getMLModels,
  type MLDataset, type MLFeature, type MLLabel, type MLModel,
} from '@/api/ml'

const jobs = ref<any[]>([])
const status = ref<any>(null)
const loading = ref(false)
const training = ref(false)
const showTrainDialog = ref(false)

const datasets = ref<MLDataset[]>([])
const features = ref<MLFeature[]>([])
const labels = ref<MLLabel[]>([])
const models = ref<MLModel[]>([])

const trainForm = ref({
  dataset_id: '',
  feature_ids: [] as string[],
  label_id: '',
  model_type: 'LINEAR_REGRESSION',
  is_classifier: false,
  train_ratio: 0.7,
  val_ratio: 0.15,
})

function statusType(s: string): string {
  if (s === 'COMPLETED') return 'success'
  if (s === 'FAILED') return 'danger'
  if (s === 'RUNNING') return 'warning'
  return 'info'
}

async function loadData() {
  loading.value = true
  try {
    const [jobsResp, dsResp, featResp, labelResp, modelResp] = await Promise.all([
      getTrainingJobs(),
      getMLDatasets(),
      getMLFeatures(),
      getMLLabels(),
      getMLModels(),
    ])
    jobs.value = jobsResp.jobs || []
    status.value = jobsResp.status
    datasets.value = dsResp.datasets || []
    features.value = featResp.features || []
    labels.value = labelResp.labels || []
    models.value = modelResp.models || []
  } catch (e) {
    ElMessage.error('Failed to load data')
  } finally {
    loading.value = false
  }
}

async function startTraining() {
  if (!trainForm.value.dataset_id || trainForm.value.feature_ids.length === 0 || !trainForm.value.label_id) {
    ElMessage.warning('Please fill all fields')
    return
  }
  training.value = true
  try {
    const result = await submitTraining(trainForm.value)
    if (result.status === 'COMPLETED') {
      ElMessage.success(`Training completed! IC=${result.metrics?.ic?.toFixed(4)}`)
    } else {
      ElMessage.error(`Training failed: ${result.error}`)
    }
    showTrainDialog.value = false
    loadData()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || 'Training failed')
  } finally {
    training.value = false
  }
}

onMounted(() => {
  loadData()
})
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

.stat {
  text-align: center;
}

.stat .label {
  color: #909399;
  font-size: 13px;
}

.stat .value {
  font-size: 24px;
  font-weight: bold;
  margin-top: 4px;
}

.stat .value.success { color: #67c23a; }
.stat .value.danger { color: #f56c6c; }
.stat .value.warning { color: #e6a23c; }
</style>
