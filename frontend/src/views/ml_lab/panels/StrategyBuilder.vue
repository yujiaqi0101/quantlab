<template>
  <div class="strategy-studio">
    <div class="panel-header">
      <h2>策略工作室 Strategy Studio</h2>
      <p class="hint">装配 Model + Signal + Position + Risk + Execution + Observe → Strategy Package (.qlstrategy)</p>
    </div>

    <el-alert type="info" :closable="false" show-icon style="margin-bottom: 16px">
      Strategy 是资产组合，不是 Model + if。这里是装配器（Assembler），不是生成器（Generator）。
      Strategy is an Asset Composition, not Model + if. This is an Assembler, not a Generator.
    </el-alert>

    <!-- 装配流程 -->
    <el-card style="margin-bottom: 16px">
      <template #header>
        <div class="card-header">
          <span>装配流程 Compose Pipeline</span>
          <el-button type="primary" :loading="composing" @click="composeStrategy" :disabled="!canCompose">
            装配策略 Compose Strategy
          </el-button>
        </div>
      </template>

      <el-steps :active="composeStep" align-center>
        <el-step title="Model" description="选择模型包" />
        <el-step title="Signal" description="选择信号包" />
        <el-step title="Position" description="选择仓位包" />
        <el-step title="Risk" description="选择风控包" />
        <el-step title="Execution" description="选择执行配置" />
        <el-step title="Observe" description="选择观察配置" />
      </el-steps>

      <el-form :model="composeForm" label-width="120px" style="margin-top: 20px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="策略名 Name">
              <el-input v-model="composeForm.name" placeholder="如 Momentum_LGBM_v2" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="策略族 Family">
              <el-input v-model="composeForm.family" placeholder="如 Momentum" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="8">
            <el-form-item label="版本 Version">
              <el-input v-model="composeForm.version" placeholder="1.0" />
            </el-form-item>
          </el-col>
          <el-col :span="16">
            <el-form-item label="描述 Description">
              <el-input v-model="composeForm.description" placeholder="策略描述" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider>组件选择 Component Selection</el-divider>

        <el-form-item label="Model">
          <el-select v-model="composeForm.model_ref" placeholder="选择模型包 Select Model Package" style="width: 100%">
            <el-option v-for="p in packages.model" :key="p.id" :label="`${p.name}@${p.version}`" :value="`ref://${p.name}@${p.version}`" />
          </el-select>
        </el-form-item>

        <el-form-item label="Signal">
          <el-select v-model="composeForm.signal_ref" placeholder="选择信号包 Select Signal Package" style="width: 100%">
            <el-option v-for="p in packages.signal" :key="p.id" :label="`${p.name}@${p.version}`" :value="`ref://${p.name}@${p.version}`" />
          </el-select>
        </el-form-item>

        <el-form-item label="Position">
          <el-select v-model="composeForm.position_ref" placeholder="选择仓位包 Select Position Package" style="width: 100%">
            <el-option v-for="p in packages.position" :key="p.id" :label="`${p.name}@${p.version}`" :value="`ref://${p.name}@${p.version}`" />
          </el-select>
        </el-form-item>

        <el-form-item label="Risk">
          <el-select v-model="composeForm.risk_ref" placeholder="选择风控包 Select Risk Package" style="width: 100%">
            <el-option v-for="p in packages.risk" :key="p.id" :label="`${p.name}@${p.version}`" :value="`ref://${p.name}@${p.version}`" />
          </el-select>
        </el-form-item>

        <el-form-item label="Execution">
          <el-select v-model="composeForm.execution_ref" placeholder="选择执行配置 Select Execution Profile" style="width: 100%">
            <el-option v-for="p in packages.execution" :key="p.id" :label="`${p.name}@${p.version}`" :value="`ref://${p.name}@${p.version}`" />
          </el-select>
        </el-form-item>

        <el-form-item label="Observe">
          <el-select v-model="composeForm.observe_ref" placeholder="选择观察配置 Select Observe Profile" style="width: 100%">
            <el-option v-for="p in packages.observe" :key="p.id" :label="`${p.name}@${p.version}`" :value="`ref://${p.name}@${p.version}`" />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 装配结果 -->
    <el-card v-if="composeResult" style="margin-bottom: 16px">
      <template #header>
        <div class="card-header">
          <span>装配结果 Compose Result</span>
          <el-tag :type="composeResult.success ? 'success' : 'danger'">
            {{ composeResult.success ? '成功 SUCCESS' : '失败 FAILED' }}
          </el-tag>
        </div>
      </template>

      <el-alert v-if="composeResult.success" type="success" :closable="false" show-icon>
        策略装配成功！Strategy ID: {{ composeResult.strategy_id }}
      </el-alert>

      <el-alert v-for="err in composeResult.errors" :key="err" type="error" :closable="false" show-icon style="margin-top: 8px">
        {{ err }}
      </el-alert>

      <div v-if="composeResult.validation" style="margin-top: 12px">
        <el-tag :type="composeResult.validation.passed ? 'success' : 'warning'">
          依赖验证: {{ composeResult.validation.passed ? '通过' : '未通过' }}
        </el-tag>
      </div>
    </el-card>

    <!-- 策略列表 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>策略列表 Strategy List</span>
          <el-button @click="loadStrategies" :loading="loadingStrategies">刷新 Refresh</el-button>
        </div>
      </template>

      <el-table :data="strategies" v-loading="loadingStrategies" border>
        <el-table-column prop="name" label="名称 Name" width="160" />
        <el-table-column prop="version" label="版本 Version" width="80" />
        <el-table-column label="状态 Status" width="100">
          <template #default="{ row }">
            <el-tag :type="strategyStatusType(row.config?.strategy_status)" size="small">
              {{ row.config?.strategy_status || 'candidate' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="验证 Validation" width="100">
          <template #default="{ row }">
            <el-tag :type="validationType(row.config?.validation)" size="small">
              {{ row.config?.validation || 'PENDING' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Model" width="150">
          <template #default="{ row }">
            <span class="ref-text">{{ row.config?.model || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="Signal" width="150">
          <template #default="{ row }">
            <span class="ref-text">{{ row.config?.signal || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="Position" width="150">
          <template #default="{ row }">
            <span class="ref-text">{{ row.config?.position || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作 Actions" width="260">
          <template #default="{ row }">
            <el-button size="small" @click="viewDependencies(row)">依赖图</el-button>
            <el-button size="small" type="primary" @click="validateStrategy(row)" :loading="validatingId === row.id">
              验证
            </el-button>
            <el-button size="small" type="success" @click="openBacktestDialog(row)" :loading="backtestingId === row.id">
              回测
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 依赖图对话框 -->
    <el-dialog v-model="depDialogVisible" title="依赖图 Dependency Graph" width="700px">
      <el-tree v-if="depGraph" :data="depTreeData" :props="{ label: 'label', children: 'children' }" default-expand-all>
        <template #default="{ data: node }">
          <span>
            <el-tag :type="node.exists ? 'success' : 'danger'" size="small">{{ node.type }}</el-tag>
            <span style="margin-left: 8px">{{ node.label }}</span>
            <span v-if="!node.exists" style="color: #f56c6c; margin-left: 8px">(缺失 missing)</span>
          </span>
        </template>
      </el-tree>
      <el-empty v-else description="无数据 No data" />
    </el-dialog>

    <!-- 验证报告对话框 -->
    <el-dialog v-model="validationDialogVisible" title="验证报告 Validation Report" width="700px">
      <div v-if="validationReport">
        <el-alert :type="validationReport.passed ? 'success' : 'error'" :closable="false" show-icon style="margin-bottom: 16px">
          {{ validationReport.passed ? '验证通过 PASSED' : '验证失败 FAILED' }}
        </el-alert>

        <h4>Smoke Test</h4>
        <el-table v-if="validationReport.smoke_test" :data="validationReport.smoke_test.checks || []" border size="small">
          <el-table-column prop="name" label="检查项 Check" />
          <el-table-column label="结果 Result" width="100">
            <template #default="{ row }">
              <el-tag :type="row.passed ? 'success' : 'danger'" size="small">{{ row.passed ? '✓' : '✗' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="detail" label="详情 Detail" />
        </el-table>

        <el-alert v-for="err in validationReport.errors" :key="err" type="error" :closable="false" show-icon style="margin-top: 8px">
          {{ err }}
        </el-alert>
      </div>
    </el-dialog>

    <!-- 回测参数对话框 -->
    <el-dialog v-model="backtestDialogVisible" title="回测参数 Backtest Parameters" width="560px" :close-on-click-modal="false">
      <el-form :model="backtestForm" label-width="110px" v-if="!backtestResult">
        <el-form-item label="策略 Strategy">
          <el-input :value="backtestTargetName" disabled />
        </el-form-item>

        <el-form-item label="数据源 Source">
          <el-radio-group v-model="backtestForm.data_source_mode" @change="onDataSourceChange">
            <el-radio value="dataset">真实数据集 Dataset</el-radio>
            <el-radio value="synthetic">合成数据 Synthetic</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 数据集选择 -->
        <template v-if="backtestForm.data_source_mode === 'dataset'">
          <el-form-item label="数据集 Dataset">
            <el-select v-model="backtestForm.dataset_id" placeholder="选择数据集" style="width: 100%" @change="onDatasetChange">
              <el-option v-for="ds in datasets" :key="ds.dataset_id" :value="ds.dataset_id"
                :label="`${ds.name} (${ds.symbols_count}标的, ${ds.rows}行, ${ds.frequency})`">
                <span>{{ ds.name }}</span>
                <el-tag size="small" type="info" style="margin-left: 8px">{{ ds.frequency }}</el-tag>
                <el-tag v-if="ds.is_multi_symbol" size="small" type="warning" style="margin-left: 4px">多标的</el-tag>
                <div style="font-size: 12px; color: #999; margin-top: 2px">
                  {{ ds.symbols_count }} symbols | {{ ds.start_date?.slice(0,10) }} ~ {{ ds.end_date?.slice(0,10) }}
                </div>
              </el-option>
            </el-select>
          </el-form-item>
          <el-form-item label="最大标的数" v-if="selectedDataset?.is_multi_symbol">
            <el-input-number v-model="backtestForm.max_symbols" :min="5" :max="200" :step="5" style="width: 100%" />
          </el-form-item>
          <el-form-item label="日期范围">
            <el-date-picker
              v-model="backtestDateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD"
              style="width: 100%"
              :disabled-date="(d: Date) => !isDateInDatasetRange(d)"
            />
          </el-form-item>
        </template>

        <!-- 合成数据参数 -->
        <template v-else>
          <el-form-item label="标的 Symbol">
            <el-input v-model="backtestForm.symbol" placeholder="如 BTCUSDT" />
          </el-form-item>
          <el-form-item label="K线数量 Bars">
            <el-input-number v-model="backtestForm.bars" :min="50" :max="2000" :step="50" style="width: 100%" />
          </el-form-item>
          <el-form-item label="随机种子 Seed">
            <el-input-number v-model="backtestForm.seed" :min="1" :max="99999" style="width: 100%" />
          </el-form-item>
        </template>

        <el-form-item label="初始资金 Capital">
          <el-input-number v-model="backtestForm.initial_capital" :min="10000" :max="100000000" :step="10000" style="width: 100%" />
        </el-form-item>

        <el-alert v-if="backtestForm.data_source_mode === 'synthetic'" type="info" :closable="false" show-icon style="margin-top: 8px">
          合成数据用于快速验证回测链路，使用几何布朗运动+趋势切换模型生成。
        </el-alert>
        <el-alert v-else-if="!backtestForm.dataset_id" type="warning" :closable="false" show-icon style="margin-top: 8px">
          请选择一个数据集。HS300 为沪深300成分股日线数据，支持多标的截面回测。
        </el-alert>
      </el-form>
      <template #footer>
        <el-button @click="backtestDialogVisible = false" :disabled="backtestRunning">取消</el-button>
        <el-button type="primary" @click="runBacktest" :loading="backtestRunning"
          :disabled="backtestForm.data_source_mode === 'dataset' && !backtestForm.dataset_id">
          开始回测 Run Backtest
        </el-button>
      </template>
    </el-dialog>

    <!-- 回测结果对话框 -->
    <el-dialog v-model="backtestResultVisible" title="回测结果 Backtest Result" width="950px" top="4vh" destroy-on-close>
      <div v-if="backtestResult">
        <el-alert v-if="backtestResult.ok" type="success" :closable="false" show-icon style="margin-bottom: 16px">
          <template #title>
            回测完成！{{ backtestResult.symbol }} | {{ backtestResult.bars }} bars
            <span v-if="backtestResult.symbols_traded > 1">（{{ backtestResult.symbols_traded }}只标的）</span>
            | 数据源: {{ backtestResult.data_source }}
          </template>
        </el-alert>
        <el-alert v-else type="error" :closable="false" show-icon style="margin-bottom: 16px">
          回测失败: {{ backtestResult.errors.join(', ') }}
        </el-alert>

        <!-- 指标卡片 -->
        <el-row :gutter="12" style="margin-bottom: 12px">
          <el-col :span="6">
            <div class="metric-card positive">
              <div class="metric-value">{{ formatPct(backtestResult.metrics.total_return) }}</div>
              <div class="metric-label">总收益 Total Return</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="metric-card" :class="backtestResult.metrics.sharpe_ratio >= 1 ? 'positive' : ''">
              <div class="metric-value">{{ backtestResult.metrics.sharpe_ratio?.toFixed(2) }}</div>
              <div class="metric-label">Sharpe Ratio</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="metric-card negative">
              <div class="metric-value">{{ formatPct(backtestResult.metrics.max_drawdown) }}</div>
              <div class="metric-label">最大回撤 Max DD</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="metric-card">
              <div class="metric-value">{{ backtestResult.total_orders }}</div>
              <div class="metric-label">交易笔数 Trades</div>
            </div>
          </el-col>
        </el-row>

        <el-row :gutter="12" style="margin-bottom: 12px">
          <el-col :span="6">
            <div class="metric-card">
              <div class="metric-value">{{ formatMoney(backtestResult.metrics.final_value) }}</div>
              <div class="metric-label">最终权益 Final Value</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="metric-card">
              <div class="metric-value">{{ formatPct(backtestResult.metrics.annual_return) }}</div>
              <div class="metric-label">年化收益 Annual</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="metric-card">
              <div class="metric-value">{{ formatPct(backtestResult.metrics.volatility) }}</div>
              <div class="metric-label">年化波动 Vol</div>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="metric-card" v-if="backtestResult.symbols_traded > 1">
              <div class="metric-value">{{ backtestResult.metrics.max_positions }} / {{ backtestResult.metrics.avg_positions?.toFixed(1) }}</div>
              <div class="metric-label">最大/平均持仓 Positions</div>
            </div>
            <div class="metric-card" v-else>
              <div class="metric-value">{{ backtestResult.metrics.buy_orders }} / {{ backtestResult.metrics.sell_orders }}</div>
              <div class="metric-label">买入/卖出 Buy/Sell</div>
            </div>
          </el-col>
        </el-row>

        <!-- 净值曲线图 -->
        <div class="chart-container">
          <div ref="equityChartRef" class="equity-chart"></div>
        </div>

        <!-- 订单列表 -->
        <el-divider>最近交易 Recent Orders（共 {{ backtestResult.total_orders }} 笔，显示最近 {{ backtestResult.orders.length }} 笔）</el-divider>
        <el-table :data="backtestResult.orders" border size="small" max-height="280">
          <el-table-column prop="timestamp" label="时间 Date" width="120" />
          <el-table-column prop="symbol" label="标的 Symbol" width="100" />
          <el-table-column label="方向 Side" width="80">
            <template #default="{ row }">
              <el-tag :type="row.side === 'BUY' ? 'success' : 'danger'" size="small">{{ row.side }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="quantity" label="数量 Qty" width="120">
            <template #default="{ row }">{{ typeof row.quantity === 'number' ? row.quantity.toFixed(2) : row.quantity }}</template>
          </el-table-column>
          <el-table-column prop="price" label="价格 Price" width="120">
            <template #default="{ row }">{{ typeof row.price === 'number' ? row.price.toFixed(2) : row.price }}</template>
          </el-table-column>
        </el-table>
      </div>
      <template #footer>
        <el-button @click="closeBacktestResult">关闭</el-button>
        <el-button type="primary" @click="reRunBacktest" :loading="backtestRunning">重新回测</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import {
  composeStrategy as composeStrategyApi, getStrategies, getPackages, validateStrategy as validateApi,
  getDependencies, runBacktest as runBacktestApi, getDatasets,
  type PackageManifest, type ComposeResult, type ValidationReport, type DependencyGraph,
  type BacktestResult, type DatasetInfo,
} from '@/api/strategyStudio'

// ==================================================================
// 装配表单
// ==================================================================

const composeForm = ref({
  name: '',
  family: '',
  version: '1.0',
  description: '',
  model_ref: '',
  signal_ref: '',
  position_ref: '',
  risk_ref: '',
  execution_ref: '',
  observe_ref: '',
})

const composing = ref(false)
const composeResult = ref<ComposeResult | null>(null)

const canCompose = computed(() => {
  const f = composeForm.value
  return f.name && f.model_ref && f.signal_ref && f.position_ref && f.risk_ref && f.execution_ref && f.observe_ref
})

const composeStep = computed(() => {
  const f = composeForm.value
  let step = 0
  if (f.model_ref) step = 1
  if (f.signal_ref) step = 2
  if (f.position_ref) step = 3
  if (f.risk_ref) step = 4
  if (f.execution_ref) step = 5
  if (f.observe_ref) step = 6
  return step
})

async function composeStrategy() {
  composing.value = true
  try {
    composeResult.value = await composeStrategyApi({
      ...composeForm.value,
      auto_validate: true,
    })
    if (composeResult.value.success) {
      ElMessage.success(`策略装配成功: ${composeResult.value.strategy_id}`)
      loadStrategies()
    } else {
      ElMessage.error('策略装配失败')
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '装配失败 Compose failed')
  } finally {
    composing.value = false
  }
}

// ==================================================================
// Package 列表
// ==================================================================

const packages = ref<{
  model: PackageManifest[]
  signal: PackageManifest[]
  position: PackageManifest[]
  risk: PackageManifest[]
  execution: PackageManifest[]
  observe: PackageManifest[]
}>({
  model: [], signal: [], position: [], risk: [], execution: [], observe: [],
})

async function loadAllPackages() {
  try {
    const [model, signal, position, risk, execution, observe] = await Promise.all([
      getPackages('MODEL'),
      getPackages('SIGNAL'),
      getPackages('POSITION'),
      getPackages('RISK'),
      getPackages('EXECUTION'),
      getPackages('OBSERVE'),
    ])
    packages.value = {
      model: model.packages || [],
      signal: signal.packages || [],
      position: position.packages || [],
      risk: risk.packages || [],
      execution: execution.packages || [],
      observe: observe.packages || [],
    }
  } catch (e) {
    ElMessage.error('加载 Package 列表失败 Failed to load packages')
  }
}

// ==================================================================
// 策略列表
// ==================================================================

const strategies = ref<PackageManifest[]>([])
const loadingStrategies = ref(false)

async function loadStrategies() {
  loadingStrategies.value = true
  try {
    const resp = await getStrategies()
    strategies.value = resp.strategies || []
  } catch (e) {
    ElMessage.error('加载策略列表失败 Failed to load strategies')
  } finally {
    loadingStrategies.value = false
  }
}

// ==================================================================
// 依赖图
// ==================================================================

const depDialogVisible = ref(false)
const depGraph = ref<DependencyGraph | null>(null)

const depTreeData = computed(() => {
  if (!depGraph.value) return []
  const buildNode = (n: any): any => ({
    label: `${n.name}@${n.version}`,
    type: n.type,
    exists: n.exists,
    children: (n.children || []).map(buildNode),
  })
  return [buildNode(depGraph.value.root)]
})

async function viewDependencies(row: PackageManifest) {
  try {
    depGraph.value = await getDependencies(row.name, row.version)
    depDialogVisible.value = true
  } catch (e) {
    ElMessage.error('加载依赖图失败 Failed to load dependencies')
  }
}

// ==================================================================
// 验证
// ==================================================================

const validationDialogVisible = ref(false)
const validationReport = ref<ValidationReport | null>(null)
const validatingId = ref('')

async function validateStrategy(row: PackageManifest) {
  validatingId.value = row.id
  try {
    validationReport.value = await validateApi({
      name: row.name,
      version: row.version,
      smoke_test_bars: 100,
    })
    validationDialogVisible.value = true
    if (validationReport.value.passed) {
      ElMessage.success('验证通过 Validation passed')
      loadStrategies()
    } else {
      ElMessage.warning('验证失败 Validation failed')
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '验证失败 Validation failed')
  } finally {
    validatingId.value = ''
  }
}

// ==================================================================
// 回测
// ==================================================================

const backtestDialogVisible = ref(false)
const backtestResultVisible = ref(false)
const backtestRunning = ref(false)
const backtestingId = ref('')
const backtestTarget = ref<PackageManifest | null>(null)
const datasets = ref<DatasetInfo[]>([])
const backtestDateRange = ref<[string, string] | null>(null)

interface BacktestFormData {
  data_source_mode: 'dataset' | 'synthetic'
  dataset_id: string
  max_symbols: number
  start_date: string
  end_date: string
  symbol: string
  bars: number
  initial_capital: number
  seed: number
}

const backtestForm = ref<BacktestFormData>({
  data_source_mode: 'dataset',
  dataset_id: '',
  max_symbols: 30,
  start_date: '',
  end_date: '',
  symbol: 'BTCUSDT',
  bars: 500,
  initial_capital: 1000000,
  seed: 42,
})

const selectedDataset = computed<DatasetInfo | null>(() => {
  if (!backtestForm.value.dataset_id) return null
  return datasets.value.find(d => d.dataset_id === backtestForm.value.dataset_id) || null
})

const backtestResult = ref<BacktestResult | null>(null)
const equityChartRef = ref<HTMLElement | null>(null)
let equityChart: echarts.ECharts | null = null

const backtestTargetName = computed(() => {
  if (!backtestTarget.value) return ''
  return `${backtestTarget.value.name}@${backtestTarget.value.version}`
})

async function loadDatasets() {
  try {
    const resp = await getDatasets()
    datasets.value = resp.datasets
    // 默认选择第一个多标的数据集（如HS300）
    const multi = resp.datasets.find(d => d.is_multi_symbol)
    if (multi && !backtestForm.value.dataset_id) {
      backtestForm.value.dataset_id = multi.dataset_id
      backtestForm.value.start_date = multi.end_date
        ? new Date(new Date(multi.end_date).getTime() - 365 * 24 * 3600 * 1000).toISOString().slice(0, 10)
        : ''
      backtestForm.value.end_date = multi.end_date?.slice(0, 10) || ''
      backtestDateRange.value = backtestForm.value.start_date && backtestForm.value.end_date
        ? [backtestForm.value.start_date, backtestForm.value.end_date]
        : null
    }
  } catch (e: any) {
    console.warn('Failed to load datasets:', e)
  }
}

function onDataSourceChange() {
  if (backtestForm.value.data_source_mode === 'synthetic') {
    backtestForm.value.initial_capital = 100000
  } else {
    backtestForm.value.initial_capital = 1000000
  }
}

function onDatasetChange() {
  const ds = selectedDataset.value
  if (ds) {
    backtestForm.value.start_date = ds.start_date?.slice(0, 10) || ''
    backtestForm.value.end_date = ds.end_date?.slice(0, 10) || ''
    backtestDateRange.value = [backtestForm.value.start_date, backtestForm.value.end_date]
  }
}

function isDateInDatasetRange(d: Date): boolean {
  const ds = selectedDataset.value
  if (!ds) return true
  const ts = d.getTime()
  if (ds.start_date) {
    const start = new Date(ds.start_date).getTime()
    if (ts < start) return true // disable dates before start
  }
  return false
}

function openBacktestDialog(row: PackageManifest) {
  backtestTarget.value = row
  backtestForm.value = {
    data_source_mode: 'dataset',
    dataset_id: backtestForm.value.dataset_id || '',
    max_symbols: 30,
    start_date: backtestForm.value.start_date || '',
    end_date: backtestForm.value.end_date || '',
    symbol: 'BTCUSDT',
    bars: 500,
    initial_capital: 1000000,
    seed: 42,
  }
  if (backtestForm.value.dataset_id) {
    onDatasetChange()
  }
  backtestResult.value = null
  backtestDialogVisible.value = true
  loadDatasets()
}

async function runBacktest() {
  if (!backtestTarget.value) return
  backtestRunning.value = true
  backtestingId.value = backtestTarget.value.id
  try {
    let startDate = ''
    let endDate = ''
    if (backtestDateRange.value) {
      startDate = backtestDateRange.value[0]
      endDate = backtestDateRange.value[1]
    }

    let reqParams: any
    if (backtestForm.value.data_source_mode === 'dataset') {
      reqParams = {
        name: backtestTarget.value.name,
        version: backtestTarget.value.version,
        dataset_id: backtestForm.value.dataset_id,
        max_symbols: backtestForm.value.max_symbols,
        start_date: startDate,
        end_date: endDate,
        initial_capital: backtestForm.value.initial_capital,
      }
    } else {
      reqParams = {
        name: backtestTarget.value.name,
        version: backtestTarget.value.version,
        symbol: backtestForm.value.symbol,
        bars: backtestForm.value.bars,
        seed: backtestForm.value.seed,
        initial_capital: backtestForm.value.initial_capital,
      }
    }

    backtestResult.value = await runBacktestApi(reqParams)
    backtestDialogVisible.value = false
    backtestResultVisible.value = true
    ElMessage.success(backtestResult.value.ok ? '回测完成 Backtest complete' : '回测有错误 Backtest with errors')
    await nextTick()
    renderEquityChart()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '回测失败 Backtest failed')
  } finally {
    backtestRunning.value = false
    backtestingId.value = ''
  }
}

function reRunBacktest() {
  backtestResultVisible.value = false
  backtestResult.value = null
  backtestDialogVisible.value = true
  if (equityChart) {
    equityChart.dispose()
    equityChart = null
  }
}

function closeBacktestResult() {
  backtestResultVisible.value = false
  if (equityChart) {
    equityChart.dispose()
    equityChart = null
  }
}

function renderEquityChart() {
  if (!equityChartRef.value || !backtestResult.value) return
  if (equityChart) equityChart.dispose()
  equityChart = echarts.init(equityChartRef.value)

  const curve = backtestResult.value.equity_curve
  const dates = curve.map(p => p.timestamp)
  const values = curve.map(p => p.value)
  const positions = curve.map(p => p.n_positions || 0)
  const initialCapital = backtestResult.value.initial_capital
  const baseline = curve.map(() => initialCapital)
  const isMulti = backtestResult.value.symbols_traded > 1

  const series: any[] = [
    {
      name: '策略净值',
      type: 'line',
      data: values,
      smooth: true,
      showSymbol: false,
      lineStyle: { width: 2, color: '#409EFF' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(64,158,255,0.3)' },
          { offset: 1, color: 'rgba(64,158,255,0.02)' },
        ]),
      },
    },
    {
      name: '初始资金',
      type: 'line',
      data: baseline,
      showSymbol: false,
      lineStyle: { width: 1, color: '#E6A23C', type: 'dashed' },
    },
  ]

  const legendData = ['策略净值', '初始资金']
  const yAxisConfig: any[] = [
    {
      type: 'value',
      scale: true,
      name: '净值',
      axisLabel: { formatter: (v: number) => formatMoney(v) },
    },
  ]

  if (isMulti && positions.some(p => p > 0)) {
    series.push({
      name: '持仓数',
      type: 'line',
      data: positions,
      yAxisIndex: 1,
      showSymbol: false,
      lineStyle: { width: 1, color: '#67C23A', type: 'dotted' },
    })
    legendData.push('持仓数')
    yAxisConfig.push({
      type: 'value',
      name: '持仓',
      position: 'right',
      axisLabel: { formatter: (v: number) => v.toFixed(0) },
      splitLine: { show: false },
    })
  }

  equityChart.setOption({
    title: { text: `净值曲线 Equity Curve (${backtestResult.value.symbols_traded} symbols)`, left: 'center', textStyle: { fontSize: 14 } },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const date = params[0]?.axisValue || ''
        let html = `<b>${date}</b><br/>`
        params.forEach((p: any) => {
          const val = p.seriesName === '持仓数' ? p.value.toFixed(0) : formatMoney(p.value)
          html += `${p.marker} ${p.seriesName}: ${val}<br/>`
        })
        return html
      },
    },
    legend: { data: legendData, bottom: 0 },
    grid: { left: 60, right: isMulti ? 50 : 20, top: 40, bottom: 40 },
    xAxis: { type: 'category', data: dates, axisLabel: { rotate: 30, fontSize: 10 } },
    yAxis: yAxisConfig,
    series,
  })

  setTimeout(() => equityChart?.resize(), 100)
}

// ==================================================================
// 工具
// ==================================================================

function strategyStatusType(s: string): string {
  if (s === 'validated') return 'success'
  if (s === 'deployed') return 'primary'
  if (s === 'archived') return 'info'
  return 'warning'
}

function validationType(v: string): string {
  if (v === 'PASS') return 'success'
  if (v === 'FAIL') return 'danger'
  return 'warning'
}

function formatPct(v: number | undefined): string {
  if (v === undefined || v === null) return 'N/A'
  return (v * 100).toFixed(2) + '%'
}

function formatMoney(v: number | undefined): string {
  if (v === undefined || v === null) return 'N/A'
  if (v >= 1000000) return (v / 1000000).toFixed(2) + 'M'
  if (v >= 1000) return (v / 1000).toFixed(1) + 'K'
  return v.toFixed(2)
}

// ==================================================================
// 初始化
// ==================================================================

onMounted(() => {
  loadAllPackages()
  loadStrategies()
  loadDatasets()
})
</script>

<style scoped>
.panel-header {
  margin-bottom: 16px;
}

.panel-header h2 {
  margin: 0 0 8px 0;
}

.hint {
  color: #909399;
  font-size: 13px;
  margin: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.ref-text {
  font-family: monospace;
  font-size: 12px;
  color: #606266;
}

.metric-card {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 16px 12px;
  text-align: center;
}

.metric-card.positive {
  background: linear-gradient(135deg, #f0f9eb 0%, #e1f3d8 100%);
}

.metric-card.negative {
  background: linear-gradient(135deg, #fef0f0 0%, #fde2e2 100%);
}

.metric-value {
  font-size: 22px;
  font-weight: 700;
  color: #303133;
  margin-bottom: 4px;
}

.metric-label {
  font-size: 12px;
  color: #909399;
}

.chart-container {
  margin: 16px 0;
}

.equity-chart {
  width: 100%;
  height: 350px;
}

.order-hint {
  text-align: center;
  color: #909399;
  font-size: 12px;
  margin-top: 8px;
}
</style>
