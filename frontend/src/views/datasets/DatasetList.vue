<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-header-row">
        <div>
          <h1 class="page-title">数据集 Datasets</h1>
          <p class="page-desc">管理行情数据 Manage market data and datasets</p>
        </div>
        <div class="page-actions">
          <el-input
            v-model="keyword"
            placeholder="搜索数据集 Search datasets..."
            :prefix-icon="Search"
            clearable
            class="search-input"
          />
          <el-button :icon="Refresh" circle @click="onRefresh" :loading="store.loading" />
        </div>
      </div>
    </div>

    <div class="page-content">
      <!-- Loading -->
      <div v-if="store.loading && store.items.length === 0" class="loading-state">
        <el-icon class="is-loading" :size="24"><Loading /></el-icon>
        <span>加载数据集中 Loading datasets...</span>
      </div>

      <!-- Error -->
      <div v-else-if="store.error" class="error-state">
        <el-icon :size="24" color="#f85149"><CircleCloseFilled /></el-icon>
        <p>{{ store.error }}</p>
        <el-button type="primary" size="small" @click="onRefresh">重试 Retry</el-button>
      </div>

      <!-- Table -->
      <el-table
        v-else
        :data="filteredItems"
        class="q-table"
        :header-cell-style="{ background: '#161b22', color: '#8b949e', borderBottom: '1px solid #1b2332' }"
        :cell-style="{ borderBottom: '1px solid #1b2332' }"
        :row-style="{ cursor: 'pointer' }"
        @row-click="onRowClick"
        empty-text="No datasets found"
      >
        <el-table-column prop="name" label="名称 Name" min-width="180">
          <template #default="{ row }">
            <span class="cell-name">{{ row.name }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="symbol" label="标的 Symbol" width="120">
          <template #default="{ row }">
            <span class="cell-id">{{ row.symbol }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="frequency" label="频率 Freq" width="80">
          <template #default="{ row }">
            <el-tag size="small" effect="dark" class="freq-tag">{{ row.frequency }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="asset_type" label="类型 Type" width="90">
          <template #default="{ row }">
            <span class="cell-muted">{{ row.asset_type }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="start_time" label="开始 Start" width="120">
          <template #default="{ row }">
            <span class="cell-muted">{{ formatDate(row.start_time) }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="end_time" label="结束 End" width="120">
          <template #default="{ row }">
            <span class="cell-muted">{{ formatDate(row.end_time) }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="rows" label="行数 Rows" width="90" align="right">
          <template #default="{ row }">
            <span class="cell-num">{{ formatNumber(row.rows) }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="is_ohlcv" label="OHLCV" width="70" align="center">
          <template #default="{ row }">
            <el-icon v-if="row.is_ohlcv" :size="14" color="#3fb950"><Check /></el-icon>
            <span v-else class="cell-muted">-</span>
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
import { useDatasetStore } from '@/stores/dataset'
import { Search, Refresh, Loading, CircleCloseFilled, ArrowRight, Check } from '@element-plus/icons-vue'

const router = useRouter()
const store = useDatasetStore()
const keyword = ref('')

const filteredItems = computed(() => {
  if (!keyword.value) return store.items
  const q = keyword.value.toLowerCase()
  return store.items.filter(
    (d) =>
      d.name.toLowerCase().includes(q) ||
      d.symbol.toLowerCase().includes(q) ||
      d.dataset_id.toLowerCase().includes(q) ||
      (d.tags || []).some((t) => t.toLowerCase().includes(q)),
  )
})

function formatNumber(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(2) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return String(n)
}

function formatDate(dt: string): string {
  if (!dt) return '-'
  return dt.split(' ')[0]
}

function onRefresh() {
  store.load()
}

function onRowClick(row: any) {
  router.push(`/datasets/${row.dataset_id}`)
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
  width: 240px;
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

.cell-name {
  font-weight: 500;
  color: #e6edf3;
}

.cell-id {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  color: #58a6ff;
}

.cell-muted {
  color: #8b949e;
  font-size: 13px;
}

.cell-num {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  color: #bc8cff;
}

.freq-tag {
  background: #1b2332;
  border-color: #1b2332;
  color: #8b949e;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 11px;
}
</style>
