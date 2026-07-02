<template>
  <div class="replay-workspace">
    <template v-if="!store.currentSessionId">
      <el-empty description="请先创建会话" :image-size="120" />
    </template>
    <template v-else>
      <!-- 顶部说明 -->
      <div class="replay-header">
        <div class="header-left">
          <span class="header-title">Time Machine</span>
          <span class="header-sub">点击左侧时间节点恢复该时间点状态</span>
        </div>
        <div class="header-right">
          <span class="event-count">事件: {{ timeline.length }}</span>
          <el-button size="small" :icon="Refresh" @click="loadTimeline" :loading="loading">刷新</el-button>
        </div>
      </div>

      <!-- 主体：左侧时间线 + 右侧恢复区 -->
      <div class="replay-body">
        <!-- 左侧 Timeline -->
        <div class="timeline-panel">
          <div class="panel-title">Timeline</div>
          <div class="timeline-scroll">
            <el-timeline v-if="timeline.length > 0">
              <el-timeline-item
                v-for="(evt, idx) in timeline"
                :key="idx"
                :timestamp="evt.ts"
                :type="timelineType(evt.event_type)"
                :hollow="!evt.restorable"
                placement="top"
                @click="onSelectEvent(evt)"
              >
                <div class="timeline-node" :class="{ active: selectedTs === evt.ts }">
                  <div class="node-type" :class="`type-${evt.event_type}`">
                    {{ evt.event_type }}
                  </div>
                  <div class="node-summary">{{ eventSummary(evt) }}</div>
                  <el-tag v-if="evt.restorable" type="success" size="small" effect="plain">可恢复</el-tag>
                </div>
              </el-timeline-item>
            </el-timeline>
            <el-empty v-else description="暂无事件" :image-size="60" />
          </div>
        </div>

        <!-- 右侧恢复区 -->
        <div class="restore-panel">
          <template v-if="!snapshot">
            <el-empty description="选择一个时间节点以恢复状态" :image-size="120" />
          </template>
          <template v-else>
            <!-- 账户状态卡片 -->
            <el-card class="account-card" shadow="never">
              <template #header>
                <div class="card-header">
                  <span class="card-title">账户状态 @ {{ selectedTs }}</span>
                  <el-tag type="info" size="small" effect="dark">Snapshot</el-tag>
                </div>
              </template>
              <div class="account-grid">
                <div class="account-item">
                  <div class="account-label">Cash</div>
                  <div class="account-value">{{ formatNum(snapshot.cash) }}</div>
                </div>
                <div class="account-item">
                  <div class="account-label">Total Value</div>
                  <div class="account-value text-info">{{ formatNum(snapshot.total_value ?? snapshot.equity) }}</div>
                </div>
                <div class="account-item">
                  <div class="account-label">Realized PnL</div>
                  <div class="account-value" :class="pnlClass(snapshot.realized_pnl)">
                    {{ formatNum(snapshot.realized_pnl) }}
                  </div>
                </div>
                <div class="account-item">
                  <div class="account-label">Unrealized PnL</div>
                  <div class="account-value" :class="pnlClass(snapshot.unrealized_pnl)">
                    {{ formatNum(snapshot.unrealized_pnl) }}
                  </div>
                </div>
              </div>
            </el-card>

            <!-- 持仓表格 -->
            <el-card class="positions-card" shadow="never">
              <template #header>
                <div class="card-header">
                  <span class="card-title">持仓 Positions</span>
                  <span class="card-sub">{{ snapshot.positions?.length ?? 0 }} positions</span>
                </div>
              </template>
              <el-table
                :data="snapshot.positions || []"
                size="small"
                stripe
                empty-text="该时间点无持仓"
              >
                <el-table-column prop="symbol" label="Symbol" min-width="110" />
                <el-table-column prop="direction" label="Side" min-width="70">
                  <template #default="{ row }">
                    <el-tag :type="row.direction === 'long' ? 'success' : 'danger'" size="small" effect="dark">
                      {{ row.direction || row.side || '-' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="quantity" label="Qty" min-width="80" align="right">
                  <template #default="{ row }">
                    <span class="num">{{ formatNum(row.quantity) }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="entry_price" label="Entry" min-width="90" align="right">
                  <template #default="{ row }">
                    <span class="num">{{ formatNum(row.entry_price) }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="current_price" label="Current" min-width="90" align="right">
                  <template #default="{ row }">
                    <span class="num">{{ formatNum(row.current_price) }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="market_value" label="Mkt Value" min-width="110" align="right">
                  <template #default="{ row }">
                    <span class="num">{{ formatNum(row.market_value) }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="unrealized_pnl" label="Unrealized PnL" min-width="120" align="right">
                  <template #default="{ row }">
                    <span class="num" :class="pnlClass(row.unrealized_pnl)">{{ formatNum(row.unrealized_pnl) }}</span>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>

            <!-- Equity Curve（截至该时间点） -->
            <el-card class="equity-card" shadow="never">
              <template #header>
                <div class="card-header">
                  <span class="card-title">Equity Curve（截至该时间点）</span>
                  <span class="card-sub">{{ snapshotEquity.length }} points</span>
                </div>
              </template>
              <v-chart :option="equityOption" autoresize class="equity-chart" />
            </el-card>
          </template>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { useTradingStore } from '@/stores/trading'
import { tradingApi, type ReplayTimelineEvent } from '@/api/trading'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])

const store = useTradingStore()

const timeline = ref<ReplayTimelineEvent[]>([])
const snapshot = ref<any>(null)
const snapshotEquity = ref<any[]>([])
const selectedTs = ref<string>('')
const loading = ref(false)

// ---- 格式化 ----
function formatNum(v: number | undefined | null): string {
  if (v == null) return '-'
  return Number(v).toLocaleString('en-US', { maximumFractionDigits: 2 })
}
function pnlClass(v: number | undefined | null): string {
  if (v == null || v === 0) return ''
  return v > 0 ? 'text-success' : 'text-danger'
}

// ---- Timeline 类型 ----
function timelineType(type: string): 'primary' | 'success' | 'info' {
  if (type === 'order') return 'primary'
  if (type === 'trade') return 'success'
  return 'info'
}

function eventSummary(evt: ReplayTimelineEvent): string {
  const t = evt.event_type
  if (t === 'order') {
    return `${evt.side || ''} ${evt.quantity || evt.qty || ''} ${evt.symbol || ''}`.trim() || 'Order'
  }
  if (t === 'trade') {
    return `${evt.symbol || ''} @ ${evt.price ?? ''}`.trim() || 'Trade'
  }
  if (t === 'snapshot') {
    return `Equity: ${formatNum(evt.total_value ?? evt.equity)}`
  }
  return t
}

// ---- Equity Curve 图表 ----
const equityOption = computed(() => {
  const curve = snapshotEquity.value
  if (!curve.length) return {}
  const times = curve.map((p: any) => p.time || p.ts)
  const equity = curve.map((p: any) => p.total_value ?? p.equity)

  return {
    backgroundColor: 'transparent',
    animation: false,
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#161b22',
      borderColor: '#21262d',
      textStyle: { color: '#e6edf3', fontSize: 12, fontFamily: 'SF Mono, monospace' },
      formatter: (params: any) => {
        if (!params?.length) return ''
        const idx = params[0].dataIndex
        const point = curve[idx]
        let html = `<div style="font-weight:600;margin-bottom:4px">${point.time || point.ts}</div>`
        html += `<span style="color:#58a6ff">●</span> Equity: ${params[0].value.toLocaleString('en-US', { maximumFractionDigits: 2 })}`
        return html
      },
    },
    grid: { left: 60, right: 20, top: 20, bottom: 30 },
    xAxis: {
      type: 'category',
      data: times,
      axisLine: { lineStyle: { color: '#21262d' } },
      axisLabel: { color: '#8b949e', fontSize: 10, fontFamily: 'SF Mono, monospace' },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      scale: true,
      axisLine: { show: false },
      axisLabel: {
        color: '#8b949e',
        fontSize: 10,
        fontFamily: 'SF Mono, monospace',
        formatter: (v: number) => {
          if (Math.abs(v) >= 1_000_000) return (v / 1_000_000).toFixed(1) + 'M'
          if (Math.abs(v) >= 1_000) return (v / 1_000).toFixed(0) + 'K'
          return String(v)
        },
      },
      splitLine: { lineStyle: { color: '#21262d', type: 'dashed' } },
    },
    series: [
      {
        name: 'Equity',
        type: 'line',
        data: equity,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: '#58a6ff', width: 1.5 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(88,166,255,0.2)' },
              { offset: 1, color: 'rgba(88,166,255,0)' },
            ],
          },
        },
      },
    ],
  }
})

// ---- 数据加载 ----
async function loadTimeline() {
  if (!store.currentSessionId) return
  loading.value = true
  try {
    const res = await tradingApi.getReplayTimeline(store.currentSessionId)
    timeline.value = res.timeline || []
    if (timeline.value.length > 0 && !selectedTs.value) {
      // 默认不选中，等待用户点击
    }
  } catch (e: any) {
    console.error('loadTimeline error', e)
    ElMessage.error('时间线加载失败: ' + (e?.message || ''))
  } finally {
    loading.value = false
  }
}

async function onSelectEvent(evt: ReplayTimelineEvent) {
  if (!evt.restorable) {
    ElMessage.warning('该事件不可恢复')
    return
  }
  selectedTs.value = evt.ts
  loading.value = true
  try {
    const res = await tradingApi.restoreReplay(store.currentSessionId, evt.ts)
    snapshot.value = res
    // 尝试获取截至该时间点的快照曲线
    snapshotEquity.value = res.equity_curve || res.curve || []
    // 如果返回中没有曲线，则使用 getReplaySnapshot 获取
    if (snapshotEquity.value.length === 0) {
      try {
        const snap = await tradingApi.getReplaySnapshot(store.currentSessionId, evt.ts)
        snapshotEquity.value = snap?.equity_curve || snap?.curve || []
      } catch {
        // 静默处理
      }
    }
  } catch (e: any) {
    console.error('restoreReplay error', e)
    ElMessage.error('恢复失败: ' + (e?.message || ''))
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadTimeline()
})
</script>

<style scoped>
.replay-workspace {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 12px;
  font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', 'JetBrains Mono', ui-monospace, monospace;
}

/* 顶部 */
.replay-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--q-bg-tertiary, #161b22);
  border: 1px solid var(--q-border, #21262d);
  border-radius: 6px;
  flex-shrink: 0;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.header-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--q-text-primary, #e6edf3);
  letter-spacing: 0.5px;
}
.header-sub {
  font-size: 12px;
  color: var(--q-text-muted, #8b949e);
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.event-count {
  font-size: 11px;
  color: var(--q-text-muted, #8b949e);
}

/* 主体 */
.replay-body {
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: 12px;
  flex: 1;
  min-height: 0;
}

/* 左侧时间线 */
.timeline-panel {
  display: flex;
  flex-direction: column;
  background: var(--q-bg-secondary, #0d1117);
  border: 1px solid var(--q-border, #21262d);
  border-radius: 6px;
  overflow: hidden;
}
.panel-title {
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.5px;
  color: var(--q-text-primary, #e6edf3);
  background: var(--q-bg-tertiary, #161b22);
  border-bottom: 1px solid var(--q-border, #21262d);
}
.timeline-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
}

/* Timeline 节点 */
:deep(.el-timeline) {
  padding-left: 8px;
}
:deep(.el-timeline-item__timestamp) {
  color: var(--q-text-muted, #8b949e);
  font-size: 11px;
  font-family: 'SF Mono, monospace';
}
.timeline-node {
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 4px;
  transition: background 0.15s;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.timeline-node:hover {
  background: var(--q-bg-tertiary, #161b22);
}
.timeline-node.active {
  background: rgba(88, 166, 255, 0.1);
  border-left: 2px solid #58a6ff;
  padding-left: 8px;
}
.node-type {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.node-type.type-order {
  color: #58a6ff;
}
.node-type.type-trade {
  color: #3fb950;
}
.node-type.type-snapshot {
  color: #8b949e;
}
.node-summary {
  font-size: 11px;
  color: var(--q-text-secondary, #8b949e);
}

/* 右侧恢复区 */
.restore-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  min-height: 0;
}

/* 账户卡片 */
.account-card {
  background: var(--q-bg-secondary, #0d1117);
  border: 1px solid var(--q-border, #21262d);
  border-radius: 6px;
  flex-shrink: 0;
}
.account-card :deep(.el-card__header) {
  padding: 10px 14px;
  background: var(--q-bg-tertiary, #161b22);
  border-bottom: 1px solid var(--q-border, #21262d);
}
.account-card :deep(.el-card__body) {
  padding: 14px;
}
.account-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.account-item {
  text-align: left;
}
.account-label {
  font-size: 11px;
  color: var(--q-text-muted, #8b949e);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}
.account-value {
  font-size: 18px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--q-text-primary, #e6edf3);
}

/* 持仓卡片 */
.positions-card {
  background: var(--q-bg-secondary, #0d1117);
  border: 1px solid var(--q-border, #21262d);
  border-radius: 6px;
  flex-shrink: 0;
}
.positions-card :deep(.el-card__header) {
  padding: 10px 14px;
  background: var(--q-bg-tertiary, #161b22);
  border-bottom: 1px solid var(--q-border, #21262d);
}
.positions-card :deep(.el-card__body) {
  padding: 0;
}

/* 表格暗色主题 */
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

/* Equity 卡片 */
.equity-card {
  background: var(--q-bg-secondary, #0d1117);
  border: 1px solid var(--q-border, #21262d);
  border-radius: 6px;
  flex: 1;
  min-height: 280px;
}
.equity-card :deep(.el-card__header) {
  padding: 10px 14px;
  background: var(--q-bg-tertiary, #161b22);
  border-bottom: 1px solid var(--q-border, #21262d);
}
.equity-card :deep(.el-card__body) {
  padding: 12px;
  height: calc(100% - 42px);
}
.equity-chart {
  width: 100%;
  height: 240px;
}

/* 卡片通用 */
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

/* 颜色 */
.text-success { color: #3fb950; }
.text-danger { color: #f85149; }
.text-warning { color: #d29922; }
.text-info { color: #58a6ff; }
.num {
  font-variant-numeric: tabular-nums;
  font-feature-settings: 'tnum';
}

/* 响应式 */
@media (max-width: 1100px) {
  .replay-body {
    grid-template-columns: 1fr;
  }
  .account-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
