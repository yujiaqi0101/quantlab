<template>
  <div class="feature-analysis">
    <div class="panel-header">
      <h2>特征分析 Feature Analysis</h2>
      <p class="hint">分析 IC、Rank IC、互信息，发现预测性特征（Alpha Factory）</p>
    </div>

    <div v-if="loading" style="text-align: center; padding: 40px;">
      <el-icon class="is-loading" :size="24"><Loading /></el-icon>
      <p style="color: #909399; margin-top: 8px;">加载分析中 Loading analysis...</p>
    </div>

    <el-alert v-else-if="!hasData && !loading" type="info" :closable="false" show-icon>
      需要包含数据的数据集才能运行特征分析，请先创建数据集并加载数据。Need a dataset with data to run feature analysis.
    </el-alert>

    <template v-else>
      <div style="margin-bottom: 12px; display: flex; align-items: center; gap: 12px;">
        <span style="color: #909399; font-size: 13px;">
          来源 Source: {{ source === 'feature_importance' ? '特征重要性（来自训练） Feature Importance (from training)' : '完整分析 Full Analysis' }}
        </span>
      </div>

      <el-table :data="results" border size="small" stripe>
        <el-table-column prop="feature_name" label="特征 Feature" width="160" />
        <el-table-column prop="ic" label="IC" width="100">
          <template #default="{ row }">
            <span :class="{ positive: row.ic > 0, negative: row.ic < 0 }">{{ row.ic?.toFixed(4) ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="rank_ic" label="Rank IC" width="100">
          <template #default="{ row }">
            <span :class="{ positive: row.rank_ic > 0, negative: row.rank_ic < 0 }">{{ row.rank_ic?.toFixed(4) ?? '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="mutual_info" label="互信息 MI" width="110">
          <template #default="{ row }">
            {{ row.mutual_info?.toFixed(4) ?? '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="ic_std" label="IC标准差 IC Std" width="100">
          <template #default="{ row }">
            {{ row.ic_std?.toFixed(4) ?? '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="ic_ir" label="IC信息比 IC IR" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.ic_ir !== undefined && row.ic_ir !== 0" :type="row.ic_ir > 0.5 ? 'success' : row.ic_ir > 0 ? 'warning' : 'danger'" size="small">
              {{ row.ic_ir.toFixed(4) }}
            </el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="importance" label="重要性 Importance" width="100">
          <template #default="{ row }">
            {{ row.importance ?? '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="importance_pct" label="重要性% Importance %" width="110">
          <template #default="{ row }">
            <span v-if="row.importance_pct !== undefined">{{ row.importance_pct.toFixed(1) }}%</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="n_samples" label="样本数 Samples" width="80" />
      </el-table>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { http } from '@/api/http'

interface FeatureAnalysisResult {
  feature_name: string
  ic: number
  rank_ic: number
  mutual_info: number
  ic_std: number
  ic_ir: number
  n_samples: number
  importance?: number
  importance_pct?: number
}

const results = ref<FeatureAnalysisResult[]>([])
const source = ref('')
const loading = ref(true)
const hasData = computed(() => results.value.length > 0)

onMounted(async () => {
  try {
    const resp = await http.get('/ml/feature-analysis/quick')
    results.value = resp.data?.results || []
    source.value = resp.data?.source || ''

    if (results.value.length === 0) {
      const jobsResp = await http.get('/ml/training/jobs')
      const jobs = jobsResp.data?.jobs || []
      const completed = jobs.filter((j: any) => j.status === 'COMPLETED')
      if (completed.length > 0) {
        const latestJob = completed[completed.length - 1]
        const jobResp = await http.get(`/ml/feature-analysis/from-job/${latestJob.job_id}`)
        results.value = jobResp.data?.results || []
        source.value = jobResp.data?.source || ''
      }
    }
  } catch (e) {
    console.error('[FeatureAnalysis] load error:', e)
  } finally {
    loading.value = false
  }
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

.positive {
  color: #67c23a;
  font-weight: bold;
}

.negative {
  color: #f56c6c;
  font-weight: bold;
}
</style>
