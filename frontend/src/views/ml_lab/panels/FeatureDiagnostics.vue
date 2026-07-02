<template>
  <div class="feature-diagnostics">
    <div class="panel-header">
      <h2>特征诊断 Feature Diagnostics</h2>
      <p class="hint">
        M1 必做：自动统计 missing_rate / inf_count / zero_rate / variance，发现坏特征并自动标红。
      </p>
    </div>

    <!-- 输入区：从 Dataset + FeatureSet 一键诊断 -->
    <el-card shadow="never" class="input-card">
      <template #header>
        <div class="card-header">
          <span>一键诊断（数据集 + 特征集）</span>
          <el-button type="primary" :loading="loading" @click="runFromDataset">运行诊断 Run</el-button>
        </div>
      </template>
      <el-form :inline="true" :model="form" label-width="120px">
        <el-form-item label="数据集 Dataset">
          <el-select v-model="form.dataset_id" placeholder="选择数据集 Select dataset" filterable style="width: 220px">
            <el-option
              v-for="d in datasets"
              :key="d.dataset_id"
              :label="d.name"
              :value="d.dataset_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="特征集 FeatureSet">
          <el-select v-model="form.feature_set_name" placeholder="选择特征集 Select feature set" filterable style="width: 220px">
            <el-option
              v-for="fs in featureSets"
              :key="fs.name"
              :label="fs.name"
              :value="fs.name"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="标签 Label">
          <el-select v-model="form.label_id" placeholder="选择标签 Select label" filterable style="width: 220px">
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
          <div class="metric-label">总特征数 Total Features</div>
        </div>
      </el-card>
      <el-card shadow="never" class="summary-card">
        <div class="metric">
          <div class="metric-value">{{ report.n_samples }}</div>
          <div class="metric-label">样本数 Samples</div>
        </div>
      </el-card>
      <el-card shadow="never" class="summary-card bad">
        <div class="metric">
          <div class="metric-value">{{ report.n_bad }}</div>
          <div class="metric-label">坏特征 Bad Features</div>
        </div>
      </el-card>
      <el-card shadow="never" class="summary-card">
        <div class="metric">
          <div class="metric-value">{{ (report.summary.bad_ratio * 100).toFixed(1) }}%</div>
          <div class="metric-label">坏特征率 Bad Ratio</div>
        </div>
      </el-card>
    </div>

    <!-- 问题类型统计 -->
    <el-card v-if="report && Object.keys(report.summary.issue_counts).length > 0" shadow="never" class="issue-card">
      <template #header>问题分类 Issue Breakdown</template>
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
      <el-table-column prop="feature_name" label="特征 Feature" width="180" fixed />
      <el-table-column prop="dtype" label="类型 Dtype" width="100" />
      <el-table-column prop="n_samples" label="样本数 Samples" width="90" />
      <el-table-column label="缺失 Missing" width="140">
        <template #default="{ row }">
          <span :class="{ 'bad-cell': row.missing_rate > 0.5 }">
            {{ row.n_missing }} ({{ (row.missing_rate * 100).toFixed(1) }}%)
          </span>
        </template>
      </el-table-column>
      <el-table-column label="无穷 Inf" width="80">
        <template #default="{ row }">
          <span :class="{ 'bad-cell': row.n_inf > 0 }">{{ row.n_inf }}</span>
        </template>
      </el-table-column>
      <el-table-column label="零值 Zero" width="140">
        <template #default="{ row }">
          <span :class="{ 'bad-cell': row.zero_rate > 0.5 }">
            {{ row.n_zero }} ({{ (row.zero_rate * 100).toFixed(1) }}%)
          </span>
        </template>
      </el-table-column>
      <el-table-column label="方差 Variance" width="130">
        <template #default="{ row }">
          <span :class="{ 'bad-cell': row.variance !== null && row.variance < 1e-10 }">
            {{ row.variance === null ? '-' : row.variance.toExponential(3) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="n_unique" label="唯一值 Unique" width="90" />
      <el-table-column label="状态 Status" width="100">
        <template #default="{ row }">
          <el-tag :type="row.is_bad ? 'danger' : 'success'" size="small">
            {{ row.is_bad ? '坏 BAD' : '好 OK' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="问题 Issues" min-width="200">
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
    ElMessage.error('加载元数据失败 Failed to load metadata')
  }
}

async function runFromDataset() {
  if (!form.value.dataset_id || !form.value.feature_set_name || !form.value.label_id) {
    ElMessage.warning('请选择数据集、特征集和标签 Please select dataset, feature set and label')
    return
  }

  loading.value = true
  try {
    const stats = await getMLDatasetStats(form.value.dataset_id)
    const fs = featureSets.value.find(f => f.name === form.value.feature_set_name)
    if (!fs || !fs.feature_ids.length) {
      throw new Error('FeatureSet has no features')
    }

    if (!stats || !stats.columns || stats.columns.length === 0) {
      throw new Error('数据集无数据，请先上传 Dataset has no data, please upload CSV first')
    }

    ElMessage.info('诊断需要特征矩阵，请确保数据集有数据 Diagnostics requires feature matrix.')
    await runViaTrainingDataset()
  } catch (e: any) {
    ElMessage.error(e.message || '诊断失败 Diagnostics failed')
  } finally {
    loading.value = false
  }
}

async function runViaTrainingDataset() {
  const { runTrainingDatasetDiagnostics } = await import('@/api/ml')
  const result = await runTrainingDatasetDiagnostics({
    dataset_id: form.value.dataset_id,
    feature_ids: featureSets.value.find(f => f.name === form.value.feature_set_name)?.feature_ids || [],
    label_id: form.value.label_id,
  })
  report.value = result.feature_diagnostics
  ElMessage.success(`诊断完成：${result.n_samples} 样本，${result.n_features} 特征 Diagnostics done`)
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
