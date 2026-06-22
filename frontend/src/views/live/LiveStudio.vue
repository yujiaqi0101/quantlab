<template>
  <div class="live-studio">
    <!-- Header -->
    <div class="studio-header">
      <div class="header-left">
        <h1 class="studio-title">实盘工作室 Live Studio</h1>
        <span class="studio-subtitle">实时交易工作室 — 看运行过程 Live trading studio — watch the process</span>
      </div>
      <div class="header-right">
        <el-button @click="loadAll" :icon="Refresh" plain>刷新 Refresh</el-button>
        <el-button @click="openDeployDialog" :icon="Plus" type="primary">部署策略 Deploy Strategy</el-button>
      </div>
    </div>

    <!-- Tabs -->
    <el-tabs v-model="activeTab" class="studio-tabs">
      <!-- Strategies -->
      <el-tab-pane label="策略 Strategies" name="strategies">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>策略库 (Strategy Library)</span>
              <el-select v-model="categoryFilter" placeholder="类别" clearable size="small" style="width: 140px">
                <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
              </el-select>
            </div>
          </template>
          <el-table :data="filteredStrategies" size="small" stripe>
            <el-table-column prop="strategy_id" label="ID" width="160" />
            <el-table-column prop="name" label="名称" min-width="180" />
            <el-table-column prop="category" label="类别" width="140">
              <template #default="{ row }">
                <el-tag size="small">{{ row.category }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="标签" min-width="200">
              <template #default="{ row }">
                <el-tag v-for="t in row.tags" :key="t" size="small" type="info" effect="plain" style="margin-right: 4px">
                  {{ t }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="timeframe" label="周期" width="80" />
            <el-table-column prop="version" label="版本" width="80" />
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button size="small" type="primary" @click="quickDeploy(row)">Deploy</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- Deployments -->
      <el-tab-pane label="Deployments" name="deployments">
        <el-card shadow="never">
          <template #header>
            <span>运行中的部署 (Active Deployments)</span>
          </template>
          <el-table :data="deployments" size="small" stripe>
            <el-table-column prop="deploy_id" label="Deploy ID" width="180" />
            <el-table-column prop="strategy_id" label="策略" width="160" />
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="statusType(row.result.status)" size="small">
                  {{ row.result.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="品种" min-width="200">
              <template #default="{ row }">
                {{ row.request.symbols.join(', ') }}
              </template>
            </el-table-column>
            <el-table-column label="初始资金" width="120">
              <template #default="{ row }">
                ${{ formatNum(row.request.initial_capital) }}
              </template>
            </el-table-column>
            <el-table-column label="部署时间" width="180">
              <template #default="{ row }">
                {{ formatTime(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="280" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="viewDeployment(row)">查看</el-button>
                <el-button size="small" type="warning" @click="pauseDeployment(row.deploy_id)" :disabled="row.result.status !== 'RUNNING'">暂停</el-button>
                <el-button size="small" type="success" @click="resumeDeployment(row.deploy_id)" :disabled="row.result.status === 'RUNNING'">恢复</el-button>
                <el-button size="small" type="danger" @click="undeploy(row.deploy_id)">卸载</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- Orders -->
      <el-tab-pane label="Orders" name="orders">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>订单 (Orders)</span>
              <div>
                <el-select v-model="selectedDeployId" placeholder="选择部署" size="small" style="width: 220px" @change="loadOrders">
                  <el-option v-for="d in activeDeployments" :key="d.deploy_id" :label="`${d.deploy_id} (${d.strategy_id})`" :value="d.deploy_id" />
                </el-select>
                <el-checkbox v-model="activeOnly" @change="loadOrders" style="margin-left: 12px">仅活跃</el-checkbox>
              </div>
            </div>
          </template>
          <el-table :data="orders" size="small" stripe>
            <el-table-column prop="id" label="Order ID" width="200" />
            <el-table-column prop="symbol" label="品种" width="120" />
            <el-table-column prop="side" label="方向" width="80">
              <template #default="{ row }">
                <el-tag :type="row.side === 'BUY' ? 'success' : 'danger'" size="small">{{ row.side }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="quantity" label="数量" width="100" />
            <el-table-column prop="order_type" label="类型" width="100" />
            <el-table-column prop="state" label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="orderStateType(row.state)" size="small">{{ row.state }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="filled_qty" label="已成交" width="100" />
            <el-table-column prop="avg_fill_price" label="成交均价" width="120">
              <template #default="{ row }">{{ row.avg_fill_price ? row.avg_fill_price.toFixed(4) : '-' }}</template>
            </el-table-column>
            <el-table-column prop="strategy_id" label="策略" width="140" />
            <el-table-column label="时间" width="180">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- Positions -->
      <el-tab-pane label="Positions" name="positions">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>持仓 (Positions)</span>
              <el-select v-model="selectedDeployId" placeholder="选择部署" size="small" style="width: 220px" @change="loadPositions">
                <el-option v-for="d in activeDeployments" :key="d.deploy_id" :label="`${d.deploy_id} (${d.strategy_id})`" :value="d.deploy_id" />
              </el-select>
            </div>
          </template>
          <el-table :data="positions" size="small" stripe>
            <el-table-column prop="symbol" label="品种" width="120" />
            <el-table-column prop="qty" label="数量" width="120" />
            <el-table-column prop="side" label="方向" width="80">
              <template #default="{ row }">
                <el-tag :type="row.side === 'LONG' ? 'success' : row.side === 'SHORT' ? 'danger' : 'info'" size="small">
                  {{ row.side }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="avg_price" label="均价" width="120">
              <template #default="{ row }">{{ row.avg_price.toFixed(4) }}</template>
            </el-table-column>
            <el-table-column prop="market_price" label="现价" width="120">
              <template #default="{ row }">{{ row.market_price.toFixed(4) }}</template>
            </el-table-column>
            <el-table-column prop="market_value" label="市值" width="140">
              <template #default="{ row }">${{ formatNum(row.market_value) }}</template>
            </el-table-column>
            <el-table-column prop="unrealized_pnl" label="未实现盈亏" width="140">
              <template #default="{ row }">
                <span :class="pnlClass(row.unrealized_pnl)">{{ formatNum(row.unrealized_pnl) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="realized_pnl" label="已实现盈亏" width="140">
              <template #default="{ row }">
                <span :class="pnlClass(row.realized_pnl)">{{ formatNum(row.realized_pnl) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="strategy_id" label="策略" width="140" />
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- Portfolio -->
      <el-tab-pane label="Portfolio" name="portfolio">
        <el-card shadow="never" v-if="portfolio">
          <template #header>
            <div class="card-header">
              <span>组合 (Portfolio)</span>
              <el-select v-model="selectedDeployId" placeholder="选择部署" size="small" style="width: 220px" @change="loadPortfolio">
                <el-option v-for="d in activeDeployments" :key="d.deploy_id" :label="`${d.deploy_id} (${d.strategy_id})`" :value="d.deploy_id" />
              </el-select>
            </div>
          </template>
          <el-row :gutter="12">
            <el-col :span="6">
              <div class="metric-card">
                <div class="metric-label">总净值 (Equity)</div>
                <div class="metric-value">${{ formatNum(portfolio.equity) }}</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="metric-card">
                <div class="metric-label">现金 (Cash)</div>
                <div class="metric-value">${{ formatNum(portfolio.cash) }}</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="metric-card">
                <div class="metric-label">总盈亏 (PnL)</div>
                <div class="metric-value" :class="pnlClass(portfolio.total_pnl)">
                  {{ formatNum(portfolio.total_pnl) }} ({{ (portfolio.total_return * 100).toFixed(2) }}%)
                </div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="metric-card">
                <div class="metric-label">最大回撤</div>
                <div class="metric-value text-danger">{{ (portfolio.max_drawdown * 100).toFixed(2) }}%</div>
              </div>
            </el-col>
          </el-row>
          <el-row :gutter="12" style="margin-top: 12px">
            <el-col :span="6">
              <div class="metric-card">
                <div class="metric-label">敞口 (Exposure)</div>
                <div class="metric-value">{{ (portfolio.exposure * 100).toFixed(2) }}%</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="metric-card">
                <div class="metric-label">多头敞口</div>
                <div class="metric-value text-success">${{ formatNum(portfolio.long_exposure) }}</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="metric-card">
                <div class="metric-label">空头敞口</div>
                <div class="metric-value text-danger">${{ formatNum(portfolio.short_exposure) }}</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="metric-card">
                <div class="metric-label">持仓数</div>
                <div class="metric-value">{{ portfolio.n_open_positions }}</div>
              </div>
            </el-col>
          </el-row>
        </el-card>
        <el-empty v-else description="选择部署查看组合" />
      </el-tab-pane>

      <!-- Risk -->
      <el-tab-pane label="Risk" name="risk">
        <el-card shadow="never" v-if="risk">
          <template #header>
            <div class="card-header">
              <span>风险 (Risk)</span>
              <el-select v-model="selectedDeployId" placeholder="选择部署" size="small" style="width: 220px" @change="loadRisk">
                <el-option v-for="d in activeDeployments" :key="d.deploy_id" :label="`${d.deploy_id} (${d.strategy_id})`" :value="d.deploy_id" />
              </el-select>
            </div>
          </template>
          <el-row :gutter="12">
            <el-col :span="6">
              <div class="metric-card">
                <div class="metric-label">净值</div>
                <div class="metric-value">${{ formatNum(risk.equity) }}</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="metric-card">
                <div class="metric-label">敞口</div>
                <div class="metric-value">{{ (risk.exposure * 100).toFixed(2) }}%</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="metric-card">
                <div class="metric-label">最大回撤</div>
                <div class="metric-value text-danger">{{ (risk.max_drawdown * 100).toFixed(2) }}%</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="metric-card">
                <div class="metric-label">当前回撤</div>
                <div class="metric-value text-warning">{{ (risk.current_drawdown * 100).toFixed(2) }}%</div>
              </div>
            </el-col>
          </el-row>
        </el-card>
        <el-empty v-else description="选择部署查看风险" />
      </el-tab-pane>
    </el-tabs>

    <!-- Deploy Dialog -->
    <el-dialog v-model="deployDialogVisible" title="Deploy Strategy" width="600px">
      <el-form :model="deployForm" label-width="120px" size="default">
        <el-form-item label="策略">
          <el-select v-model="deployForm.strategy_id" placeholder="选择策略" style="width: 100%" @change="onStrategyChange">
            <el-option v-for="s in strategies" :key="s.strategy_id" :label="`${s.name} (${s.strategy_id})`" :value="s.strategy_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="品种">
          <el-select v-model="deployForm.symbols" multiple placeholder="选择品种" style="width: 100%">
            <el-option v-for="sym in availableSymbols" :key="sym" :label="sym" :value="sym" />
          </el-select>
        </el-form-item>
        <el-form-item label="初始资金">
          <el-input-number v-model="deployForm.initial_capital" :min="1000" :step="10000" style="width: 100%" />
        </el-form-item>
        <el-form-item label="Broker">
          <el-select v-model="deployForm.broker_type" style="width: 100%">
            <el-option label="Paper (模拟)" value="PAPER" />
            <el-option label="Binance (实盘)" value="BINANCE" disabled />
          </el-select>
        </el-form-item>
        <el-form-item v-if="selectedStrategyParams.length > 0" label="参数">
          <div v-for="p in selectedStrategyParams" :key="p.name" style="margin-bottom: 8px; display: flex; align-items: center; gap: 12px">
            <span style="width: 140px; font-size: 13px">{{ p.name }}</span>
            <el-input-number
              v-if="p.type === 'int' || p.type === 'float'"
              v-model="deployForm.params[p.name]"
              :min="p.min"
              :max="p.max"
              :step="p.type === 'int' ? 1 : 0.1"
              size="small"
            />
            <el-select v-else-if="p.type === 'choice'" v-model="deployForm.params[p.name]" size="small" style="width: 200px">
              <el-option v-for="c in p.choices" :key="c" :label="c" :value="c" />
            </el-select>
            <el-input v-else v-model="deployForm.params[p.name]" size="small" style="width: 200px" />
            <span style="color: #909399; font-size: 12px">{{ p.description }}</span>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="deployDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="doDeploy" :loading="deploying">部署</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { Refresh, Plus } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { liveApi } from '@/api/live'
import type {
  StrategyInfo,
  DeploymentRecord,
  Order,
  Position,
  PortfolioBook,
  RiskStatus,
} from '@/api/live'

// State
const activeTab = ref('strategies')
const strategies = ref<StrategyInfo[]>([])
const categories = ref<string[]>([])
const categoryFilter = ref('')
const deployments = ref<DeploymentRecord[]>([])
const orders = ref<Order[]>([])
const positions = ref<Position[]>([])
const portfolio = ref<PortfolioBook | null>(null)
const risk = ref<RiskStatus | null>(null)
const selectedDeployId = ref('')
const activeOnly = ref(false)

// Deploy dialog
const deployDialogVisible = ref(false)
const deploying = ref(false)
const deployForm = ref({
  strategy_id: '',
  symbols: [] as string[],
  params: {} as Record<string, any>,
  initial_capital: 100000,
  broker_type: 'PAPER',
})

// Computed
const filteredStrategies = computed(() => {
  if (!categoryFilter.value) return strategies.value
  return strategies.value.filter(s => s.category === categoryFilter.value)
})

const activeDeployments = computed(() =>
  deployments.value.filter(d => d.result.status === 'RUNNING')
)

const availableSymbols = computed(() => {
  const s = strategies.value.find(x => x.strategy_id === deployForm.value.strategy_id)
  return s?.symbols || ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT']
})

const selectedStrategyParams = computed(() => {
  const s = strategies.value.find(x => x.strategy_id === deployForm.value.strategy_id)
  return s?.parameters || []
})

// Methods
const formatNum = (n: number) => {
  if (!n) return '0.00'
  return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const formatTime = (ts: number) => {
  if (!ts) return '-'
  return new Date(ts).toLocaleString('zh-CN')
}

const pnlClass = (n: number) => {
  if (n > 0) return 'text-success'
  if (n < 0) return 'text-danger'
  return ''
}

const statusType = (status: string) => {
  const map: Record<string, string> = {
    RUNNING: 'success',
    STOPPED: 'info',
    FAILED: 'danger',
    PENDING: 'warning',
  }
  return map[status] || 'info'
}

const orderStateType = (state: string) => {
  const map: Record<string, string> = {
    FILLED: 'success',
    CANCELLED: 'info',
    REJECTED: 'danger',
    SUBMITTED: 'warning',
    PARTIAL: 'warning',
    NEW: 'info',
  }
  return map[state] || 'info'
}

const loadStrategies = async () => {
  try {
    const res = await liveApi.listStrategies()
    strategies.value = res.strategies
    categories.value = res.categories
  } catch (e: any) {
    ElMessage.error(`加载策略失败: ${e.message}`)
  }
}

const loadDeployments = async () => {
  try {
    const res = await liveApi.listDeployments()
    deployments.value = res.deployments
  } catch (e: any) {
    ElMessage.error(`加载部署失败: ${e.message}`)
  }
}

const loadOrders = async () => {
  if (!selectedDeployId.value) return
  try {
    const res = await liveApi.deploymentOrders(selectedDeployId.value, activeOnly.value)
    orders.value = res.orders
  } catch (e: any) {
    ElMessage.error(`加载订单失败: ${e.message}`)
  }
}

const loadPositions = async () => {
  if (!selectedDeployId.value) return
  try {
    const res = await liveApi.deploymentPositions(selectedDeployId.value)
    positions.value = res.positions
  } catch (e: any) {
    ElMessage.error(`加载持仓失败: ${e.message}`)
  }
}

const loadPortfolio = async () => {
  if (!selectedDeployId.value) return
  try {
    portfolio.value = await liveApi.deploymentPortfolio(selectedDeployId.value)
  } catch (e: any) {
    ElMessage.error(`加载组合失败: ${e.message}`)
  }
}

const loadRisk = async () => {
  if (!selectedDeployId.value) return
  try {
    risk.value = await liveApi.deploymentRisk(selectedDeployId.value)
  } catch (e: any) {
    ElMessage.error(`加载风险失败: ${e.message}`)
  }
}

const loadAll = async () => {
  await Promise.all([loadStrategies(), loadDeployments()])
  if (selectedDeployId.value) {
    if (activeTab.value === 'orders') await loadOrders()
    if (activeTab.value === 'positions') await loadPositions()
    if (activeTab.value === 'portfolio') await loadPortfolio()
    if (activeTab.value === 'risk') await loadRisk()
  }
}

const openDeployDialog = () => {
  deployForm.value = {
    strategy_id: '',
    symbols: [],
    params: {},
    initial_capital: 100000,
    broker_type: 'PAPER',
  }
  deployDialogVisible.value = true
}

const onStrategyChange = (id: string) => {
  const s = strategies.value.find(x => x.strategy_id === id)
  if (s) {
    deployForm.value.symbols = [...s.symbols]
    deployForm.value.params = {}
    for (const p of s.parameters) {
      deployForm.value.params[p.name] = p.default
    }
  }
}

const quickDeploy = (s: StrategyInfo) => {
  deployForm.value = {
    strategy_id: s.strategy_id,
    symbols: [...s.symbols],
    params: {},
    initial_capital: 100000,
    broker_type: 'PAPER',
  }
  for (const p of s.parameters) {
    deployForm.value.params[p.name] = p.default
  }
  deployDialogVisible.value = true
}

const doDeploy = async () => {
  if (!deployForm.value.strategy_id) {
    ElMessage.warning('请选择策略')
    return
  }
  if (deployForm.value.symbols.length === 0) {
    ElMessage.warning('请选择品种')
    return
  }
  deploying.value = true
  try {
    const result = await liveApi.deploy(deployForm.value)
    if (result.status === 'RUNNING') {
      ElMessage.success(`部署成功: ${result.deploy_id}`)
      deployDialogVisible.value = false
      await loadDeployments()
    } else {
      ElMessage.error(`部署失败: ${result.message}`)
    }
  } catch (e: any) {
    ElMessage.error(`部署失败: ${e.message}`)
  } finally {
    deploying.value = false
  }
}

const undeploy = async (deployId: string) => {
  try {
    await ElMessageBox.confirm('确定要卸载此部署吗？', '确认', { type: 'warning' })
    await liveApi.undeploy(deployId)
    ElMessage.success('卸载成功')
    await loadDeployments()
  } catch (e: any) {
    if (e !== 'cancel') ElMessage.error(`卸载失败: ${e.message}`)
  }
}

const pauseDeployment = async (deployId: string) => {
  try {
    await liveApi.pauseDeployment(deployId)
    ElMessage.success('已暂停')
    await loadDeployments()
  } catch (e: any) {
    ElMessage.error(`暂停失败: ${e.message}`)
  }
}

const resumeDeployment = async (deployId: string) => {
  try {
    await liveApi.resumeDeployment(deployId)
    ElMessage.success('已恢复')
    await loadDeployments()
  } catch (e: any) {
    ElMessage.error(`恢复失败: ${e.message}`)
  }
}

const viewDeployment = (row: DeploymentRecord) => {
  selectedDeployId.value = row.deploy_id
  activeTab.value = 'portfolio'
  loadPortfolio()
}

onMounted(() => {
  loadAll()
})
</script>

<style scoped>
.live-studio {
  padding: 16px;
}

.studio-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.studio-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
}

.studio-subtitle {
  color: #909399;
  font-size: 13px;
  margin-left: 12px;
}

.studio-tabs {
  margin-top: 8px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.metric-card {
  background: var(--el-bg-color-page, #f5f7fa);
  border-radius: 6px;
  padding: 16px;
  text-align: center;
}

.metric-label {
  color: #909399;
  font-size: 12px;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 20px;
  font-weight: 700;
}

.text-success {
  color: #67c23a;
}

.text-danger {
  color: #f56c6c;
}

.text-warning {
  color: #e6a23c;
}
</style>
