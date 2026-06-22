<template>
  <div class="validation-center">
    <div class="panel-header">
      <h2>验证中心 Validation Center</h2>
      <p class="hint">滚动前进验证 Walk Forward validation — 量化金融必备</p>
    </div>

    <el-alert type="warning" :closable="false" show-icon style="margin-bottom: 16px">
      时间序列切勿使用 train_test_split()，请始终使用滚动前进验证。Never use train_test_split() for time series. Always use Walk Forward validation.
    </el-alert>

    <el-card v-if="result">
      <template #header>滚动前进验证结果 Walk Forward Result</template>
      <el-row :gutter="16">
        <el-col :span="6">
          <el-statistic title="折数 Splits" :value="result.n_splits" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="平均IC Avg IC" :value="result.avg_ic" :precision="4" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="平均Rank IC Avg Rank IC" :value="result.avg_rank_ic" :precision="4" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="IC稳定性 IC Stability" :value="result.ic_stability" :precision="4" />
        </el-col>
      </el-row>

      <el-divider />

      <h4>折详情 Fold Details</h4>
      <el-table :data="result.fold_details" border size="small">
        <el-table-column prop="fold" label="折 Fold" width="80" />
        <el-table-column prop="train_start" label="训练开始 Train Start" width="150" />
        <el-table-column prop="train_end" label="训练结束 Train End" width="150" />
        <el-table-column prop="test_start" label="测试开始 Test Start" width="150" />
        <el-table-column prop="test_end" label="测试结束 Test End" width="150" />
        <el-table-column prop="n_train" label="训练数 N Train" width="100" />
        <el-table-column prop="n_test" label="测试数 N Test" width="100" />
        <el-table-column prop="ic" label="IC" width="100">
          <template #default="{ row }">
            <span :class="{ positive: row.ic > 0, negative: row.ic < 0 }">{{ row.ic?.toFixed(4) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="rank_ic" label="Rank IC" width="100" />
      </el-table>
    </el-card>

    <el-empty v-else description="请从训练中心运行滚动前进验证 Run Walk Forward validation from Training Center" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { WalkForwardResult } from '@/api/ml'

const result = ref<WalkForwardResult | null>(null)
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

.positive { color: #67c23a; font-weight: bold; }
.negative { color: #f56c6c; font-weight: bold; }
</style>
