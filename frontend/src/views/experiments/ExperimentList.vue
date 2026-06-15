<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-header-row">
        <div>
          <h1 class="page-title">Experiments</h1>
          <p class="page-desc">{{ store.items.length }} experiments recorded</p>
        </div>
        <div class="page-actions">
          <el-input
            v-model="keyword"
            placeholder="Search experiments..."
            :prefix-icon="Search"
            clearable
            class="search-input"
          />
          <el-select v-model="sortField" class="sort-select" @change="onSort">
            <el-option label="Sort by Return" value="total_return" />
            <el-option label="Sort by Sharpe" value="sharpe" />
            <el-option label="Sort by MaxDD" value="max_drawdown" />
            <el-option label="Sort by Created" value="created_at" />
          </el-select>
          <el-button :icon="Refresh" circle @click="onRefresh" :loading="store.loading" />
        </div>
      </div>
    </div>

    <div class="page-content">
      <!-- Loading -->
      <div v-if="store.loading && store.items.length === 0" class="loading-state">
        <el-icon class="is-loading" :size="24"><Loading /></el-icon>
        <span>Loading experiments...</span>
      </div>

      <!-- Error -->
      <div v-else-if="store.error" class="error-state">
        <el-icon :size="24" color="#f85149"><CircleCloseFilled /></el-icon>
        <p>{{ store.error }}</p>
        <el-button type="primary" size="small" @click="onRefresh">Retry</el-button>
      </div>

      <!-- Table -->
      <el-table
        v-else
        :data="sortedItems"
        class="q-table"
        :header-cell-style="{ background: '#161b22', color: '#8b949e', borderBottom: '1px solid #1b2332' }"
        :cell-style="{ borderBottom: '1px solid #1b2332' }"
        :row-style="{ cursor: 'pointer' }"
        @row-click="onRowClick"
        empty-text="No experiments found"
      >
        <el-table-column prop="name" label="Experiment" min-width="180">
          <template #default="{ row }">
            <div class="cell-exp">
              <span class="cell-name">{{ row.name || row.id }}</span>
              <span class="cell-id-sub">{{ row.id }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="strategy" label="Strategy" width="140">
          <template #default="{ row }">
            <span class="cell-strategy">{{ row.strategy }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="total_return" label="Return" width="100" align="right" sortable>
          <template #default="{ row }">
            <span :class="row.total_return >= 0 ? 'cell-positive' : 'cell-negative'">
              {{ row.total_return >= 0 ? '+' : '' }}{{ row.total_return?.toFixed(2) }}%
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="sharpe" label="Sharpe" width="90" align="right" sortable>
          <template #default="{ row }">
            <span class="cell-num">{{ row.sharpe?.toFixed(2) }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="max_drawdown" label="MaxDD" width="90" align="right" sortable>
          <template #default="{ row }">
            <span class="cell-negative">{{ row.max_drawdown?.toFixed(2) }}%</span>
          </template>
        </el-table-column>

        <el-table-column prop="win_rate" label="Win%" width="80" align="right">
          <template #default="{ row }">
            <span class="cell-num">{{ row.win_rate?.toFixed(1) }}%</span>
          </template>
        </el-table-column>

        <el-table-column prop="trade_count" label="Trades" width="80" align="right">
          <template #default="{ row }">
            <span class="cell-num">{{ row.trade_count }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="Created" width="120">
          <template #default="{ row }">
            <span class="cell-muted">{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="" width="60" align="center">
          <template #default>
            <el-icon :size="14" color="#484f58"><ArrowRight /></el-icon>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useExperimentStore } from '@/stores/experiment'
import { Search, Refresh, Loading, CircleCloseFilled, ArrowRight } from '@element-plus/icons-vue'

const router = useRouter()
const store = useExperimentStore()
const keyword = ref('')
const sortField = ref('created_at')
const sortOrder = ref<'asc' | 'desc'>('desc')

const filteredItems = computed(() => {
  if (!keyword.value) return store.items
  const q = keyword.value.toLowerCase()
  return store.items.filter(
    (e) =>
      (e.name || '').toLowerCase().includes(q) ||
      e.id.toLowerCase().includes(q) ||
      e.strategy.toLowerCase().includes(q) ||
      (e.note || '').toLowerCase().includes(q),
  )
})

const sortedItems = computed(() => {
  const items = [...filteredItems.value]
  const field = sortField.value as keyof (typeof items)[0]
  const order = sortOrder.value === 'asc' ? 1 : -1
  items.sort((a, b) => {
    const va = a[field] ?? ''
    const vb = b[field] ?? ''
    if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * order
    return String(va).localeCompare(String(vb)) * order
  })
  return items
})

function onSort() {
  sortOrder.value = sortOrder.value === 'desc' ? 'asc' : 'desc'
}

function onRefresh() {
  store.load()
}

function onRowClick(row: any) {
  router.push(`/experiments/${row.id}`)
}

function formatDate(dt: string): string {
  if (!dt) return '-'
  return dt.split('T')[0]
}

onMounted(() => {
  store.load()
})
</script>

<style scoped>
.page-container {
  max-width: 1200px;
}

.page-header {
  margin-bottom: 24px;
}

.page-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #e6edf3;
  margin: 0 0 4px 0;
  letter-spacing: -0.5px;
}

.page-desc {
  font-size: 14px;
  color: #484f58;
  margin: 0;
}

.page-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.search-input {
  width: 200px;
}

.search-input :deep(.el-input__wrapper) {
  background: #161b22;
  border: 1px solid #1b2332;
  box-shadow: none;
}

.search-input :deep(.el-input__inner) {
  color: #e6edf3;
}

.search-input :deep(.el-input__inner::placeholder) {
  color: #484f58;
}

.sort-select {
  width: 160px;
}

.sort-select :deep(.el-input__wrapper) {
  background: #161b22;
  border: 1px solid #1b2332;
  box-shadow: none;
}

.sort-select :deep(.el-input__inner) {
  color: #e6edf3;
}

.page-content {
  min-height: 400px;
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

.q-table {
  --el-table-bg-color: #0d1117;
  --el-table-tr-bg-color: #0d1117;
  --el-table-row-hover-bg-color: #161b22;
  --el-table-text-color: #e6edf3;
  --el-table-border-color: #1b2332;
  --el-table-header-text-color: #8b949e;
}

.q-table :deep(.el-table__empty-text) {
  color: #484f58;
}

.cell-exp {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.cell-name {
  font-weight: 500;
  color: #e6edf3;
  font-size: 13px;
}

.cell-id-sub {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 11px;
  color: #484f58;
}

.cell-strategy {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 12px;
  color: #58a6ff;
}

.cell-positive {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  color: #3fb950;
  font-weight: 600;
}

.cell-negative {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  color: #f85149;
}

.cell-num {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  color: #c9d1d9;
}

.cell-muted {
  color: #8b949e;
  font-size: 12px;
}
</style>
