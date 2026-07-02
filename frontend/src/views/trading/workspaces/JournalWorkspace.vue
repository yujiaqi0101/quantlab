<template>
  <div class="journal-workspace">
    <template v-if="!store.currentSessionId">
      <el-empty description="请先创建会话" :image-size="120" />
    </template>
    <template v-else>
      <!-- 工具栏 -->
      <div class="toolbar">
        <div class="toolbar-left">
          <span class="page-title">Journal</span>
          <span class="page-sub">交易日志 Trade Journal</span>
        </div>
        <div class="toolbar-right">
          <el-input
            v-model="symbolFilter"
            placeholder="按 Symbol 筛选"
            clearable
            size="small"
            style="width: 220px"
            :prefix-icon="Search"
          />
          <span class="session-tag">SID: {{ store.currentSessionId }}</span>
          <el-button :icon="Refresh" size="small" @click="loadJournal" :loading="loading">刷新</el-button>
        </div>
      </div>

      <!-- 日志表格 -->
      <el-card class="table-card" shadow="never">
        <el-table :data="filteredJournal" stripe size="small" height="100%" v-loading="loading" empty-text="暂无交易日志">
          <el-table-column label="Time" width="170">
            <template #default="{ row }">{{ formatTime(row.time) }}</template>
          </el-table-column>
          <el-table-column label="Type" width="100">
            <template #default="{ row }">{{ row.type || '-' }}</template>
          </el-table-column>
          <el-table-column label="Symbol" min-width="120">
            <template #default="{ row }"><span class="symbol-text">{{ row.symbol }}</span></template>
          </el-table-column>
          <el-table-column label="Side" width="80">
            <template #default="{ row }">
              <el-tag :type="sideType(row.side)" size="small" effect="dark">{{ row.side || '-' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="Qty" width="100" align="right">
            <template #default="{ row }"><span class="num">{{ formatNum(row.quantity) }}</span></template>
          </el-table-column>
          <el-table-column label="Price" width="100" align="right">
            <template #default="{ row }"><span class="num">{{ formatNum(row.price) }}</span></template>
          </el-table-column>
          <el-table-column label="Amount" width="130" align="right">
            <template #default="{ row }"><span class="num">{{ formatNum(row.amount) }}</span></template>
          </el-table-column>
          <el-table-column label="Commission" width="120" align="right">
            <template #default="{ row }"><span class="num muted">{{ formatNum(row.commission) }}</span></template>
          </el-table-column>
          <el-table-column label="Reason" min-width="220" show-overflow-tooltip>
            <template #default="{ row }">{{ row.reason || '-' }}</template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Refresh, Search } from '@element-plus/icons-vue'
import { useTradingStore } from '@/stores/trading'
import { tradingApi, type JournalItem } from '@/api/trading'

const store = useTradingStore()
const loading = ref(false)
const journal = ref<JournalItem[]>([])
const symbolFilter = ref('')

// ---- 筛选 ----
const filteredJournal = computed(() => {
  const kw = symbolFilter.value.trim().toUpperCase()
  if (!kw) return journal.value
  return journal.value.filter(j => (j.symbol || '').toUpperCase().includes(kw))
})

// ---- 格式化 ----
function formatNum(v: number | undefined | null): string {
  if (v == null) return '-'
  return Number(v).toLocaleString('en-US', { maximumFractionDigits: 4 })
}
function formatTime(t: string | undefined): string {
  if (!t) return '-'
  return t.replace('T', ' ').slice(0, 19)
}
function sideType(side: string): 'success' | 'danger' | 'info' {
  const s = (side || '').toUpperCase()
  if (s === 'BUY') return 'success'
  if (s === 'SELL') return 'danger'
  return 'info'
}

// ---- 数据加载 ----
async function loadJournal() {
  if (!store.currentSessionId) return
  loading.value = true
  try {
    const res = await tradingApi.getJournal(store.currentSessionId)
    journal.value = res.journal || []
  } catch (e) {
    console.error('loadJournal error', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadJournal()
})
</script>

<style scoped>
.journal-workspace {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 12px;
  font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', 'JetBrains Mono', ui-monospace, monospace;
}

/* 工具栏 */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-shrink: 0;
}
.toolbar-left {
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.page-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--q-text-primary, #e6edf3);
}
.page-sub {
  font-size: 11px;
  color: var(--q-text-muted, #8b949e);
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
.muted {
  color: var(--q-text-muted, #8b949e);
}
</style>
