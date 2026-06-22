<template>
  <div class="leakage-detector">
    <div class="panel-header">
      <h2>泄露检测 Leakage Detector</h2>
      <p class="hint">检测未来函数、数据泄露和标签泄露</p>
    </div>

    <el-alert type="warning" :closable="false" show-icon style="margin-bottom: 16px">
      泄露检测至关重要。shift(-1) 和 rolling(center=True) 是常见的前瞻偏差来源。Leakage detection is critical. shift(-1) and rolling(center=True) are common sources of lookahead bias.
    </el-alert>

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

    <el-empty v-else description="请从训练中心运行泄露检测 Run leakage detection from Training Center" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { LeakageReport } from '@/api/ml'

const report = ref<LeakageReport | null>(null)

function severityType(s: string): string {
  if (s === 'CRITICAL') return 'danger'
  if (s === 'WARNING') return 'warning'
  return 'info'
}
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
