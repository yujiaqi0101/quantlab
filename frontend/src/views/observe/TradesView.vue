<template>
  <div class="observe-trades">
    <div class="page-header">
      <div>
        <h1 class="page-title">成交 Trades</h1>
        <span class="page-subtitle">成交分析 Trade analysis</span>
      </div>
      <div class="header-actions">
        <el-select v-model="hours" size="small" style="width: 140px">
          <el-option label="最近24小时 Last 24h" :value="24" />
          <el-option label="最近7天 Last 7 days" :value="168" />
          <el-option label="最近30天 Last 30 days" :value="720" />
        </el-select>
        <el-button :icon="Refresh" @click="refresh" :loading="loading">刷新 Refresh</el-button>
      </div>
    </div>

    <!-- Analytics Cards -->
    <div class="analytics-grid" v-if="analytics">
      <el-card class="analytics-card" shadow="hover">
        <div class="metric-label">总成交 Total Trades</div>
        <div class="metric-value">{{ analytics.n_trades }}</div>
      </el-card>
      <el-card class="analytics-card" shadow="hover">
        <div class="metric-label">胜率 Win Rate</div>
        <div class="metric-value">{{ (analytics.win_rate * 100).toFixed(1) }}%</div>
        <div class="metric-sub">{{ analytics.n_wins }}胜 / {{ analytics.n_losses }}负</div>
      </el-card>
      <el-card class="analytics-card" shadow="hover">
        <div class="metric-label">盈亏比 P&L Ratio</div>
        <div class="metric-value">{{ analytics.profit_factor.toFixed(2) }}</div>
      </el-card>
      <el-card class="analytics-card" shadow="hover">
        <div class="metric-label">期望值</div>
        <div class="metric-value" :class="pnlClass(analytics.expectancy)">
          {{ formatPnl(analytics.expectancy) }}
        </div>
      </el-card>
      <el-card class="analytics-card" shadow="hover">
        <div class="metric-label">平均盈利</div>
        <div class="metric-value text-success">{{ formatPnl(analytics.avg_win) }}</div>
      </el-card>
      <el-card class="analytics-card" shadow="hover">
        <div class="metric-label">平均亏损</div>
        <div class="metric-value text-danger">{{ formatPnl(analytics.avg_loss) }}</div>
      </el-card>
      <el-card class="analytics-card" shadow="hover">
        <div class="metric-label">最大盈利</div>
        <div class="metric-value text-success">{{ formatPnl(analytics.largest_win) }}</div>
      </el-card>
      <el-card class="analytics-card" shadow="hover">
        <div class="metric-label">最大亏损</div>
        <div class="metric-value text-danger">{{ formatPnl(analytics.largest_loss) }}</div>
      </el-card>
      <el-card class="analytics-card" shadow="hover">
        <div class="metric-label">总盈亏</div>
        <div class="metric-value" :class="pnlClass(analytics.total_pnl)">
          {{ formatPnl(analytics.total_pnl) }}
        </div>
      </el-card>
    </div>

    <!-- Trades Table -->
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>成交记录</span>
          <el-tag size="small">{{ trades.length }} 笔</el-tag>
        </div>
      </template>
      <el-table :data="trades" stripe size="small">
        <el-table-column prop="timestamp" label="时间" min-width="180" />
        <el-table-column prop="symbol" label="Symbol" width="120" />
        <el-table-column prop="side" label="方向" width="80">
          <template #default="{ row }">
            <el-tag :type="row.side === 'BUY' ? 'success' : 'danger'" size="small">
              {{ row.side }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="qty" label="数量" width="100">
          <template #default="{ row }">{{ formatNum(row.qty) }}</template>
        </el-table-column>
        <el-table-column prop="price" label="价格" width="120">
          <template #default="{ row }">{{ formatNum(row.price) }}</template>
        </el-table-column>
        <el-table-column prop="fee" label="手续费" width="100">
          <template #default="{ row }">{{ formatNum(row.fee) }}</template>
        </el-table-column>
        <el-table-column label="PnL" width="120">
          <template #default="{ row }">
            <span :class="pnlClass(row.pnl)">{{ formatPnl(row.pnl) }}</span>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && trades.length === 0" description="暂无成交" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { useObserveStore } from '@/stores/observe'

const store = useObserveStore()
const trades = computed(() => store.tradesData?.trades ?? [])
const analytics = computed(() => store.tradesData?.analytics)
const loading = computed(() => store.loading)

const hours = ref(24)

function formatNum(v?: number): string {
  if (v == null) return '-'
  return v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
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
  await store.fetchTrades(hours.value)
}

watch(hours, refresh)

onMounted(() => {
  refresh()
})
</script>

<style scoped>
.observe-trades { padding: 20px; }
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.page-title { margin: 0; font-size: 24px; font-weight: 700; }
.page-subtitle { color: var(--q-text-muted); font-size: 13px; }

.analytics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}
.analytics-card {
  border-radius: 8px;
  text-align: center;
}
.metric-label {
  font-size: 12px;
  color: var(--q-text-muted);
  margin-bottom: 4px;
}
.metric-value {
  font-size: 22px;
  font-weight: 700;
}
.metric-sub {
  font-size: 11px;
  color: var(--q-text-muted);
  margin-top: 4px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.text-success { color: #3fb950; }
.text-danger { color: #f85149; }
</style>
