<template>
  <div class="observe-health">
    <div class="page-header">
      <div>
        <h1 class="page-title">策略健康 Strategy Health</h1>
        <span class="page-subtitle">策略健康监控 Strategy health monitoring</span>
      </div>
      <el-button :icon="Refresh" @click="refresh" :loading="loading">刷新 Refresh</el-button>
    </div>

    <!-- Summary Cards -->
    <div class="summary-grid">
      <el-card class="summary-card" shadow="hover">
        <div class="metric-label">总策略数 Total Strategies</div>
        <div class="metric-value">{{ healthList.length }}</div>
      </el-card>
      <el-card class="summary-card" shadow="hover">
        <div class="metric-label">健康 Healthy</div>
        <div class="metric-value text-success">{{ countByStatus('healthy') }}</div>
      </el-card>
      <el-card class="summary-card" shadow="hover">
        <div class="metric-label">告警</div>
        <div class="metric-value text-warning">
          {{ countByStatus('low_activity') + countByStatus('no_fills') }}
        </div>
      </el-card>
      <el-card class="summary-card" shadow="hover">
        <div class="metric-label">异常</div>
        <div class="metric-value text-danger">
          {{ countByStatus('stalled') + countByStatus('losing') }}
        </div>
      </el-card>
    </div>

    <!-- Health Table -->
    <el-card shadow="hover">
      <template #header><span>策略状态详情</span></template>
      <el-table :data="healthList" stripe>
        <el-table-column prop="strategy_id" label="策略" min-width="140" />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="signals_24h" label="24h信号" width="100" />
        <el-table-column prop="fills_24h" label="24h成交" width="100" />
        <el-table-column label="24h PnL" width="120">
          <template #default="{ row }">
            <span :class="pnlClass(row.pnl_24h)">{{ formatPnl(row.pnl_24h) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="total_signals" label="总信号" width="100" />
        <el-table-column prop="total_fills" label="总成交" width="100" />
        <el-table-column label="总PnL" width="120">
          <template #default="{ row }">
            <span :class="pnlClass(row.total_pnl)">{{ formatPnl(row.total_pnl) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="last_signal_time" label="最近信号" min-width="180" />
        <el-table-column label="告警" min-width="200">
          <template #default="{ row }">
            <div v-for="(alert, i) in row.alerts" :key="i" class="alert-item">
              <el-tag type="danger" size="small" effect="plain">{{ alert }}</el-tag>
            </div>
            <span v-if="!row.alerts || row.alerts.length === 0" class="text-muted">-</span>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && healthList.length === 0" description="暂无策略" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { useObserveStore } from '@/stores/observe'

const store = useObserveStore()
const healthList = computed(() => store.healthList)
const loading = computed(() => store.loading)

function countByStatus(status: string): number {
  return healthList.value.filter(h => h.status === status).length
}

function statusType(status: string): 'success' | 'warning' | 'danger' | 'info' {
  switch (status) {
    case 'healthy': return 'success'
    case 'low_activity':
    case 'no_fills': return 'warning'
    case 'stalled':
    case 'losing': return 'danger'
    case 'stopped': return 'info'
    default: return 'info'
  }
}

function formatPnl(v?: number): string {
  if (v == null) return '$0.00'
  const sign = v >= 0 ? '+' : ''
  return `${sign}$${Math.abs(v).toFixed(2)}`
}

function pnlClass(v?: number): string {
  if (v == null || v === 0) return ''
  return v > 0 ? 'text-success' : 'text-danger'
}

async function refresh() {
  await store.fetchHealth()
}

onMounted(() => {
  refresh()
})
</script>

<style scoped>
.observe-health { padding: 20px; }
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-title { margin: 0; font-size: 24px; font-weight: 700; }
.page-subtitle { color: var(--q-text-muted); font-size: 13px; }

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}
.summary-card {
  border-radius: 8px;
  text-align: center;
}
.metric-label { font-size: 12px; color: var(--q-text-muted); margin-bottom: 4px; }
.metric-value { font-size: 24px; font-weight: 700; }

.alert-item { margin-bottom: 4px; }
.text-muted { color: var(--q-text-muted); }
.text-success { color: #3fb950; }
.text-danger { color: #f85149; }
.text-warning { color: #d29922; }
</style>
