<template>
  <div class="feature-analysis">
    <div class="panel-header">
      <h2>Feature Analysis</h2>
      <p class="hint">Analyze IC, Rank IC, Mutual Information to discover predictive features (Alpha Factory)</p>
    </div>

    <el-alert v-if="!hasData" type="info" :closable="false" show-icon>
      Need features and labels to run analysis. Please train a model first or load data from Dataset Center.
    </el-alert>

    <el-table v-if="results.length > 0" :data="results" border>
      <el-table-column prop="feature_name" label="Feature" width="200" />
      <el-table-column prop="ic" label="IC" width="120">
        <template #default="{ row }">
          <span :class="{ positive: row.ic > 0, negative: row.ic < 0 }">{{ row.ic }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="rank_ic" label="Rank IC" width="120">
        <template #default="{ row }">
          <span :class="{ positive: row.rank_ic > 0, negative: row.rank_ic < 0 }">{{ row.rank_ic }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="mutual_info" label="Mutual Info" width="120" />
      <el-table-column prop="ic_std" label="IC Std" width="120" />
      <el-table-column prop="ic_ir" label="IC IR" width="120">
        <template #default="{ row }">
          <el-tag :type="row.ic_ir > 0.5 ? 'success' : row.ic_ir > 0 ? 'warning' : 'danger'" size="small">
            {{ row.ic_ir }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="n_samples" label="Samples" width="100" />
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { FeatureAnalysisResult } from '@/api/ml'

const results = ref<FeatureAnalysisResult[]>([])
const hasData = computed(() => results.value.length > 0)

// 这个面板需要从 Training Center 或其他地方获取数据
// 暂时作为展示页面
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
