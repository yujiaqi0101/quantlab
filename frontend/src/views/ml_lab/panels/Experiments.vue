<template>
  <div class="experiments">
    <div class="panel-header">
      <h2>Experiments</h2>
      <div>
        <el-select v-model="filterModelType" placeholder="Model Type" clearable style="width: 160px; margin-right: 8px" @change="loadData">
          <el-option label="Linear" value="LINEAR_REGRESSION" />
          <el-option label="Random Forest" value="RANDOM_FOREST" />
          <el-option label="LightGBM" value="LIGHTGBM" />
          <el-option label="XGBoost" value="XGBOOST" />
        </el-select>
        <el-button @click="showSummary = true">Summary</el-button>
        <el-button type="primary" @click="showLeaderboard = true">Leaderboard</el-button>
      </div>
    </div>

    <el-table :data="experiments" v-loading="loading" border style="width: 100%">
      <el-table-column prop="experiment_id" label="ID" width="120" />
      <el-table-column prop="name" label="Name" width="180" />
      <el-table-column prop="model_type" label="Model" width="140" />
      <el-table-column label="IC" width="100">
        <template #default="{ row }">
          {{ row.metrics?.ic?.toFixed(4) ?? '-' }}
        </template>
      </el-table-column>
      <el-table-column label="Rank IC" width="100">
        <template #default="{ row }">
          {{ row.metrics?.rank_ic?.toFixed(4) ?? '-' }}
        </template>
      </el-table-column>
      <el-table-column label="RMSE" width="100">
        <template #default="{ row }">
          {{ row.metrics?.rmse?.toFixed(4) ?? '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="status" label="Status" width="120">
        <template #default="{ row }">
          <el-tag :type="row.status === 'COMPLETED' ? 'success' : 'info'" size="small">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="Created" width="180" />
      <el-table-column label="Actions" width="100">
        <template #default="{ row }">
          <el-button size="small" @click="viewDetail(row)">Detail</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 详情对话框 -->
    <el-dialog v-model="showDetail" title="Experiment Detail" width="700px">
      <div v-if="current">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="ID">{{ current.experiment_id }}</el-descriptions-item>
          <el-descriptions-item label="Name">{{ current.name }}</el-descriptions-item>
          <el-descriptions-item label="Dataset">{{ current.dataset_id }}</el-descriptions-item>
          <el-descriptions-item label="FeatureSet">{{ current.feature_set_id }}</el-descriptions-item>
          <el-descriptions-item label="LabelSet">{{ current.label_set_id }}</el-descriptions-item>
          <el-descriptions-item label="Model">{{ current.model_type }}</el-descriptions-item>
          <el-descriptions-item label="Classifier">{{ current.is_classifier }}</el-descriptions-item>
          <el-descriptions-item label="Status">{{ current.status }}</el-descriptions-item>
        </el-descriptions>
        <h4>Metrics</h4>
        <pre>{{ JSON.stringify(current.metrics, null, 2) }}</pre>
        <h4>Params</h4>
        <pre>{{ JSON.stringify(current.model_params, null, 2) }}</pre>
        <h4 v-if="current.feature_importance && Object.keys(current.feature_importance).length > 0">Feature Importance</h4>
        <pre v-if="current.feature_importance">{{ JSON.stringify(current.feature_importance, null, 2) }}</pre>
      </div>
    </el-dialog>

    <!-- 排行榜 -->
    <el-dialog v-model="showLeaderboard" title="Experiment Leaderboard" width="700px">
      <el-table :data="leaderboard" border>
        <el-table-column type="index" label="Rank" width="80" />
        <el-table-column prop="name" label="Name" />
        <el-table-column prop="model_type" label="Model" width="140" />
        <el-table-column label="IC" width="120">
          <template #default="{ row }">
            {{ row.metrics?.ic?.toFixed(4) ?? '-' }}
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 统计 -->
    <el-dialog v-model="showSummary" title="Experiment Summary" width="600px">
      <pre v-if="summary">{{ JSON.stringify(summary, null, 2) }}</pre>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getExperiments,
  getExperiment,
  getExperimentLeaderboard,
  getExperimentSummary,
  type MLExperiment,
} from '@/api/ml'

const experiments = ref<MLExperiment[]>([])
const loading = ref(false)
const filterModelType = ref('')
const showDetail = ref(false)
const showLeaderboard = ref(false)
const showSummary = ref(false)
const current = ref<MLExperiment | null>(null)
const leaderboard = ref<any[]>([])
const summary = ref<any>(null)

async function loadData() {
  loading.value = true
  try {
    const resp = await getExperiments({ model_type: filterModelType.value || undefined })
    experiments.value = resp.experiments
  } catch (e: any) {
    ElMessage.error(e.message || 'Failed to load')
  } finally {
    loading.value = false
  }
}

async function viewDetail(row: MLExperiment) {
  try {
    current.value = await getExperiment(row.experiment_id)
    showDetail.value = true
  } catch (e: any) {
    ElMessage.error(e.message || 'Failed to load')
  }
}

async function loadLeaderboard() {
  try {
    const resp = await getExperimentLeaderboard('ic', 20)
    leaderboard.value = resp.leaderboard
  } catch (e: any) {
    ElMessage.error(e.message || 'Failed to load leaderboard')
  }
}

async function loadSummary() {
  try {
    summary.value = await getExperimentSummary()
  } catch (e: any) {
    ElMessage.error(e.message || 'Failed to load summary')
  }
}

onMounted(() => {
  loadData()
  loadLeaderboard()
  loadSummary()
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
pre {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  max-height: 300px;
  overflow: auto;
}
</style>
