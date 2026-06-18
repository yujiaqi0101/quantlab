<template>
  <div class="observe-replay">
    <div class="page-header">
      <div>
        <h1 class="page-title">Replay Engine</h1>
        <span class="page-subtitle">还原历史现场 · 理解系统正在发生什么</span>
      </div>
      <div class="header-actions">
        <el-tag :type="statusTagType" size="large">{{ snapshot?.status || 'IDLE' }}</el-tag>
        <el-button :icon="Refresh" @click="refreshAll" :loading="loading">刷新</el-button>
      </div>
    </div>

    <el-row :gutter="16">
      <!-- 左侧：会话列表 -->
      <el-col :span="6">
        <el-card shadow="hover" class="sessions-card">
          <template #header>
            <div class="card-header">
              <span>会话列表</span>
              <el-button size="small" type="primary" :icon="Plus" @click="showCreateDialog = true">新建</el-button>
            </div>
          </template>
          <el-table
            :data="sessions"
            stripe
            size="small"
            highlight-current-row
            @current-change="onSelectSession"
            :row-class-name="sessionRowClass"
          >
            <el-table-column prop="session_id" label="Session ID" min-width="140">
              <template #default="{ row }">
                <div class="session-id-cell">
                  <span class="session-id-text">{{ row.session_id }}</span>
                  <el-tag v-if="row.is_active" type="success" size="small">活跃</el-tag>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="strategy" label="策略" width="100" />
            <el-table-column prop="symbol" label="标的" width="80" />
            <el-table-column prop="n_events" label="事件" width="60" align="center" />
          </el-table>
          <el-empty v-if="sessions.length === 0" description="暂无会话" :image-size="60" />
        </el-card>
      </el-col>

      <!-- 中间：事件时间线 + 控制器 -->
      <el-col :span="11">
        <el-card shadow="hover" class="timeline-card">
          <template #header>
            <div class="card-header">
              <span>事件时间线</span>
              <div v-if="snapshot" class="progress-info">
                <span>{{ snapshot.position }} / {{ snapshot.total_events }}</span>
                <span class="progress-pct">({{ (snapshot.progress * 100).toFixed(1) }}%)</span>
              </div>
            </div>
          </template>

          <!-- 播放控制器 -->
          <div class="replay-controls" v-if="snapshot">
            <el-button-group>
              <el-button
                size="small"
                :icon="VideoPause"
                @click="onPrev"
                :disabled="snapshot.position === 0"
              >上一个</el-button>
              <el-button
                v-if="snapshot.status === 'PLAYING'"
                size="small"
                :icon="VideoPause"
                @click="onPause"
              >暂停</el-button>
              <el-button
                v-else-if="snapshot.status === 'PAUSED'"
                size="small"
                :icon="VideoPlay"
                @click="onResume"
              >恢复</el-button>
              <el-button
                v-else
                size="small"
                :icon="VideoPlay"
                @click="onPlay"
                :disabled="snapshot.total_events === 0"
              >播放</el-button>
              <el-button
                size="small"
                :icon="VideoPlay"
                @click="onNext"
                :disabled="snapshot.position >= snapshot.total_events"
              >下一个</el-button>
              <el-button
                size="small"
                :icon="CircleClose"
                @click="onStop"
                :disabled="snapshot.status === 'IDLE'"
              >停止</el-button>
            </el-button-group>

            <el-select v-model="speed" size="small" style="width: 100px" @change="onSpeedChange">
              <el-option label="0.5x" :value="0.5" />
              <el-option label="1x" :value="1" />
              <el-option label="5x" :value="5" />
              <el-option label="10x" :value="10" />
              <el-option label="50x" :value="50" />
              <el-option label="100x" :value="100" />
            </el-select>

            <el-slider
              v-model="seekPosition"
              :max="snapshot.total_events"
              :step="1"
              style="flex: 1; margin-left: 16px"
              @change="onSeek"
            />
          </div>

          <el-progress
            v-if="snapshot"
            :percentage="snapshot.progress * 100"
            :status="progressStatus"
            :show-text="false"
            style="margin-bottom: 12px"
          />

          <!-- 事件列表 -->
          <div class="events-list" v-if="events.length > 0">
            <div
              v-for="(event, idx) in events"
              :key="event.event_id"
              class="event-item"
              :class="{
                'event-current': idx === snapshot?.position - 1,
                'event-past': idx < (snapshot?.position || 0) - 1,
              }"
              @click="onSelectEvent(event)"
            >
              <div class="event-time">{{ formatTime(event.timestamp) }}</div>
              <div class="event-type" :class="`event-type-${eventCategory(event.event_type)}`">
                {{ event.event_type }}
              </div>
              <div class="event-summary">{{ eventSummary(event) }}</div>
              <div class="event-trace" v-if="event.trace_id">{{ event.trace_id }}</div>
            </div>
          </div>
          <el-empty v-else description="选择会话并加载事件" :image-size="60" />
        </el-card>
      </el-col>

      <!-- 右侧：事件详情 + 当前状态 -->
      <el-col :span="7">
        <!-- 当前状态 -->
        <el-card shadow="hover" class="state-card" v-if="snapshot && snapshot.state">
          <template #header><span>当前状态</span></template>
          <div class="state-grid">
            <div class="state-item">
              <div class="state-label">权益</div>
              <div class="state-value">${{ formatNum(snapshot.state.equity) }}</div>
            </div>
            <div class="state-item">
              <div class="state-label">现金</div>
              <div class="state-value">${{ formatNum(snapshot.state.cash) }}</div>
            </div>
            <div class="state-item">
              <div class="state-label">总盈亏</div>
              <div class="state-value" :class="pnlClass(snapshot.state.total_pnl)">
                {{ formatPnl(snapshot.state.total_pnl) }}
              </div>
            </div>
            <div class="state-item">
              <div class="state-label">已实现</div>
              <div class="state-value" :class="pnlClass(snapshot.state.realized_pnl)">
                {{ formatPnl(snapshot.state.realized_pnl) }}
              </div>
            </div>
            <div class="state-item">
              <div class="state-label">未实现</div>
              <div class="state-value" :class="pnlClass(snapshot.state.unrealized_pnl)">
                {{ formatPnl(snapshot.state.unrealized_pnl) }}
              </div>
            </div>
            <div class="state-item">
              <div class="state-label">持仓数</div>
              <div class="state-value">{{ snapshot.state.n_positions }}</div>
            </div>
          </div>

          <!-- 持仓 -->
          <div class="state-section" v-if="snapshot.state.positions.length > 0">
            <div class="state-section-title">持仓</div>
            <el-table :data="snapshot.state.positions" size="small" stripe>
              <el-table-column prop="symbol" label="标的" width="80" />
              <el-table-column prop="qty" label="数量" width="70" />
              <el-table-column prop="avg_price" label="均价" width="80">
                <template #default="{ row }">{{ formatNum(row.avg_price) }}</template>
              </el-table-column>
              <el-table-column prop="current_price" label="现价" width="80">
                <template #default="{ row }">{{ formatNum(row.current_price) }}</template>
              </el-table-column>
              <el-table-column prop="unrealized_pnl" label="未实现盈亏" width="100">
                <template #default="{ row }">
                  <span :class="pnlClass(row.unrealized_pnl)">{{ formatPnl(row.unrealized_pnl) }}</span>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <!-- 订单 -->
          <div class="state-section" v-if="snapshot.state.orders.length > 0">
            <div class="state-section-title">订单 ({{ snapshot.state.orders.length }})</div>
            <el-table :data="snapshot.state.orders.slice(-5)" size="small" stripe>
              <el-table-column prop="symbol" label="标的" width="70" />
              <el-table-column prop="side" label="方向" width="60" />
              <el-table-column prop="qty" label="数量" width="60" />
              <el-table-column prop="status" label="状态" width="80">
                <template #default="{ row }">
                  <el-tag :type="orderStatusType(row.status)" size="small">{{ row.status }}</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>

        <!-- 事件详情 -->
        <el-card shadow="hover" class="detail-card" v-if="selectedEvent">
          <template #header>
            <div class="card-header">
              <span>事件详情</span>
              <el-button size="small" type="primary" @click="onAnalyzeTrace" v-if="selectedEvent.trace_id">
                分析链路
              </el-button>
            </div>
          </template>
          <div class="event-detail">
            <div class="detail-row">
              <span class="detail-label">Event ID:</span>
              <span class="detail-value">{{ selectedEvent.event_id }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">类型:</span>
              <span class="detail-value">{{ selectedEvent.event_type }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">时间:</span>
              <span class="detail-value">{{ formatTime(selectedEvent.timestamp) }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">来源:</span>
              <span class="detail-value">{{ selectedEvent.source }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Trace ID:</span>
              <span class="detail-value">{{ selectedEvent.trace_id }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">Session:</span>
              <span class="detail-value">{{ selectedEvent.session_id }}</span>
            </div>
            <div class="detail-payload">
              <div class="detail-label">Payload:</div>
              <pre>{{ JSON.stringify(selectedEvent.payload, null, 2) }}</pre>
            </div>
          </div>
        </el-card>

        <!-- 交易链路分析 -->
        <el-card shadow="hover" class="chain-card" v-if="tradeChain">
          <template #header>
            <div class="card-header">
              <span>交易链路</span>
              <el-button size="small" @click="tradeChain = null">关闭</el-button>
            </div>
          </template>
          <div class="chain-summary">{{ tradeChain.summary }}</div>
          <div class="chain-meta">
            <span>Symbol: {{ tradeChain.symbol || '-' }}</span>
            <span>耗时: {{ tradeChain.duration_ms }}ms</span>
            <span v-if="tradeChain.pnl !== null" :class="pnlClass(tradeChain.pnl)">
              PnL: {{ formatPnl(tradeChain.pnl) }}
            </span>
          </div>
          <el-timeline class="chain-timeline">
            <el-timeline-item
              v-for="node in tradeChain.nodes"
              :key="node.event_id"
              :timestamp="formatTime(node.timestamp)"
              :type="chainNodeType(node.event_type)"
            >
              <strong>{{ node.event_type }}</strong>
              <div class="chain-node-summary">{{ eventSummary(node) }}</div>
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>

    <!-- 新建会话对话框 -->
    <el-dialog v-model="showCreateDialog" title="新建会话" width="400px">
      <el-form :model="newSession" label-width="80px">
        <el-form-item label="策略">
          <el-input v-model="newSession.strategy" placeholder="如 momentum" />
        </el-form-item>
        <el-form-item label="标的">
          <el-input v-model="newSession.symbol" placeholder="如 BTCUSDT" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="onCreateSession">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Plus, VideoPlay, VideoPause, CircleClose } from '@element-plus/icons-vue'
import { observeApi, type SessionInfo, type StoredEvent, type ReplaySnapshot, type TradeChain } from '@/api/observe'

// 状态
const loading = ref(false)
const sessions = ref<SessionInfo[]>([])
const events = ref<StoredEvent[]>([])
const snapshot = ref<ReplaySnapshot | null>(null)
const selectedEvent = ref<StoredEvent | null>(null)
const tradeChain = ref<TradeChain | null>(null)
const speed = ref(1)
const seekPosition = ref(0)
const showCreateDialog = ref(false)
const newSession = ref({ strategy: '', symbol: '' })

// 轮询定时器
let pollTimer: ReturnType<typeof setInterval> | null = null

// 计算属性
const statusTagType = computed(() => {
  const s = snapshot.value?.status
  if (s === 'PLAYING') return 'success'
  if (s === 'PAUSED') return 'warning'
  if (s === 'STOPPED' || s === 'FINISHED') return 'info'
  return 'info'
})

const progressStatus = computed(() => {
  if (!snapshot.value) return ''
  if (snapshot.value.progress >= 1) return 'success'
  return ''
})

// 格式化
function formatNum(n: number | undefined | null): string {
  if (n === undefined || n === null) return '0.00'
  return Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatPnl(n: number | undefined | null): string {
  if (n === undefined || n === null) return '$0.00'
  const v = Number(n)
  return (v >= 0 ? '+$' : '-$') + Math.abs(v).toFixed(2)
}

function formatTime(ts: number): string {
  if (!ts) return ''
  return new Date(ts).toLocaleString('zh-CN', { hour12: false })
}

function pnlClass(n: number | undefined | null): string {
  const v = Number(n || 0)
  if (v > 0) return 'pnl-positive'
  if (v < 0) return 'pnl-negative'
  return ''
}

// 事件分类
function eventCategory(type: string): string {
  const t = type.toUpperCase()
  if (t.includes('MARKET')) return 'market'
  if (t.includes('SIGNAL')) return 'signal'
  if (t.includes('ORDER')) return 'order'
  if (t.includes('FILL')) return 'fill'
  if (t.includes('POSITION')) return 'position'
  if (t.includes('RISK') || t.includes('KILL')) return 'risk'
  return 'system'
}

function eventSummary(event: StoredEvent): string {
  const p = event.payload
  const t = event.event_type.toUpperCase()
  if (t.includes('MARKET')) {
    return `${p.symbol || ''} @ ${p.price || ''}`
  }
  if (t.includes('SIGNAL')) {
    return `${p.side || p.signal || ''} ${p.symbol || ''} score=${p.score ?? p.strength ?? ''}`
  }
  if (t.includes('ORDER')) {
    return `${p.side || ''} ${p.qty ?? p.quantity ?? ''} ${p.symbol || ''} @ ${p.price || ''}`
  }
  if (t.includes('FILL')) {
    return `filled ${p.qty ?? p.filled_qty ?? ''} ${p.symbol || ''} @ ${p.price ?? p.filled_price ?? ''}`
  }
  if (t.includes('POSITION')) {
    return `${p.symbol || ''} qty=${p.qty ?? p.quantity ?? ''}`
  }
  if (t.includes('RISK') || t.includes('KILL')) {
    return p.message || p.reason || t
  }
  return p.message || t
}

function orderStatusType(status: string): 'success' | 'warning' | 'info' | 'danger' {
  switch (status?.toUpperCase()) {
    case 'FILLED': return 'success'
    case 'SUBMITTED':
    case 'CREATED': return 'warning'
    case 'CANCELLED':
    case 'REJECTED': return 'danger'
    default: return 'info'
  }
}

function chainNodeType(type: string): 'primary' | 'success' | 'warning' | 'danger' | 'info' {
  const t = type.toUpperCase()
  if (t.includes('SIGNAL')) return 'primary'
  if (t.includes('ORDER')) return 'warning'
  if (t.includes('FILL')) return 'success'
  if (t.includes('RISK') || t.includes('KILL')) return 'danger'
  return 'info'
}

function sessionRowClass({ row }: { row: SessionInfo }): string {
  return row.is_active ? 'row-active' : ''
}

// 操作
async function refreshAll() {
  loading.value = true
  try {
    const [sessRes, snap] = await Promise.all([
      observeApi.listSessions({ limit: 100 }),
      observeApi.replaySnapshot(),
    ])
    sessions.value = sessRes.sessions
    snapshot.value = snap
    seekPosition.value = snap.position
    if (snap.session_id) {
      await loadEvents()
    }
  } catch (e: any) {
    ElMessage.error('加载失败: ' + (e.message || e))
  } finally {
    loading.value = false
  }
}

async function onSelectSession(row: SessionInfo | null) {
  if (!row) return
  try {
    const n = await observeApi.replayLoad(row.session_id)
    ElMessage.success(`已加载 ${n.n_events} 个事件`)
    snapshot.value = await observeApi.replaySnapshot()
    seekPosition.value = 0
    await loadEvents()
  } catch (e: any) {
    ElMessage.error('加载会话失败: ' + (e.message || e))
  }
}

async function loadEvents() {
  const res = await observeApi.replayEvents({ start: 0, limit: 500 })
  events.value = res.events
}

async function onPlay() {
  try {
    snapshot.value = await observeApi.replayPlay(speed.value)
    startPolling()
  } catch (e: any) {
    ElMessage.error('播放失败: ' + (e.message || e))
  }
}

async function onPause() {
  try {
    snapshot.value = await observeApi.replayPause()
    stopPolling()
  } catch (e: any) {
    ElMessage.error('暂停失败: ' + (e.message || e))
  }
}

async function onResume() {
  try {
    snapshot.value = await observeApi.replayResume()
    startPolling()
  } catch (e: any) {
    ElMessage.error('恢复失败: ' + (e.message || e))
  }
}

async function onStop() {
  try {
    snapshot.value = await observeApi.replayStop()
    seekPosition.value = 0
    stopPolling()
  } catch (e: any) {
    ElMessage.error('停止失败: ' + (e.message || e))
  }
}

async function onNext() {
  try {
    snapshot.value = await observeApi.replayNext()
    seekPosition.value = snapshot.value.position
  } catch (e: any) {
    ElMessage.error('前进失败: ' + (e.message || e))
  }
}

async function onPrev() {
  try {
    snapshot.value = await observeApi.replayPrev()
    seekPosition.value = snapshot.value.position
  } catch (e: any) {
    ElMessage.error('后退失败: ' + (e.message || e))
  }
}

async function onSeek(pos: number) {
  try {
    snapshot.value = await observeApi.replaySeek(pos)
  } catch (e: any) {
    ElMessage.error('跳转失败: ' + (e.message || e))
  }
}

async function onSpeedChange() {
  // 速度变化时如果正在播放，重新 play
  if (snapshot.value?.status === 'PLAYING') {
    try {
      snapshot.value = await observeApi.replayPlay(speed.value)
    } catch (e: any) {
      ElMessage.error('速度调整失败: ' + (e.message || e))
    }
  }
}

function onSelectEvent(event: StoredEvent) {
  selectedEvent.value = event
}

async function onAnalyzeTrace() {
  if (!selectedEvent.value?.trace_id) return
  try {
    tradeChain.value = await observeApi.rcaByTrace(selectedEvent.value.trace_id)
  } catch (e: any) {
    ElMessage.error('链路分析失败: ' + (e.message || e))
  }
}

async function onCreateSession() {
  try {
    const session = await observeApi.createSession({
      strategy: newSession.value.strategy,
      symbol: newSession.value.symbol,
    })
    ElMessage.success(`会话已创建: ${session.session_id}`)
    showCreateDialog.value = false
    newSession.value = { strategy: '', symbol: '' }
    await refreshAll()
  } catch (e: any) {
    ElMessage.error('创建会话失败: ' + (e.message || e))
  }
}

// 轮询
function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    try {
      snapshot.value = await observeApi.replaySnapshot()
      seekPosition.value = snapshot.value.position
      if (snapshot.value.status !== 'PLAYING') {
        stopPolling()
      }
    } catch (e) {
      stopPolling()
    }
  }, 1000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

onMounted(() => {
  refreshAll()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.observe-replay { padding: 20px; }
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-title { margin: 0; font-size: 24px; font-weight: 700; }
.page-subtitle { color: var(--q-text-muted, #909399); font-size: 13px; }
.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.progress-info {
  font-size: 13px;
  color: var(--q-text-muted, #909399);
}
.progress-pct { margin-left: 8px; }

.sessions-card :deep(.row-active) {
  background-color: var(--el-color-success-light-9, #f0f9eb);
}
.session-id-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.session-id-text {
  font-size: 12px;
  font-family: monospace;
}

/* 控制器 */
.replay-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

/* 事件列表 */
.events-list {
  max-height: 500px;
  overflow-y: auto;
  border: 1px solid var(--el-border-color-lighter, #ebeef5);
  border-radius: 4px;
}
.event-item {
  display: grid;
  grid-template-columns: 80px 100px 1fr 80px;
  gap: 8px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--el-border-color-lighter, #ebeef5);
  cursor: pointer;
  font-size: 12px;
  transition: background-color 0.2s;
}
.event-item:hover {
  background-color: var(--el-fill-color-light, #f5f7fa);
}
.event-item.event-current {
  background-color: var(--el-color-primary-light-9, #ecf5ff);
  border-left: 3px solid var(--el-color-primary, #409eff);
}
.event-item.event-past {
  opacity: 0.6;
}
.event-time {
  color: var(--q-text-muted, #909399);
  font-family: monospace;
}
.event-type {
  font-weight: 600;
}
.event-type-market { color: #909399; }
.event-type-signal { color: #409eff; }
.event-type-order { color: #e6a23c; }
.event-type-fill { color: #67c23a; }
.event-type-position { color: #9b59b6; }
.event-type-risk { color: #f56c6c; }
.event-type-system { color: #909399; }
.event-summary {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.event-trace {
  color: var(--q-text-muted, #909399);
  font-family: monospace;
  font-size: 11px;
}

/* 状态卡片 */
.state-card { margin-bottom: 16px; }
.state-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.state-item {
  text-align: center;
}
.state-label {
  font-size: 12px;
  color: var(--q-text-muted, #909399);
  margin-bottom: 4px;
}
.state-value {
  font-size: 16px;
  font-weight: 600;
}
.state-section {
  margin-top: 12px;
}
.state-section-title {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--q-text-muted, #909399);
}

/* 事件详情 */
.detail-card { margin-bottom: 16px; }
.event-detail {
  font-size: 13px;
}
.detail-row {
  display: flex;
  margin-bottom: 6px;
}
.detail-label {
  width: 80px;
  color: var(--q-text-muted, #909399);
}
.detail-value {
  flex: 1;
  font-family: monospace;
  word-break: break-all;
}
.detail-payload {
  margin-top: 12px;
}
.detail-payload pre {
  background: var(--el-fill-color-darker, #f5f7fa);
  padding: 8px;
  border-radius: 4px;
  font-size: 12px;
  max-height: 200px;
  overflow-y: auto;
  margin: 4px 0 0 0;
}

/* 交易链路 */
.chain-card { margin-bottom: 16px; }
.chain-summary {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
}
.chain-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--q-text-muted, #909399);
  margin-bottom: 12px;
}
.chain-timeline {
  max-height: 300px;
  overflow-y: auto;
}
.chain-node-summary {
  font-size: 12px;
  color: var(--q-text-muted, #909399);
  margin-top: 2px;
}

/* PnL 颜色 */
.pnl-positive { color: var(--el-color-success, #67c23a); }
.pnl-negative { color: var(--el-color-danger, #f56c6c); }
</style>
