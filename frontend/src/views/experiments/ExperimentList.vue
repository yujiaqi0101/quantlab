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
          <el-select v-model="statusFilter" placeholder="Status" clearable class="filter-select" @change="onFilterChange">
            <el-option label="Normal" value="normal" />
            <el-option label="Candidate" value="candidate" />
            <el-option label="Production" value="production" />
          </el-select>
          <el-select v-model="folderFilter" placeholder="Folder" clearable class="filter-select" @change="onFilterChange">
            <el-option v-for="f in store.folders" :key="f" :label="f" :value="f" />
          </el-select>
          <el-button
            v-if="selectedIds.length >= 2"
            type="primary"
            :icon="DataLine"
            @click="goCompare"
          >
            Compare ({{ selectedIds.length }})
          </el-button>
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
        @selection-change="onSelectionChange"
        empty-text="No experiments found"
      >
        <el-table-column type="selection" width="40" />

        <el-table-column prop="name" label="Experiment" min-width="180">
          <template #default="{ row }">
            <div class="cell-exp">
              <div class="cell-name-row">
                <span
                  class="cell-fav"
                  :class="{ active: row.favorite === 1 }"
                  @click.stop="toggleFavorite(row)"
                >★</span>
                <span class="cell-name">{{ row.name || row.id }}</span>
              </div>
              <div class="cell-sub-row">
                <span class="cell-id-sub">{{ row.id }}</span>
                <el-tag
                  v-if="row.status && row.status !== 'normal'"
                  :type="statusTagType(row.status)"
                  effect="dark"
                  size="small"
                  class="status-tag"
                >{{ row.status }}</el-tag>
                <el-tag
                  v-if="row.folder"
                  effect="plain"
                  size="small"
                  class="folder-tag"
                >{{ row.folder }}</el-tag>
              </div>
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

        <el-table-column label="" width="80" align="center">
          <template #default="{ row }">
            <div @click.stop>
              <el-dropdown trigger="click" @command="(cmd: string) => onAction(cmd, row)">
                <el-icon :size="14" color="#484f58" class="action-icon"><MoreFilled /></el-icon>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="candidate">
                    {{ row.status === 'candidate' ? 'Remove Candidate' : 'Mark Candidate' }}
                  </el-dropdown-item>
                  <el-dropdown-item command="production">
                    {{ row.status === 'production' ? 'Remove Production' : 'Mark Production' }}
                  </el-dropdown-item>
                  <el-dropdown-item command="normal" :disabled="row.status === 'normal'">
                    Set Normal
                  </el-dropdown-item>
                  <el-dropdown-item divided command="folder">Move to Folder...</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Folder Dialog -->
    <el-dialog v-model="folderDialogVisible" title="Move to Folder" width="360px">
      <el-select v-model="folderInput" placeholder="Select or type folder name" filterable allow-create class="folder-dialog-select">
        <el-option v-for="f in store.folders" :key="f" :label="f" :value="f" />
      </el-select>
      <template #footer>
        <el-button @click="folderDialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="confirmFolder">Move</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useExperimentStore } from '@/stores/experiment'
import { Search, Refresh, Loading, CircleCloseFilled, DataLine, MoreFilled } from '@element-plus/icons-vue'
import type { ExperimentInfo } from '@/api/experiment'

const router = useRouter()
const store = useExperimentStore()
const keyword = ref('')
const sortField = ref('created_at')
const sortOrder = ref<'asc' | 'desc'>('desc')
const statusFilter = ref('')
const folderFilter = ref('')
const selectedIds = ref<string[]>([])
const folderDialogVisible = ref(false)
const folderInput = ref('')
const folderTargetId = ref('')

const filteredItems = computed(() => {
  let items = store.items
  if (keyword.value) {
    const q = keyword.value.toLowerCase()
    items = items.filter(
      (e) =>
        (e.name || '').toLowerCase().includes(q) ||
        e.id.toLowerCase().includes(q) ||
        e.strategy.toLowerCase().includes(q) ||
        (e.note || '').toLowerCase().includes(q),
    )
  }
  if (statusFilter.value) {
    items = items.filter((e) => (e.status || 'normal') === statusFilter.value)
  }
  if (folderFilter.value) {
    items = items.filter((e) => e.folder === folderFilter.value)
  }
  return items
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

function onFilterChange() {
  // 过滤已通过 computed 响应式处理
}

function onRefresh() {
  store.load()
  store.loadFolders()
}

function onRowClick(row: any) {
  router.push(`/experiments/${row.id}`)
}

function onSelectionChange(rows: ExperimentInfo[]) {
  selectedIds.value = rows.map((r) => r.id)
}

function goCompare() {
  if (selectedIds.value.length >= 2) {
    router.push({ path: '/compare', query: { ids: selectedIds.value.join(',') } })
  }
}

function statusTagType(status: string): '' | 'success' | 'warning' | 'danger' | 'info' {
  if (status === 'candidate') return 'warning'
  if (status === 'production') return 'success'
  return 'info'
}

async function toggleFavorite(row: ExperimentInfo) {
  await store.updateFavorite(row.id, row.favorite !== 1)
}

function onAction(cmd: string, row: ExperimentInfo) {
  if (cmd === 'folder') {
    folderTargetId.value = row.id
    folderInput.value = row.folder || ''
    folderDialogVisible.value = true
  } else if (cmd === 'candidate' || cmd === 'production' || cmd === 'normal') {
    const newStatus = row.status === cmd ? 'normal' : cmd
    store.updateStatus(row.id, newStatus)
  }
}

async function confirmFolder() {
  if (folderTargetId.value && folderInput.value) {
    await store.updateFolder(folderTargetId.value, folderInput.value)
    store.loadFolders()
  }
  folderDialogVisible.value = false
}

function formatDate(dt: string): string {
  if (!dt) return '-'
  return dt.split('T')[0]
}

onMounted(() => {
  store.load()
  store.loadFolders()
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
  flex-wrap: wrap;
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

.filter-select {
  width: 120px;
}

.filter-select :deep(.el-input__wrapper) {
  background: #161b22;
  border: 1px solid #1b2332;
  box-shadow: none;
}

.filter-select :deep(.el-input__inner) {
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

.cell-name-row {
  display: flex;
  align-items: center;
  gap: 4px;
}

.cell-fav {
  cursor: pointer;
  color: #484f58;
  font-size: 14px;
  transition: color 0.2s;
  user-select: none;
}

.cell-fav.active {
  color: #e3b341;
}

.cell-fav:hover {
  color: #e3b341;
}

.cell-name {
  font-weight: 500;
  color: #e6edf3;
  font-size: 13px;
}

.cell-sub-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.cell-id-sub {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 11px;
  color: #484f58;
}

.status-tag {
  font-size: 10px;
  height: 18px;
  line-height: 16px;
  padding: 0 4px;
}

.folder-tag {
  font-size: 10px;
  height: 18px;
  line-height: 16px;
  padding: 0 4px;
  background: rgba(88, 166, 255, 0.1);
  border-color: #1f6feb;
  color: #58a6ff;
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

.action-icon {
  cursor: pointer;
}

.action-icon:hover {
  color: #58a6ff !important;
}

.folder-dialog-select {
  width: 100%;
}
</style>
