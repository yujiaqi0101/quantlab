<template>
  <div class="leakage-detector">
    <div class="panel-header">
      <h2>Leakage Detector</h2>
      <p class="hint">Detect future functions, data leakage, and label leakage</p>
    </div>

    <el-alert type="warning" :closable="false" show-icon style="margin-bottom: 16px">
      Leakage detection is critical. shift(-1) and rolling(center=True) are common sources of lookahead bias.
    </el-alert>

    <el-card v-if="report">
      <template #header>
        <div class="report-header">
          <span>Detection Report</span>
          <el-tag :type="report.passed ? 'success' : 'danger'" size="large">
            {{ report.passed ? 'PASSED' : 'FAILED' }}
          </el-tag>
        </div>
      </template>

      <el-row :gutter="16" style="margin-bottom: 16px">
        <el-col :span="8">
          <el-statistic title="Critical" :value="report.n_critical" />
        </el-col>
        <el-col :span="8">
          <el-statistic title="Warning" :value="report.n_warning" />
        </el-col>
        <el-col :span="8">
          <el-statistic title="Info" :value="report.n_info" />
        </el-col>
      </el-row>

      <el-table v-if="report.issues.length > 0" :data="report.issues" border>
        <el-table-column prop="type" label="Type" width="200" />
        <el-table-column prop="severity" label="Severity" width="120">
          <template #default="{ row }">
            <el-tag :type="severityType(row.severity)" size="small">{{ row.severity }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="Message" />
        <el-table-column prop="location" label="Location" width="200" />
        <el-table-column prop="suggestion" label="Suggestion" />
      </el-table>

      <el-empty v-else description="No issues detected" />
    </el-card>

    <el-empty v-else description="Run leakage detection from Training Center" />
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
