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
      </el-form>

      <div style="margin-top: 16px; text-align: right">
        <el-button type="primary" :loading="running" @click="runAnalysis">计算重要性 Compute</el-button>
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
import { ref, onMounted } from 'vue'
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

  await autoLoadFromJob()
}

async function autoLoadFromJob() {
  try {
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

    const jobsResp = await http.get('/ml/training/jobs')
    const jobs = jobsResp.data?.jobs || []
    const completed = jobs.filter((j: any) => j.status === 'COMPLETED')
    if (completed.length === 0) return

    const latestJob = completed[completed.length - 1]
    const resp = await http.get(`/ml/feature-importance/from-job/${latestJob.job_id}`)
    if (resp.data) {
      results.value = resp.data
      const methods = Object.keys(resp.data)
      if (methods.length > 0) activeMethod.value = methods[0]
    }
  } catch (e: any) {
    // 静默失败
  }
}

async function onDatasetChange() {}

async function onFeatureSetChange() {}

async function runAnalysis() {
  if (!form.value.dataset_id || !form.value.feature_set_id || !form.value.label_set_id) {
    ElMessage.warning('请选择数据集、特征集和标签集 Please select dataset, FeatureSet, and LabelSet')
    return
  }
  running.value = true
  try {
    const jobsResp = await http.get('/ml/training/jobs')
    const jobs = jobsResp.data?.jobs || []
    const matched = jobs.find((j: any) =>
      j.status === 'COMPLETED' && j.dataset_id === form.value.dataset_id
    )
    if (matched) {
      const resp = await http.get(`/ml/feature-importance/from-job/${matched.job_id}`)
      if (resp.data) {
        results.value = resp.data
        const methods = Object.keys(resp.data)
        if (methods.length > 0) activeMethod.value = methods[0]
        ElMessage.success('已从训练结果加载特征重要性 Feature importance loaded from training result')
      }
    } else {
      ElMessage.info('未找到该数据集的已完成训练任务，请先训练模型 No completed training job found for this dataset.')
    }
  } catch (e: any) {
    ElMessage.error(e.message || '分析失败 Analysis failed')
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
