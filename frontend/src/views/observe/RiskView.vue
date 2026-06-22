<template>
  <div class="observe-risk">
    <div class="page-header">
      <div>
        <h1 class="page-title">风控仪表盘 Risk Dashboard</h1>
        <span class="page-subtitle">风险控制 Risk control</span>
      </div>
      <el-button :icon="Refresh" @click="refresh" :loading="loading">刷新 Refresh</el-button>
    </div>

    <!-- Risk Status Banner -->
    <el-card class="status-banner" :class="statusClass" shadow="hover">
      <div class="status-content">
        <div class="status-label">风险状态 Risk Status</div>
        <div class="status-value">{{ risk?.status || 'NORMAL' }}</div>
      </div>
      <el-tag v-if="risk?.kill_switch_active" type="danger" effect="dark" size="large">
        KILL SWITCH ACTIVE
      </el-tag>
    </el-card>

    <!-- Risk Metrics -->
    <div class="metrics-grid">
      <el-card class="metric-card" shadow="hover">
        <div class="metric-label">仓位占比 Position Ratio</div>
        <div class="metric-value">{{ (risk?.max_position_pct ?? 0).toFixed(2) }}%</div>
        <el-progress
          :percentage="Math.min(risk?.max_position_pct ?? 0, 100)"
          :color="progressColor(risk?.max_position_pct ?? 0, 20)"
        />
      </el-card>

      <el-card class="metric-card" shadow="hover">
        <div class="metric-label">日亏损</div>
        <div class="metric-value" :class="pnlClass(risk?.daily_loss)">
          {{ formatPnl(risk?.daily_loss) }}
        </div>
        <div class="metric-sub">限额: {{ formatPnl(risk?.max_daily_loss) }}</div>
      </el-card>

      <el-card class="metric-card" shadow="hover">
        <div class="metric-label">最大回撤</div>
        <div class="metric-value text-warning">
          {{ (risk?.max_drawdown ?? 0).toFixed(2) }}%
        </div>
        <div class="metric-sub">限额: 15%</div>
      </el-card>
    </div>

    <!-- Risk Rules -->
    <el-card shadow="hover">
      <template #header><span>风险规则</span></template>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="最大仓位占比">20%</el-descriptions-item>
        <el-descriptions-item label="日亏损限额">3%</el-descriptions-item>
        <el-descriptions-item label="最大回撤限额">15%</el-descriptions-item>
        <el-descriptions-item label="Kill Switch">
          <el-tag :type="risk?.kill_switch_active ? 'danger' : 'success'" size="small">
            {{ risk?.kill_switch_active ? '已触发' : '未触发' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { useObserveStore } from '@/stores/observe'

const store = useObserveStore()
const risk = computed(() => store.risk)
const loading = computed(() => store.loading)

const statusClass = computed(() => {
  const s = risk.value?.status ?? 'NORMAL'
  if (s === 'CRITICAL') return 'status-critical'
  if (s === 'WARNING') return 'status-warning'
  return 'status-normal'
})

function formatPnl(v?: number): string {
  if (v == null) return '$0.00'
  const sign = v >= 0 ? '+' : ''
  return `${sign}$${Math.abs(v).toFixed(2)}`
}

function pnlClass(v?: number): string {
  if (v == null || v === 0) return ''
  return v > 0 ? 'text-success' : 'text-danger'
}

function progressColor(value: number, threshold: number): string {
  if (value > threshold) return '#f85149'
  if (value > threshold * 0.8) return '#d29922'
  return '#3fb950'
}

async function refresh() {
  await store.fetchRisk()
}

onMounted(() => {
  refresh()
})
</script>

<style scoped>
.observe-risk { padding: 20px; }
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-title { margin: 0; font-size: 24px; font-weight: 700; }
.page-subtitle { color: var(--q-text-muted); font-size: 13px; }

.status-banner {
  margin-bottom: 20px;
  border-radius: 8px;
}
.status-banner :deep(.el-card__body) {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
}
.status-normal { border-left: 4px solid #3fb950; }
.status-warning { border-left: 4px solid #d29922; }
.status-critical { border-left: 4px solid #f85149; }

.status-label { font-size: 13px; color: var(--q-text-muted); }
.status-value { font-size: 28px; font-weight: 700; margin-top: 4px; }

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}
.metric-card {
  border-radius: 8px;
}
.metric-label { font-size: 12px; color: var(--q-text-muted); margin-bottom: 4px; }
.metric-value { font-size: 24px; font-weight: 700; margin-bottom: 8px; }
.metric-sub { font-size: 11px; color: var(--q-text-muted); }

.text-success { color: #3fb950; }
.text-danger { color: #f85149; }
.text-warning { color: #d29922; }
</style>
