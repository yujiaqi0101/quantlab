<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-header-row">
        <div>
          <h1 class="page-title">Strategies</h1>
          <p class="page-desc">Manage and configure trading strategies</p>
        </div>
        <div class="page-actions">
          <el-input
            v-model="keyword"
            placeholder="Search strategies..."
            :prefix-icon="Search"
            clearable
            class="search-input"
            @input="onSearch"
          />
          <el-button :icon="Refresh" circle @click="onRefresh" :loading="store.loading" />
        </div>
      </div>
    </div>

    <div class="page-content">
      <!-- Loading -->
      <div v-if="store.loading && store.items.length === 0" class="loading-state">
        <el-icon class="is-loading" :size="24"><Loading /></el-icon>
        <span>Loading strategies...</span>
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
        :data="filteredItems"
        class="q-table"
        :header-cell-style="{ background: '#161b22', color: '#8b949e', borderBottom: '1px solid #1b2332' }"
        :cell-style="{ borderBottom: '1px solid #1b2332' }"
        :row-style="{ cursor: 'pointer' }"
        @row-click="onRowClick"
        empty-text="No strategies found"
      >
        <el-table-column prop="id" label="ID" min-width="140">
          <template #default="{ row }">
            <span class="cell-id">{{ row.id }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="name" label="Name" min-width="180">
          <template #default="{ row }">
            <span class="cell-name">{{ row.name }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="version" label="Version" width="100">
          <template #default="{ row }">
            <el-tag size="small" effect="plain" class="version-tag">{{ row.version }}</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="tags" label="Tags" min-width="200">
          <template #default="{ row }">
            <el-tag
              v-for="tag in (row.tags || []).slice(0, 3)"
              :key="tag"
              size="small"
              effect="dark"
              class="tag-item"
            >
              {{ tag }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="parameters" label="Params" width="90" align="center">
          <template #default="{ row }">
            <span class="cell-params">{{ (row.parameters || []).length }}</span>
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
import { useStrategyStore } from '@/stores/strategy'
import { Search, Refresh, Loading, CircleCloseFilled, ArrowRight } from '@element-plus/icons-vue'

const router = useRouter()
const store = useStrategyStore()
const keyword = ref('')

const filteredItems = computed(() => {
  if (!keyword.value) return store.items
  const q = keyword.value.toLowerCase()
  return store.items.filter(
    (s) =>
      s.id.toLowerCase().includes(q) ||
      s.name.toLowerCase().includes(q) ||
      (s.tags || []).some((t) => t.toLowerCase().includes(q)),
  )
})

function onSearch() {
  // client-side filtering via computed
}

function onRefresh() {
  store.load(keyword.value || undefined)
}

function onRowClick(row: any) {
  router.push(`/strategies/${row.id}`)
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

/* Table */
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

.cell-id {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  color: #58a6ff;
}

.cell-name {
  font-weight: 500;
  color: #e6edf3;
}

.cell-params {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  color: #8b949e;
}

.version-tag {
  background: transparent;
  border-color: #1b2332;
  color: #8b949e;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 12px;
}

.tag-item {
  margin-right: 4px;
  background: #1b2332;
  border-color: #1b2332;
  color: #8b949e;
  font-size: 11px;
}
</style>
