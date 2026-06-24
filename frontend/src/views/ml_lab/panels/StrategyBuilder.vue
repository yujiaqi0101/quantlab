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
        <el-table-column prop="name" label="名称 Name" width="200" />
        <el-table-column prop="version" label="版本 Version" width="100" />
        <el-table-column label="状态 Status" width="120">
          <template #default="{ row }">
            <el-tag :type="strategyStatusType(row.config?.strategy_status)" size="small">
              {{ row.config?.strategy_status || 'candidate' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="验证 Validation" width="120">
          <template #default="{ row }">
            <el-tag :type="validationType(row.config?.validation)" size="small">
              {{ row.config?.validation || 'PENDING' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Model" width="180">
          <template #default="{ row }">
            <span class="ref-text">{{ row.config?.model || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="Signal" width="180">
          <template #default="{ row }">
            <span class="ref-text">{{ row.config?.signal || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="Position" width="180">
          <template #default="{ row }">
            <span class="ref-text">{{ row.config?.position || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作 Actions" width="200">
          <template #default="{ row }">
            <el-button size="small" @click="viewDependencies(row)">依赖图</el-button>
            <el-button size="small" type="primary" @click="validateStrategy(row)" :loading="validatingId === row.id">
              验证
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  composeStrategy as composeStrategyApi, getStrategies, getPackages, validateStrategy as validateApi,
  getDependencies,
  type PackageManifest, type ComposeResult, type ValidationReport, type DependencyGraph,
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

// ==================================================================
// 初始化
// ==================================================================

onMounted(() => {
  loadAllPackages()
  loadStrategies()
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
</style>
