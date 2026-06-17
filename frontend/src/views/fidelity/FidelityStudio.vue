<template>
  <div class="fidelity-studio">
    <!-- Header -->
    <div class="studio-header">
      <div class="header-left">
        <h1 class="studio-title">Execution Fidelity Studio</h1>
        <span class="studio-subtitle">让纸上交易 ≈ 真实交易</span>
      </div>
      <div class="header-right">
        <el-button-group>
          <el-button :icon="Refresh" @click="fetchAll" size="small">Refresh</el-button>
        </el-button-group>
      </div>
    </div>

    <!-- Tabs -->
    <el-tabs v-model="activeTab" class="studio-tabs">
      <!-- Overview -->
      <el-tab-pane label="Overview" name="overview">
        <div class="metrics-grid">
          <el-card class="metric-card">
            <div class="metric-label">Fill Engines</div>
            <div class="metric-value">{{ status.fill_engines?.length || 0 }}</div>
            <div class="metric-sub">symbols</div>
          </el-card>
          <el-card class="metric-card">
            <div class="metric-label">Avg Cost</div>
            <div class="metric-value">{{ (status.cost_stats?.total || 0).toFixed(2) }} bps</div>
            <div class="metric-sub">total execution cost</div>
          </el-card>
          <el-card class="metric-card">
            <div class="metric-label">Latency</div>
            <div class="metric-value">{{ (status.latency_stats?.avg_total_ms || 0).toFixed(0) }} ms</div>
            <div class="metric-sub">avg round-trip</div>
          </el-card>
          <el-card class="metric-card">
            <div class="metric-label">Shadow Alerts</div>
            <div class="metric-value" :class="{ alert: (status.shadow_summary?.critical || 0) > 0 }">
              {{ status.shadow_summary?.critical || 0 }}
            </div>
            <div class="metric-sub">critical alerts</div>
          </el-card>
          <el-card class="metric-card">
            <div class="metric-label">True PnL</div>
            <div class="metric-value" :class="{ positive: truePnl >= 0, negative: truePnl < 0 }">
              {{ truePnl.toFixed(2) }}
            </div>
            <div class="metric-sub">net of all costs</div>
          </el-card>
          <el-card class="metric-card">
            <div class="metric-label">Adaptive Plans</div>
            <div class="metric-value">{{ status.adaptive_stats?.count || 0 }}</div>
            <div class="metric-sub">execution plans</div>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- Order Book -->
      <el-tab-pane label="Order Book" name="orderbook">
        <div class="control-row">
          <el-input v-model="obForm.symbol" placeholder="Symbol" style="width: 120px" />
          <el-input-number v-model="obForm.mid_price" :min="0" :step="100" style="width: 150px" />
          <el-input-number v-model="obForm.volatility" :min="0" :step="0.01" :precision="4" style="width: 150px" />
          <el-input-number v-model="obForm.volume" :min="0" :step="100000" style="width: 180px" />
          <el-button type="primary" @click="generateOrderBook">Generate</el-button>
          <el-button @click="sweepOrderBook">Sweep Market</el-button>
          <el-select v-model="sweepSide" style="width: 100px">
            <el-option label="BUY" value="BUY" />
            <el-option label="SELL" value="SELL" />
          </el-select>
          <el-input-number v-model="sweepQty" :min="0.01" :step="1" style="width: 120px" />
        </div>
        <el-row :gutter="16" v-if="orderbook">
          <el-col :span="12">
            <el-card>
              <template #header>Asks (卖盘)</template>
              <el-table :data="orderbook.asks?.slice(0, 10)" size="small" max-height="400">
                <el-table-column prop="price" label="Price" :formatter="(r: any) => r.price.toFixed(2)" />
                <el-table-column prop="qty" label="Qty" :formatter="(r: any) => r.qty.toFixed(4)" />
              </el-table>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card>
              <template #header>Bids (买盘)</template>
              <el-table :data="orderbook.bids?.slice(0, 10)" size="small" max-height="400">
                <el-table-column prop="price" label="Price" :formatter="(r: any) => r.price.toFixed(2)" />
                <el-table-column prop="qty" label="Qty" :formatter="(r: any) => r.qty.toFixed(4)" />
              </el-table>
            </el-card>
          </el-col>
        </el-row>
        <el-card v-if="sweepResult" class="sweep-result">
          <template #header>Sweep Result</template>
          <el-descriptions :column="3" border>
            <el-descriptions-item label="Avg Price">{{ sweepResult.avg_price?.toFixed(2) }}</el-descriptions-item>
            <el-descriptions-item label="Impact">{{ sweepResult.impact_bps?.toFixed(2) }} bps</el-descriptions-item>
            <el-descriptions-item label="Filled">{{ sweepResult.filled_qty?.toFixed(4) }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-tab-pane>

      <!-- Impact -->
      <el-tab-pane label="Impact" name="impact">
        <div class="control-row">
          <el-input-number v-model="impactForm.order_qty" :min="0" :step="1" style="width: 150px" />
          <el-input-number v-model="impactForm.mid_price" :min="0" :step="100" style="width: 150px" />
          <el-input-number v-model="impactForm.volume" :min="0" :step="100000" style="width: 180px" />
          <el-input-number v-model="impactForm.volatility" :min="0" :step="0.01" :precision="4" style="width: 150px" />
          <el-select v-model="impactForm.model" style="width: 100px">
            <el-option label="Sqrt" value="sqrt" />
            <el-option label="Linear" value="linear" />
            <el-option label="Power" value="power" />
          </el-select>
          <el-button type="primary" @click="calculateImpact">Calculate</el-button>
          <el-button @click="suggestSplit">Suggest Split</el-button>
        </div>
        <el-card v-if="impactResult">
          <template #header>Impact Result</template>
          <el-descriptions :column="3" border>
            <el-descriptions-item label="Impact (bps)">{{ impactResult.impact_bps?.toFixed(4) }}</el-descriptions-item>
            <el-descriptions-item label="Impact Price">{{ impactResult.impact_price?.toFixed(4) }}</el-descriptions-item>
            <el-descriptions-item label="Impact Cost">{{ impactResult.impact_cost?.toFixed(4) }}</el-descriptions-item>
            <el-descriptions-item label="Permanent">{{ impactResult.permanent_impact?.toFixed(4) }} bps</el-descriptions-item>
            <el-descriptions-item label="Temporary">{{ impactResult.temporary_impact?.toFixed(4) }} bps</el-descriptions-item>
            <el-descriptions-item label="Model">{{ impactResult.model }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
        <el-card v-if="splitResult" style="margin-top: 16px">
          <template #header>Split Suggestion ({{ splitResult.num_slices }} slices)</template>
          <el-tag v-for="(s, i) in splitResult.splits" :key="i" class="split-tag">
            #{{ i + 1 }}: {{ s.toFixed(4) }}
          </el-tag>
        </el-card>
      </el-tab-pane>

      <!-- Cost -->
      <el-tab-pane label="Cost" name="cost">
        <div class="control-row">
          <el-input v-model="costForm.symbol" placeholder="Symbol" style="width: 120px" />
          <el-select v-model="costForm.side" style="width: 100px">
            <el-option label="BUY" value="BUY" />
            <el-option label="SELL" value="SELL" />
          </el-select>
          <el-input-number v-model="costForm.qty" :min="0" :step="1" style="width: 120px" />
          <el-input-number v-model="costForm.price" :min="0" :step="100" style="width: 150px" />
          <el-input-number v-model="costForm.slippage_bps" :min="0" :step="0.5" :precision="2" style="width: 150px" />
          <el-input-number v-model="costForm.volume" :min="0" :step="100000" style="width: 180px" />
          <el-input-number v-model="costForm.volatility" :min="0" :step="0.01" :precision="4" style="width: 150px" />
          <el-button type="primary" @click="calculateCost">Calculate</el-button>
        </div>
        <el-card v-if="costResult">
          <template #header>Cost Breakdown</template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="Fee">{{ costResult.costs.fee_cost?.toFixed(4) }}</el-descriptions-item>
            <el-descriptions-item label="Slippage">{{ costResult.costs.slippage_cost?.toFixed(4) }}</el-descriptions-item>
            <el-descriptions-item label="Impact">{{ costResult.costs.impact_cost?.toFixed(4) }}</el-descriptions-item>
            <el-descriptions-item label="Opportunity">{{ costResult.costs.opportunity_cost?.toFixed(4) }}</el-descriptions-item>
            <el-descriptions-item label="Funding">{{ costResult.costs.funding_cost?.toFixed(4) }}</el-descriptions-item>
            <el-descriptions-item label="Total">
              <strong>{{ costResult.costs.total_cost?.toFixed(4) }}</strong>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-tab-pane>

      <!-- Fill Engine -->
      <el-tab-pane label="Fill Engine" name="fill">
        <div class="control-row">
          <el-input v-model="fillForm.order_id" placeholder="Order ID" style="width: 150px" />
          <el-input v-model="fillForm.symbol" placeholder="Symbol" style="width: 120px" />
          <el-select v-model="fillForm.side" style="width: 100px">
            <el-option label="BUY" value="BUY" />
            <el-option label="SELL" value="SELL" />
          </el-select>
          <el-input-number v-model="fillForm.qty" :min="0" :step="1" style="width: 120px" />
          <el-select v-model="fillForm.order_type" style="width: 120px">
            <el-option label="MARKET" value="MARKET" />
            <el-option label="LIMIT" value="LIMIT" />
          </el-select>
          <el-input-number v-model="fillForm.mid_price" :min="0" :step="100" style="width: 150px" />
          <el-input-number v-model="fillForm.volatility" :min="0" :step="0.01" :precision="4" style="width: 150px" />
          <el-input-number v-model="fillForm.volume" :min="0" :step="100000" style="width: 180px" />
          <el-button type="primary" @click="processFill">Process Order</el-button>
        </div>
        <el-card v-if="fillResult">
          <template #header>Fill Result</template>
          <el-descriptions :column="3" border>
            <el-descriptions-item label="Fill ID">{{ fillResult.fill.id }}</el-descriptions-item>
            <el-descriptions-item label="Filled Qty">{{ fillResult.fill.fill_qty?.toFixed(4) }}</el-descriptions-item>
            <el-descriptions-item label="Fill Price">{{ fillResult.fill.fill_price?.toFixed(2) }}</el-descriptions-item>
            <el-descriptions-item label="Slippage">{{ fillResult.match?.slippage_bps?.toFixed(2) }} bps</el-descriptions-item>
            <el-descriptions-item label="Commission">{{ fillResult.fill.commission?.toFixed(4) }}</el-descriptions-item>
            <el-descriptions-item label="Partial">{{ fillResult.fill.is_partial ? 'Yes' : 'No' }}</el-descriptions-item>
          </el-descriptions>
          <el-table v-if="fillResult.match?.fills?.length" :data="fillResult.match.fills" size="small" style="margin-top: 12px">
            <el-table-column prop="price" label="Price" :formatter="(r: any) => r.price.toFixed(2)" />
            <el-table-column prop="qty" label="Qty" :formatter="(r: any) => r.qty.toFixed(4)" />
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- Shadow Mode -->
      <el-tab-pane label="Shadow Mode" name="shadow">
        <el-card>
          <template #header>Shadow Mode Summary</template>
          <el-descriptions :column="4" border>
            <el-descriptions-item label="Comparisons">{{ status.shadow_summary?.total_comparisons || 0 }}</el-descriptions-item>
            <el-descriptions-item label="OK">{{ status.shadow_summary?.ok || 0 }}</el-descriptions-item>
            <el-descriptions-item label="Warning">{{ status.shadow_summary?.warning || 0 }}</el-descriptions-item>
            <el-descriptions-item label="Critical">{{ status.shadow_summary?.critical || 0 }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
        <el-card style="margin-top: 16px">
          <template #header>Record Fills</template>
          <div class="control-row">
            <el-input v-model="shadowForm.order_id" placeholder="Order ID" style="width: 150px" />
            <el-input v-model="shadowForm.symbol" placeholder="Symbol" style="width: 120px" />
            <el-input-number v-model="shadowForm.qty" :min="0" :step="1" style="width: 120px" />
            <el-input-number v-model="shadowForm.paper_price" :min="0" :step="100" style="width: 150px" />
            <el-input-number v-model="shadowForm.live_price" :min="0" :step="100" style="width: 150px" />
            <el-button type="primary" @click="recordShadowFills">Record & Compare</el-button>
            <el-button @click="compareAllShadow">Compare All</el-button>
          </div>
        </el-card>
        <el-card v-if="shadowComparisons.length" style="margin-top: 16px">
          <template #header>Comparisons</template>
          <el-table :data="shadowComparisons" size="small">
            <el-table-column prop="order_id" label="Order ID" width="120" />
            <el-table-column prop="symbol" label="Symbol" width="100" />
            <el-table-column label="Paper Price" :formatter="(r: any) => r.paper_fill?.fill_price?.toFixed(2) || '-'" />
            <el-table-column label="Live Price" :formatter="(r: any) => r.live_fill?.fill_price?.toFixed(2) || '-'" />
            <el-table-column label="Diff (bps)" :formatter="(r: any) => r.price_diff_bps?.toFixed(2)" />
            <el-table-column prop="severity" label="Severity" width="100">
              <template #default="{ row }">
                <el-tag :type="row.severity === 'CRITICAL' ? 'danger' : row.severity === 'WARNING' ? 'warning' : 'success'" size="small">
                  {{ row.severity }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- Adaptive -->
      <el-tab-pane label="Adaptive" name="adaptive">
        <div class="control-row">
          <el-input v-model="adaptiveForm.order_id" placeholder="Order ID" style="width: 150px" />
          <el-input v-model="adaptiveForm.symbol" placeholder="Symbol" style="width: 120px" />
          <el-select v-model="adaptiveForm.side" style="width: 100px">
            <el-option label="BUY" value="BUY" />
            <el-option label="SELL" value="SELL" />
          </el-select>
          <el-input-number v-model="adaptiveForm.total_qty" :min="0" :step="10" style="width: 150px" />
          <el-input-number v-model="adaptiveForm.volatility" :min="0" :step="0.01" :precision="4" style="width: 150px" />
          <el-input-number v-model="adaptiveForm.liquidity_score" :min="0" :max="1" :step="0.1" :precision="2" style="width: 150px" />
          <el-input-number v-model="adaptiveForm.urgency" :min="0" :max="1" :step="0.1" :precision="2" style="width: 120px" />
          <el-button type="primary" @click="generatePlan">Generate Plan</el-button>
        </div>
        <el-card v-if="adaptivePlan">
          <template #header>Execution Plan — {{ adaptivePlan.regime }} / {{ adaptivePlan.style }}</template>
          <el-alert :title="adaptivePlan.rationale" type="info" :closable="false" style="margin-bottom: 12px" />
          <el-table :data="adaptivePlan.slices" size="small">
            <el-table-column type="index" label="#" width="50" />
            <el-table-column prop="qty" label="Qty" :formatter="(r: any) => r.qty.toFixed(4)" />
            <el-table-column prop="delay_ms" label="Delay (ms)" />
            <el-table-column prop="order_type" label="Type" />
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- Truth Layer -->
      <el-tab-pane label="True PnL" name="truth">
        <div class="control-row">
          <el-input v-model="truthForm.symbol" placeholder="Symbol" style="width: 120px" />
          <el-input-number v-model="truthForm.qty" :step="0.1" :precision="4" style="width: 150px" />
          <el-input-number v-model="truthForm.avg_entry" :min="0" :step="100" style="width: 150px" />
          <el-button @click="updatePosition">Update Position</el-button>
          <el-input-number v-model="truthForm.price" :min="0" :step="100" style="width: 150px" />
          <el-button @click="updatePrice">Update Price</el-button>
          <el-button type="primary" @click="computeTruePnL">Compute True PnL</el-button>
        </div>
        <el-card v-if="truthReport">
          <template #header>True PnL Report</template>
          <el-descriptions :column="3" border>
            <el-descriptions-item label="Gross PnL">{{ truthReport.gross_pnl?.toFixed(4) }}</el-descriptions-item>
            <el-descriptions-item label="Total Cost">{{ truthReport.total_cost?.toFixed(4) }}</el-descriptions-item>
            <el-descriptions-item label="True PnL">
              <strong :class="{ positive: truthReport.true_pnl >= 0, negative: truthReport.true_pnl < 0 }">
                {{ truthReport.true_pnl?.toFixed(4) }}
              </strong>
            </el-descriptions-item>
            <el-descriptions-item label="Fee">{{ truthReport.fee_cost?.toFixed(4) }}</el-descriptions-item>
            <el-descriptions-item label="Slippage">{{ truthReport.slippage_cost?.toFixed(4) }}</el-descriptions-item>
            <el-descriptions-item label="Impact">{{ truthReport.impact_cost?.toFixed(4) }}</el-descriptions-item>
            <el-descriptions-item label="True PnL (bps)">{{ truthReport.true_pnl_bps?.toFixed(2) }}</el-descriptions-item>
            <el-descriptions-item label="Cost Drag (bps)">{{ truthReport.cost_drag_bps?.toFixed(2) }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
        <el-card v-if="truthPositions.length" style="margin-top: 16px">
          <template #header>Positions</template>
          <el-table :data="truthPositions" size="small">
            <el-table-column prop="symbol" label="Symbol" width="100" />
            <el-table-column prop="qty" label="Qty" :formatter="(r: any) => r.qty.toFixed(4)" />
            <el-table-column prop="avg_entry" label="Avg Entry" :formatter="(r: any) => r.avg_entry.toFixed(2)" />
            <el-table-column prop="current_price" label="Current" :formatter="(r: any) => r.current_price.toFixed(2)" />
            <el-table-column prop="gross_pnl" label="Gross" :formatter="(r: any) => r.gross_pnl.toFixed(2)" />
            <el-table-column prop="total_cost" label="Cost" :formatter="(r: any) => r.total_cost.toFixed(2)" />
            <el-table-column prop="true_pnl" label="True PnL" :formatter="(r: any) => r.true_pnl.toFixed(2)" />
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { api } from '@/utils/api'

const activeTab = ref('overview')
const status = ref<any>({})
const orderbook = ref<any>(null)
const sweepResult = ref<any>(null)
const impactResult = ref<any>(null)
const splitResult = ref<any>(null)
const costResult = ref<any>(null)
const fillResult = ref<any>(null)
const adaptivePlan = ref<any>(null)
const truthReport = ref<any>(null)
const truthPositions = ref<any[]>([])
const shadowComparisons = ref<any[]>([])

const truePnl = computed(() => truthReport.value?.true_pnl || 0)

// Forms
const obForm = ref({ symbol: 'BTCUSDT', mid_price: 50000, volatility: 0.02, volume: 1000000 })
const sweepSide = ref('BUY')
const sweepQty = ref(10)
const impactForm = ref({ order_qty: 10, mid_price: 50000, volume: 1000000, volatility: 0.02, model: 'sqrt' })
const costForm = ref({ symbol: 'BTCUSDT', side: 'BUY', qty: 10, price: 50000, slippage_bps: 2.0, volume: 1000000, volatility: 0.02 })
const fillForm = ref({ order_id: '', symbol: 'BTCUSDT', side: 'BUY', qty: 10, order_type: 'MARKET', mid_price: 50000, volatility: 0.02, volume: 1000000 })
const adaptiveForm = ref({ order_id: '', symbol: 'BTCUSDT', side: 'BUY', total_qty: 100, volatility: 0.03, liquidity_score: 0.5, urgency: 0.5 })
const truthForm = ref({ symbol: 'BTCUSDT', qty: 0.5, avg_entry: 50000, price: 51000 })
const shadowForm = ref({ order_id: '', symbol: 'BTCUSDT', qty: 10, paper_price: 50000, live_price: 50010 })

let pollTimer: any = null

async function fetchAll() {
  try {
    status.value = await api.get('/fidelity/status')
  } catch (e: any) {
    ElMessage.error('Failed to fetch status: ' + e.message)
  }
}

async function generateOrderBook() {
  try {
    orderbook.value = await api.post('/fidelity/orderbook/generate', obForm.value)
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

async function sweepOrderBook() {
  try {
    const params = new URLSearchParams({ side: sweepSide.value, qty: String(sweepQty.value) })
    const result = await api.post(`/fidelity/orderbook/sweep?${params}`, obForm.value)
    orderbook.value = result.book
    sweepResult.value = result.sweep_result
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

async function calculateImpact() {
  try {
    impactResult.value = await api.post('/fidelity/impact/calculate', { ...impactForm.value, side: 'BUY' })
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

async function suggestSplit() {
  try {
    splitResult.value = await api.post('/fidelity/impact/suggest-split', { ...impactForm.value, side: 'BUY' })
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

async function calculateCost() {
  try {
    costResult.value = await api.post('/fidelity/cost/calculate', costForm.value)
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

async function processFill() {
  try {
    fillResult.value = await api.post('/fidelity/fill/process', fillForm.value)
    ElMessage.success('Order processed')
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

async function generatePlan() {
  try {
    adaptivePlan.value = await api.post('/fidelity/adaptive/plan', adaptiveForm.value)
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

async function updatePosition() {
  try {
    await api.post('/fidelity/truth/position', { symbol: truthForm.value.symbol, qty: truthForm.value.qty, avg_entry: truthForm.value.avg_entry })
    ElMessage.success('Position updated')
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

async function updatePrice() {
  try {
    await api.post('/fidelity/truth/price', { symbol: truthForm.value.symbol, price: truthForm.value.price })
    ElMessage.success('Price updated')
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

async function computeTruePnL() {
  try {
    const result = await api.get('/fidelity/truth/pnl')
    truthReport.value = result.report
    truthPositions.value = result.positions || []
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

async function recordShadowFills() {
  try {
    await api.post('/fidelity/shadow/paper-fill', { order_id: shadowForm.value.order_id, symbol: shadowForm.value.symbol, qty: shadowForm.value.qty, price: shadowForm.value.paper_price })
    await api.post('/fidelity/shadow/live-fill', { order_id: shadowForm.value.order_id, symbol: shadowForm.value.symbol, qty: shadowForm.value.qty, price: shadowForm.value.live_price })
    const comp = await api.post(`/fidelity/shadow/compare/${shadowForm.value.order_id}`, {})
    shadowComparisons.value = [comp, ...shadowComparisons.value].slice(0, 50)
    ElMessage.success(`Compared: ${comp.severity}`)
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

async function compareAllShadow() {
  try {
    const result = await api.get('/fidelity/shadow/compare-all')
    shadowComparisons.value = result.comparisons || []
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

onMounted(() => {
  fetchAll()
  pollTimer = setInterval(fetchAll, 10000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.fidelity-studio {
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
}

.studio-subtitle {
  color: #909399;
  font-size: 14px;
  margin-left: 12px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.metric-card {
  text-align: center;
}

.metric-label {
  color: #909399;
  font-size: 13px;
}

.metric-value {
  font-size: 28px;
  font-weight: bold;
  margin: 8px 0;
}

.metric-value.alert {
  color: #f56c6c;
}

.metric-value.positive {
  color: #67c23a;
}

.metric-value.negative {
  color: #f56c6c;
}

.metric-sub {
  color: #c0c4cc;
  font-size: 12px;
}

.control-row {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
}

.sweep-result {
  margin-top: 16px;
}

.split-tag {
  margin: 4px;
}
</style>
