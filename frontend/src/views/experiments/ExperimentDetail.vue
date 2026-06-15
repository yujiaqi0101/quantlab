<template>
  <div class="detail-container">
    <!-- Back -->
    <div class="detail-back" @click="router.push('/experiments')">
      <el-icon :size="14"><ArrowLeft /></el-icon>
      <span>Back to Experiments</span>
    </div>

    <!-- Loading -->
    <div v-if="store.loading" class="loading-state">
      <el-icon class="is-loading" :size="24"><Loading /></el-icon>
      <span>Loading experiment...</span>
    </div>

    <!-- Error -->
    <div v-else-if="store.error" class="error-state">
      <el-icon :size="24" color="#f85149"><CircleCloseFilled /></el-icon>
      <p>{{ store.error }}</p>
    </div>

    <!-- Content -->
    <template v-else-if="exp">
      <!-- Header -->
      <div class="detail-header">
        <div>
          <h1 class="detail-title">{{ exp.name || exp.id }}</h1>
          <p class="detail-sub">
            <span class="detail-id">{{ exp.id }}</span>
            <span class="detail-sep">|</span>
            <span class="detail-strategy">{{ exp.strategy }}</span>
            <span v-if="exp.dataset_id" class="detail-sep">|</span>
            <span v-if="exp.dataset_id" class="detail-dataset">{{ exp.dataset_id }}</span>
          </p>
        </div>
        <div class="detail-meta">
          <span class="detail-date">{{ formatDate(exp.created_at) }}</span>
          <el-tag v-if="exp.tag" effect="dark" class="source-tag">{{ exp.tag }}</el-tag>
        </div>
      </div>

      <!-- Metrics Cards -->
      <div class="metrics-grid">
        <div class="metric-card">
          <span class="metric-label">Return</span>
          <span :class="['metric-value', exp.total_return >= 0 ? 'positive' : 'negative']">
            {{ exp.total_return >= 0 ? '+' : '' }}{{ exp.total_return?.toFixed(2) }}%
          </span>
        </div>
        <div class="metric-card">
          <span class="metric-label">Sharpe</span>
          <span class="metric-value">{{ exp.sharpe?.toFixed(3) }}</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">Max DD</span>
          <span class="metric-value negative">{{ exp.max_drawdown?.toFixed(2) }}%</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">Win Rate</span>
          <span class="metric-value">{{ exp.win_rate?.toFixed(1) }}%</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">Trades</span>
          <span class="metric-value">{{ exp.trade_count }}</span>
        </div>
        <div class="metric-card">
          <span class="metric-label">Final Equity</span>
          <span class="metric-value">{{ formatMoney(exp.final_equity) }}</span>
        </div>
      </div>

      <!-- Tabs -->
      <el-tabs v-model="activeTab" class="detail-tabs">
        <!-- Equity Curve Tab -->
        <el-tab-pane label="Equity Curve" name="equity">
          <div v-if="store.equity?.equity?.length" class="tab-content">
            <EquityCurveChart :equity="store.equity" :show-drawdown="true" />
          </div>
          <div v-else class="empty-tab">
            No equity curve data available
          </div>
        </el-tab-pane>

        <!-- Trades Tab -->
        <el-tab-pane :label="`Trades (${store.trades.length})`" name="trades">
          <div v-if="store.trades.length > 0" class="tab-content">
            <el-table
              :data="store.trades"
              class="q-table"
              size="small"
              :header-cell-style="{ background: '#161b22', color: '#8b949e', borderBottom: '1px solid #1b2332' }"
              :cell-style="{ borderBottom: '1px solid #1b2332' }"
              max-height="500"
            >
              <el-table-column prop="entry_time" label="Entry" width="160">
                <template #default="{ row }">
                  <span class="cell-date">{{ formatDateTime(row.entry_time) }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="exit_time" label="Exit" width="160">
                <template #default="{ row }">
                  <span class="cell-date">{{ formatDateTime(row.exit_time) }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="symbol" label="Symbol" width="100">
                <template #default="{ row }">
                  <span class="cell-symbol">{{ row.symbol }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="side" label="Side" width="70">
                <template #default="{ row }">
                  <span :class="row.side === 'long' ? 'cell-long' : 'cell-short'">{{ row.side }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="qty" label="Qty" width="80" align="right">
                <template #default="{ row }">
                  <span class="cell-num">{{ row.qty }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="entry_price" label="Entry Price" width="110" align="right">
                <template #default="{ row }">
                  <span class="cell-num">{{ row.entry_price?.toFixed(2) }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="exit_price" label="Exit Price" width="110" align="right">
                <template #default="{ row }">
                  <span class="cell-num">{{ row.exit_price?.toFixed(2) }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="pnl" label="PnL" width="110" align="right">
                <template #default="{ row }">
                  <span :class="row.pnl >= 0 ? 'cell-positive' : 'cell-negative'">
                    {{ row.pnl >= 0 ? '+' : '' }}{{ row.pnl?.toFixed(2) }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="return_pct" label="Return%" width="90" align="right">
                <template #default="{ row }">
                  <span :class="row.return_pct >= 0 ? 'cell-positive' : 'cell-negative'">
                    {{ row.return_pct >= 0 ? '+' : '' }}{{ row.return_pct?.toFixed(2) }}%
                  </span>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <div v-else class="empty-tab">
            No trade data available
          </div>
        </el-tab-pane>

        <!-- Params Tab -->
        <el-tab-pane label="Parameters" name="params">
          <div v-if="exp.params && Object.keys(exp.params).length > 0" class="tab-content">
            <div class="params-list">
              <div v-for="(val, key) in exp.params" :key="key" class="param-row">
                <span class="param-key">{{ key }}</span>
                <span class="param-val">{{ JSON.stringify(val) }}</span>
              </div>
            </div>
          </div>
          <div v-else class="empty-tab">
            No parameters recorded
          </div>
        </el-tab-pane>

        <!-- Attribution Tab (placeholder) -->
        <el-tab-pane label="Attribution" name="attribution" disabled>
          <template #label>
            <span style="color: #484f58">Attribution</span>
          </template>
        </el-tab-pane>
      </el-tabs>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useExperimentStore } from '@/stores/experiment'
import { ArrowLeft, Loading, CircleCloseFilled } from '@element-plus/icons-vue'
import EquityCurveChart from '@/components/charts/EquityCurveChart.vue'

const route = useRoute()
const router = useRouter()
const store = useExperimentStore()
const activeTab = ref('equity')

const exp = computed(() => store.current)

function formatDate(dt: string): string {
  if (!dt) return '-'
  return dt.split('T')[0]
}

function formatDateTime(dt: string): string {
  if (!dt) return '-'
  return dt.replace('T', ' ').substring(0, 19)
}

function formatMoney(v: number): string {
  if (!v) return '-'
  return '$' + v.toLocaleString(undefined, { maximumFractionDigits: 0 })
}

onMounted(() => {
  const id = route.params.id as string
  if (id) {
    store.loadDetail(id)
  }
})
</script>

<style scoped>
.detail-container {
  max-width: 1100px;
}

.detail-back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #58a6ff;
  font-size: 13px;
  cursor: pointer;
  margin-bottom: 24px;
  transition: color 0.2s;
}

.detail-back:hover {
  color: #79c0ff;
}

.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  color: #8b949e;
  font-size: 14px;
  gap: 12px;
}

/* Header */
.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.detail-title {
  font-size: 28px;
  font-weight: 700;
  color: #e6edf3;
  margin: 0 0 6px 0;
  letter-spacing: -0.5px;
}

.detail-sub {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  margin: 0;
}

.detail-id {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  color: #484f58;
}

.detail-sep {
  color: #1b2332;
}

.detail-strategy {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  color: #58a6ff;
}

.detail-dataset {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  color: #8b949e;
}

.detail-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.detail-date {
  font-size: 13px;
  color: #484f58;
}

.source-tag {
  background: #1b2332;
  border-color: #1b2332;
  color: #8b949e;
  font-size: 11px;
}

/* Metrics */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
  margin-bottom: 28px;
}

.metric-card {
  background: #161b22;
  border: 1px solid #1b2332;
  border-radius: 8px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-label {
  font-size: 11px;
  color: #484f58;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.metric-value {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 20px;
  font-weight: 700;
  color: #e6edf3;
}

.metric-value.positive {
  color: #3fb950;
}

.metric-value.negative {
  color: #f85149;
}

/* Tabs */
.detail-tabs {
  --el-tabs-header-bg-color: transparent;
}

.detail-tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
  border-bottom: 1px solid #1b2332;
}

.detail-tabs :deep(.el-tabs__item) {
  color: #8b949e;
  font-size: 13px;
}

.detail-tabs :deep(.el-tabs__item.is-active) {
  color: #58a6ff;
}

.detail-tabs :deep(.el-tabs__active-bar) {
  background-color: #58a6ff;
}

.detail-tabs :deep(.el-tabs__nav-wrap::after) {
  background-color: #1b2332;
}

.tab-content {
  min-height: 200px;
}

.empty-tab {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 0;
  color: #484f58;
  font-size: 14px;
}

/* Table */
.q-table {
  --el-table-bg-color: #0d1117;
  --el-table-tr-bg-color: #0d1117;
  --el-table-row-hover-bg-color: #161b22;
  --el-table-text-color: #e6edf3;
  --el-table-border-color: #1b2332;
  --el-table-header-text-color: #8b949e;
}

.cell-date {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 12px;
  color: #8b949e;
}

.cell-symbol {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 12px;
  color: #58a6ff;
}

.cell-long {
  font-size: 12px;
  color: #3fb950;
  font-weight: 600;
}

.cell-short {
  font-size: 12px;
  color: #f85149;
  font-weight: 600;
}

.cell-num {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 12px;
  color: #c9d1d9;
}

.cell-positive {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 12px;
  color: #3fb950;
  font-weight: 600;
}

.cell-negative {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 12px;
  color: #f85149;
}

/* Params */
.params-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.param-row {
  display: flex;
  gap: 16px;
  padding: 8px 14px;
  background: #161b22;
  border: 1px solid #1b2332;
  border-radius: 6px;
}

.param-key {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  color: #58a6ff;
  min-width: 140px;
}

.param-val {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  color: #c9d1d9;
}
</style>
