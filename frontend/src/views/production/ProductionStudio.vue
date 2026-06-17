<template>
  <div class="production-studio">
    <!-- Header -->
    <div class="studio-header">
      <div class="header-left">
        <h1 class="studio-title">Production Studio</h1>
        <span class="studio-subtitle">监控一台交易机器</span>
      </div>
      <div class="header-right">
        <el-tag :type="runtimeStateType" effect="dark" size="large">
          {{ runtimeStateText }}
        </el-tag>
        <el-tag v-if="killSwitchActive" type="danger" effect="dark" size="large">
          KILL SWITCH ACTIVE
        </el-tag>
        <el-button-group>
          <el-button
            :icon="VideoPlay"
            :disabled="runtimeState === 'RUNNING'"
            @click="startRuntime"
            size="small"
          >Start</el-button>
          <el-button
            :icon="VideoPause"
            :disabled="runtimeState !== 'RUNNING'"
            @click="pauseRuntime"
            size="small"
          >Pause</el-button>
          <el-button
            :icon="CircleClose"
            :disabled="runtimeState === 'STOPPED'"
            @click="stopRuntime"
            size="small"
          >Stop</el-button>
        </el-button-group>
        <el-button
          type="danger"
          :icon="WarningFilled"
          @click="triggerKillSwitch"
          :disabled="killSwitchActive"
          size="small"
        >KILL SWITCH</el-button>
      </div>
    </div>

    <!-- Tabs -->
    <el-tabs v-model="activeTab" class="studio-tabs">
      <!-- Overview -->
      <el-tab-pane label="Overview" name="overview">
        <div class="metrics-grid">
          <el-card class="metric-card" shadow="hover">
            <template #header><span>Runtime</span></template>
            <div class="metric-content">
              <div class="metric-row">
                <span class="metric-label">State</span>
                <el-tag :type="runtimeStateType" size="small">{{ runtimeStateText }}</el-tag>
              </div>
              <div class="metric-row">
                <span class="metric-label">Ticks</span>
                <span class="metric-value">{{ overview.runtime?.tick_count ?? 0 }}</span>
              </div>
              <div class="metric-row">
                <span class="metric-label">Errors</span>
                <span class="metric-value" :class="{ 'text-danger': (overview.runtime?.error_count ?? 0) > 0 }">
                  {{ overview.runtime?.error_count ?? 0 }}
                </span>
              </div>
              <div class="metric-row">
                <span class="metric-label">Readonly</span>
                <el-tag :type="overview.runtime?.readonly ? 'danger' : 'success'" size="small">
                  {{ overview.runtime?.readonly ? 'YES' : 'NO' }}
                </el-tag>
              </div>
            </div>
          </el-card>

          <el-card class="metric-card" shadow="hover">
            <template #header><span>Capital</span></template>
            <div class="metric-content">
              <div class="metric-row">
                <span class="metric-label">Total</span>
                <span class="metric-value">${{ formatNum(overview.capital?.total_capital ?? 0) }}</span>
              </div>
              <div class="metric-row">
                <span class="metric-label">Allocated</span>
                <span class="metric-value">${{ formatNum(overview.capital?.total_allocated ?? 0) }}</span>
              </div>
              <div class="metric-row">
                <span class="metric-label">Available</span>
                <span class="metric-value">${{ formatNum(overview.capital?.total_available ?? 0) }}</span>
              </div>
            </div>
          </el-card>

          <el-card class="metric-card" shadow="hover">
            <template #header><span>Health</span></template>
            <div class="metric-content">
              <div class="metric-row">
                <span class="metric-label">All Alive</span>
                <el-tag :type="overview.health?.all_alive ? 'success' : 'danger'" size="small">
                  {{ overview.health?.all_alive ? 'YES' : 'NO' }}
                </el-tag>
              </div>
              <div class="metric-row">
                <span class="metric-label">Components</span>
                <span class="metric-value">{{ overview.health?.components?.length ?? 0 }}</span>
              </div>
              <div class="metric-row">
                <span class="metric-label">Watchdog Alerts</span>
                <span class="metric-value" :class="{ 'text-warning': overview.watchdog_alerts > 0 }">
                  {{ overview.watchdog_alerts ?? 0 }}
                </span>
              </div>
            </div>
          </el-card>

          <el-card class="metric-card" shadow="hover">
            <template #header><span>Self-Healing</span></template>
            <div class="metric-content">
              <div class="metric-row">
                <span class="metric-label">Total Heals</span>
                <span class="metric-value">{{ overview.self_healing?.total_heals ?? 0 }}</span>
              </div>
              <div class="metric-row">
                <span class="metric-label">Success Rate</span>
                <span class="metric-value">{{ formatPct(overview.self_healing?.success_rate ?? 0) }}</span>
              </div>
            </div>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- Execution Health -->
      <el-tab-pane label="Execution Health" name="execution">
        <el-card shadow="never">
          <template #header>
            <div class="card-header-flex">
              <span>Heartbeat Monitor</span>
              <el-tag :type="healthData.all_alive ? 'success' : 'danger'" size="small">
                {{ healthData.all_alive ? 'ALL ALIVE' : 'TIMEOUT DETECTED' }}
              </el-tag>
            </div>
          </template>
          <el-table :data="healthData.heartbeat" stripe size="small">
            <el-table-column prop="component" label="Component" />
            <el-table-column prop="beat_count" label="Beats" width="100" />
            <el-table-column label="Status" width="120">
              <template #default="{ row }">
                <el-tag :type="row.alive ? 'success' : 'danger'" size="small">
                  {{ row.alive ? 'ALIVE' : 'DEAD' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="Last Beat" width="180">
              <template #default="{ row }">
                {{ formatTime(row.last_beat) }}
              </template>
            </el-table-column>
            <el-table-column label="Lag (s)" width="100">
              <template #default="{ row }">
                <span :class="{ 'text-warning': row.seconds_since_beat > 10, 'text-danger': row.seconds_since_beat > 15 }">
                  {{ row.seconds_since_beat.toFixed(1) }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card shadow="never" style="margin-top: 16px">
          <template #header><span>Watchdog Alerts</span></template>
          <el-table :data="healthData.watchdog_alerts" stripe size="small">
            <el-table-column prop="level" label="Level" width="100">
              <template #default="{ row }">
                <el-tag :type="row.level === 'CRITICAL' ? 'danger' : 'warning'" size="small">
                  {{ row.level }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="category" label="Category" width="150" />
            <el-table-column prop="message" label="Message" />
            <el-table-column label="Time" width="180">
              <template #default="{ row }">{{ formatTime(row.timestamp / 1000) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- Risk -->
      <el-tab-pane label="Risk" name="risk">
        <el-card shadow="never">
          <template #header>
            <div class="card-header-flex">
              <span>Risk Engine</span>
              <el-tag :type="killSwitchActive ? 'danger' : 'success'" effect="dark">
                {{ killSwitchActive ? 'KILL SWITCH ACTIVE' : 'NORMAL' }}
              </el-tag>
            </div>
          </template>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="Kill Switch">
              <el-tag :type="killSwitchActive ? 'danger' : 'success'" size="small">
                {{ killSwitchActive ? 'ACTIVE' : 'INACTIVE' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="Rejects Count">
              {{ riskData.rejects?.length ?? 0 }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card shadow="never" style="margin-top: 16px" v-if="riskData.rejects?.length > 0">
          <template #header><span>Recent Rejects</span></template>
          <el-table :data="riskData.rejects" stripe size="small">
            <el-table-column prop="reason" label="Reason" />
            <el-table-column prop="symbol" label="Symbol" width="120" />
            <el-table-column prop="qty" label="Qty" width="100" />
            <el-table-column label="Time" width="180">
              <template #default="{ row }">{{ formatTime(row.timestamp / 1000) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- Positions -->
      <el-tab-pane label="Positions" name="positions">
        <el-card shadow="never">
          <template #header><span>Portfolio Positions</span></template>
          <el-table :data="positionsData" stripe size="small">
            <el-table-column prop="symbol" label="Symbol" width="120" />
            <el-table-column prop="qty" label="Qty" width="100" />
            <el-table-column prop="avg_price" label="Avg Price" width="120">
              <template #default="{ row }">{{ formatNum(row.avg_price) }}</template>
            </el-table-column>
            <el-table-column prop="market_price" label="Market Price" width="120">
              <template #default="{ row }">{{ formatNum(row.market_price) }}</template>
            </el-table-column>
            <el-table-column prop="market_value" label="Market Value" width="140">
              <template #default="{ row }">${{ formatNum(row.market_value) }}</template>
            </el-table-column>
            <el-table-column label="Unrealized PnL" width="140">
              <template #default="{ row }">
                <span :class="row.unrealized_pnl >= 0 ? 'text-success' : 'text-danger'">
                  ${{ formatNum(row.unrealized_pnl) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="strategy_id" label="Strategy" width="120" />
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- Orders -->
      <el-tab-pane label="Orders" name="orders">
        <el-card shadow="never">
          <template #header><span>Recent Orders</span></template>
          <el-table :data="ordersData" stripe size="small">
            <el-table-column prop="id" label="Order ID" width="180" />
            <el-table-column prop="symbol" label="Symbol" width="100" />
            <el-table-column prop="side" label="Side" width="80">
              <template #default="{ row }">
                <el-tag :type="row.side === 'BUY' ? 'success' : 'danger'" size="small">{{ row.side }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="quantity" label="Qty" width="80" />
            <el-table-column prop="filled_qty" label="Filled" width="80" />
            <el-table-column label="State" width="120">
              <template #default="{ row }">
                <el-tag :type="orderStateType(row.state)" size="small">{{ row.state }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="signal_id" label="Signal ID" width="150" />
            <el-table-column prop="strategy_id" label="Strategy" width="100" />
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- PnL Attribution -->
      <el-tab-pane label="PnL Attribution" name="pnl">
        <el-card shadow="never">
          <template #header><span>Live PnL Attribution</span></template>
          <div class="pnl-grid">
            <div class="pnl-card">
              <div class="pnl-label">Total PnL</div>
              <div class="pnl-value" :class="pnlClass(pnlData.current?.total_pnl)">
                ${{ formatNum(pnlData.current?.total_pnl ?? 0) }}
              </div>
            </div>
            <div class="pnl-card">
              <div class="pnl-label">Market PnL</div>
              <div class="pnl-value" :class="pnlClass(pnlData.current?.market_pnl)">
                ${{ formatNum(pnlData.current?.market_pnl ?? 0) }}
              </div>
            </div>
            <div class="pnl-card">
              <div class="pnl-label">Strategy PnL</div>
              <div class="pnl-value" :class="pnlClass(pnlData.current?.strategy_pnl)">
                ${{ formatNum(pnlData.current?.strategy_pnl ?? 0) }}
              </div>
            </div>
            <div class="pnl-card">
              <div class="pnl-label">Execution PnL</div>
              <div class="pnl-value" :class="pnlClass(pnlData.current?.execution_pnl)">
                ${{ formatNum(pnlData.current?.execution_pnl ?? 0) }}
              </div>
            </div>
            <div class="pnl-card">
              <div class="pnl-label">Slippage Cost</div>
              <div class="pnl-value text-danger">
                -${{ formatNum(Math.abs(pnlData.current?.slippage_cost ?? 0)) }}
              </div>
            </div>
            <div class="pnl-card">
              <div class="pnl-label">Commission Cost</div>
              <div class="pnl-value text-danger">
                -${{ formatNum(Math.abs(pnlData.current?.commission_cost ?? 0)) }}
              </div>
            </div>
          </div>
        </el-card>
      </el-tab-pane>

      <!-- Journal -->
      <el-tab-pane label="Journal" name="journal">
        <el-card shadow="never">
          <template #header>
            <div class="card-header-flex">
              <span>Trade Journal</span>
              <el-select v-model="journalFilter" placeholder="Filter" size="small" style="width: 150px" clearable>
                <el-option label="All" value="" />
                <el-option label="Signal" value="SIGNAL" />
                <el-option label="Order" value="ORDER" />
                <el-option label="Fill" value="FILL" />
                <el-option label="Risk Alert" value="RISK_ALERT" />
                <el-option label="Kill Switch" value="KILL_SWITCH" />
                <el-option label="Recovery" value="RECOVERY" />
              </el-select>
            </div>
          </template>
          <el-table :data="journalData.entries" stripe size="small" max-height="500">
            <el-table-column label="Time" width="180">
              <template #default="{ row }">{{ formatTime(row.timestamp / 1000) }}</template>
            </el-table-column>
            <el-table-column prop="type" label="Type" width="130">
              <template #default="{ row }">
                <el-tag :type="journalTypeColor(row.type)" size="small">{{ row.type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="strategy_id" label="Strategy" width="100" />
            <el-table-column prop="symbol" label="Symbol" width="100" />
            <el-table-column prop="message" label="Message" show-overflow-tooltip />
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- System Status -->
      <el-tab-pane label="System Status" name="system">
        <el-card shadow="never">
          <template #header><span>Recovery Status</span></template>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="State Restorer">
              <el-tag :type="recoveryData.state_restorer ? 'success' : 'info'" size="small">
                {{ recoveryData.state_restorer ? 'READY' : 'NOT INIT' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="Order Recovery">
              <el-tag :type="recoveryData.order_recovery ? 'success' : 'info'" size="small">
                {{ recoveryData.order_recovery ? 'READY' : 'NOT INIT' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="Position Recovery">
              {{ recoveryData.position_recovery?.recovery_count ?? 0 }} recoveries
            </el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card shadow="never" style="margin-top: 16px">
          <template #header>
            <div class="card-header-flex">
              <span>Self-Healing History</span>
              <el-button type="primary" size="small" @click="refreshSelfHealing">Refresh</el-button>
            </div>
          </template>
          <el-descriptions :column="3" border size="small" style="margin-bottom: 12px">
            <el-descriptions-item label="Total Heals">{{ selfHealingData.stats?.total_heals ?? 0 }}</el-descriptions-item>
            <el-descriptions-item label="Successful">{{ selfHealingData.stats?.successful ?? 0 }}</el-descriptions-item>
            <el-descriptions-item label="Success Rate">{{ formatPct(selfHealingData.stats?.success_rate ?? 0) }}</el-descriptions-item>
          </el-descriptions>
          <el-table :data="selfHealingData.history" stripe size="small" max-height="300">
            <el-table-column label="Time" width="180">
              <template #default="{ row }">{{ formatTime(row.timestamp / 1000) }}</template>
            </el-table-column>
            <el-table-column prop="action" label="Action" width="200" />
            <el-table-column prop="reason" label="Reason" show-overflow-tooltip />
            <el-table-column label="Status" width="100">
              <template #default="{ row }">
                <el-tag :type="row.success ? 'success' : 'danger'" size="small">
                  {{ row.success ? 'OK' : 'FAIL' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card shadow="never" style="margin-top: 16px">
          <template #header>
            <div class="card-header-flex">
              <span>Replay Engine</span>
              <el-tag size="small">{{ replayData.state ?? 'IDLE' }}</el-tag>
            </div>
          </template>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="Position">{{ replayData.position ?? 0 }} / {{ replayData.total_events ?? 0 }}</el-descriptions-item>
            <el-descriptions-item label="Progress">{{ formatPct(replayData.progress ?? 0) }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { VideoPlay, VideoPause, CircleClose, WarningFilled } from '@element-plus/icons-vue'
import { api } from '@/utils/api'

const activeTab = ref('overview')
const overview = ref<any>({})
const healthData = ref<any>({ heartbeat: [], watchdog_alerts: [], all_alive: true })
const riskData = ref<any>({ rejects: [] })
const positionsData = ref<any[]>([])
const ordersData = ref<any[]>([])
const pnlData = ref<any>({})
const journalData = ref<any>({ entries: [] })
const journalFilter = ref('')
const recoveryData = ref<any>({})
const selfHealingData = ref<any>({ stats: {}, history: [] })
const replayData = ref<any>({})

let pollTimer: any = null

const runtimeState = computed(() => overview.value.runtime?.state ?? 'IDLE')
const killSwitchActive = computed(() => overview.value.kill_switch_active ?? false)

const runtimeStateText = computed(() => {
  const map: Record<string, string> = {
    IDLE: 'IDLE', RUNNING: 'RUNNING', PAUSED: 'PAUSED',
    STOPPING: 'STOPPING', STOPPED: 'STOPPED',
    READONLY: 'READONLY', RECOVERING: 'RECOVERING',
  }
  return map[runtimeState.value] || runtimeState.value
})

const runtimeStateType = computed(() => {
  const map: Record<string, string> = {
    RUNNING: 'success', PAUSED: 'warning', STOPPED: 'info',
    READONLY: 'danger', RECOVERING: 'warning', IDLE: 'info',
  }
  return map[runtimeState.value] || 'info'
})

function formatNum(n: number): string {
  if (!n) return '0'
  return n.toLocaleString('en-US', { maximumFractionDigits: 2 })
}

function formatPct(n: number): string {
  return (n * 100).toFixed(2) + '%'
}

function formatTime(ts: number): string {
  if (!ts) return '-'
  return new Date(ts * 1000).toLocaleString('en-US', { hour12: false })
}

function pnlClass(val: number): string {
  if (val > 0) return 'text-success'
  if (val < 0) return 'text-danger'
  return ''
}

function orderStateType(state: string): string {
  const map: Record<string, string> = {
    NEW: 'info', SUBMITTED: 'warning', PARTIALLY_FILLED: 'warning',
    FILLED: 'success', CANCELLED: 'info', REJECTED: 'danger',
  }
  return map[state] || 'info'
}

function journalTypeColor(type: string): string {
  const map: Record<string, string> = {
    SIGNAL: 'primary', ORDER: 'warning', FILL: 'success',
    RISK_ALERT: 'danger', KILL_SWITCH: 'danger',
    RECOVERY: 'info', SYSTEM: 'info', MANUAL: 'warning',
  }
  return map[type] || 'info'
}

async function fetchOverview() {
  try {
    const res = await api.get('/api/v1/production/status')
    overview.value = res.data
  } catch (e) { /* silent */ }
}

async function fetchHealth() {
  try {
    const res = await api.get('/api/v1/production/health')
    healthData.value = res.data
  } catch (e) { /* silent */ }
}

async function fetchRisk() {
  try {
    const res = await api.get('/api/v1/production/risk')
    riskData.value = res.data
  } catch (e) { /* silent */ }
}

async function fetchPnl() {
  try {
    const res = await api.get('/api/v1/production/pnl/attribution')
    pnlData.value = res.data
  } catch (e) { /* silent */ }
}

async function fetchJournal() {
  try {
    const params: any = { limit: 200 }
    if (journalFilter.value) params.type = journalFilter.value
    const res = await api.get('/api/v1/production/journal', { params })
    journalData.value = res.data
  } catch (e) { /* silent */ }
}

async function fetchRecovery() {
  try {
    const res = await api.get('/api/v1/production/recovery')
    recoveryData.value = res.data
  } catch (e) { /* silent */ }
}

async function refreshSelfHealing() {
  try {
    const res = await api.get('/api/v1/production/self-healing')
    selfHealingData.value = res.data
  } catch (e) { /* silent */ }
}

async function fetchReplay() {
  try {
    const res = await api.get('/api/v1/production/replay/status')
    replayData.value = res.data
  } catch (e) { /* silent */ }
}

async function fetchAll() {
  await Promise.all([
    fetchOverview(),
    fetchHealth(),
    fetchRisk(),
    fetchPnl(),
    fetchJournal(),
    fetchRecovery(),
    refreshSelfHealing(),
    fetchReplay(),
  ])
  // 从 overview 提取 positions 和 orders
  if (overview.value.capital?.portfolio?.positions) {
    positionsData.value = Object.values(overview.value.capital.portfolio.positions)
  }
}

async function startRuntime() {
  try {
    await api.post('/api/v1/production/runtime/start')
    ElMessage.success('Runtime started')
    fetchOverview()
  } catch (e) { ElMessage.error('Start failed') }
}

async function pauseRuntime() {
  try {
    await api.post('/api/v1/production/runtime/pause')
    ElMessage.success('Runtime paused')
    fetchOverview()
  } catch (e) { ElMessage.error('Pause failed') }
}

async function stopRuntime() {
  try {
    await api.post('/api/v1/production/runtime/stop')
    ElMessage.success('Runtime stopped')
    fetchOverview()
  } catch (e) { ElMessage.error('Stop failed') }
}

async function triggerKillSwitch() {
  try {
    await ElMessageBox.confirm(
      'This will STOP ALL STRATEGIES, CANCEL ALL ORDERS, and enable READONLY mode. Are you sure?',
      'KILL SWITCH CONFIRMATION',
      { type: 'warning', confirmButtonText: 'TRIGGER KILL SWITCH', cancelButtonText: 'Cancel' }
    )
    await api.post('/api/v1/production/risk/kill-switch', { reason: 'Manual trigger from Production Studio' })
    ElMessage.warning('Kill Switch triggered')
    fetchOverview()
  } catch (e) { /* cancelled */ }
}

onMounted(() => {
  fetchAll()
  pollTimer = setInterval(fetchAll, 5000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.production-studio {
  padding: 20px;
}

.studio-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.studio-title {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
}

.studio-subtitle {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  margin-left: 12px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.studio-tabs {
  margin-top: 8px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.metric-card {
  min-height: 180px;
}

.metric-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.metric-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.metric-label {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.metric-value {
  font-weight: 600;
  font-size: 15px;
}

.card-header-flex {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pnl-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.pnl-card {
  padding: 20px;
  border: 1px solid var(--el-border-color);
  border-radius: 8px;
  text-align: center;
}

.pnl-label {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  margin-bottom: 8px;
}

.pnl-value {
  font-size: 22px;
  font-weight: 700;
}

.text-success { color: #3fb950; }
.text-danger { color: #f85149; }
.text-warning { color: #d29922; }
</style>
