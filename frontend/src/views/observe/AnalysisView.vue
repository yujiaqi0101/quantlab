<template>
  <div class="analysis-view">
    <el-row :gutter="16">
      <!-- 左侧：会话 + 亏损交易列表 -->
      <el-col :span="6">
        <el-card shadow="never" class="left-panel">
          <template #header>
            <div class="card-header">
              <span>会话</span>
              <el-button size="small" @click="loadSessions">刷新</el-button>
            </div>
          </template>
          <el-table
            :data="sessions"
            size="small"
            highlight-current-row
            @current-change="onSelectSession"
            height="200"
          >
            <el-table-column prop="session_id" label="Session" width="140" />
            <el-table-column prop="n_events" label="事件" width="60" />
            <el-table-column prop="strategy" label="策略" />
          </el-table>
        </el-card>

        <el-card shadow="never" class="left-panel" v-if="currentSessionId">
          <template #header>
            <div class="card-header">
              <span>亏损交易 ({{ lossReports.length }})</span>
              <el-button size="small" @click="loadLosses">刷新</el-button>
            </div>
          </template>
          <el-table
            :data="lossReports"
            size="small"
            highlight-current-row
            @current-change="onSelectLoss"
            height="300"
          >
            <el-table-column label="标的" width="90">
              <template #default="{ row }">{{ row.trace.symbol }}</template>
            </el-table-column>
            <el-table-column label="盈亏" width="90">
              <template #default="{ row }">
                <span :class="pnlClass(row.trace.pnl)">
                  {{ formatNum(row.trace.pnl) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="%" width="70">
              <template #default="{ row }">
                <span :class="pnlClass(row.trace.pnl_pct)">
                  {{ row.trace.pnl_pct?.toFixed(2) }}%
                </span>
              </template>
            </el-table-column>
            <el-table-column label="根因">
              <template #default="{ row }">
                <el-tag
                  v-for="c in row.causes.slice(0, 2)"
                  :key="c.type"
                  :type="causeTagType(c)"
                  size="small"
                  style="margin-right: 4px"
                >
                  {{ causeLabel(c) }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card shadow="never" class="left-panel" v-if="currentSessionId">
          <template #header>
            <div class="card-header">
              <span>异常检测 ({{ anomalies.length }})</span>
              <el-button size="small" @click="loadAnomalies">检测</el-button>
            </div>
          </template>
          <div class="anomaly-list">
            <el-alert
              v-for="(a, i) in anomalies"
              :key="i"
              :type="anomalyAlertType(a.severity)"
              :title="a.title"
              :description="a.description"
              :closable="false"
              show-icon
              style="margin-bottom: 6px"
            />
            <el-empty v-if="anomalies.length === 0" description="无异常" :image-size="60" />
          </div>
        </el-card>
      </el-col>

      <!-- 中间：交易链路图 -->
      <el-col :span="11">
        <el-card shadow="never" v-if="currentReport">
          <template #header>
            <div class="card-header">
              <span>交易链路 - {{ currentReport.trace.symbol }}</span>
              <div>
                <el-tag :type="currentReport.trace.is_loss ? 'danger' : 'success'" size="small">
                  {{ currentReport.trace.pnl?.toFixed(2) }}
                  ({{ currentReport.trace.pnl_pct?.toFixed(2) }}%)
                </el-tag>
              </div>
            </div>
          </template>

          <!-- 链路图 -->
          <div class="trace-flow">
            <div
              v-for="(node, i) in traceNodes"
              :key="i"
              class="trace-node"
              :class="`node-${node.kind}`"
            >
              <div class="node-time">{{ formatTime(node.timestamp) }}</div>
              <div class="node-icon">{{ node.icon }}</div>
              <div class="node-title">{{ node.title }}</div>
              <div class="node-detail">{{ node.detail }}</div>
              <div class="node-arrow" v-if="i < traceNodes.length - 1">↓</div>
            </div>
          </div>

          <!-- 关键指标 -->
          <el-descriptions :column="4" size="small" border class="metrics-grid">
            <el-descriptions-item label="入场价">
              {{ currentReport.trace.entry_price || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="出场价">
              {{ currentReport.trace.exit_price || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="持仓时长">
              {{ formatDuration(currentReport.trace.holding_ms) }}
            </el-descriptions-item>
            <el-descriptions-item label="市场变动">
              <span :class="pnlClass(currentReport.trace.market_change)">
                {{ (currentReport.trace.market_change * 100).toFixed(2) }}%
              </span>
            </el-descriptions-item>
            <el-descriptions-item label="入场滑点" v-if="currentReport.trace.entry">
              {{ currentReport.trace.entry.slippage_bps.toFixed(1) }} bps
            </el-descriptions-item>
            <el-descriptions-item label="出场滑点" v-if="currentReport.trace.exit">
              {{ currentReport.trace.exit.slippage_bps.toFixed(1) }} bps
            </el-descriptions-item>
            <el-descriptions-item label="手续费">
              {{ currentReport.trace.fee.toFixed(2) }}
            </el-descriptions-item>
            <el-descriptions-item label="风险事件">
              {{ currentReport.trace.n_risk_events }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-empty v-else description="选择一笔交易查看链路" />
      </el-col>

      <!-- 右侧：根因分析 + 解释 -->
      <el-col :span="7">
        <el-card shadow="never" v-if="currentReport">
          <template #header>根因分析</template>

          <!-- 根因列表 -->
          <div class="causes-list">
            <div
              v-for="(c, i) in currentReport.causes"
              :key="i"
              class="cause-item"
              :class="`severity-${c.severity.toLowerCase()}`"
            >
              <div class="cause-header">
                <el-tag :type="causeTagType(c)" size="small">
                  {{ causeLabel(c) }}
                </el-tag>
                <span class="cause-confidence">
                  置信度 {{ (c.confidence * 100).toFixed(0) }}%
                </span>
              </div>
              <div class="cause-title">{{ c.title }}</div>
              <div class="cause-desc">{{ c.description }}</div>
              <ul class="cause-evidence">
                <li v-for="(e, j) in c.evidence" :key="j">{{ e }}</li>
              </ul>
            </div>
            <el-empty
              v-if="currentReport.causes.length === 0"
              description="无根因（非亏损或数据不足）"
              :image-size="60"
            />
          </div>
        </el-card>

        <el-card shadow="never" v-if="currentReport?.explanation" class="explain-panel">
          <template #header>解释引擎</template>
          <div class="explain-summary">{{ currentReport.explanation.summary }}</div>
          <div
            v-for="(p, i) in currentReport.explanation.paragraphs"
            :key="i"
            class="explain-paragraph"
          >
            <pre>{{ p }}</pre>
          </div>
          <div v-if="currentReport.explanation.suggestions.length > 0" class="suggestions">
            <div class="suggestions-title">改进建议：</div>
            <ul>
              <li v-for="(s, i) in currentReport.explanation.suggestions" :key="i">{{ s }}</li>
            </ul>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { observeApi } from '@/api/observe'
import type {
  SessionInfo,
  TraceReport,
  Anomaly,
  RootCause,
} from '@/api/observe'

// 会话
const sessions = ref<SessionInfo[]>([])
const currentSessionId = ref('')

// 报告
const lossReports = ref<TraceReport[]>([])
const currentReport = ref<TraceReport | null>(null)

// 异常
const anomalies = ref<Anomaly[]>([])

// 加载会话
async function loadSessions() {
  try {
    const data = await observeApi.listSessions()
    sessions.value = data.sessions
  } catch (e: any) {
    ElMessage.error('加载会话失败: ' + e.message)
  }
}

function onSelectSession(row: SessionInfo | null) {
  if (!row) return
  currentSessionId.value = row.session_id
  currentReport.value = null
  lossReports.value = []
  anomalies.value = []
  loadLosses()
  loadAnomalies()
}

// 加载亏损交易
async function loadLosses() {
  if (!currentSessionId.value) return
  try {
    const data = await observeApi.analysisLosses(currentSessionId.value, 20)
    lossReports.value = data.reports
  } catch (e: any) {
    ElMessage.error('加载亏损交易失败: ' + e.message)
  }
}

function onSelectLoss(row: TraceReport | null) {
  currentReport.value = row
}

// 加载异常
async function loadAnomalies() {
  if (!currentSessionId.value) return
  try {
    const data = await observeApi.analysisAnomalies(currentSessionId.value)
    anomalies.value = data.anomalies
  } catch (e: any) {
    ElMessage.error('异常检测失败: ' + e.message)
  }
}

// 链路节点（用于可视化）
const traceNodes = computed(() => {
  if (!currentReport.value) return []
  const t = currentReport.value.trace
  const nodes: Array<{
    kind: string
    timestamp: number
    icon: string
    title: string
    detail: string
  }> = []

  if (t.entry?.signal_event) {
    nodes.push({
      kind: 'signal',
      timestamp: t.entry.signal_event.timestamp,
      icon: 'S',
      title: 'SignalEvent',
      detail: `${t.entry.signal_strategy || '策略'} ${t.entry.side} 分数${t.entry.signal_score ?? '-'}`,
    })
  }
  if (t.entry?.order_event) {
    nodes.push({
      kind: 'order',
      timestamp: t.entry.order_event.timestamp,
      icon: 'O',
      title: 'OrderEvent',
      detail: `${t.entry.side} ${t.entry.qty} @ ${t.entry.order_price ?? t.entry.price}`,
    })
  }
  if (t.entry?.fill_event) {
    nodes.push({
      kind: 'fill',
      timestamp: t.entry.fill_event.timestamp,
      icon: 'F',
      title: 'FillEvent (入场)',
      detail: `成交 ${t.entry.qty} @ ${t.entry.price}`,
    })
  }
  if (t.risk_events.length > 0) {
    for (const re of t.risk_events) {
      nodes.push({
        kind: 'risk',
        timestamp: re.timestamp,
        icon: '!',
        title: 'RiskEvent',
        detail: re.payload.message || re.payload.reason || re.event_type,
      })
    }
  }
  if (t.exit?.fill_event) {
    nodes.push({
      kind: 'exit',
      timestamp: t.exit.fill_event.timestamp,
      icon: 'X',
      title: 'FillEvent (出场)',
      detail: `成交 ${t.exit.qty} @ ${t.exit.price}`,
    })
  }
  return nodes.sort((a, b) => a.timestamp - b.timestamp)
})

// 工具函数
function formatTime(ts: number): string {
  if (!ts) return '-'
  return new Date(ts).toLocaleTimeString('zh-CN', { hour12: false })
}

function formatNum(n: number | null | undefined): string {
  if (n == null) return '-'
  return n.toFixed(2)
}

function formatDuration(ms: number): string {
  if (!ms) return '-'
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}秒`
  if (ms < 3600000) return `${(ms / 60000).toFixed(1)}分钟`
  return `${(ms / 3600000).toFixed(1)}小时`
}

function pnlClass(v: number | null | undefined): string {
  if (v == null) return ''
  if (v > 0) return 'text-success'
  if (v < 0) return 'text-danger'
  return ''
}

function causeLabel(c: RootCause): string {
  const map: Record<string, string> = {
    SIGNAL_ERROR: '信号错误',
    EXECUTION_ERROR: '执行错误',
    RISK_EXIT: '风控退出',
    MARKET_SHOCK: '市场冲击',
    OVEREXPOSURE: '仓位过大',
    UNKNOWN: '未知',
  }
  return map[c.type] || c.type
}

function causeTagType(c: RootCause): 'info' | 'warning' | 'danger' {
  if (c.severity === 'CRITICAL') return 'danger'
  if (c.severity === 'WARNING') return 'warning'
  return 'info'
}

function anomalyAlertType(severity: string): 'info' | 'warning' | 'error' {
  if (severity === 'CRITICAL') return 'error'
  if (severity === 'WARNING') return 'warning'
  return 'info'
}

onMounted(() => {
  loadSessions()
})
</script>

<style scoped>
.analysis-view {
  padding: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.left-panel {
  margin-bottom: 12px;
}

.anomaly-list {
  max-height: 250px;
  overflow-y: auto;
}

/* 链路图 */
.trace-flow {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 0;
  background: #fafafa;
  border-radius: 4px;
  margin-bottom: 12px;
}

.trace-node {
  text-align: center;
  position: relative;
  padding: 8px 16px;
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 4px;
  min-width: 240px;
  margin-bottom: 4px;
}

.node-time {
  font-size: 11px;
  color: #999;
}

.node-icon {
  width: 28px;
  height: 28px;
  line-height: 28px;
  border-radius: 50%;
  margin: 4px auto;
  font-weight: bold;
  color: #fff;
  background: #909399;
}

.node-signal .node-icon { background: #409eff; }
.node-order .node-icon { background: #e6a23c; }
.node-fill .node-icon { background: #67c23a; }
.node-exit .node-icon { background: #f56c6c; }
.node-risk .node-icon { background: #f56c6c; }

.node-title {
  font-weight: 600;
  font-size: 13px;
}

.node-detail {
  font-size: 12px;
  color: #666;
  margin-top: 2px;
}

.node-arrow {
  color: #c0c4cc;
  font-size: 14px;
  margin: 2px 0;
}

.metrics-grid {
  margin-top: 8px;
}

/* 根因 */
.causes-list {
  max-height: 320px;
  overflow-y: auto;
}

.cause-item {
  padding: 10px;
  border-left: 3px solid #909399;
  background: #fafafa;
  margin-bottom: 8px;
  border-radius: 0 4px 4px 0;
}

.cause-item.severity-critical {
  border-left-color: #f56c6c;
  background: #fef0f0;
}

.cause-item.severity-warning {
  border-left-color: #e6a23c;
  background: #fdf6ec;
}

.cause-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.cause-confidence {
  font-size: 12px;
  color: #909399;
}

.cause-title {
  font-weight: 600;
  font-size: 13px;
}

.cause-desc {
  font-size: 12px;
  color: #666;
  margin: 2px 0;
}

.cause-evidence {
  margin: 4px 0 0 0;
  padding-left: 18px;
  font-size: 12px;
  color: #606266;
}

.cause-evidence li {
  list-style: disc;
  margin: 2px 0;
}

/* 解释 */
.explain-panel {
  margin-top: 12px;
}

.explain-summary {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
  padding: 8px;
  background: #ecf5ff;
  border-radius: 4px;
  margin-bottom: 8px;
}

.explain-paragraph {
  margin: 6px 0;
}

.explain-paragraph pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: 12px;
  color: #606266;
  margin: 0;
}

.suggestions {
  margin-top: 12px;
  padding: 8px;
  background: #f0f9eb;
  border-radius: 4px;
}

.suggestions-title {
  font-weight: 600;
  font-size: 13px;
  color: #67c23a;
  margin-bottom: 4px;
}

.suggestions ul {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
}

.text-success { color: #67c23a; }
.text-danger { color: #f56c6c; }
</style>
