<template>
  <div class="label-diagnostics">
    <div class="panel-header">
      <h2>Label Diagnostics</h2>
      <p class="hint">
        M1 必做：统计 label_distribution，发现标签严重失衡并报警（如 上涨 95% / 下跌 5%）。
      </p>
    </div>

    <!-- 输入区 -->
    <el-card shadow="never" class="input-card">
      <template #header>
        <div class="card-header">
          <span>一键诊断（Dataset + FeatureSet + Label）</span>
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
      v-if="report && report.is_imbalanced"
      type="error"
      :closable="false"
      show-icon
      class="alert-banner"
    >
      <span>
        <strong>标签严重失衡！</strong>
        最大类别占比 {{ (report.result.max_class_ratio * 100).toFixed(1) }}%，
        最小类别占比 {{ (report.result.min_class_ratio * 100).toFixed(1) }}%。
        <span v-if="report.issues.length">问题：{{ report.issues.map(issueLabel).join('、') }}</span>
      </span>
    </el-alert>
    <el-alert
      v-else-if="report && report.is_bad"
      type="warning"
      :closable="false"
      show-icon
      class="alert-banner"
    >
      <span>标签存在问题：{{ report.issues.map(issueLabel).join('、') }}</span>
    </el-alert>
    <el-alert
      v-else-if="report && !report.is_bad"
      type="success"
      :closable="false"
      show-icon
      class="alert-banner"
    >
      标签诊断通过，分布正常。
    </el-alert>

    <!-- 汇总卡片 -->
    <div v-if="report" class="summary-cards">
      <el-card shadow="never" class="summary-card">
        <div class="metric">
          <div class="metric-value">{{ report.result.n_samples }}</div>
          <div class="metric-label">Samples</div>
        </div>
      </el-card>
      <el-card shadow="never" class="summary-card">
        <div class="metric">
          <div class="metric-value">{{ report.result.label_type }}</div>
          <div class="metric-label">Label Type</div>
        </div>
      </el-card>
      <el-card shadow="never" class="summary-card">
        <div class="metric">
          <div class="metric-value">{{ report.result.n_classes }}</div>
          <div class="metric-label">Classes</div>
        </div>
      </el-card>
      <el-card shadow="never" class="summary-card" :class="{ bad: report.is_imbalanced }">
        <div class="metric">
          <div class="metric-value">{{ (report.result.max_class_ratio * 100).toFixed(1) }}%</div>
          <div class="metric-label">Max Class Ratio</div>
        </div>
      </el-card>
    </div>

    <!-- 分类标签：类别分布 -->
    <el-card v-if="report && report.result.label_type === 'classification' && hasClassDist" shadow="never" class="dist-card">
      <template #header>Class Distribution</template>
      <div class="dist-bars">
        <div v-for="(ratio, cls) in report.result.class_distribution" :key="cls" class="dist-item">
          <div class="dist-label">Class {{ cls }}</div>
          <div class="dist-bar-wrapper">
            <div
              class="dist-bar"
              :class="{ imbalanced: ratio > 0.9 || ratio < 0.01 }"
              :style="{ width: (ratio * 100) + '%' }"
            ></div>
          </div>
          <div class="dist-ratio">{{ (ratio * 100).toFixed(2) }}%</div>
        </div>
      </div>
    </el-card>

    <!-- 回归标签：统计信息 -->
    <el-card v-if="report && report.result.label_type === 'regression'" shadow="never" class="dist-card">
      <template #header>Regression Statistics</template>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="Mean">
          {{ report.result.mean === null ? '-' : report.result.mean.toFixed(6) }}
        </el-descriptions-item>
        <el-descriptions-item label="Std">
          {{ report.result.std === null ? '-' : report.result.std.toFixed(6) }}
        </el-descriptions-item>
        <el-descriptions-item label="Variance">
          <span :class="{ 'bad-cell': report.result.variance !== null && report.result.variance < 1e-10 }">
            {{ report.result.variance === null ? '-' : report.result.variance.toExponential(3) }}
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="Unique Values">
          {{ report.result.n_unique }}
        </el-descriptions-item>
        <el-descriptions-item label="Missing">
          {{ report.result.n_missing }} ({{ (report.result.missing_rate * 100).toFixed(2) }}%)
        </el-descriptions-item>
        <el-descriptions-item label="Inf Count">
          <span :class="{ 'bad-cell': report.result.n_inf > 0 }">{{ report.result.n_inf }}</span>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 问题列表 -->
    <el-card v-if="report && report.issues.length > 0" shadow="never" class="issue-card">
      <template #header>Issues</template>
      <div class="issue-tags">
        <el-tag
          v-for="issue in report.issues"
          :key="issue"
          :type="issue.includes('imbalance') || issue === 'all_missing' ? 'danger' : 'warning'"
          class="issue-tag"
        >
          {{ issueLabel(issue) }}
        </el-tag>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getMLDatasets,
  getFeatureSets,
  getMLLabels,
  runTrainingDatasetDiagnostics,
  type MLDataset,
  type MLFeatureSet,
  type MLLabel,
  type LabelDiagnosticsReport,
} from '@/api/ml'

const datasets = ref<MLDataset[]>([])
const featureSets = ref<MLFeatureSet[]>([])
const labels = ref<MLLabel[]>([])
const loading = ref(false)
const report = ref<LabelDiagnosticsReport | null>(null)

const form = ref({
  dataset_id: '',
  feature_set_name: '',
  label_id: '',
})

const hasClassDist = computed(() => {
  if (!report.value) return false
  return Object.keys(report.value.result.class_distribution).length > 0
})

// 问题类型中文标签
const ISSUE_LABELS: Record<string, string> = {
  all_missing: '全为空',
  high_missing_rate: '缺失率过高',
  has_inf: '含无穷值',
  near_zero_variance: '方差≈0',
  constant_label: '常量标签',
  single_class: '仅一个类别',
  severe_imbalance: '严重失衡',
  rare_class: '稀有类别',
  empty_label: '空标签',
}

function issueLabel(issue: string): string {
  return ISSUE_LABELS[issue] || issue
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
    const fs = featureSets.value.find(f => f.name === form.value.feature_set_name)
    if (!fs || !fs.feature_ids.length) {
      throw new Error('FeatureSet has no features')
    }

    // 通过后端 /diagnostics/training-dataset 端点直接诊断
    const result = await runTrainingDatasetDiagnostics({
      dataset_id: form.value.dataset_id,
      feature_ids: fs.feature_ids,
      label_id: form.value.label_id,
    })
    report.value = result.label_diagnostics
    ElMessage.success(`Diagnostics done: ${result.n_samples} samples`)
  } catch (e: any) {
    ElMessage.error(e.message || 'Diagnostics failed')
  } finally {
    loading.value = false
  }
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
  font-size: 24px;
  font-weight: bold;
  color: #409eff;
}

.metric-label {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.dist-card {
  margin-bottom: 16px;
}

.dist-bars {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dist-item {
  display: grid;
  grid-template-columns: 120px 1fr 80px;
  align-items: center;
  gap: 12px;
}

.dist-label {
  font-size: 13px;
  color: #606266;
}

.dist-bar-wrapper {
  background: #f5f7fa;
  border-radius: 4px;
  height: 20px;
  overflow: hidden;
}

.dist-bar {
  height: 100%;
  background: #409eff;
  transition: width 0.3s;
}

.dist-bar.imbalanced {
  background: #f56c6c;
}

.dist-ratio {
  font-size: 13px;
  color: #606266;
  text-align: right;
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
</style>
