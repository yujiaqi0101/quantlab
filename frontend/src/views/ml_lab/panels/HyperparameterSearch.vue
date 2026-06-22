<template>
  <div class="hyperparameter-search">
    <div class="panel-header">
      <h2>超参搜索 Hyperparameter Search</h2>
    </div>

    <el-card>
      <el-form :model="form" label-width="140px" inline>
        <el-form-item label="数据集 Dataset">
          <el-select v-model="form.dataset_id" placeholder="选择数据集 Select dataset" style="width: 200px">
            <el-option v-for="d in datasets" :key="d.dataset_id" :label="d.name" :value="d.dataset_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="特征集 FeatureSet">
          <el-select v-model="form.feature_set_id" placeholder="可选 Optional" style="width: 200px">
            <el-option v-for="f in featureSets" :key="f.name" :label="f.name" :value="f.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签集 LabelSet">
          <el-select v-model="form.label_set_id" placeholder="可选 Optional" style="width: 200px">
            <el-option v-for="l in labelSets" :key="l.name" :label="l.name" :value="l.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="模型 Model">
          <el-select v-model="form.model_type" style="width: 200px">
            <el-option label="线性回归 Linear" value="LINEAR_REGRESSION" />
            <el-option label="随机森林 Random Forest" value="RANDOM_FOREST" />
            <el-option label="LightGBM" value="LIGHTGBM" />
            <el-option label="XGBoost" value="XGBOOST" />
          </el-select>
        </el-form-item>
        <el-form-item label="搜索类型 Search Type">
          <el-radio-group v-model="searchType">
            <el-radio-button label="grid">网格 Grid</el-radio-button>
            <el-radio-button label="random">随机 Random</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="指标 Metric">
          <el-select v-model="form.metric" style="width: 120px">
            <el-option label="IC" value="ic" />
            <el-option label="RMSE" value="rmse" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="searchType === 'random'" label="试验次数 N Trials">
          <el-input-number v-model="form.n_trials" :min="1" :max="100" />
        </el-form-item>
      </el-form>

      <el-divider content-position="left">参数空间（JSON）Parameter Space</el-divider>
      <el-input
        v-model="paramJson"
        type="textarea"
        :rows="6"
        placeholder='Grid: {"n_estimators": [50, 100], "max_depth": [3, 5]}  Random: {"n_estimators": [50, 500], "learning_rate": [0.01, 0.3]}'
      />

      <div style="margin-top: 16px; text-align: right">
        <el-button type="primary" :loading="running" @click="runSearch">运行搜索 Run Search</el-button>
      </div>
    </el-card>

    <!-- 结果 -->
    <el-card v-if="result" style="margin-top: 16px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span>搜索结果（{{ result.n_trials }} 次试验）Search Results</span>
          <el-tag type="success">最佳 Best: {{ result.best_metric?.toFixed(4) }}</el-tag>
        </div>
      </template>

      <el-descriptions :column="1" border>
        <el-descriptions-item label="最佳指标 Best Metric">{{ result.best_metric?.toFixed(6) }}</el-descriptions-item>
        <el-descriptions-item label="最佳参数 Best Params">
          <pre>{{ JSON.stringify(result.best_params, null, 2) }}</pre>
        </el-descriptions-item>
      </el-descriptions>

      <h4>试验记录 Trials</h4>
      <el-table :data="result.trials" border size="small">
        <el-table-column prop="trial_id" label="试验 Trial" width="80" />
        <el-table-column label="参数 Params">
          <template #default="{ row }">
            <pre style="margin: 0">{{ JSON.stringify(row.params) }}</pre>
          </template>
        </el-table-column>
        <el-table-column label="指标 Metric" width="120">
          <template #default="{ row }">
            {{ row.metric_value?.toFixed(4) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态 Status" width="100" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  runGridSearch,
  runRandomSearch,
  getMLDatasets,
  getFeatureSets,
  getLabelSets,
  type SearchResult,
  type MLDataset,
  type MLFeatureSet,
  type MLLabelSet,
} from '@/api/ml'

const datasets = ref<MLDataset[]>([])
const featureSets = ref<MLFeatureSet[]>([])
const labelSets = ref<MLLabelSet[]>([])
const running = ref(false)
const result = ref<SearchResult | null>(null)
const searchType = ref<'grid' | 'random'>('grid')
const paramJson = ref('{\n  "n_estimators": [50, 100],\n  "max_depth": [3, 5]\n}')

const form = ref({
  dataset_id: '',
  feature_set_id: '',
  label_set_id: '',
  model_type: 'LIGHTGBM',
  metric: 'ic',
  n_trials: 10,
})

async function loadOptions() {
  const [ds, fs, ls] = await Promise.all([getMLDatasets(), getFeatureSets(), getLabelSets()])
  datasets.value = ds.datasets
  featureSets.value = fs.sets
  labelSets.value = ls.sets
}

async function runSearch() {
  if (!form.value.dataset_id) {
    ElMessage.warning('请选择数据集 Please select a dataset')
    return
  }
  if (!form.value.feature_set_id || !form.value.label_set_id) {
    ElMessage.warning('请选择特征集和标签集 Please select FeatureSet and LabelSet')
    return
  }

  let params: any
  try {
    params = JSON.parse(paramJson.value)
  } catch {
    ElMessage.error('无效的JSON Invalid JSON')
    return
  }

  running.value = true
  try {
    const base = {
      dataset_id: form.value.dataset_id,
      feature_set_id: form.value.feature_set_id,
      label_set_id: form.value.label_set_id,
      model_type: form.value.model_type,
      metric: form.value.metric,
    }
    if (searchType.value === 'grid') {
      result.value = await runGridSearch({ ...base, param_grid: params })
    } else {
      result.value = await runRandomSearch({ ...base, param_space: params, n_trials: form.value.n_trials })
    }
    ElMessage.success('搜索完成 Search completed')
  } catch (e: any) {
    ElMessage.error(e.message || '搜索失败 Search failed')
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
pre {
  background: #f5f7fa;
  padding: 8px;
  border-radius: 4px;
  font-size: 12px;
  margin: 0;
}
</style>
