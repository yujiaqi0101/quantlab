<template>
  <div class="trades-widget">
    <el-table
      v-if="rows.length > 0"
      :data="rows"
      class="q-table"
      size="small"
      :header-cell-style="{ background: '#161b22', color: '#8b949e', borderBottom: '1px solid #1b2332' }"
      :cell-style="{ borderBottom: '1px solid #1b2332' }"
      :max-height="maxHeight"
      empty-text="No trades"
    >
      <el-table-column prop="entry_time" label="Entry" min-width="150">
        <template #default="{ row }">
          <span class="cell-date">{{ formatDateTime(row.entry_time) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="exit_time" label="Exit" min-width="150">
        <template #default="{ row }">
          <span class="cell-date">{{ formatDateTime(row.exit_time) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="symbol" label="Symbol" width="90">
        <template #default="{ row }">
          <span class="cell-symbol">{{ row.symbol }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="side" label="Side" width="70">
        <template #default="{ row }">
          <span :class="row.side === 'long' ? 'cell-long' : 'cell-short'">{{ row.side }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="qty" label="Qty" width="70" align="right">
        <template #default="{ row }">
          <span class="cell-num">{{ row.qty }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="entry_price" label="Entry $" width="90" align="right">
        <template #default="{ row }">
          <span class="cell-num">{{ formatPrice(row.entry_price) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="exit_price" label="Exit $" width="90" align="right">
        <template #default="{ row }">
          <span class="cell-num">{{ formatPrice(row.exit_price) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="pnl" label="PnL" width="100" align="right">
        <template #default="{ row }">
          <span :class="row.pnl >= 0 ? 'cell-positive' : 'cell-negative'">
            {{ row.pnl >= 0 ? '+' : '' }}{{ formatPrice(row.pnl) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="return_pct" label="%" width="80" align="right">
        <template #default="{ row }">
          <span :class="row.return_pct >= 0 ? 'cell-positive' : 'cell-negative'">
            {{ row.return_pct >= 0 ? '+' : '' }}{{ row.return_pct?.toFixed(2) }}%
          </span>
        </template>
      </el-table-column>
    </el-table>

    <div v-else class="empty-state">
      <el-icon :size="32" color="#1b2332"><List /></el-icon>
      <p>No trade data</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { List } from '@element-plus/icons-vue'

import type { TradeInfo } from '@/api/experiment'

const props = withDefaults(defineProps<{
  trades: TradeInfo[]
  maxHeight?: string | number
}>(), {
  maxHeight: '100%',
})

const rows = computed(() => props.trades || [])

function formatDateTime(dt?: string): string {
  if (!dt) return '-'
  return dt.replace('T', ' ').substring(0, 19)
}

function formatPrice(v?: number): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '-'
  return v.toFixed(2)
}
</script>

<style scoped>
.trades-widget {
  width: 100%;
  height: 100%;
  background: #0d1117;
  border: 1px solid #1b2332;
  border-radius: 8px;
  padding: 4px;
  box-sizing: border-box;
  overflow: hidden;
}

.q-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
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

.cell-num {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 12px;
  color: #c9d1d9;
}

.cell-long {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 11px;
  color: #3fb950;
  background: rgba(63, 185, 80, 0.1);
  padding: 2px 6px;
  border-radius: 3px;
}

.cell-short {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 11px;
  color: #f85149;
  background: rgba(248, 81, 73, 0.1);
  padding: 2px 6px;
  border-radius: 3px;
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
  font-weight: 600;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 200px;
  color: #484f58;
  gap: 8px;
  font-size: 13px;
}
</style>
