<template>
  <div class="signals-workspace">
    <template v-if="!store.currentSessionId">
      <el-empty description="请先创建会话" :image-size="120" />
    </template>
    <template v-else>
      <!-- 工具栏 -->
      <div class="toolbar">
        <div class="toolbar-left">
          <span class="page-title">Signals</span>
          <span class="page-sub">信号输出 Signal Output · 点击行展开详情</span>
        </div>
        <div class="toolbar-right">
          <span class="session-tag">SID: {{ store.currentSessionId }}</span>
          <el-button :icon="Refresh" size="small" @click="loadSignals" :loading="loading">刷新</el-button>
        </div>
      </div>

      <!-- 信号表格 -->
      <el-card class="table-card" shadow="never">
        <el-table :data="signals" stripe size="small" height="100%" v-loading="loading" empty-text="暂无信号">
          <el-table-column type="expand">
            <template #default="{ row }">
              <div class="expand-detail">
                <div class="detail-label">完整原因 Reason</div>
                <div class="detail-content">{{ row.reason || '无' }}</div>
                <div class="detail-meta">
                  <span>Signal ID: {{ row.signal_id }}</span>
                  <span v-if="row.order_id">Order ID: {{ row.order_id }}</span>
                  <span>Score: {{ formatNum(row.score) }}</span>
                  <span>Confidence: {{ formatPct(row.confidence) }}</span>
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="Time" width="170">
            <template #default="{ row }">{{ formatTime(row.time) }}</template>
          </el-table-column>
          <el-table-column label="Symbol" min-width="120">
            <template #default="{ row }"><span class="symbol-text">{{ row.symbol }}</span></template>
          </el-table-column>
          <el-table-column label="Direction" width="110">
            <template #default="{ row }">
              <el-tag :type="dirType(row.direction)" size="small" effect="dark">{{ row.direction || '-' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="Score" width="100" align="right">
            <template #default="{ row }"><span class="num">{{ formatNum(row.score) }}</span></template>
          </el-table-column>
          <el-table-column label="Confidence" width="170">
            <template #default="{ row }">
              <el-progress
                :percentage="confPct(row.confidence)"
                :color="confColor(row.confidence)"
                :stroke-width="10"
                :format="formatConf"
              />
            </template>
          </el-table-column>
          <el-table-column label="Reason" min-width="220" show-overflow-tooltip>
            <template #default="{ row }">{{ row.reason || '-' }}</template>
          </el-table-column>
          <el-table-column label="Status" width="110">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small" effect="dark">{{ row.status || '-' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="Order ID" min-width="150" show-overflow-tooltip>
            <template #default="{ row }">{{ row.order_id || '-' }}</template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { useTradingStore } from '@/stores/trading'
import { tradingApi, type SignalItem } from '@/api/trading'

const store = useTradingStore()
const loading = ref(false)
const signals = ref<SignalItem[]>([])

// ---- 格式化 ----
function formatNum(v: number | undefined | null): string {
  if (v == null) return '-'
  return Number(v).toLocaleString('en-US', { maximumFractionDigits: 4 })
}
function formatPct(v: number | undefined | null): string {
  if (v == null) return '-'
  return (v * 100).toFixed(2) + '%'
}
function formatTime(t: string | undefined): string {
  if (!t) return '-'
  return t.replace('T', ' ').slice(0, 19)
}
function formatConf(p: number): string {
  return p.toFixed(1) + '%'
}

// ---- 置信度归一化（兼容 0~1 与 0~100） ----
function confPct(confidence: number | undefined | null): number {
  if (confidence == null) return 0
  const v = confidence <= 1 ? confidence * 100 : confidence
  return Math.max(0, Math.min(100, v))
}
function confColor(confidence: number | undefined | null): string {
  const p = confPct(confidence)
  if (p >= 70) return '#3fb950'
  if (p >= 40) return '#d29922'
  return '#f85149'
}

// ---- Tag 类型 ----
function dirType(direction: string): 'success' | 'danger' | 'info' {
  const d = (direction || '').toUpperCase()
  if (d === 'BUY' || d === 'LONG') return 'success'
  if (d === 'SELL' || d === 'SHORT') return 'danger'
  return 'info'
}
function statusType(status: string): 'success' | 'warning' | 'danger' | 'info' {
  switch ((status || '').toUpperCase()) {
    case 'FILLED':
    case 'EXECUTED':
    case 'ACTIVE': return 'success'
    case 'PENDING':
    case 'SUBMITTED': return 'warning'
    case 'REJECTED':
    case 'EXPIRED':
    case 'CANCELLED': return 'danger'
    default: return 'info'
  }
}

// ---- 数据加载 ----
async function loadSignals() {
  if (!store.currentSessionId) return
  loading.value = true
  try {
    const res = await tradingApi.getSignals(store.currentSessionId)
    signals.value = res.signals || []
  } catch (e) {
    console.error('loadSignals error', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadSignals()
})
</script>

<style scoped>
.signals-workspace {
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

/* 展开详情 */
.expand-detail {
  padding: 12px 20px;
  background: var(--q-bg-tertiary, #161b22);
}
.detail-label {
  font-size: 11px;
  color: var(--q-text-muted, #8b949e);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}
.detail-content {
  font-size: 13px;
  color: var(--q-text-primary, #e6edf3);
  line-height: 1.6;
  margin-bottom: 10px;
  white-space: pre-wrap;
  word-break: break-word;
}
.detail-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  font-size: 11px;
  color: var(--q-text-secondary, #8b949e);
  font-variant-numeric: tabular-nums;
}

/* 进度条暗色轨道 */
:deep(.el-progress-bar__outer) {
  background-color: var(--q-bg-tertiary, #161b22);
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
</style>
