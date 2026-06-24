<template>
  <div class="model-arena">
    <div class="panel-header">
      <h2>模型竞技场 Model Arena</h2>
      <el-button type="primary" @click="showRunDialog = true">运行对比 Run Comparison</el-button>
    </div>

    <!-- 排行榜 -->
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>排行榜（按IC）Leaderboard (by IC)</span>
          <el-button size="small" @click="loadLeaderboard">刷新 Refresh</el-button>
        </div>
      </template>
      <el-table :data="leaderboard" v-loading="loading" border>
        <el-table-column type="index" label="排名 Rank" width="80" />
        <el-table-column prop="name" label="模型 Model" width="180" />
        <el-table-column prop="model_type" label="类型 Type" width="160" />
        <el-table-column label="IC" width="120">
          <template #default="{ row }">
            {{ row.metrics?.ic?.toFixed(4) ?? '-' }}
          </template>
        </el-table-column>
        <el-table-column label="Rank IC" width="120">
          <template #default="{ row }">
            {{ row.metrics?.rank_ic?.toFixed(4) ?? '-' }}
          </template>
        </el-table-column>
        <el-table-column label="RMSE" width="120">
          <template #default="{ row }">
            {{ row.metrics?.rmse?.toFixed(4) ?? '-' }}
          </template>
        </el-table-column>
        <el-table-column label="训练时间 Train Time" width="120">
          <template #default="{ row }">
            {{ row.train_time?.toFixed(2) }}s
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态 Status" width="120" />
        <el-table-column label="操作 Action" width="140" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.status === 'COMPLETED'"
              type="primary"
              size="small"
              @click="useForTraining(row)"
            >
              用此模型训练
            </el-button>
            <span v-else style="color: #c0c4cc; font-size: 12px;">—</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 运行对比对话框 -->
    <el-dialog v-model="showRunDialog" title="运行模型对比 Run Model Comparison" width="600px">
      <el-form :model="form" label-width="120px">
        <el-form-item label="数据集 Dataset">
          <el-select v-model="form.dataset_id" placeholder="选择数据集 Select dataset" style="width: 100%">
            <el-option v-for="d in datasets" :key="d.dataset_id" :label="d.name" :value="d.dataset_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="特征集 FeatureSet">
          <el-select v-model="form.feature_set_id" placeholder="选择特征集 Select feature set" style="width: 100%">
            <el-option v-for="f in featureSets" :key="f.name" :label="f.name" :value="f.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签集 LabelSet">
          <el-select v-model="form.label_set_id" placeholder="选择标签集 Select label set" style="width: 100%">
            <el-option v-for="l in labelSets" :key="l.name" :label="l.name" :value="l.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="模型 Models">
          <el-checkbox-group v-model="form.model_types">
            <el-checkbox label="LINEAR_REGRESSION">线性回归 Linear</el-checkbox>
            <el-checkbox label="RANDOM_FOREST">随机森林 Random Forest</el-checkbox>
            <el-checkbox label="LIGHTGBM">LightGBM</el-checkbox>
            <el-checkbox label="XGBOOST">XGBoost</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRunDialog = false">取消 Cancel</el-button>
        <el-button type="primary" :loading="running" @click="runComparison">运行 Run</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getArenaLeaderboard,
  runModelComparison,
  getMLDatasets,
  getFeatureSets,
  getLabelSets,
  type ModelLeaderboardEntry,
  type MLDataset,
  type MLFeatureSet,
  type MLLabelSet,
} from '@/api/ml'
import { useMlTrainingStore } from '@/stores/mlTraining'

const leaderboard = ref<ModelLeaderboardEntry[]>([])
const loading = ref(false)
const running = ref(false)
const showRunDialog = ref(false)
const datasets = ref<MLDataset[]>([])
const featureSets = ref<MLFeatureSet[]>([])
const labelSets = ref<MLLabelSet[]>([])

const mlTrainingStore = useMlTrainingStore()

const form = ref({
  dataset_id: '',
  feature_set_id: '',
  label_set_id: '',
  model_types: ['LINEAR_REGRESSION', 'LIGHTGBM'] as string[],
})

async function loadLeaderboard() {
  loading.value = true
  try {
    const resp = await getArenaLeaderboard('ic', false)
    leaderboard.value = resp.leaderboard
  } catch (e: any) {
    ElMessage.error(e.message || '加载失败 Failed to load')
  } finally {
    loading.value = false
  }
}

async function loadOptions() {
  const [ds, fs, ls] = await Promise.all([getMLDatasets(), getFeatureSets(), getLabelSets()])
  datasets.value = ds.datasets
  featureSets.value = fs.sets
  labelSets.value = ls.sets
}

async function runComparison() {
  if (!form.value.dataset_id || !form.value.feature_set_id || !form.value.label_set_id) {
    ElMessage.warning('请选择数据集、特征集和标签集 Please select dataset, FeatureSet, and LabelSet')
    return
  }
  if (form.value.model_types.length === 0) {
    ElMessage.warning('请至少选择一个模型 Please select at least one model')
    return
  }

  running.value = true
  try {
    const resp = await runModelComparison({
      dataset_id: form.value.dataset_id,
      feature_set_id: form.value.feature_set_id,
      label_set_id: form.value.label_set_id,
      model_types: form.value.model_types,
    })
    leaderboard.value = resp.leaderboard
    ElMessage.success(`对比完成：${resp.total} 个模型 Comparison done: ${resp.total} models`)
    showRunDialog.value = false
  } catch (e: any) {
    ElMessage.error(e.message || '对比失败 Comparison failed')
  } finally {
    running.value = false
  }
}

function useForTraining(row: ModelLeaderboardEntry) {
  // 将 Arena 的配置写入 store，触发 MLLab 切到 training tab + TrainingCenter 预填充
  mlTrainingStore.setPrefill({
    dataset_id: form.value.dataset_id,
    feature_set_id: form.value.feature_set_id,
    label_set_id: form.value.label_set_id,
    model_type: row.model_type,
  })
  ElMessage.success(`已选择 ${row.model_type}，即将跳转到训练`)
}

onMounted(() => {
  loadLeaderboard()
  loadOptions()
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
</style>
