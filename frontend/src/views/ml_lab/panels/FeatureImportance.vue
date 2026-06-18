<template>
  <div class="feature-importance">
    <div class="panel-header">
      <h2>Feature Importance</h2>
    </div>

    <el-card>
      <el-form :model="form" label-width="120px" inline>
        <el-form-item label="Dataset">
          <el-select v-model="form.dataset_id" placeholder="Select dataset" style="width: 200px" @change="onDatasetChange">
            <el-option v-for="d in datasets" :key="d.dataset_id" :label="d.name" :value="d.dataset_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="FeatureSet">
          <el-select v-model="form.feature_set_id" style="width: 200px" @change="onFeatureSetChange">
            <el-option v-for="f in featureSets" :key="f.name" :label="f.name" :value="f.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="LabelSet">
          <el-select v-model="form.label_set_id" style="width: 200px">
            <el-option v-for="l in labelSets" :key="l.name" :label="l.name" :value="l.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="Model">
          <el-select v-model="form.model_type" style="width: 160px">
            <el-option label="Linear" value="LINEAR_REGRESSION" />
            <el-option label="Random Forest" value="RANDOM_FOREST" />
            <el-option label="LightGBM" value="LIGHTGBM" />
            <el-option label="XGBoost" value="XGBOOST" />
          </el-select>
        </el-form-item>
        <el-form-item label="Methods">
          <el-checkbox-group v-model="form.methods">
            <el-checkbox label="gain">Gain</el-checkbox>
            <el-checkbox label="permutation">Permutation</el-checkbox>
            <el-checkbox label="shap">SHAP</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>

      <div style="margin-top: 16px; text-align: right">
        <el-button type="primary" :loading="running" @click="runAnalysis">Compute Importance</el-button>
      </div>
    </el-card>

    <!-- 结果 -->
    <el-card v-if="results" style="margin-top: 16px">
      <el-tabs v-model="activeMethod">
        <el-tab-pane
          v-for="method in Object.keys(results)"
          :key="method"
          :label="method.toUpperCase()"
          :name="method"
        >
          <div v-if="results[method]">
            <el-table :data="results[method].details" border size="small">
              <el-table-column prop="rank" label="Rank" width="80" sortable />
              <el-table-column prop="feature" label="Feature" />
              <el-table-column label="Importance" width="160" sortable :sort-by="'importance'">
                <template #default="{ row }">
                  {{ row.importance.toFixed(6) }}
                </template>
              </el-table-column>
              <el-table-column label="Normalized" width="180">
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
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  computeFeatureImportance,
  getMLDatasets,
  getFeatureSets,
  getLabelSets,
  getMLDatasetStats,
  type MLDataset,
  type MLFeatureSet,
  type MLLabelSet,
  type ImportanceResult,
} from '@/api/ml'

const datasets = ref<MLDataset[]>([])
const featureSets = ref<MLFeatureSet[]>([])
const labelSets = ref<MLLabelSet[]>([])
const running = ref(false)
const results = ref<Record<string, ImportanceResult> | null>(null)
const activeMethod = ref('')

const form = ref({
  dataset_id: '',
  feature_set_id: '',
  label_set_id: '',
  model_type: 'LIGHTGBM',
  methods: ['gain', 'permutation'] as string[],
})

async function loadOptions() {
  const [ds, fs, ls] = await Promise.all([getMLDatasets(), getFeatureSets(), getLabelSets()])
  datasets.value = ds.datasets
  featureSets.value = fs.sets
  labelSets.value = ls.sets
}

async function onDatasetChange() {
  // 可在此加载预览数据
}

async function onFeatureSetChange() {
  // 可在此加载特征列表
}

async function runAnalysis() {
  if (!form.value.dataset_id || !form.value.feature_set_id || !form.value.label_set_id) {
    ElMessage.warning('Please select dataset, FeatureSet, and LabelSet')
    return
  }
  running.value = true
  try {
    // 这里简化处理：前端直接调用 API，后端需要从 dataset 加载数据
    // 实际应用中可能需要先获取数据预览，再传给 API
    ElMessage.info('Feature Importance analysis requires data preview. This is a simplified UI.')
    // TODO: 实际实现需要先获取数据，然后调用 computeFeatureImportance
    running.value = false
  } catch (e: any) {
    ElMessage.error(e.message || 'Analysis failed')
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
</style>
