<template>
  <div class="observe-positions">
    <div class="page-header">
      <div>
        <h1 class="page-title">Positions</h1>
        <span class="page-subtitle">实时持仓</span>
      </div>
      <el-button :icon="Refresh" @click="refresh" :loading="loading">刷新</el-button>
    </div>

    <el-card shadow="hover">
      <el-table :data="positions" stripe>
        <el-table-column prop="symbol" label="Symbol" min-width="120" />
        <el-table-column prop="side" label="方向" width="80">
          <template #default="{ row }">
            <el-tag :type="row.side === 'LONG' ? 'success' : 'danger'" size="small">
              {{ row.side || '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="qty" label="数量" width="120">
          <template #default="{ row }">{{ formatNum(row.qty) }}</template>
        </el-table-column>
        <el-table-column prop="avg_price" label="均价" width="120">
          <template #default="{ row }">{{ formatNum(row.avg_price) }}</template>
        </el-table-column>
        <el-table-column prop="current_price" label="当前价" width="120">
          <template #default="{ row }">{{ formatNum(row.current_price) }}</template>
        </el-table-column>
        <el-table-column label="未实现盈亏" width="140">
          <template #default="{ row }">
            <span :class="pnlClass(row.unrealized_pnl)">
              {{ formatPnl(row.unrealized_pnl) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="收益率" width="120">
          <template #default="{ row }">
            <span :class="pnlClass(row.pnl_pct)">{{ formatPct(row.pnl_pct) }}</span>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && positions.length === 0" description="暂无持仓" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { useObserveStore } from '@/stores/observe'

const store = useObserveStore()
const positions = computed(() => store.positions)
const loading = computed(() => store.loading)

function formatNum(v?: number): string {
  if (v == null) return '-'
  return v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
}

function formatPnl(v?: number): string {
  if (v == null) return '$0.00'
  const sign = v >= 0 ? '+' : ''
  return `${sign}$${Math.abs(v).toFixed(2)}`
}

function formatPct(v?: number): string {
  if (v == null) return '0.00%'
  return `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`
}

function pnlClass(v?: number): string {
  if (v == null || v === 0) return ''
  return v > 0 ? 'text-success' : 'text-danger'
}

async function refresh() {
  await store.fetchPositions()
}

onMounted(() => {
  refresh()
})
</script>

<style scoped>
.observe-positions { padding: 20px; }
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-title { margin: 0; font-size: 24px; font-weight: 700; }
.page-subtitle { color: var(--q-text-muted); font-size: 13px; }
.text-success { color: #3fb950; }
.text-danger { color: #f85149; }
</style>
