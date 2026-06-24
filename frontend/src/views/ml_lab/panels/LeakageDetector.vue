<template>
  <div class="leakage-detector">
    <div class="panel-header">
      <h2>泄露检测 Leakage Detector</h2>
      <p class="hint">检测未来函数、数据泄露和标签泄露</p>
    </div>

    <el-alert type="warning" :closable="false" show-icon style="margin-bottom: 16px">
      泄露检测至关重要。shift(-1) 和 rolling(center=True) 是常见的前瞻偏差来源。Leakage detection is critical. shift(-1) and rolling(center=True) are common sources of lookahead bias.
    </el-alert>

    <!-- 检测配置 -->
    <el-card style="margin-bottom: 16px">
      <template #header>
        <span>检测配置 Detection Config</span>
      </template>
      <el-form :model="form" label-width="140px" :inline="false">
        <el-form-item label="数据集 Dataset">
          <el-select v-model="form.dataset_id" placeholder="选择数据集 Select dataset" style="width: 100%">
            <el-option v-for="ds in datasets" :key="ds.dataset_id" :label="ds.name" :value="ds.dataset_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="输入模式 Mode">
          <el-radio-group v-model="mode">
            <el-radio label="set">特征集 FeatureSet（推荐）</el-radio>
            <el-radio label="raw">单个特征 Features</el-radio>
          </el-radio-group>
        </el-form-item>
        <template v-if="mode === 'set'">
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
        </template>
        <template v-else>
          <el-form-item label="特征 Features">
            <el-select v-model="form.feature_ids" multiple placeholder="选择特征 Select features" style="width: 100%">
              <el-option v-for="f in features" :key="f.feature_id" :label="f.name" :value="f.feature_id" />
            </el-select>
          </el-form-item>
          <el-form-item label="标签 Label">
            <el-select v-model="form.label_id" placeholder="选择标签 Select label" style="width: 100%">
              <el-option v-for="l in labels" :key="l.label_id" :label="l.name" :value="l.label_id" />
            </el-select>
          </el-form-item>
        </template>
        <el-form-item>
          <el-button type="primary" :loading="checking" @click="runCheck">
            运行检测 Run Detection
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 检测报告 -->
    <el-card v-if="report">
      <template #header>
        <div class="report-header">
          <span>检测报告 Detection Report</span>
          <el-tag :type="report.passed ? 'success' : 'danger'" size="large">
            {{ report.passed ? '通过 PASSED' : '未通过 FAILED' }}
          </el-tag>
        </div>
      </template>

      <el-row :gutter="16" style="margin-bottom: 16px">
        <el-col :span="8">
          <el-statistic title="严重 Critical" :value="report.n_critical" />
        </el-col>
        <el-col :span="8">
          <el-statistic title="警告 Warning" :value="report.n_warning" />
        </el-col>
        <el-col :span="8">
          <el-statistic title="信息 Info" :value="report.n_info" />
        </el-col>
      </el-row>

      <el-table v-if="report.issues.length > 0" :data="report.issues" border>
        <el-table-column prop="type" label="类型 Type" width="200" />
        <el-table-column prop="severity" label="严重程度 Severity" width="120">
          <template #default="{ row }">
            <el-tag :type="severityType(row.severity)" size="small">{{ row.severity }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="消息 Message" />
        <el-table-column prop="location" label="位置 Location" width="200" />
        <el-table-column prop="suggestion" label="建议 Suggestion" />
      </el-table>

      <el-empty v-else description="未检测到问题 No issues detected" />
    </el-card>

    <el-empty v-else-if="!checking" description="选择数据集和特征集后点击运行检测 Select dataset and FeatureSet then click Run" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  checkLeakageDataset,
  getMLDatasets, getMLFeatures, getMLLabels,
  getFeatureSets, getLabelSets,
  type MLDataset, type MLFeature, type MLLabel,
  type MLFeatureSet, type MLLabelSet,
  type LeakageReport,
} from '@/api/ml'

const report = ref<LeakageReport | null>(null)
const checking = ref(false)
const mode = ref<'set' | 'raw'>('set')

const datasets = ref<MLDataset[]>([])
const features = ref<MLFeature[]>([])
const labels = ref<MLLabel[]>([])
const featureSets = ref<MLFeatureSet[]>([])
const labelSets = ref<MLLabelSet[]>([])

const form = ref({
  dataset_id: '',
  feature_set_id: '',
  label_set_id: '',
  feature_ids: [] as string[],
  label_id: '',
})

function severityType(s: string): string {
  if (s === 'CRITICAL') return 'danger'
  if (s === 'WARNING') return 'warning'
  return 'info'
}

async function loadOptions() {
  try {
    const [dsResp, featResp, labelResp, fsResp, lsResp] = await Promise.all([
      getMLDatasets(),
      getMLFeatures(),
      getMLLabels(),
      getFeatureSets(),
      getLabelSets(),
    ])
    datasets.value = dsResp.datasets || []
    features.value = featResp.features || []
    labels.value = labelResp.labels || []
    featureSets.value = fsResp.sets || []
    labelSets.value = lsResp.sets || []
  } catch (e) {
    ElMessage.error('加载数据失败 Failed to load data')
  }
}

async function runCheck() {
  if (!form.value.dataset_id) {
    ElMessage.warning('请选择数据集 Please select dataset')
    return
  }
  if (mode.value === 'set') {
    if (!form.value.feature_set_id || !form.value.label_set_id) {
      ElMessage.warning('请选择特征集和标签集 Please select FeatureSet and LabelSet')
      return
    }
  } else {
    if (form.value.feature_ids.length === 0 || !form.value.label_id) {
      ElMessage.warning('请选择特征和标签 Please select features and label')
      return
    }
  }

  checking.value = true
  try {
    report.value = await checkLeakageDataset({
      dataset_id: form.value.dataset_id,
      feature_set_id: mode.value === 'set' ? form.value.feature_set_id : undefined,
      label_set_id: mode.value === 'set' ? form.value.label_set_id : undefined,
      feature_ids: mode.value === 'raw' ? form.value.feature_ids : undefined,
      label_id: mode.value === 'raw' ? form.value.label_id : undefined,
    })
    if (report.value.passed) {
      ElMessage.success('检测通过 No leakage detected')
    } else {
      ElMessage.warning(`检测到 ${report.value.n_critical + report.value.n_warning} 个问题`)
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '检测失败 Detection failed')
  } finally {
    checking.value = false
  }
}

onMounted(() => {
  loadOptions()
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

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
