<template>
  <div class="observe-timeline">
    <div class="page-header">
      <div>
        <h1 class="page-title">事件时间线 Event Timeline</h1>
        <span class="page-subtitle">事件时间线 Event timeline</span>
      </div>
      <div class="header-actions">
        <el-select v-model="filter.category" placeholder="类别 Category" clearable size="small" style="width: 140px">
          <el-option label="Market" value="market" />
          <el-option label="Signal" value="signal" />
          <el-option label="Order" value="order" />
          <el-option label="Fill" value="fill" />
          <el-option label="Risk" value="risk" />
          <el-option label="Position" value="position" />
        </el-select>
        <el-button :icon="Refresh" @click="refresh" :loading="loading">刷新 Refresh</el-button>
      </div>
    </div>

    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>事件流</span>
          <el-tag size="small">{{ timeline.length }} 条</el-tag>
        </div>
      </template>

      <el-timeline v-if="timeline.length > 0">
        <el-timeline-item
          v-for="(item, idx) in timeline"
          :key="idx"
          :timestamp="item.timestamp_str"
          :type="timelineType(item.category)"
          :hollow="item.duration_ms === 0"
        >
          <div class="timeline-item">
            <div class="timeline-header">
              <el-tag :type="timelineType(item.category)" size="small">{{ item.label }}</el-tag>
              <span class="trace-id">trace: {{ item.trace_id }}</span>
              <span v-if="item.duration_ms > 0" class="duration">
                {{ item.duration_ms.toFixed(1) }}ms
              </span>
            </div>
            <div class="timeline-payload" v-if="Object.keys(item.payload || {}).length > 0">
              <pre>{{ JSON.stringify(item.payload, null, 2) }}</pre>
            </div>
          </div>
        </el-timeline-item>
      </el-timeline>

      <el-empty v-else description="暂无事件" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, watch } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { useObserveStore } from '@/stores/observe'

const store = useObserveStore()
const timeline = computed(() => store.timeline)
const loading = computed(() => store.loading)

const filter = reactive({
  category: '' as string,
})

function timelineType(category: string): 'primary' | 'success' | 'warning' | 'danger' | 'info' {
  switch (category) {
    case 'signal': return 'primary'
    case 'order': return 'warning'
    case 'fill': return 'success'
    case 'risk': return 'danger'
    default: return 'info'
  }
}

async function refresh() {
  await store.fetchTimeline({
    limit: 200,
    category: filter.category || undefined,
  })
}

watch(filter, refresh, { deep: true })

onMounted(() => {
  refresh()
})
</script>

<style scoped>
.observe-timeline { padding: 20px; }
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

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.timeline-item {
  margin-left: 8px;
}
.timeline-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}
.trace-id {
  font-size: 11px;
  color: var(--q-text-muted);
  font-family: monospace;
}
.duration {
  font-size: 11px;
  color: var(--q-text-muted);
}
.timeline-payload {
  margin-top: 4px;
  background: var(--q-bg-tertiary);
  padding: 8px;
  border-radius: 4px;
  font-size: 12px;
}
.timeline-payload pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
