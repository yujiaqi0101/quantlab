<template>
  <div class="positions-workspace">
    <template v-if="!store.currentSessionId">
      <el-empty description="请先创建会话" :image-size="120" />
    </template>
    <template v-else>
      <!-- 汇总栏 -->
      <div class="summary-bar">
        <div class="summary-item">
          <span class="summary-label">总市值 Market Value</span>
          <span class="summary-value">{{ formatNum(totalMarketValue) }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">总 PnL</span>
          <span class="summary-value" :class="pnlClass(totalPnl)">{{ formatNum(totalPnl) }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">多头 Long</span>
          <span class="summary-value text-success">{{ longCount }}</span>
        </div>
        <div class="summary-item">
          <span class="summary-label">空头 Short</span>
          <span class="summary-value text-danger">{{ shortCount }}</span>
        </div>
        <div class="summary-spacer"></div>
        <div class="summary-actions">
          <span class="session-tag">SID: {{ store.currentSessionId }}</span>
          <el-button :icon="Refresh" size="small" @click="store.fetchPositions()" :loading="loading">刷新</el-button>
        </div>
      </div>

      <!-- 持仓表格 -->
      <el-card class="table-card" shadow="never">
        <el-table :data="positions" stripe size="small" height="100%" v-loading="loading" empty-text="暂无持仓">
          <el-table-column label="Symbol" min-width="120">
            <template #default="{ row }"><span class="symbol-text">{{ row.symbol }}</span></template>
          </el-table-column>
          <el-table-column label="Direction" width="100">
            <template #default="{ row }">
              <el-tag :type="dirType(row.direction)" size="small" effect="dark">{{ row.direction || '-' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="Qty" width="110" align="right">
            <template #default="{ row }"><span class="num">{{ formatNum(row.quantity) }}</span></template>
          </el-table-column>
          <el-table-column label="Cost" width="110" align="right">
            <template #default="{ row }"><span class="num">{{ formatNum(row.entry_price) }}</span></template>
          </el-table-column>
          <el-table-column label="Current" width="110" align="right">
            <template #default="{ row }"><span class="num">{{ formatNum(row.current_price) }}</span></template>
          </el-table-column>
          <el-table-column label="Market Value" width="140" align="right">
            <template #default="{ row }"><span class="num">{{ formatNum(row.market_value) }}</span></template>
          </el-table-column>
          <el-table-column label="Unrealized PnL" width="150" align="right">
            <template #default="{ row }">
              <span class="num" :class="pnlClass(row.unrealized_pnl)">{{ formatNum(row.unrealized_pnl) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="PnL%" width="110" align="right">
            <template #default="{ row }">
              <span class="num" :class="pnlClass(pnlPct(row))">{{ formatPct(pnlPct(row)) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="Holding Days" width="120" align="right">
            <template #default="{ row }"><span class="num">{{ holdingDays(row.entry_date) }}</span></template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { useTradingStore } from '@/stores/trading'
import type { PositionItem } from '@/api/trading'

const store = useTradingStore()
const positions = computed(() => store.positions)
const loading = computed(() => store.loading)

// ---- 汇总 ----
const totalMarketValue = computed(() =>
  positions.value.reduce((s, p) => s + (p.market_value || 0), 0),
)
const totalPnl = computed(() =>
  positions.value.reduce((s, p) => s + (p.unrealized_pnl || 0), 0),
)
const longCount = computed(() =>
  positions.value.filter(p => (p.direction || '').toUpperCase() === 'LONG').length,
)
const shortCount = computed(() =>
  positions.value.filter(p => (p.direction || '').toUpperCase() === 'SHORT').length,
)

// ---- 计算 ----
function pnlPct(row: PositionItem): number {
  const cost = (row.entry_price || 0) * (row.quantity || 0)
  if (!cost) return 0
  return (row.unrealized_pnl || 0) / cost
}
function holdingDays(entryDate: string): number {
  if (!entryDate) return 0
  const t = new Date(entryDate).getTime()
  if (isNaN(t)) return 0
  return Math.max(0, Math.floor((Date.now() - t) / (1000 * 60 * 60 * 24)))
}

// ---- 格式化 ----
function formatNum(v: number | undefined | null): string {
  if (v == null) return '-'
  return Number(v).toLocaleString('en-US', { maximumFractionDigits: 2 })
}
function formatPct(v: number | undefined | null): string {
  if (v == null) return '-'
  return (v * 100).toFixed(2) + '%'
}
function pnlClass(v: number | undefined | null): string {
  if (v == null || v === 0) return ''
  return v > 0 ? 'text-success' : 'text-danger'
}
function dirType(direction: string): 'success' | 'danger' | 'info' {
  const d = (direction || '').toUpperCase()
  if (d === 'LONG') return 'success'
  if (d === 'SHORT') return 'danger'
  return 'info'
}

onMounted(() => {
  store.fetchPositions()
})
</script>

<style scoped>
.positions-workspace {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 12px;
  font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', 'JetBrains Mono', ui-monospace, monospace;
}

/* 汇总栏 */
.summary-bar {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 10px 14px;
  background: var(--q-bg-secondary, #0d1117);
  border: 1px solid var(--q-border, #21262d);
  border-radius: 6px;
  flex-shrink: 0;
}
.summary-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.summary-label {
  font-size: 10px;
  color: var(--q-text-muted, #8b949e);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.summary-value {
  font-size: 16px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--q-text-primary, #e6edf3);
}
.summary-spacer {
  flex: 1;
}
.summary-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.session-tag {
  font-size: 11px;
  color: var(--q-text-muted, #8b949e);
  background: var(--q-bg-tertiary, #161b22);
  border: 1px solid var(--q-border, #21262d);
  padding: 4px 10px;
  border-radius: 4px;
}

/* 表格卡片 */
.table-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--q-bg-secondary, #0d1117);
  border: 1px solid var(--q-border, #21262d);
  border-radius: 6px;
  overflow: hidden;
}
.table-card :deep(.el-card__body) {
  flex: 1;
  padding: 0;
  overflow: hidden;
}
:deep(.el-table) {
  background: transparent;
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: var(--q-bg-tertiary, #161b22);
  --el-table-border-color: var(--q-border, #21262d);
  --el-table-header-text-color: var(--q-text-secondary, #8b949e);
  --el-table-text-color: var(--q-text-primary, #e6edf3);
  --el-table-row-hover-bg-color: rgba(88, 166, 255, 0.06);
}
:deep(.el-table th.el-table__cell) {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* 单元格 */
.symbol-text {
  font-weight: 600;
  color: var(--q-text-primary, #e6edf3);
}
.num {
  font-variant-numeric: tabular-nums;
  font-feature-settings: 'tnum';
}

/* 颜色 */
.text-success { color: #3fb950; }
.text-danger { color: #f85149; }
.text-warning { color: #d29922; }
</style>
