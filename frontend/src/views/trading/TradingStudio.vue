<template>
  <div class="trading-studio">
    <!-- 顶部栏 -->
    <header class="studio-topbar">
      <div class="topbar-left">
        <span class="logo-icon">Q</span>
        <span class="topbar-title">Trading Studio</span>
        <el-tag size="small" :type="modeTagType" effect="dark">{{ modeLabel }}</el-tag>
      </div>
      <div class="topbar-center">
        <el-radio-group v-model="store.mode" size="small" @change="onModeChange">
          <el-radio-button value="paper">Paper</el-radio-button>
          <el-radio-button value="live">Live</el-radio-button>
          <el-radio-button value="replay">Replay</el-radio-button>
        </el-radio-group>
      </div>
      <div class="topbar-right">
        <el-select
          v-model="store.currentSessionId"
          size="small"
          placeholder="选择会话"
          style="width: 220px"
          @change="onSessionChange"
        >
          <el-option
            v-for="s in store.sessions"
            :key="s.sid"
            :label="`${s.sid} (${s.status})`"
            :value="s.sid"
          />
        </el-select>
        <el-button size="small" type="primary" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon> 新建
        </el-button>
        <el-button
          size="small"
          :type="store.sessionStatus?.status === 'running' ? 'warning' : 'success'"
          @click="toggleSession"
          :disabled="!store.currentSessionId"
        >
          {{ store.sessionStatus?.status === 'running' ? '暂停' : '启动' }}
        </el-button>
        <el-button size="small" type="danger" @click="handleKillSwitch" :disabled="!store.currentSessionId">
          KILL
        </el-button>
      </div>
    </header>

    <!-- 会话状态栏 -->
    <div class="session-header">
      <template v-if="store.overview">
        <div class="metric">
          <span class="metric-label">PnL</span>
          <span class="metric-value" :class="pnlClass(store.overview.today_pnl)">
            {{ formatNum(store.overview.today_pnl) }}
          </span>
        </div>
        <div class="metric">
          <span class="metric-label">Return</span>
          <span class="metric-value" :class="pnlClass(store.overview.today_return)">
            {{ formatPct(store.overview.today_return) }}
          </span>
        </div>
        <div class="metric">
          <span class="metric-label">Cash</span>
          <span class="metric-value">{{ formatNum(store.overview.cash) }}</span>
        </div>
        <div class="metric">
          <span class="metric-label">Equity</span>
          <span class="metric-value">{{ formatNum(store.overview.equity) }}</span>
        </div>
        <div class="metric">
          <span class="metric-label">Exposure</span>
          <span class="metric-value">{{ formatPct(store.overview.exposure) }}</span>
        </div>
        <div class="metric">
          <span class="metric-label">Drawdown</span>
          <span class="metric-value text-danger">{{ formatPct(store.overview.max_drawdown) }}</span>
        </div>
        <div class="metric">
          <span class="metric-label">Positions</span>
          <span class="metric-value">{{ store.overview.n_positions }}</span>
        </div>
        <div class="metric">
          <span class="metric-label">Open Orders</span>
          <span class="metric-value">{{ store.overview.n_open_orders }}</span>
        </div>
      </template>
      <template v-else>
        <span class="metric-muted">无活跃会话，点击"新建"创建</span>
      </template>
    </div>

    <!-- 主体 -->
    <div class="studio-body">
      <!-- 左侧 Workspace 导航 -->
      <aside class="workspace-nav">
        <div
          v-for="ws in workspaces"
          :key="ws.name"
          class="nav-item"
          :class="{ active: isActive(ws.path) }"
          @click="navigate(ws.path)"
        >
          <el-icon><component :is="ws.icon" /></el-icon>
          <span class="nav-label">{{ ws.label }}</span>
        </div>
      </aside>

      <!-- 主内容区 -->
      <main class="workspace-main">
        <router-view />
      </main>
    </div>

    <!-- 底部状态栏 -->
    <footer class="status-bar">
      <span class="status-item">
        <span class="status-dot" :class="store.currentSessionId ? 'online' : 'offline'"></span>
        {{ store.currentSessionId ? 'Connected' : 'Disconnected' }}
      </span>
      <span class="status-item">Mode: {{ modeLabel }}</span>
      <span class="status-item" v-if="store.currentSessionId">
        Session: {{ store.currentSessionId }}
      </span>
      <span class="status-item" v-if="store.sessionStatus">
        Status: {{ store.sessionStatus.status }}
      </span>
      <span class="status-item status-right">QuantLab Trading Studio v1.0</span>
    </footer>

    <!-- 创建会话对话框 -->
    <el-dialog v-model="showCreateDialog" title="新建交易会话" width="500px">
      <el-form :model="createForm" label-width="120px" size="default">
        <el-form-item label="模式">
          <el-radio-group v-model="createForm.mode">
            <el-radio value="paper">Paper 模拟</el-radio>
            <el-radio value="live">Live 实盘</el-radio>
            <el-radio value="replay">Replay 回放</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="策略">
          <el-select v-model="createForm.strategy_id" placeholder="选择策略（可选）" clearable filterable>
            <el-option
              v-for="s in strategies"
              :key="s.strategy_id"
              :label="s.name"
              :value="s.strategy_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="初始资金">
          <el-input-number v-model="createForm.initial_capital" :min="1000" :step="10000" />
        </el-form-item>
        <el-form-item label="交易标的">
          <el-input
            v-model="symbolsInput"
            placeholder="逗号分隔，如 000001.SZ,000002.SZ"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="creating">创建并启动</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import {
  Plus, DataLine, Histogram, Switch, List, Wallet,
  TrendCharts, Warning, Notebook, VideoPlay,
} from '@element-plus/icons-vue'
import { useTradingStore } from '@/stores/trading'
import { tradingApi, type StrategyInfo } from '@/api/trading'

const router = useRouter()
const route = useRoute()
const store = useTradingStore()

// ---- Workspace 导航 ----
const workspaces = [
  { name: 'overview', label: 'Overview', path: '/trading/overview', icon: DataLine },
  { name: 'market', label: 'Market', path: '/trading/market', icon: Histogram },
  { name: 'signals', label: 'Signals', path: '/trading/signals', icon: Switch },
  { name: 'orders', label: 'Orders', path: '/trading/orders', icon: List },
  { name: 'positions', label: 'Positions', path: '/trading/positions', icon: Wallet },
  { name: 'portfolio', label: 'Portfolio', path: '/trading/portfolio', icon: TrendCharts },
  { name: 'risk', label: 'Risk', path: '/trading/risk', icon: Warning },
  { name: 'journal', label: 'Journal', path: '/trading/journal', icon: Notebook },
  { name: 'replay', label: 'Replay', path: '/trading/replay', icon: VideoPlay },
]

// ---- 创建会话对话框 ----
const showCreateDialog = ref(false)
const creating = ref(false)
const strategies = ref<StrategyInfo[]>([])
const symbolsInput = ref('')
const createForm = ref({
  mode: 'paper' as 'paper' | 'live' | 'replay',
  strategy_id: '',
  initial_capital: 1000000,
})

// ---- 计算属性 ----
const modeLabel = computed(() => {
  const m: Record<string, string> = { paper: 'PAPER', live: 'LIVE', replay: 'REPLAY' }
  return m[store.mode] || 'PAPER'
})
const modeTagType = computed(() => {
  const t: Record<string, string> = { paper: 'warning', live: 'danger', replay: 'info' }
  return t[store.mode] || 'warning'
})

// ---- 方法 ----
function formatNum(v: number | undefined): string {
  if (v == null) return '-'
  return v.toLocaleString('en-US', { maximumFractionDigits: 2 })
}
function formatPct(v: number | undefined): string {
  if (v == null) return '-'
  return (v * 100).toFixed(2) + '%'
}
function pnlClass(v: number | undefined): string {
  if (v == null) return ''
  return v > 0 ? 'text-success' : v < 0 ? 'text-danger' : ''
}

function isActive(path: string): boolean {
  return route.path.startsWith(path)
}
function navigate(path: string) {
  router.push(path)
}

function onModeChange(m: string) {
  store.switchMode(m as any)
  store.fetchSessions(m as any)
}

async function onSessionChange(sid: string) {
  if (sid) {
    await Promise.all([store.fetchOverview(sid), store.fetchStatus(sid)])
  }
}

async function toggleSession() {
  if (!store.currentSessionId) return
  if (store.sessionStatus?.status === 'running') {
    await store.pauseSession(store.currentSessionId)
  } else {
    await store.startSession(store.currentSessionId)
  }
}

async function handleKillSwitch() {
  try {
    await ElMessageBox.confirm('确定要触发 Kill Switch 吗？将取消所有订单并停止会话。', '危险操作', {
      type: 'warning',
      confirmButtonText: '触发 KILL SWITCH',
      cancelButtonText: '取消',
    })
    await store.killSwitch()
  } catch {}
}

async function handleCreate() {
  creating.value = true
  try {
    const symbols = symbolsInput.value
      ? symbolsInput.value.split(',').map(s => s.trim()).filter(Boolean)
      : []
    await store.createSession({
      mode: createForm.value.mode,
      strategy_id: createForm.value.strategy_id,
      initial_capital: createForm.value.initial_capital,
      symbols,
    })
    showCreateDialog.value = false
    symbolsInput.value = ''
  } finally {
    creating.value = false
  }
}

async function loadStrategies() {
  try {
    const res = await tradingApi.listStrategies()
    strategies.value = res.strategies || []
  } catch {}
}

// ---- 生命周期 ----
onMounted(async () => {
  await Promise.all([store.fetchSessions(), loadStrategies()])
  if (store.currentSessionId) {
    await Promise.all([store.fetchOverview(), store.fetchStatus()])
  }
  store.startPolling(5000)
})

onUnmounted(() => {
  store.stopPolling()
})
</script>

<style scoped>
.trading-studio {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--q-bg-primary, #0a0e17);
  color: var(--q-text-primary, #e6edf3);
  font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', 'JetBrains Mono', ui-monospace, monospace;
}

/* 顶部栏 */
.studio-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 16px;
  background: var(--q-bg-secondary, #0d1117);
  border-bottom: 1px solid var(--q-border, #21262d);
  flex-shrink: 0;
}
.topbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.logo-icon {
  width: 28px;
  height: 28px;
  background: linear-gradient(135deg, #58a6ff 0%, #1f6feb 100%);
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 16px;
  color: #fff;
}
.topbar-title {
  font-size: 15px;
  font-weight: 700;
  letter-spacing: -0.3px;
}
.topbar-center {
  display: flex;
  align-items: center;
  gap: 8px;
}
.topbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 会话状态栏 */
.session-header {
  display: flex;
  align-items: center;
  gap: 24px;
  height: 40px;
  padding: 0 16px;
  background: var(--q-bg-tertiary, #161b22);
  border-bottom: 1px solid var(--q-border, #21262d);
  overflow-x: auto;
  flex-shrink: 0;
}
.metric {
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}
.metric-label {
  font-size: 11px;
  color: var(--q-text-muted, #8b949e);
  text-transform: uppercase;
}
.metric-value {
  font-size: 13px;
  font-weight: 600;
}
.metric-muted {
  color: var(--q-text-muted, #8b949e);
  font-size: 13px;
}
.text-success { color: #3fb950; }
.text-danger { color: #f85149; }
.text-warning { color: #d29922; }

/* 主体 */
.studio-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* 左侧导航 */
.workspace-nav {
  width: 180px;
  background: var(--q-bg-secondary, #0d1117);
  border-right: 1px solid var(--q-border, #21262d);
  padding: 8px 0;
  overflow-y: auto;
  flex-shrink: 0;
}
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 38px;
  padding: 0 16px;
  cursor: pointer;
  color: var(--q-text-secondary, #8b949e);
  font-size: 13px;
  transition: all 0.15s;
  border-left: 2px solid transparent;
}
.nav-item:hover {
  background: var(--q-bg-tertiary, #161b22);
  color: var(--q-text-primary, #e6edf3);
}
.nav-item.active {
  background: var(--q-bg-tertiary, #161b22);
  color: #58a6ff;
  border-left-color: #58a6ff;
}
.nav-label {
  white-space: nowrap;
}

/* 主内容区 */
.workspace-main {
  flex: 1;
  overflow: auto;
  padding: 16px;
  background: var(--q-bg-primary, #0a0e17);
}

/* 底部状态栏 */
.status-bar {
  display: flex;
  align-items: center;
  gap: 20px;
  height: 28px;
  padding: 0 16px;
  background: var(--q-bg-secondary, #0d1117);
  border-top: 1px solid var(--q-border, #21262d);
  font-size: 11px;
  color: var(--q-text-muted, #8b949e);
  flex-shrink: 0;
}
.status-item {
  display: flex;
  align-items: center;
  gap: 4px;
}
.status-right {
  margin-left: auto;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.status-dot.online {
  background: #3fb950;
  box-shadow: 0 0 4px #3fb950;
}
.status-dot.offline {
  background: #f85149;
}

/* 亮色主题 */
html.light .trading-studio {
  background: #f6f8fa;
  color: #24292f;
}
html.light .studio-topbar,
html.light .workspace-nav,
html.light .status-bar {
  background: #ffffff;
  border-color: #d0d7de;
}
html.light .session-header {
  background: #f6f8fa;
  border-color: #d0d7de;
}
html.light .nav-item.active {
  background: #0969da1a;
  color: #0969da;
  border-left-color: #0969da;
}
html.light .workspace-main {
  background: #f6f8fa;
}
</style>
