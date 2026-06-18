<template>
  <div class="feature-diagnostics">
    <div class="panel-header">
      <h2>Feature Diagnostics</h2>
      <p class="hint">
        M1 必做：自动统计 missing_rate / inf_count / zero_rate / variance，发现坏特征并自动标红。
      </p>
    </div>

    <!-- 输入区：从 Dataset + FeatureSet 一键诊断 -->
    <el-card shadow="never" class="input-card">
      <template #header>
        <div class="card-header">
          <span>一键诊断（Dataset + FeatureSet）</span>
          <el-button type="primary" :loading="loading" @click="runFromDataset">Run Diagnostics</el-button>
        </div>
      </template>
      <el-form :inline="true" :model="form" label-width="120px">
        <el-form-item label="Dataset">
          <el-select v-model="form.dataset_id" placeholder="Select dataset" filterable style="width: 220px">
            <el-option
              v-for="d in datasets"
              :key="d.dataset_id"
              :label="d.name"
              :value="d.dataset_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="FeatureSet">
          <el-select v-model="form.feature_set_name" placeholder="Select feature set" filterable style="width: 220px">
            <el-option
              v-for="fs in featureSets"
              :key="fs.name"
              :label="fs.name"
              :value="fs.name"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="Label">
          <el-select v-model="form.label_id" placeholder="Select label" filterable style="width: 220px">
            <el-option
              v-for="l in labels"
              :key="l.label_id"
              :label="l.name"
              :value="l.label_id"
            />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 报警横幅 -->
    <el-alert
      v-if="report && report.n_bad > 0"
      type="error"
      :closable="false"
      show-icon
      class="alert-banner"
    >
      <span>
        发现 <strong>{{ report.n_bad }}</strong> 个坏特征（共 {{ report.n_features }} 个）：
        <el-tag v-for="f in report.bad_features" :key="f" type="danger" size="small" style="margin: 0 4px">
          {{ f }}
        </el-tag>
      </span>
    </el-alert>
    <el-alert
      v-else-if="report && report.n_bad === 0"
      type="success"
      :closable="false"
      show-icon
      class="alert-banner"
    >
      所有 {{ report.n_features }} 个特征均通过诊断，未发现坏特征。
    </el-alert>

    <!-- 汇总卡片 -->
    <div v-if="report" class="summary-cards">
      <el-card shadow="never" class="summary-card">
        <div class="metric">
          <div class="metric-value">{{ report.n_features }}</div>
          <div class="metric-label">Total Features</div>
        </div>
      </el-card>
      <el-card shadow="never" class="summary-card">
        <div class="metric">
          <div class="metric-value">{{ report.n_samples }}</div>
          <div class="metric-label">Samples</div>
        </div>
      </el-card>
      <el-card shadow="never" class="summary-card bad">
        <div class="metric">
          <div class="metric-value">{{ report.n_bad }}</div>
          <div class="metric-label">Bad Features</div>
        </div>
      </el-card>
      <el-card shadow="never" class="summary-card">
        <div class="metric">
          <div class="metric-value">{{ (report.summary.bad_ratio * 100).toFixed(1) }}%</div>
          <div class="metric-label">Bad Ratio</div>
        </div>
      </el-card>
    </div>

    <!-- 问题类型统计 -->
    <el-card v-if="report && Object.keys(report.summary.issue_counts).length > 0" shadow="never" class="issue-card">
      <template #header>Issue Breakdown</template>
      <div class="issue-tags">
        <el-tag
          v-for="(count, issue) in report.summary.issue_counts"
          :key="issue"
          type="warning"
          class="issue-tag"
        >
          {{ issueLabel(issue as string) }}: {{ count }}
        </el-tag>
      </div>
    </el-card>

    <!-- 详细结果表格 -->
    <el-table
      v-if="report"
      :data="report.results"
      border
      style="width: 100%; margin-top: 16px"
      :row-class-name="rowClassName"
    >
      <el-table-column prop="feature_name" label="Feature" width="180" fixed />
      <el-table-column prop="dtype" label="Dtype" width="100" />
      <el-table-column prop="n_samples" label="Samples" width="90" />
      <el-table-column label="Missing" width="140">
        <template #default="{ row }">
          <span :class="{ 'bad-cell': row.missing_rate > 0.5 }">
            {{ row.n_missing }} ({{ (row.missing_rate * 100).toFixed(1) }}%)
          </span>
        </template>
      </el-table-column>
      <el-table-column label="Inf" width="80">
        <template #default="{ row }">
          <span :class="{ 'bad-cell': row.n_inf > 0 }">{{ row.n_inf }}</span>
        </template>
      </el-table-column>
      <el-table-column label="Zero" width="140">
        <template #default="{ row }">
          <span :class="{ 'bad-cell': row.zero_rate > 0.5 }">
            {{ row.n_zero }} ({{ (row.zero_rate * 100).toFixed(1) }}%)
          </span>
        </template>
      </el-table-column>
      <el-table-column label="Variance" width="130">
        <template #default="{ row }">
          <span :class="{ 'bad-cell': row.variance !== null && row.variance < 1e-10 }">
            {{ row.variance === null ? '-' : row.variance.toExponential(3) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="n_unique" label="Unique" width="90" />
      <el-table-column label="Status" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_bad ? 'danger' : 'success'" size="small">
            {{ row.is_bad ? 'BAD' : 'OK' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Issues" min-width="200">
        <template #default="{ row }">
          <el-tag
            v-for="issue in row.issues"
            :key="issue"
            type="danger"
            size="small"
            style="margin: 2px"
          >
            {{ issueLabel(issue) }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getMLDatasets,
  getFeatureSets,
  getMLLabels,
  getMLDatasetStats,
  computeMLFeatures,
  runFeatureDiagnostics,
  type MLDataset,
  type MLFeatureSet,
  type MLLabel,
  type FeatureDiagnosticsReport,
} from '@/api/ml'

const datasets = ref<MLDataset[]>([])
const featureSets = ref<MLFeatureSet[]>([])
const labels = ref<MLLabel[]>([])
const loading = ref(false)
const report = ref<FeatureDiagnosticsReport | null>(null)

const form = ref({
  dataset_id: '',
  feature_set_name: '',
  label_id: '',
})

// 问题类型中文标签
const ISSUE_LABELS: Record<string, string> = {
  all_missing: '全为空',
  high_missing_rate: '缺失率过高',
  has_inf: '含无穷值',
  all_zero: '全为0',
  high_zero_rate: '零值率过高',
  near_zero_variance: '方差≈0',
  constant_feature: '常量特征',
  empty_column: '空列',
  diagnose_error: '诊断错误',
}

function issueLabel(issue: string): string {
  return ISSUE_LABELS[issue] || issue
}

function rowClassName({ row }: { row: any }): string {
  return row.is_bad ? 'bad-row' : ''
}

async function loadData() {
  try {
    const [dsResp, fsResp, lblResp] = await Promise.all([
      getMLDatasets(),
      getFeatureSets(),
      getMLLabels(),
    ])
    datasets.value = dsResp.datasets || []
    featureSets.value = fsResp.sets || []
    labels.value = lblResp.labels || []
  } catch (e) {
    ElMessage.error('Failed to load metadata')
  }
}

async function runFromDataset() {
  if (!form.value.dataset_id || !form.value.feature_set_name || !form.value.label_id) {
    ElMessage.warning('Please select dataset, feature set and label')
    return
  }

  loading.value = true
  try {
    // 1. 获取数据集统计信息（含数据预览）
    const stats = await getMLDatasetStats(form.value.dataset_id)
    // 2. 获取 FeatureSet 详情，拿到 feature_ids
    const fs = featureSets.value.find(f => f.name === form.value.feature_set_name)
    if (!fs || !fs.feature_ids.length) {
      throw new Error('FeatureSet has no features')
    }

    // 3. 从数据集预览中取数据，计算特征
    // 注意：这里使用 stats 中的 preview 数据；实际生产应通过专用接口拉取全量数据
    // 此处采用简化路径：直接调用 /features/compute
    // 由于 Dataset Center 的 preview 数据有限，这里给出提示
    if (!stats || !stats.columns || stats.columns.length === 0) {
      throw new Error('Dataset has no data, please upload CSV first')
    }

    ElMessage.info('Diagnostics requires feature matrix. Please use the manual input below or ensure dataset has data.')
    // 简化：如果数据集有数据，前端无法直接拿到全量 DataFrame
    // 这里给出一个占位提示，实际全量诊断建议通过 /diagnostics/training-dataset 端点
    // 该端点在后端直接读取 Dataset 数据并诊断
    await runViaTrainingDataset()
  } catch (e: any) {
    ElMessage.error(e.message || 'Diagnostics failed')
  } finally {
    loading.value = false
  }
}

async function runViaTrainingDataset() {
  // 通过后端 /diagnostics/training-dataset 端点直接诊断
  // 该端点在后端读取 Dataset 全量数据，无需前端传 DataFrame
  const { runTrainingDatasetDiagnostics } = await import('@/api/ml')
  const result = await runTrainingDatasetDiagnostics({
    dataset_id: form.value.dataset_id,
    feature_ids: featureSets.value.find(f => f.name === form.value.feature_set_name)?.feature_ids || [],
    label_id: form.value.label_id,
  })
  report.value = result.feature_diagnostics
  ElMessage.success(`Diagnostics done: ${result.n_samples} samples, ${result.n_features} features`)
}

onMounted(() => {
  loadData()
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

.input-card {
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.alert-banner {
  margin-bottom: 16px;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.summary-card {
  text-align: center;
}

.summary-card.bad .metric-value {
  color: #f56c6c;
}

.metric-value {
  font-size: 28px;
  font-weight: bold;
  color: #409eff;
}

.metric-label {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.issue-card {
  margin-bottom: 16px;
}

.issue-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.issue-tag {
  font-size: 13px;
}

.bad-cell {
  color: #f56c6c;
  font-weight: bold;
}

:deep(.bad-row) {
  background-color: #fef0f0;
}
</style>
