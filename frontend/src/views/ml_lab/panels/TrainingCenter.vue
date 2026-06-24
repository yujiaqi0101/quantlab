<template>
  <div class="training-center">
    <div class="panel-header">
      <h2>训练中心 Training Center</h2>
      <el-button type="primary" @click="showTrainDialog = true">开始训练 Start Training</el-button>
    </div>

    <!-- 状态卡片 -->
    <el-row :gutter="16" v-if="status" style="margin-bottom: 16px">
      <el-col :span="6">
        <el-card><div class="stat"><div class="label">总计 Total</div><div class="value">{{ status.total }}</div></div></el-card>
      </el-col>
      <el-col :span="6">
        <el-card><div class="stat"><div class="label">已完成 Completed</div><div class="value success">{{ status.completed }}</div></div></el-card>
      </el-col>
      <el-col :span="6">
        <el-card><div class="stat"><div class="label">失败 Failed</div><div class="value danger">{{ status.failed }}</div></div></el-card>
      </el-col>
      <el-col :span="6">
        <el-card><div class="stat"><div class="label">运行中 Running</div><div class="value warning">{{ status.running }}</div></div></el-card>
      </el-col>
    </el-row>

    <!-- 任务列表 -->
    <el-table :data="jobs" v-loading="loading" border>
      <el-table-column prop="job_id" label="任务ID Job ID" width="120" />
      <el-table-column prop="dataset_id" label="数据集 Dataset" width="120" />
      <el-table-column prop="feature_ids" label="特征 Features" width="200">
        <template #default="{ row }">
          <el-tag v-for="f in row.feature_ids" :key="f" size="small" style="margin-right: 4px">{{ f }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="label_id" label="标签 Label" width="150" />
      <el-table-column prop="model_type" label="模型 Model" width="150" />
      <el-table-column label="方法 Methods" width="200">
        <template #default="{ row }">
          <el-tag v-for="m in (row.methods || ['gain'])" :key="m" size="small" :type="methodTagType(m)" style="margin-right: 4px">{{ m }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="训练比例 Train Ratio" width="120">
        <template #default="{ row }">
          <span>{{ ((row.train_ratio || 0) * 100).toFixed(0) }}%</span>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态 Status" width="120">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="指标 Metrics" v-if="jobs.length > 0 && jobs[0].metrics">
        <template #default="{ row }">
          <span v-if="row.metrics">IC: {{ row.metrics.ic?.toFixed(4) }}, RMSE: {{ row.metrics.rmse?.toFixed(4) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="Raw Model" width="140">
        <template #default="{ row }">
          <el-tag v-if="row.model_version_id" type="warning" size="small">
            {{ row.model_version_id }}
          </el-tag>
          <span v-else style="color: #c0c4cc; font-size: 12px;">无</span>
        </template>
      </el-table-column>
      <el-table-column label="实验 Experiment" width="140">
        <template #default="{ row }">
          <el-tag v-if="row.experiment_id" size="small">
            {{ row.experiment_id }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>

    <!-- 训练对话框 -->
    <el-dialog v-model="showTrainDialog" title="开始训练 Start Training" width="600px">
      <el-form :model="trainForm" label-width="120px">
        <el-form-item label="数据集 Dataset">
          <el-select v-model="trainForm.dataset_id" placeholder="选择数据集 Select dataset" style="width: 100%">
            <el-option v-for="ds in datasets" :key="ds.dataset_id" :label="ds.name" :value="ds.dataset_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="输入模式 Mode">
          <el-radio-group v-model="trainMode">
            <el-radio label="set">特征集 FeatureSet（推荐）</el-radio>
            <el-radio label="raw">单个特征 Features</el-radio>
          </el-radio-group>
        </el-form-item>
        <template v-if="trainMode === 'set'">
          <el-form-item label="特征集 FeatureSet">
            <el-select v-model="trainForm.feature_set_id" placeholder="选择特征集 Select feature set" style="width: 100%">
              <el-option v-for="f in featureSets" :key="f.name" :label="f.name" :value="f.name" />
            </el-select>
          </el-form-item>
          <el-form-item label="标签集 LabelSet">
            <el-select v-model="trainForm.label_set_id" placeholder="选择标签集 Select label set" style="width: 100%">
              <el-option v-for="l in labelSets" :key="l.name" :label="l.name" :value="l.name" />
            </el-select>
          </el-form-item>
        </template>
        <template v-else>
          <el-form-item label="特征 Features">
            <el-select v-model="trainForm.feature_ids" multiple placeholder="选择特征 Select features" style="width: 100%">
              <el-option v-for="f in features" :key="f.feature_id" :label="f.name" :value="f.feature_id" />
            </el-select>
          </el-form-item>
          <el-form-item label="标签 Label">
            <el-select v-model="trainForm.label_id" placeholder="选择标签 Select label" style="width: 100%">
              <el-option v-for="l in labels" :key="l.label_id" :label="l.name" :value="l.label_id" />
            </el-select>
          </el-form-item>
        </template>
        <el-form-item label="模型 Model">
          <el-select v-model="trainForm.model_type" style="width: 100%">
            <el-option v-for="m in models" :key="m.type" :label="m.name" :value="m.type" />
          </el-select>
        </el-form-item>
        <el-form-item label="分类器 Classifier">
          <el-switch v-model="trainForm.is_classifier" />
        </el-form-item>
        <el-form-item label="训练比例 Train Ratio">
          <el-slider v-model="trainForm.train_ratio" :min="0.5" :max="0.9" :step="0.05" show-input />
        </el-form-item>
        <el-form-item label="方法 Methods">
          <el-checkbox-group v-model="trainForm.methods">
            <el-checkbox label="gain">增益 Gain</el-checkbox>
            <el-checkbox label="permutation">置换 Permutation</el-checkbox>
            <el-checkbox label="shap">SHAP</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showTrainDialog = false">取消 Cancel</el-button>
        <el-button type="primary" :loading="training" @click="startTraining">训练 Train</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getTrainingJobs, submitTraining,
  getMLDatasets, getMLFeatures, getMLLabels, getMLModels,
  getFeatureSets, getLabelSets,
  type MLDataset, type MLFeature, type MLLabel, type MLModel,
  type MLFeatureSet, type MLLabelSet,
} from '@/api/ml'
import { useMlTrainingStore } from '@/stores/mlTraining'

const jobs = ref<any[]>([])
const status = ref<any>(null)
const loading = ref(false)
const training = ref(false)
const showTrainDialog = ref(false)

const datasets = ref<MLDataset[]>([])
const features = ref<MLFeature[]>([])
const labels = ref<MLLabel[]>([])
const models = ref<MLModel[]>([])
const featureSets = ref<MLFeatureSet[]>([])
const labelSets = ref<MLLabelSet[]>([])

// 输入模式：set=特征集（推荐，与 Arena 一致），raw=单个特征
const trainMode = ref<'set' | 'raw'>('set')

const mlTrainingStore = useMlTrainingStore()

const trainForm = ref({
  dataset_id: '',
  feature_ids: [] as string[],
  label_id: '',
  feature_set_id: '',
  label_set_id: '',
  model_type: 'LINEAR_REGRESSION',
  is_classifier: false,
  train_ratio: 0.7,
  val_ratio: 0.15,
  methods: [] as string[],
})

function statusType(s: string): string {
  if (s === 'COMPLETED') return 'success'
  if (s === 'FAILED') return 'danger'
  if (s === 'RUNNING') return 'warning'
  return 'info'
}

function methodTagType(m: string): string {
  if (m === 'gain') return 'success'
  if (m === 'permutation') return 'warning'
  if (m === 'shap') return 'danger'
  return 'info'
}

async function loadData() {
  loading.value = true
  try {
    const [jobsResp, dsResp, featResp, labelResp, modelResp, fsResp, lsResp] = await Promise.all([
      getTrainingJobs(),
      getMLDatasets(),
      getMLFeatures(),
      getMLLabels(),
      getMLModels(),
      getFeatureSets(),
      getLabelSets(),
    ])
    jobs.value = jobsResp.jobs || []
    status.value = jobsResp.status
    datasets.value = dsResp.datasets || []
    features.value = featResp.features || []
    labels.value = labelResp.labels || []
    models.value = modelResp.models || []
    featureSets.value = fsResp.sets || []
    labelSets.value = lsResp.sets || []
  } catch (e) {
    ElMessage.error('加载数据失败 Failed to load data')
  } finally {
    loading.value = false
  }
}

async function startTraining() {
  if (!trainForm.value.dataset_id) {
    ElMessage.warning('请选择数据集 Please select dataset')
    return
  }
  if (trainMode.value === 'set') {
    if (!trainForm.value.feature_set_id || !trainForm.value.label_set_id) {
      ElMessage.warning('请选择特征集和标签集 Please select FeatureSet and LabelSet')
      return
    }
  } else {
    if (trainForm.value.feature_ids.length === 0 || !trainForm.value.label_id) {
      ElMessage.warning('请选择特征和标签 Please select features and label')
      return
    }
  }
  if (trainForm.value.methods.length === 0) {
    ElMessage.warning('请至少选择一种特征重要性方法 Please select at least one method')
    return
  }
  training.value = true
  try {
    const result = await submitTraining(trainForm.value)
    if (result.status === 'COMPLETED') {
      ElMessage.success(`训练完成！IC=${result.metrics?.ic?.toFixed(4)}`)
    } else {
      ElMessage.error(`训练失败：${result.error}`)
    }
    showTrainDialog.value = false
    loadData()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '训练失败 Training failed')
  } finally {
    training.value = false
  }
}

// Arena → TrainingCenter 联动：预填充就绪后填充表单并打开对话框
watch(() => mlTrainingStore.prefill.ready, (ready) => {
  if (!ready) return
  const p = mlTrainingStore.prefill
  trainMode.value = 'set'
  trainForm.value.dataset_id = p.dataset_id
  trainForm.value.feature_set_id = p.feature_set_id
  trainForm.value.label_set_id = p.label_set_id
  trainForm.value.model_type = p.model_type
  showTrainDialog.value = true
  mlTrainingStore.consume()
})

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
