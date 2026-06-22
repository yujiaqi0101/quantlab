<template>
  <div class="performance-view">
    <!-- 顶部控制栏 -->
    <el-card shadow="never" class="control-bar">
      <div class="control-row">
        <div class="control-left">
          <el-select
            v-model="sessionId"
            placeholder="选择会话 Select session"
            filterable
            style="width: 280px"
            @change="loadAll"
          >
            <el-option
              v-for="s in sessions"
              :key="s.session_id"
              :label="`${s.session_id} (${s.strategy || '-'})`"
              :value="s.session_id"
            />
          </el-select>
          <el-button @click="loadSessions" :icon="Refresh" plain>刷新会话 Refresh</el-button>
          <el-button
            v-if="sessionId"
            @click="loadAll"
            :icon="Refresh"
            type="primary"
          >
            重新分析 Re-analyze
          </el-button>
        </div>
        <div class="control-right">
          <el-button @click="openMonthly" :icon="Document">月度报告</el-button>
        </div>
      </div>
    </el-card>

    <!-- 核心指标 -->
    <el-row :gutter="12" v-if="strategyReport" class="metrics-row">
      <el-col :span="6">
        <el-card shadow="never" class="metric-card">
          <div class="metric-label">总收益</div>
          <div class="metric-value" :class="pnlClass(strategyReport.total_pnl)">
            {{ formatNum(strategyReport.total_pnl) }}
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="metric-card">
          <div class="metric-label">交易笔数</div>
          <div class="metric-value">{{ strategyReport.total_trades }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="metric-card">
          <div class="metric-label">策略数量</div>
          <div class="metric-value">{{ strategyReport.strategies.length }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="metric-card">
          <div class="metric-label">集中度 (HHI)</div>
          <div class="metric-value" :class="concentrationClass(strategyReport.concentration)">
            {{ (strategyReport.concentration * 100).toFixed(1) }}%
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-empty v-if="!sessionId" description="请选择会话开始绩效归因分析" />

    <template v-else>
      <!-- 策略贡献图 -->
      <el-card shadow="never" class="section-card" v-if="strategyReport">
        <template #header>
          <div class="card-header">
            <span>策略归因 (Strategy Attribution)</span>
            <el-tag v-if="strategyReport.best_strategy" type="success" size="small">
              最佳: {{ strategyReport.best_strategy }}
            </el-tag>
          </div>
        </template>
        <el-table :data="strategyReport.strategies" size="small" stripe>
          <el-table-column prop="strategy" label="策略" min-width="140" />
          <el-table-column label="PnL" width="110">
            <template #default="{ row }">
              <span :class="pnlClass(row.pnl)">{{ formatNum(row.pnl) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="收益贡献" width="180">
            <template #default="{ row }">
              <div class="bar-cell">
                <div class="bar-bg">
                  <div
                    class="bar-fill"
                    :class="pnlClass(row.pnl_pct)"
                    :style="{ width: Math.min(Math.abs(row.pnl_pct), 100) + '%' }"
                  ></div>
                </div>
                <span class="bar-text">{{ row.pnl_pct.toFixed(1) }}%</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="n_trades" label="交易数" width="80" />
          <el-table-column label="胜率" width="100">
            <template #default="{ row }">
              {{ (row.win_rate * 100).toFixed(1) }}%
            </template>
          </el-table-column>
          <el-table-column label="盈亏比" width="90">
            <template #default="{ row }">
              {{ row.profit_factor.toFixed(2) }}
            </template>
          </el-table-column>
          <el-table-column label="风险贡献" width="160">
            <template #default="{ row }">
              <div class="bar-cell">
                <div class="bar-bg">
                  <div
                    class="bar-fill risk"
                    :style="{ width: Math.min(row.risk_pct, 100) + '%' }"
                  ></div>
                </div>
                <span class="bar-text">{{ row.risk_pct.toFixed(1) }}%</span>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 品种贡献图 + 多空归因 -->
      <el-row :gutter="12" v-if="symbolReport">
        <el-col :span="16">
          <el-card shadow="never" class="section-card">
            <template #header>
              <div class="card-header">
                <span>品种归因 (Symbol Leaderboard)</span>
                <el-tag v-if="symbolReport.best_symbol" type="success" size="small">
                  最佳: {{ symbolReport.best_symbol }}
                </el-tag>
              </div>
            </template>
            <el-table :data="symbolReport.symbols" size="small" stripe>
              <el-table-column prop="symbol" label="品种" width="120" />
              <el-table-column label="PnL" width="110">
                <template #default="{ row }">
                  <span :class="pnlClass(row.pnl)">{{ formatNum(row.pnl) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="占比" width="150">
                <template #default="{ row }">
                  <div class="bar-cell">
                    <div class="bar-bg">
                      <div
                        class="bar-fill"
                        :class="pnlClass(row.pnl_pct)"
                        :style="{ width: Math.min(Math.abs(row.pnl_pct), 100) + '%' }"
                      ></div>
                    </div>
                    <span class="bar-text">{{ row.pnl_pct.toFixed(1) }}%</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="n_trades" label="交易数" width="80" />
              <el-table-column label="胜率" width="90">
                <template #default="{ row }">
                  {{ (row.win_rate * 100).toFixed(1) }}%
                </template>
              </el-table-column>
              <el-table-column label="多头" width="100">
                <template #default="{ row }">
                  <span :class="pnlClass(row.long_pnl)">{{ formatNum(row.long_pnl) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="空头" width="100">
                <template #default="{ row }">
                  <span :class="pnlClass(row.short_pnl)">{{ formatNum(row.short_pnl) }}</span>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="never" class="section-card">
            <template #header>多空归因 (Long / Short)</template>
            <div class="ls-block" v-if="symbolReport.long_short">
              <div class="ls-row">
                <span class="ls-label">多头 PnL</span>
                <span class="ls-value" :class="pnlClass(symbolReport.long_short.long_pnl)">
                  {{ formatNum(symbolReport.long_short.long_pnl) }}
                </span>
                <span class="ls-count">({{ symbolReport.long_short.n_long }} 笔)</span>
              </div>
              <div class="ls-row">
                <span class="ls-label">空头 PnL</span>
                <span class="ls-value" :class="pnlClass(symbolReport.long_short.short_pnl)">
                  {{ formatNum(symbolReport.long_short.short_pnl) }}
                </span>
                <span class="ls-count">({{ symbolReport.long_short.n_short }} 笔)</span>
              </div>
              <el-divider />
              <div class="ls-row">
                <span class="ls-label">多头胜率</span>
                <span class="ls-value">
                  {{ (symbolReport.long_short.long_win_rate * 100).toFixed(1) }}%
                </span>
              </div>
              <div class="ls-row">
                <span class="ls-label">空头胜率</span>
                <span class="ls-value">
                  {{ (symbolReport.long_short.short_win_rate * 100).toFixed(1) }}%
                </span>
              </div>
              <el-divider />
              <div class="ls-note">
                <el-tag :type="biasTagType(symbolReport.long_short.bias)" size="small">
                  {{ biasLabel(symbolReport.long_short.bias) }}
                </el-tag>
                <span class="ls-note-text">{{ symbolReport.long_short.note }}</span>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 时段归因 + Regime 归因 -->
      <el-row :gutter="12" v-if="timeReport">
        <el-col :span="12">
          <el-card shadow="never" class="section-card">
            <template #header>
              <div class="card-header">
                <span>时段归因 (Time Attribution)</span>
                <el-tag v-if="timeReport.best_slot" type="success" size="small">
                  最佳: {{ slotLabel(timeReport.best_slot) }}
                </el-tag>
              </div>
            </template>
            <el-table :data="timeReport.time_slots" size="small" stripe>
              <el-table-column prop="label" label="时段" width="100" />
              <el-table-column label="PnL" width="120">
                <template #default="{ row }">
                  <span :class="pnlClass(row.pnl)">{{ formatNum(row.pnl) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="占比" width="160">
                <template #default="{ row }">
                  <div class="bar-cell">
                    <div class="bar-bg">
                      <div
                        class="bar-fill"
                        :class="pnlClass(row.pnl_pct)"
                        :style="{ width: Math.min(Math.abs(row.pnl_pct), 100) + '%' }"
                      ></div>
                    </div>
                    <span class="bar-text">{{ row.pnl_pct.toFixed(1) }}%</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="n_trades" label="交易数" width="80" />
              <el-table-column label="胜率" width="100">
                <template #default="{ row }">
                  {{ (row.win_rate * 100).toFixed(1) }}%
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card shadow="never" class="section-card">
            <template #header>
              <div class="card-header">
                <span>市场状态归因 (Regime Attribution)</span>
              </div>
            </template>
            <el-table :data="timeReport.regimes" size="small" stripe>
              <el-table-column prop="label" label="状态" width="100" />
              <el-table-column label="PnL" width="120">
                <template #default="{ row }">
                  <span :class="pnlClass(row.pnl)">{{ formatNum(row.pnl) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="占比" width="160">
                <template #default="{ row }">
                  <div class="bar-cell">
                    <div class="bar-bg">
                      <div
                        class="bar-fill"
                        :class="pnlClass(row.pnl_pct)"
                        :style="{ width: Math.min(Math.abs(row.pnl_pct), 100) + '%' }"
                      ></div>
                    </div>
                    <span class="bar-text">{{ row.pnl_pct.toFixed(1) }}%</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="n_trades" label="交易数" width="80" />
              <el-table-column label="时长占比" width="100">
                <template #default="{ row }">
                  {{ row.duration_pct.toFixed(1) }}%
                </template>
              </el-table-column>
            </el-table>
            <div v-if="timeReport.regime_note" class="regime-note">
              <el-alert
                :title="timeReport.regime_note"
                type="info"
                :closable="false"
                show-icon
              />
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 风险归因 -->
      <el-card shadow="never" class="section-card" v-if="riskReport">
        <template #header>
          <div class="card-header">
            <span>风险归因 (Risk Attribution)</span>
            <el-tag v-if="riskReport.worst_quality_strategy" type="danger" size="small">
              质量最差: {{ riskReport.worst_quality_strategy }}
            </el-tag>
          </div>
        </template>
        <el-table :data="riskReport.risk_contributions" size="small" stripe>
          <el-table-column prop="strategy" label="策略" min-width="140" />
          <el-table-column label="收益贡献" width="120">
            <template #default="{ row }">
              {{ row.pnl_pct.toFixed(1) }}%
            </template>
          </el-table-column>
          <el-table-column label="风险贡献" width="120">
            <template #default="{ row }">
              {{ row.risk_pct.toFixed(1) }}%
            </template>
          </el-table-column>
          <el-table-column label="收益质量" width="100">
            <template #default="{ row }">
              <el-tag :type="qualityTagType(row.quality_label)" size="small">
                {{ qualityLabel(row.quality_label) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="质量比" width="100">
            <template #default="{ row }">
              {{ row.quality_ratio.toFixed(2) }}
            </template>
          </el-table-column>
          <el-table-column label="Sharpe" width="100">
            <template #default="{ row }">
              {{ row.sharpe.toFixed(2) }}
            </template>
          </el-table-column>
          <el-table-column label="PnL 波动率" width="120">
            <template #default="{ row }">
              {{ formatNum(row.pnl_std) }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 回撤归因 -->
      <el-card shadow="never" class="section-card" v-if="riskReport && riskReport.drawdown_contributions.length">
        <template #header>
          <div class="card-header">
            <span>回撤归因 (Drawdown Attribution)</span>
            <el-tag v-if="riskReport.drawdown_culprit" type="danger" size="small">
              元凶: {{ riskReport.drawdown_culprit }}
            </el-tag>
          </div>
        </template>
        <el-table :data="riskReport.drawdown_contributions" size="small" stripe>
          <el-table-column prop="strategy" label="策略" min-width="140" />
          <el-table-column label="最大回撤" width="140">
            <template #default="{ row }">
              <span class="text-danger">{{ formatNum(row.max_drawdown) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="占比" width="160">
            <template #default="{ row }">
              <div class="bar-cell">
                <div class="bar-bg">
                  <div
                    class="bar-fill danger"
                    :style="{ width: Math.min(Math.abs(row.drawdown_pct), 100) + '%' }"
                  ></div>
                </div>
                <span class="bar-text">{{ row.drawdown_pct.toFixed(1) }}%</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="n_trades" label="交易数" width="80" />
          <el-table-column label="回撤时长" width="120">
            <template #default="{ row }">
              {{ formatDuration(row.duration_ms) }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 因子归因（预留） -->
      <el-card shadow="never" class="section-card" v-if="factorReport">
        <template #header>因子归因 (Factor Attribution)</template>
        <el-alert
          v-if="!factorReport.implemented"
          :title="factorReport.note"
          type="info"
          :closable="false"
          show-icon
        />
        <el-table v-else :data="factorReport.factors" size="small" stripe>
          <el-table-column prop="label" label="因子" width="120" />
          <el-table-column label="PnL" width="120">
            <template #default="{ row }">
              <span :class="pnlClass(row.pnl)">{{ formatNum(row.pnl) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="贡献" width="120">
            <template #default="{ row }">
              {{ row.pnl_pct.toFixed(1) }}%
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <!-- 月度报告对话框 -->
    <el-dialog
      v-model="monthlyVisible"
      title="月度报告"
      width="80%"
      :close-on-click-modal="false"
    >
      <div class="monthly-control">
        <el-date-picker
          v-model="monthlyPeriod"
          type="month"
          placeholder="选择月份"
          format="YYYY-MM"
          value-format="YYYY-MM"
        />
        <el-button @click="loadMonthly" type="primary">生成</el-button>
        <el-button @click="exportMd" :disabled="!monthlyReport">导出 Markdown</el-button>
        <el-button @click="exportHtml" :disabled="!monthlyReport">导出 HTML</el-button>
      </div>
      <el-divider />
      <div v-if="monthlyReport" class="monthly-content">
        <el-descriptions :column="4" border size="small">
          <el-descriptions-item label="期间">{{ monthlyReport.period_label }}</el-descriptions-item>
          <el-descriptions-item label="总收益">
            <span :class="pnlClass(monthlyReport.total_pnl)">
              {{ formatNum(monthlyReport.total_pnl) }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="交易数">{{ monthlyReport.total_trades }}</el-descriptions-item>
          <el-descriptions-item label="胜率">
            {{ (monthlyReport.win_rate * 100).toFixed(1) }}%
          </el-descriptions-item>
          <el-descriptions-item label="最大回撤">
            <span class="text-danger">{{ formatNum(monthlyReport.max_drawdown) }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="盈亏比">
            {{ monthlyReport.profit_factor.toFixed(2) }}
          </el-descriptions-item>
          <el-descriptions-item label="平均单笔">
            {{ formatNum(monthlyReport.avg_pnl) }}
          </el-descriptions-item>
          <el-descriptions-item label="最佳交易" v-if="monthlyReport.best_trade">
            {{ monthlyReport.best_trade.symbol }}
            <span :class="pnlClass(monthlyReport.best_trade.pnl)">
              {{ formatNum(monthlyReport.best_trade.pnl) }}
            </span>
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="monthlyReport.summary" class="monthly-summary">
          <strong>总结：</strong>{{ monthlyReport.summary }}
        </div>

        <div v-if="monthlyReport.suggestions.length" class="monthly-suggestions">
          <strong>改进建议：</strong>
          <ul>
            <li v-for="(s, i) in monthlyReport.suggestions" :key="i">{{ s }}</li>
          </ul>
        </div>

        <el-tabs v-model="monthlyTab" class="monthly-tabs">
          <el-tab-pane label="Markdown" name="md">
            <pre class="md-preview">{{ monthlyMd }}</pre>
          </el-tab-pane>
          <el-tab-pane label="HTML" name="html">
            <iframe
              v-if="monthlyHtml"
              :srcdoc="monthlyHtml"
              class="html-preview"
            />
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Refresh, Document } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { observeApi } from '@/api/observe'
import type {
  SessionInfo,
  StrategyAttributionReport,
  SymbolAttributionReport,
  TimeAttributionReport,
  RiskAttributionReport,
  FactorAttributionReport,
  MonthlyReport,
} from '@/api/observe'

// 状态
const sessions = ref<SessionInfo[]>([])
const sessionId = ref<string>('')

const strategyReport = ref<StrategyAttributionReport | null>(null)
const symbolReport = ref<SymbolAttributionReport | null>(null)
const timeReport = ref<TimeAttributionReport | null>(null)
const riskReport = ref<RiskAttributionReport | null>(null)
const factorReport = ref<FactorAttributionReport | null>(null)

// 月度报告
const monthlyVisible = ref(false)
const monthlyPeriod = ref<string>('')
const monthlyReport = ref<MonthlyReport | null>(null)
const monthlyMd = ref('')
const monthlyHtml = ref('')
const monthlyTab = ref('md')

// ------------------------------------------------------------------
// 加载
// ------------------------------------------------------------------

async function loadSessions() {
  try {
    const res = await observeApi.listSessions({ limit: 200 })
    sessions.value = res.sessions
  } catch (e: any) {
    ElMessage.error('加载会话失败: ' + (e.message || e))
  }
}

async function loadAll() {
  if (!sessionId.value) return
  try {
    const [strategy, symbol, time, risk, factor] = await Promise.all([
      observeApi.attributionStrategy(sessionId.value),
      observeApi.attributionSymbol(sessionId.value),
      observeApi.attributionTime(sessionId.value),
      observeApi.attributionRisk(sessionId.value),
      observeApi.attributionFactor(sessionId.value),
    ])
    strategyReport.value = strategy
    symbolReport.value = symbol
    timeReport.value = time
    riskReport.value = risk
    factorReport.value = factor
  } catch (e: any) {
    ElMessage.error('归因分析失败: ' + (e.message || e))
  }
}

// ------------------------------------------------------------------
// 月度报告
// ------------------------------------------------------------------

function openMonthly() {
  const now = new Date()
  monthlyPeriod.value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
  monthlyVisible.value = true
}

async function loadMonthly() {
  if (!monthlyPeriod.value) return
  const [year, month] = monthlyPeriod.value.split('-').map(Number)
  try {
    const [report, md, html] = await Promise.all([
      observeApi.attributionMonthly({ year, month }),
      observeApi.attributionMonthlyMd({ year, month }),
      observeApi.attributionMonthlyHtml({ year, month }),
    ])
    monthlyReport.value = report
    monthlyMd.value = md.markdown
    monthlyHtml.value = html.html
  } catch (e: any) {
    ElMessage.error('生成月度报告失败: ' + (e.message || e))
  }
}

function exportMd() {
  if (!monthlyMd.value) return
  download(`${monthlyPeriod.value}_monthly.md`, monthlyMd.value, 'text/markdown')
}

function exportHtml() {
  if (!monthlyHtml.value) return
  download(`${monthlyPeriod.value}_monthly.html`, monthlyHtml.value, 'text/html')
}

function download(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

// ------------------------------------------------------------------
// 格式化
// ------------------------------------------------------------------

function formatNum(n: number | null | undefined): string {
  if (n === null || n === undefined) return '-'
  return n.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

function pnlClass(n: number | null | undefined): string {
  if (n === null || n === undefined || n === 0) return 'text-neutral'
  return n > 0 ? 'text-profit' : 'text-loss'
}

function concentrationClass(c: number): string {
  if (c > 0.5) return 'text-loss'
  if (c > 0.3) return 'text-warning'
  return 'text-profit'
}

function slotLabel(slot: string): string {
  return { asia: '亚洲', europe: '欧洲', america: '美洲' }[slot] || slot
}

function biasLabel(bias: string): string {
  return {
    long_only: '仅做多',
    short_only: '仅做空',
    long_bias: '多头偏好',
    short_bias: '空头偏好',
    balanced: '多空均衡',
  }[bias] || bias
}

function biasTagType(bias: string): 'success' | 'warning' | 'info' | 'danger' {
  if (bias === 'long_bias' || bias === 'short_bias') return 'warning'
  if (bias === 'balanced') return 'success'
  return 'info'
}

function qualityLabel(label: string): string {
  return { good: '好', bad: '差', neutral: '中' }[label] || label
}

function qualityTagType(label: string): 'success' | 'danger' | 'info' {
  if (label === 'good') return 'success'
  if (label === 'bad') return 'danger'
  return 'info'
}

function formatDuration(ms: number): string {
  if (!ms) return '-'
  const seconds = Math.floor(ms / 1000)
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  if (h > 0) return `${h}h${m}m`
  return `${m}m`
}

onMounted(() => {
  loadSessions()
})
</script>

<style scoped>
.performance-view {
  padding: 12px;
}

.control-bar {
  margin-bottom: 12px;
}

.control-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.control-left {
  display: flex;
  gap: 8px;
  align-items: center;
}

.metrics-row {
  margin-bottom: 12px;
}

.metric-card {
  text-align: center;
}

.metric-label {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  margin-bottom: 6px;
}

.metric-value {
  font-size: 24px;
  font-weight: 600;
}

.section-card {
  margin-bottom: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.bar-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}

.bar-bg {
  flex: 1;
  height: 8px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
  overflow: hidden;
  min-width: 60px;
}

.bar-fill {
  height: 100%;
  background: var(--el-color-success);
  transition: width 0.3s;
}

.bar-fill.text-loss {
  background: var(--el-color-danger);
}

.bar-fill.risk {
  background: var(--el-color-warning);
}

.bar-fill.danger {
  background: var(--el-color-danger);
}

.bar-text {
  font-size: 12px;
  min-width: 50px;
  text-align: right;
}

.text-profit {
  color: var(--el-color-success);
}

.text-loss {
  color: var(--el-color-danger);
}

.text-warning {
  color: var(--el-color-warning);
}

.text-neutral {
  color: var(--el-text-color-primary);
}

.text-danger {
  color: var(--el-color-danger);
}

.ls-block {
  padding: 4px 0;
}

.ls-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
}

.ls-label {
  color: var(--el-text-color-secondary);
}

.ls-value {
  font-weight: 600;
}

.ls-count {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.ls-note {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ls-note-text {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.regime-note {
  margin-top: 12px;
}

.monthly-control {
  display: flex;
  gap: 8px;
  align-items: center;
}

.monthly-content {
  max-height: 60vh;
  overflow-y: auto;
}

.monthly-summary {
  margin-top: 12px;
  padding: 8px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
}

.monthly-suggestions {
  margin-top: 12px;
}

.monthly-suggestions ul {
  margin: 6px 0 0 20px;
  padding: 0;
}

.monthly-tabs {
  margin-top: 12px;
}

.md-preview {
  background: var(--el-fill-color-light);
  padding: 12px;
  border-radius: 4px;
  max-height: 400px;
  overflow: auto;
  font-size: 13px;
  white-space: pre-wrap;
}

.html-preview {
  width: 100%;
  height: 400px;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
}
</style>
