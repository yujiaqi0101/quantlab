<template>
  <div class="observe-overview">
    <div class="page-header">
      <div>
        <h1 class="page-title">观测工作室 Observe Studio</h1>
        <span class="page-subtitle">理解系统正在发生什么 Understand what the system is doing</span>
      </div>
      <div class="header-actions">
        <el-button :icon="Refresh" @click="refreshAll" :loading="loading">刷新 Refresh</el-button>
      </div>
    </div>

    <!-- Account Summary Cards -->
    <div class="cards-grid">
      <el-card class="summary-card" shadow="hover">
        <template #header><span>账户权益 Account Equity</span></template>
        <div class="metric-value">${{ formatNum(overview?.equity) }}</div>
        <div class="metric-sub">现金: ${{ formatNum(overview?.cash) }}</div>
      </el-card>

      <el-card class="summary-card" shadow="hover">
        <template #header><span>今日收益 Today P&L</span></template>
        <div class="metric-value" :class="pnlClass(overview?.today_pnl)">
          {{ formatPnl(overview?.today_pnl) }}
        </div>
        <div class="metric-sub" :class="pnlClass(overview?.today_pnl_pct)">
          {{ formatPct(overview?.today_pnl_pct) }}
        </div>
      </el-card>

      <el-card class="summary-card" shadow="hover">
        <template #header><span>总收益</span></template>
        <div class="metric-value" :class="pnlClass(overview?.total_pnl)">
          {{ formatPnl(overview?.total_pnl) }}
        </div>
        <div class="metric-sub" :class="pnlClass(overview?.total_pnl_pct)">
          {{ formatPct(overview?.total_pnl_pct) }}
        </div>
      </el-card>

      <el-card class="summary-card" shadow="hover">
        <template #header><span>当前回撤</span></template>
        <div class="metric-value text-warning">
          {{ formatPct(overview?.max_drawdown) }}
        </div>
        <div class="metric-sub">最大回撤</div>
      </el-card>

      <el-card class="summary-card" shadow="hover">
        <template #header><span>活跃策略</span></template>
        <div class="metric-value">{{ overview?.active_strategies ?? 0 }}</div>
        <div class="metric-sub">运行中</div>
      </el-card>

      <el-card class="summary-card" shadow="hover">
        <template #header><span>持仓数量</span></template>
        <div class="metric-value">{{ overview?.n_positions ?? 0 }}</div>
        <div class="metric-sub">活跃持仓</div>
      </el-card>
    </div>

    <!-- Equity Curve Placeholder -->
    <el-card class="curve-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>权益曲线</span>
          <el-tag size="small" type="info">实时</el-tag>
        </div>
      </template>
      <div class="curve-placeholder">
        <el-empty description="暂无权益曲线数据" />
      </div>
    </el-card>

    <!-- Strategy Status -->
    <el-card class="strategy-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>策略状态</span>
          <el-button text size="small" @click="$router.push('/observe/health')">查看全部</el-button>
        </div>
      </template>
      <el-table :data="healthList.slice(0, 5)" stripe size="small">
        <el-table-column prop="strategy_id" label="策略" min-width="120" />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="healthTagType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="signals_24h" label="24h信号" width="100" />
        <el-table-column prop="fills_24h" label="24h成交" width="100" />
        <el-table-column label="24h PnL" width="120">
          <template #default="{ row }">
            <span :class="pnlClass(row.pnl_24h)">{{ formatPnl(row.pnl_24h) }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { useObserveStore } from '@/stores/observe'

const store = useObserveStore()

const overview = computed(() => store.overview)
const healthList = computed(() => store.healthList)
const loading = computed(() => store.loading)

function formatNum(v?: number): string {
  if (v == null) return '0.00'
  return v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatPnl(v?: number): string {
  if (v == null) return '$0.00'
  const sign = v >= 0 ? '+' : ''
  return `${sign}$${Math.abs(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function formatPct(v?: number): string {
  if (v == null) return '0.00%'
  return `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`
}

function pnlClass(v?: number): string {
  if (v == null || v === 0) return ''
  return v > 0 ? 'text-success' : 'text-danger'
}

function healthTagType(status: string): 'success' | 'warning' | 'danger' | 'info' {
  switch (status) {
    case 'healthy': return 'success'
    case 'low_activity': return 'warning'
    case 'stalled':
    case 'no_fills':
    case 'losing':
      return 'danger'
    case 'stopped': return 'info'
    default: return 'info'
  }
}

async function refreshAll() {
  await store.fetchAll()
}

onMounted(() => {
  refreshAll()
})
</script>

<style scoped>
.observe-overview {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
}

.page-subtitle {
  color: var(--q-text-muted);
  font-size: 13px;
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.summary-card {
  border-radius: 8px;
}

.metric-value {
  font-size: 24px;
  font-weight: 700;
  margin: 8px 0 4px;
}

.metric-sub {
  font-size: 12px;
  color: var(--q-text-muted);
}

.curve-card,
.strategy-card {
  margin-bottom: 16px;
  border-radius: 8px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.curve-placeholder {
  height: 280px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.text-success { color: #3fb950; }
.text-danger { color: #f85149; }
.text-warning { color: #d29922; }
</style>
