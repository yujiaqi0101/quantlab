<template>
  <div class="market-workspace">
    <template v-if="!store.currentSessionId">
      <el-empty description="请先创建会话" :image-size="120" />
    </template>
    <template v-else>
      <!-- 顶部：添加标的 + 状态 -->
      <div class="toolbar">
        <div class="toolbar-left">
          <el-input
            v-model="symbolInput"
            placeholder="输入标的代码，如 000001.SZ"
            size="default"
            clearable
            style="width: 260px"
            @keyup.enter="addSymbol"
          />
          <el-button type="primary" size="default" @click="addSymbol">添加</el-button>
          <el-button size="default" @click="clearSymbols">清空</el-button>
        </div>
        <div class="toolbar-right">
          <span class="session-tag">SID: {{ store.currentSessionId }}</span>
          <el-button size="default" :icon="Refresh" @click="loadMarket" :loading="loading">刷新</el-button>
        </div>
      </div>

      <!-- Watchlist 表格 -->
      <el-card class="table-card" shadow="never">
        <template #header>
          <div class="card-header">
            <span class="card-title">Watchlist</span>
            <span class="card-sub">{{ quotes.length }} symbols · auto-refresh 3s</span>
          </div>
        </template>
        <el-table
          :data="quotes"
          stripe
          size="small"
          height="100%"
          :row-class-name="rowClass"
          empty-text="暂无行情数据"
        >
          <el-table-column prop="symbol" label="Symbol" min-width="120">
            <template #default="{ row }">
              <span class="symbol-text">{{ row.symbol }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="last" label="Last" min-width="110" align="right">
            <template #default="{ row }">
              <span class="num">{{ formatNum(row.last) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="change_pct" label="Change%" min-width="110" align="right">
            <template #default="{ row }">
              <el-tag
                :type="changeTagType(row.change_pct)"
                effect="dark"
                size="small"
                class="change-tag"
              >
                {{ formatPct(row.change_pct) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="volume" label="Volume" min-width="130" align="right">
            <template #default="{ row }">
              <span class="num muted">{{ formatVolume(row.volume) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="bid" label="Bid" min-width="110" align="right">
            <template #default="{ row }">
              <span class="num bid-color">{{ formatNum(row.bid) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="ask" label="Ask" min-width="110" align="right">
            <template #default="{ row }">
              <span class="num ask-color">{{ formatNum(row.ask) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { useTradingStore } from '@/stores/trading'
import { tradingApi, type Quote } from '@/api/trading'

const store = useTradingStore()

const symbolInput = ref('')
const symbols = ref<string[]>([])
const quotes = ref<Quote[]>([])
const loading = ref(false)
let pollTimer: ReturnType<typeof setInterval> | null = null

// ---- 格式化 ----
function formatNum(v: number | undefined | null): string {
  if (v == null) return '-'
  return Number(v).toLocaleString('en-US', { maximumFractionDigits: 4 })
}
function formatPct(v: number | undefined | null): string {
  if (v == null) return '-'
  const sign = v > 0 ? '+' : ''
  return sign + (v * 100).toFixed(2) + '%'
}
function formatVolume(v: number | undefined | null): string {
  if (v == null) return '-'
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(2) + 'M'
  if (v >= 1_000) return (v / 1_000).toFixed(2) + 'K'
  return v.toLocaleString('en-US')
}
function changeTagType(v: number | undefined | null): 'success' | 'danger' | 'info' {
  if (v == null) return 'info'
  if (v > 0) return 'success'
  if (v < 0) return 'danger'
  return 'info'
}
function rowClass({ row }: { row: Quote }): string {
  if (row.change_pct > 0) return 'row-up'
  if (row.change_pct < 0) return 'row-down'
  return ''
}

// ---- 操作 ----
function addSymbol() {
  const s = symbolInput.value.trim().toUpperCase()
  if (!s) return
  if (symbols.value.includes(s)) {
    ElMessage.warning(`${s} 已存在`)
    return
  }
  symbols.value.push(s)
  symbolInput.value = ''
  loadMarket()
}

function clearSymbols() {
  symbols.value = []
  quotes.value = []
}

async function loadMarket() {
  if (!store.currentSessionId) return
  loading.value = true
  try {
    const res = await tradingApi.getMarket(
      store.currentSessionId,
      symbols.value.length ? symbols.value : undefined,
    )
    quotes.value = res.quotes || []
    if (symbols.value.length === 0 && res.symbols?.length) {
      // 首次加载未指定 symbols 时，回填已返回的 symbol 列表
      symbols.value = res.symbols
    }
  } catch (e: any) {
    console.error('loadMarket error', e)
    ElMessage.error('行情加载失败: ' + (e?.message || ''))
  } finally {
    loading.value = false
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(() => {
    if (store.currentSessionId) loadMarket()
  }, 3000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

onMounted(() => {
  if (store.currentSessionId) {
    loadMarket()
    startPolling()
  }
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.market-workspace {
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
  align-items: center;
  gap: 8px;
}
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
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
.table-card :deep(.el-card__header) {
  padding: 10px 14px;
  background: var(--q-bg-tertiary, #161b22);
  border-bottom: 1px solid var(--q-border, #21262d);
}
.table-card :deep(.el-card__body) {
  flex: 1;
  padding: 0;
  overflow: hidden;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-title {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: var(--q-text-primary, #e6edf3);
}
.card-sub {
  font-size: 11px;
  color: var(--q-text-muted, #8b949e);
}

/* 表格行 */
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
:deep(.el-table .row-up) {
  background: rgba(63, 185, 80, 0.04);
}
:deep(.el-table .row-down) {
  background: rgba(248, 81, 73, 0.04);
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
.bid-color {
  color: #3fb950;
}
.ask-color {
  color: #f85149;
}
.change-tag {
  min-width: 70px;
  text-align: center;
  font-weight: 600;
}
</style>
