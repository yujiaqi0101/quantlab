<template>
  <div class="observe-journal">
    <div class="page-header">
      <div>
        <h1 class="page-title">交易日志 Trading Journal</h1>
        <span class="page-subtitle">交易日志 — 决策记录 Trading journal — decision records</span>
      </div>
      <div class="header-actions">
        <el-button type="primary" :icon="Plus" @click="showAddDialog = true">新增 Add</el-button>
        <el-button :icon="Refresh" @click="refresh" :loading="loading">刷新 Refresh</el-button>
      </div>
    </div>

    <!-- Filter -->
    <el-card class="filter-card" shadow="hover">
      <el-form :inline="true" size="small">
        <el-form-item label="类别">
          <el-select v-model="filter.category" placeholder="全部" clearable style="width: 140px">
            <el-option label="Signal" value="SIGNAL" />
            <el-option label="Order" value="ORDER" />
            <el-option label="Fill" value="FILL" />
            <el-option label="Risk Alert" value="RISK_ALERT" />
            <el-option label="Kill Switch" value="KILL_SWITCH" />
            <el-option label="Recovery" value="RECOVERY" />
            <el-option label="Manual" value="MANUAL" />
            <el-option label="System" value="SYSTEM" />
          </el-select>
        </el-form-item>
        <el-form-item label="策略">
          <el-input v-model="filter.strategy" placeholder="策略ID" clearable style="width: 140px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="refresh">查询</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- Journal Entries -->
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>日志条目</span>
          <el-tag size="small">{{ entries.length }} 条</el-tag>
        </div>
      </template>

      <el-timeline v-if="entries.length > 0">
        <el-timeline-item
          v-for="(entry, idx) in entries"
          :key="idx"
          :timestamp="formatTime(entry.timestamp)"
          :type="entryType(entry.type)"
        >
          <div class="journal-entry">
            <div class="entry-header">
              <el-tag :type="entryType(entry.type)" size="small">{{ entry.type }}</el-tag>
              <span v-if="entry.strategy_id" class="entry-meta">
                策略: {{ entry.strategy_id }}
              </span>
              <span v-if="entry.symbol" class="entry-meta">
                Symbol: {{ entry.symbol }}
              </span>
              <span v-if="entry.order_id" class="entry-meta">
                Order: {{ entry.order_id }}
              </span>
            </div>
            <div class="entry-message">{{ entry.message }}</div>
            <div class="entry-data" v-if="entry.data && Object.keys(entry.data).length > 0">
              <pre>{{ JSON.stringify(entry.data, null, 2) }}</pre>
            </div>
            <div class="entry-tags" v-if="entry.tags && entry.tags.length > 0">
              <el-tag v-for="(tag, i) in entry.tags" :key="i" size="small" effect="plain">
                {{ tag }}
              </el-tag>
            </div>
          </div>
        </el-timeline-item>
      </el-timeline>

      <el-empty v-else description="暂无日志" />
    </el-card>

    <!-- Add Dialog -->
    <el-dialog v-model="showAddDialog" title="新增日志" width="500px">
      <el-form :model="newEntry" label-width="80px" size="small">
        <el-form-item label="类别">
          <el-select v-model="newEntry.category" style="width: 100%">
            <el-option label="观察" value="observation" />
            <el-option label="反思" value="reflection" />
            <el-option label="开仓" value="open" />
            <el-option label="平仓" value="close" />
          </el-select>
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="newEntry.title" placeholder="日志标题" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="newEntry.content" type="textarea" :rows="4" placeholder="详细内容" />
        </el-form-item>
        <el-form-item label="策略">
          <el-input v-model="newEntry.strategy" placeholder="策略ID（可选）" />
        </el-form-item>
        <el-form-item label="Symbol">
          <el-input v-model="newEntry.symbol" placeholder="交易对（可选）" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="submitEntry">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useObserveStore } from '@/stores/observe'
import { observeApi } from '@/api/observe'

const store = useObserveStore()
const entries = computed(() => store.journal?.entries ?? [])
const loading = computed(() => store.loading)

const filter = reactive({
  category: '' as string,
  strategy: '' as string,
})

const showAddDialog = ref(false)
const newEntry = reactive({
  category: 'observation',
  title: '',
  content: '',
  strategy: '',
  symbol: '',
})

function entryType(type: string): 'primary' | 'success' | 'warning' | 'danger' | 'info' {
  switch (type) {
    case 'SIGNAL': return 'primary'
    case 'ORDER': return 'warning'
    case 'FILL': return 'success'
    case 'RISK_ALERT':
    case 'KILL_SWITCH': return 'danger'
    default: return 'info'
  }
}

function formatTime(ts: number): string {
  if (!ts) return ''
  return new Date(ts).toLocaleString('zh-CN')
}

async function refresh() {
  await store.fetchJournal({
    category: filter.category || undefined,
    strategy: filter.strategy || undefined,
    limit: 200,
  })
}

async function submitEntry() {
  if (!newEntry.title || !newEntry.content) {
    ElMessage.warning('请填写标题和内容')
    return
  }
  try {
    await observeApi.addJournalEntry({
      category: newEntry.category,
      title: newEntry.title,
      content: newEntry.content,
      strategy: newEntry.strategy,
      symbol: newEntry.symbol,
    })
    ElMessage.success('日志已添加')
    showAddDialog.value = false
    newEntry.title = ''
    newEntry.content = ''
    await refresh()
  } catch (e: any) {
    ElMessage.error(e.message || '添加失败')
  }
}

watch(filter, refresh, { deep: true })

onMounted(() => {
  refresh()
})
</script>

<style scoped>
.observe-journal { padding: 20px; }
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

.filter-card { margin-bottom: 16px; }

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.journal-entry {
  margin-left: 8px;
}
.entry-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}
.entry-meta {
  font-size: 12px;
  color: var(--q-text-muted);
}
.entry-message {
  margin: 8px 0;
  font-size: 14px;
}
.entry-data {
  background: var(--q-bg-tertiary);
  padding: 8px;
  border-radius: 4px;
  margin: 8px 0;
}
.entry-data pre {
  margin: 0;
  font-size: 12px;
  white-space: pre-wrap;
}
.entry-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-top: 4px;
}
</style>
