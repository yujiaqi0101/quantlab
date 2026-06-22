<template>
  <div class="alpha-aware-studio">
    <!-- Header -->
    <div class="studio-header">
      <div class="header-left">
        <h1 class="studio-title">执行感知Alpha工作室 Execution-Aware Alpha Studio</h1>
        <span class="studio-subtitle">从"预测收益"到"真实可交易" — 优化市场存活率 From "predicted returns" to "truly tradeable" — optimize market survival</span>
      </div>
      <div class="header-right">
        <el-button type="primary" :icon="MagicStick" @click="evaluateAll" :loading="evaluating">
          一键全流程评估 Evaluate All
        </el-button>
      </div>
    </div>

    <!-- Summary Cards (after evaluate all) -->
    <div v-if="allResult" class="summary-grid">
      <el-card class="summary-card" :class="verdictClass(allResult.summary?.realizability_verdict)">
        <div class="summary-label">可实现性</div>
        <div class="summary-value">{{ allResult.summary?.realizability_verdict }}</div>
      </el-card>
      <el-card class="summary-card" :class="verdictClass(allResult.summary?.survival_verdict)">
        <div class="summary-label">生存判定</div>
        <div class="summary-value">{{ allResult.summary?.survival_verdict }}</div>
      </el-card>
      <el-card class="summary-card" :class="rankClass(allResult.summary?.tradeability_rank)">
        <div class="summary-label">可交易评级</div>
        <div class="summary-value rank">{{ allResult.summary?.tradeability_rank }}</div>
      </el-card>
      <el-card class="summary-card">
        <div class="summary-label">真实夏普</div>
        <div class="summary-value">{{ (allResult.summary?.adjusted_sharpe || 0).toFixed(2) }}</div>
      </el-card>
      <el-card class="summary-card" :class="{ recommended: allResult.summary?.is_recommended }">
        <div class="summary-label">推荐实盘</div>
        <div class="summary-value">{{ allResult.summary?.is_recommended ? 'YES' : 'NO' }}</div>
      </el-card>
    </div>

    <!-- Tabs -->
    <el-tabs v-model="activeTab" class="studio-tabs">
      <!-- 1. Realizability -->
      <el-tab-pane label="Realizability" name="realizability">
        <div class="tab-content">
          <el-form :model="realizabilityForm" label-width="160px" inline>
            <el-form-item label="IC">
              <el-input-number v-model="realizabilityForm.ic" :step="0.01" :precision="4" />
            </el-form-item>
            <el-form-item label="IC IR">
              <el-input-number v-model="realizabilityForm.ic_ir" :step="0.1" />
            </el-form-item>
            <el-form-item label="Sharpe">
              <el-input-number v-model="realizabilityForm.sharpe" :step="0.1" />
            </el-form-item>
            <el-form-item label="Turnover">
              <el-input-number v-model="realizabilityForm.turnover" :step="0.5" />
            </el-form-item>
            <el-form-item label="Avg Return">
              <el-input-number v-model="realizabilityForm.avg_return" :step="0.05" />
            </el-form-item>
            <el-form-item label="Slippage (bps)">
              <el-input-number v-model="realizabilityForm.slippage_bps" :step="0.5" />
            </el-form-item>
          </el-form>
          <el-button type="primary" @click="evalRealizability" :loading="loading.realalizability">
            评估可实现性
          </el-button>

          <div v-if="realizabilityResult" class="result-panel">
            <el-descriptions :column="3" border>
              <el-descriptions-item label="Signal Strength">
                {{ realizabilityResult.signal_strength?.toFixed(3) }}
              </el-descriptions-item>
              <el-descriptions-item label="Liquidity Score">
                {{ realizabilityResult.liquidity_score?.toFixed(3) }}
              </el-descriptions-item>
              <el-descriptions-item label="Turnover Penalty">
                {{ realizabilityResult.turnover_penalty?.toFixed(3) }}
              </el-descriptions-item>
              <el-descriptions-item label="Cost Adjusted Return">
                {{ realizabilityResult.cost_adjusted_return?.toFixed(3) }}
              </el-descriptions-item>
              <el-descriptions-item label="Real Score">
                <strong>{{ realizabilityResult.real_score?.toFixed(3) }}</strong>
              </el-descriptions-item>
              <el-descriptions-item label="Real Sharpe">
                <strong>{{ realizabilityResult.real_sharpe?.toFixed(2) }}</strong>
              </el-descriptions-item>
            </el-descriptions>
            <el-alert
              :title="realizabilityResult.verdict"
              :type="verdictAlertType(realizabilityResult.verdict)"
              :description="realizabilityResult.warnings?.join('; ') || 'No warnings'"
              show-icon
              :closable="false"
              style="margin-top: 12px"
            />
          </div>
        </div>
      </el-tab-pane>

      <!-- 2. Turnover -->
      <el-tab-pane label="Turnover" name="turnover">
        <div class="tab-content">
          <el-form label-width="160px">
            <el-form-item label="持仓序列 (逗号分隔)">
              <el-input
                v-model="turnoverInput"
                placeholder="0.1, 0.15, 0.12, 0.18, 0.1, 0.2"
                style="width: 500px"
              />
            </el-form-item>
            <el-form-item label="资金量">
              <el-input-number v-model="turnoverForm.capital" :step="100000" />
            </el-form-item>
            <el-form-item label="手续费率">
              <el-input-number v-model="turnoverForm.fee_rate" :step="0.0001" :precision="4" />
            </el-form-item>
            <el-form-item label="滑点 (bps)">
              <el-input-number v-model="turnoverForm.slippage_bps" :step="0.5" />
            </el-form-item>
          </el-form>
          <el-button type="primary" @click="evalTurnover" :loading="loading.turnover">
            分析换手压力
          </el-button>

          <div v-if="turnoverResult" class="result-panel">
            <el-descriptions :column="3" border>
              <el-descriptions-item label="日均换手">
                {{ turnoverResult.avg_daily_turnover?.toFixed(3) }}
              </el-descriptions-item>
              <el-descriptions-item label="最大日换手">
                {{ turnoverResult.max_daily_turnover?.toFixed(3) }}
              </el-descriptions-item>
              <el-descriptions-item label="年化换手">
                {{ turnoverResult.annual_turnover?.toFixed(1) }}
              </el-descriptions-item>
              <el-descriptions-item label="年化成本">
                ${{ (turnoverResult.annual_cost || 0).toFixed(0) }}
              </el-descriptions-item>
              <el-descriptions-item label="成本拖累">
                {{ (turnoverResult.cost_drag_bps || 0).toFixed(1) }} bps
              </el-descriptions-item>
              <el-descriptions-item label="压力评分">
                <strong>{{ (turnoverResult.pressure_score || 0).toFixed(3) }}</strong>
              </el-descriptions-item>
            </el-descriptions>
            <el-alert
              :title="turnoverResult.is_sustainable ? '可持续' : '不可持续'"
              :type="turnoverResult.is_sustainable ? 'success' : 'error'"
              show-icon
              :closable="false"
              style="margin-top: 12px"
            />
          </div>
        </div>
      </el-tab-pane>

      <!-- 3. Liquidity Filter -->
      <el-tab-pane label="Liquidity" name="liquidity">
        <div class="tab-content">
          <el-form :model="liquidityForm" label-width="180px" inline>
            <el-form-item label="Symbol">
              <el-input v-model="liquidityForm.symbol" style="width: 120px" />
            </el-form-item>
            <el-form-item label="24h Volume (USD)">
              <el-input-number v-model="liquidityForm.avg_volume_24h" :step="1000000" />
            </el-form-item>
            <el-form-item label="Spread (bps)">
              <el-input-number v-model="liquidityForm.avg_spread_bps" :step="0.5" />
            </el-form-item>
            <el-form-item label="Depth (USD)">
              <el-input-number v-model="liquidityForm.avg_depth_usd" :step="100000" />
            </el-form-item>
            <el-form-item label="Volatility">
              <el-input-number v-model="liquidityForm.volatility" :step="0.01" :precision="4" />
            </el-form-item>
            <el-form-item label="Impact (bps)">
              <el-input-number v-model="liquidityForm.impact_cost_bps" :step="0.5" />
            </el-form-item>
          </el-form>
          <el-button type="primary" @click="evalLiquidity" :loading="loading.liquidity">
            流动性过滤
          </el-button>

          <div v-if="liquidityResult" class="result-panel">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="Verdict">
                <el-tag :type="filterTagType(liquidityResult.verdict)">{{ liquidityResult.verdict }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="Overall Score">
                {{ (liquidityResult.overall_score || 0).toFixed(3) }}
              </el-descriptions-item>
            </el-descriptions>
            <div v-if="liquidityResult.scores" class="score-bars">
              <div v-for="(score, key) in liquidityResult.scores" :key="key" class="score-bar">
                <span class="score-label">{{ key }}</span>
                <el-progress :percentage="Math.round(score * 100)" :stroke-width="14" />
              </div>
            </div>
            <el-alert
              v-if="liquidityResult.reasons?.length"
              title="拒绝原因"
              type="warning"
              :description="liquidityResult.reasons.join('; ')"
              show-icon
              :closable="false"
              style="margin-top: 12px"
            />
          </div>
        </div>
      </el-tab-pane>

      <!-- 4. Sensitivity -->
      <el-tab-pane label="Sensitivity" name="sensitivity">
        <div class="tab-content">
          <el-form :model="sensitivityForm" label-width="180px" inline>
            <el-form-item label="Base Sharpe">
              <el-input-number v-model="sensitivityForm.base_sharpe" :step="0.1" />
            </el-form-item>
            <el-form-item label="Base Return">
              <el-input-number v-model="sensitivityForm.base_return" :step="0.05" />
            </el-form-item>
            <el-form-item label="Slippage Sensitivity">
              <el-input-number v-model="sensitivityForm.slippage_sensitivity" :step="0.1" :precision="2" :min="0" :max="1" />
            </el-form-item>
          </el-form>
          <el-button type="primary" @click="evalSensitivity" :loading="loading.sensitivity">
            执行敏感性测试
          </el-button>

          <div v-if="sensitivityResult" class="result-panel">
            <el-descriptions :column="3" border>
              <el-descriptions-item label="Sharpe Stability">
                {{ (sensitivityResult.sharpe_stability || 0).toFixed(3) }}
              </el-descriptions-item>
              <el-descriptions-item label="Return Degradation">
                {{ (sensitivityResult.return_degradation || 0).toFixed(3) }}
              </el-descriptions-item>
              <el-descriptions-item label="Breakpoint Multiplier">
                {{ (sensitivityResult.breakpoint_multiplier || 0).toFixed(2) }}x
              </el-descriptions-item>
            </el-descriptions>

            <el-table v-if="sensitivityResult.scenarios" :data="sensitivityResult.scenarios" style="margin-top: 12px">
              <el-table-column prop="scenario.name" label="Scenario" />
              <el-table-column prop="scenario.slippage_multiplier" label="Slippage Mult" />
              <el-table-column prop="sharpe" label="Sharpe" :formatter="(r: any) => r.sharpe?.toFixed(2)" />
              <el-table-column prop="total_return" label="Return" :formatter="(r: any) => (r.total_return * 100).toFixed(1) + '%'" />
              <el-table-column prop="cost_ratio" label="Cost Ratio" :formatter="(r: any) => (r.cost_ratio * 100).toFixed(1) + '%'" />
              <el-table-column label="Profitable">
                <template #default="{ row }">
                  <el-tag :type="row.is_profitable ? 'success' : 'danger'">{{ row.is_profitable ? 'YES' : 'NO' }}</el-tag>
                </template>
              </el-table-column>
            </el-table>

            <el-alert
              :title="sensitivityResult.verdict"
              :type="verdictAlertType(sensitivityResult.verdict)"
              :description="sensitivityResult.warnings?.join('; ') || 'No warnings'"
              show-icon
              :closable="false"
              style="margin-top: 12px"
            />
          </div>
        </div>
      </el-tab-pane>

      <!-- 5. Latency Fragility -->
      <el-tab-pane label="Latency" name="latency">
        <div class="tab-content">
          <el-form :model="latencyForm" label-width="180px" inline>
            <el-form-item label="Base Sharpe">
              <el-input-number v-model="latencyForm.base_sharpe" :step="0.1" />
            </el-form-item>
            <el-form-item label="Alpha Decay Rate (/ms)">
              <el-input-number v-model="latencyForm.alpha_decay_rate" :step="0.0005" :precision="4" />
            </el-form-item>
          </el-form>
          <el-button type="primary" @click="evalLatency" :loading="loading.latency">
            延迟脆弱性测试
          </el-button>

          <div v-if="latencyResult" class="result-panel">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="Alpha Half Life">
                {{ (latencyResult.alpha_half_life_ms || 0).toFixed(0) }} ms
              </el-descriptions-item>
              <el-descriptions-item label="Critical Latency">
                {{ (latencyResult.critical_latency_ms || 0).toFixed(0) }} ms
              </el-descriptions-item>
              <el-descriptions-item label="Latency Class">
                <el-tag>{{ latencyResult.latency_class }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="Scalable">
                <el-tag :type="latencyResult.is_scalable ? 'success' : 'danger'">{{ latencyResult.is_scalable ? 'YES' : 'NO' }}</el-tag>
              </el-descriptions-item>
            </el-descriptions>

            <el-table v-if="latencyResult.results" :data="latencyResult.results" style="margin-top: 12px">
              <el-table-column prop="scenario.name" label="Scenario" />
              <el-table-column prop="scenario.delay_ms" label="Delay (ms)" />
              <el-table-column prop="sharpe" label="Sharpe" :formatter="(r: any) => r.sharpe?.toFixed(2)" />
              <el-table-column prop="alpha_decay" label="Alpha Decay" :formatter="(r: any) => (r.alpha_decay * 100).toFixed(1) + '%'" />
              <el-table-column prop="fill_rate" label="Fill Rate" :formatter="(r: any) => (r.fill_rate * 100).toFixed(1) + '%'" />
            </el-table>

            <el-alert
              :title="latencyResult.verdict"
              :type="verdictAlertType(latencyResult.verdict)"
              :description="latencyResult.warnings?.join('; ') || 'No warnings'"
              show-icon
              :closable="false"
              style="margin-top: 12px"
            />
          </div>
        </div>
      </el-tab-pane>

      <!-- 6. Impact Backtest -->
      <el-tab-pane label="Impact BT" name="impact">
        <div class="tab-content">
          <el-form :model="impactForm" label-width="180px" inline>
            <el-form-item label="Paper Sharpe">
              <el-input-number v-model="impactForm.paper_sharpe" :step="0.1" />
            </el-form-item>
            <el-form-item label="Paper Return">
              <el-input-number v-model="impactForm.paper_return" :step="0.05" />
            </el-form-item>
            <el-form-item label="Volume">
              <el-input-number v-model="impactForm.volume" :step="100000" />
            </el-form-item>
            <el-form-item label="Volatility">
              <el-input-number v-model="impactForm.volatility" :step="0.01" :precision="4" />
            </el-form-item>
          </el-form>
          <el-button type="primary" @click="evalImpact" :loading="loading.impact">
            冲击回测
          </el-button>

          <div v-if="impactResult" class="result-panel">
            <el-descriptions :column="3" border>
              <el-descriptions-item label="Paper Sharpe">
                {{ (impactResult.paper_sharpe || 0).toFixed(2) }}
              </el-descriptions-item>
              <el-descriptions-item label="Real Sharpe">
                <strong>{{ (impactResult.real_sharpe || 0).toFixed(2) }}</strong>
              </el-descriptions-item>
              <el-descriptions-item label="Sharpe Decay">
                {{ ((impactResult.sharpe_decay || 0) * 100).toFixed(1) }}%
              </el-descriptions-item>
              <el-descriptions-item label="Paper Return">
                {{ ((impactResult.paper_return || 0) * 100).toFixed(1) }}%
              </el-descriptions-item>
              <el-descriptions-item label="Real Return">
                <strong>{{ ((impactResult.real_return || 0) * 100).toFixed(1) }}%</strong>
              </el-descriptions-item>
              <el-descriptions-item label="Return Decay">
                {{ ((impactResult.return_decay || 0) * 100).toFixed(1) }}%
              </el-descriptions-item>
              <el-descriptions-item label="Total Impact Cost">
                ${{ (impactResult.total_impact_cost || 0).toFixed(0) }}
              </el-descriptions-item>
              <el-descriptions-item label="Avg Impact">
                {{ (impactResult.avg_impact_bps || 0).toFixed(1) }} bps
              </el-descriptions-item>
              <el-descriptions-item label="Max Impact">
                {{ (impactResult.max_impact_bps || 0).toFixed(1) }} bps
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </div>
      </el-tab-pane>

      <!-- 7. Adjusted Sharpe -->
      <el-tab-pane label="Adj Sharpe" name="adjsharpe">
        <div class="tab-content">
          <el-form :model="adjSharpeForm" label-width="180px" inline>
            <el-form-item label="Paper Sharpe">
              <el-input-number v-model="adjSharpeForm.paper_sharpe" :step="0.1" />
            </el-form-item>
            <el-form-item label="Annual Return">
              <el-input-number v-model="adjSharpeForm.annual_return" :step="0.05" />
            </el-form-item>
            <el-form-item label="Turnover">
              <el-input-number v-model="adjSharpeForm.turnover" :step="0.5" />
            </el-form-item>
            <el-form-item label="Fee Rate">
              <el-input-number v-model="adjSharpeForm.fee_rate" :step="0.0001" :precision="4" />
            </el-form-item>
            <el-form-item label="Slippage (bps)">
              <el-input-number v-model="adjSharpeForm.slippage_bps" :step="0.5" />
            </el-form-item>
          </el-form>
          <el-button type="primary" @click="evalAdjSharpe" :loading="loading.adjsharpe">
            计算执行调整夏普
          </el-button>

          <div v-if="adjSharpeResult" class="result-panel">
            <div class="sharpe-comparison">
              <div class="sharpe-box paper">
                <div class="sharpe-label">Paper Sharpe</div>
                <div class="sharpe-value">{{ (adjSharpeResult.decomposition?.paper_sharpe || 0).toFixed(2) }}</div>
              </div>
              <div class="sharpe-arrow">→</div>
              <div class="sharpe-box real">
                <div class="sharpe-label">Real Sharpe</div>
                <div class="sharpe-value">{{ (adjSharpeResult.decomposition?.real_sharpe || 0).toFixed(2) }}</div>
              </div>
              <div class="sharpe-box grade">
                <div class="sharpe-label">Grade</div>
                <div class="sharpe-value grade-value">{{ adjSharpeResult.grade }}</div>
              </div>
            </div>

            <el-descriptions :column="2" border style="margin-top: 12px">
              <el-descriptions-item label="Fee Penalty">
                {{ (adjSharpeResult.decomposition?.fee_penalty || 0).toFixed(3) }}
              </el-descriptions-item>
              <el-descriptions-item label="Slippage Penalty">
                {{ (adjSharpeResult.decomposition?.slippage_penalty || 0).toFixed(3) }}
              </el-descriptions-item>
              <el-descriptions-item label="Impact Penalty">
                {{ (adjSharpeResult.decomposition?.impact_penalty || 0).toFixed(3) }}
              </el-descriptions-item>
              <el-descriptions-item label="Total Penalty">
                <strong>{{ (adjSharpeResult.decomposition?.total_penalty || 0).toFixed(3) }}</strong>
              </el-descriptions-item>
            </el-descriptions>

            <el-alert
              :title="adjSharpeResult.verdict"
              :type="adjSharpeResult.is_institutional ? 'success' : 'warning'"
              :description="adjSharpeResult.is_institutional ? '达到机构标准' : '未达机构标准'"
              show-icon
              :closable="false"
              style="margin-top: 12px"
            />
          </div>
        </div>
      </el-tab-pane>

      <!-- 8. Survival -->
      <el-tab-pane label="Survival" name="survival">
        <div class="tab-content">
          <el-form :model="survivalForm" label-width="180px" inline>
            <el-form-item label="IC Mean">
              <el-input-number v-model="survivalForm.ic_mean" :step="0.01" :precision="4" />
            </el-form-item>
            <el-form-item label="IC IR">
              <el-input-number v-model="survivalForm.ic_ir" :step="0.1" />
            </el-form-item>
            <el-form-item label="IC Hit Rate">
              <el-input-number v-model="survivalForm.ic_hit_rate" :step="0.05" :precision="2" :min="0" :max="1" />
            </el-form-item>
            <el-form-item label="Turnover">
              <el-input-number v-model="survivalForm.turnover" :step="0.5" />
            </el-form-item>
            <el-form-item label="Slippage Sensitivity">
              <el-input-number v-model="survivalForm.slippage_sensitivity" :step="0.1" :precision="2" :min="0" :max="1" />
            </el-form-item>
            <el-form-item label="Breakpoint Mult">
              <el-input-number v-model="survivalForm.breakpoint_multiplier" :step="0.5" />
            </el-form-item>
            <el-form-item label="Liquidity Score">
              <el-input-number v-model="survivalForm.liquidity_score" :step="0.1" :precision="2" :min="0" :max="1" />
            </el-form-item>
            <el-form-item label="Real Sharpe">
              <el-input-number v-model="survivalForm.real_sharpe" :step="0.1" />
            </el-form-item>
          </el-form>
          <el-button type="primary" @click="evalSurvival" :loading="loading.survival">
            评估生存能力
          </el-button>

          <div v-if="survivalResult" class="result-panel">
            <div class="survival-verdict" :class="survivalResult.verdict?.toLowerCase()">
              {{ survivalResult.verdict }}
            </div>
            <el-progress
              :percentage="Math.round((survivalResult.survival_score || 0) * 100)"
              :stroke-width="20"
              :color="survivalResult.survives ? '#67c23a' : '#f56c6c'"
              style="margin: 12px 0"
            />

            <div v-if="survivalResult.scores" class="score-bars">
              <div v-for="(score, key) in survivalResult.scores" :key="key" class="score-bar">
                <span class="score-label">{{ key }}</span>
                <el-progress :percentage="Math.round(score * 100)" :stroke-width="14" />
              </div>
            </div>

            <el-row :gutter="12" style="margin-top: 12px">
              <el-col :span="12">
                <el-card v-if="survivalResult.strengths?.length">
                  <template #header>Strengths</template>
                  <ul>
                    <li v-for="s in survivalResult.strengths" :key="s">{{ s }}</li>
                  </ul>
                </el-card>
              </el-col>
              <el-col :span="12">
                <el-card v-if="survivalResult.failure_reasons?.length">
                  <template #header>Failure Reasons</template>
                  <ul>
                    <li v-for="r in survivalResult.failure_reasons" :key="r">{{ r }}</li>
                  </ul>
                </el-card>
              </el-col>
            </el-row>
          </div>
        </div>
      </el-tab-pane>

      <!-- 9. Features -->
      <el-tab-pane label="Features" name="features">
        <div class="tab-content">
          <el-form :model="featureForm" label-width="160px" inline>
            <el-form-item label="RSI">
              <el-input-number v-model="featureForm.rsi" :step="1" :min="0" :max="100" />
            </el-form-item>
            <el-form-item label="Momentum">
              <el-input-number v-model="featureForm.momentum" :step="0.01" :precision="4" />
            </el-form-item>
            <el-form-item label="Mean Reversion">
              <el-input-number v-model="featureForm.mean_reversion" :step="0.01" :precision="4" />
            </el-form-item>
          </el-form>
          <el-divider content-position="left">市场环境</el-divider>
          <el-form :model="featureCtx" label-width="160px" inline>
            <el-form-item label="Volume">
              <el-input-number v-model="featureCtx.volume" :step="100000" />
            </el-form-item>
            <el-form-item label="Spread (bps)">
              <el-input-number v-model="featureCtx.spread_bps" :step="0.5" />
            </el-form-item>
            <el-form-item label="Depth">
              <el-input-number v-model="featureCtx.depth" :step="10" />
            </el-form-item>
            <el-form-item label="Volatility">
              <el-input-number v-model="featureCtx.volatility" :step="0.01" :precision="4" />
            </el-form-item>
            <el-form-item label="Turnover">
              <el-input-number v-model="featureCtx.turnover" :step="0.5" />
            </el-form-item>
            <el-form-item label="Impact (bps)">
              <el-input-number v-model="featureCtx.impact_bps" :step="0.5" />
            </el-form-item>
          </el-form>
          <el-button type="primary" @click="evalFeatures" :loading="loading.features">
            执行感知特征调整
          </el-button>

          <div v-if="featureResult" class="result-panel">
            <el-table :data="featureTableData" style="margin-top: 12px">
              <el-table-column prop="name" label="Feature" />
              <el-table-column prop="original" label="Original" :formatter="(r: any) => r.original?.toFixed(3)" />
              <el-table-column prop="adjusted" label="Adjusted" :formatter="(r: any) => r.adjusted?.toFixed(3)" />
              <el-table-column prop="weight" label="Weight" :formatter="(r: any) => r.weight?.toFixed(3)" />
              <el-table-column prop="adjustment_factor" label="Adjustment Factor" :formatter="(r: any) => r.adjustment_factor?.toFixed(3)" />
            </el-table>
          </div>
        </div>
      </el-tab-pane>

      <!-- 10. Tradeability -->
      <el-tab-pane label="Tradeability" name="tradeability">
        <div class="tab-content">
          <el-button type="primary" size="large" @click="evalTradeability" :loading="loading.tradeability">
            计算可交易评分
          </el-button>

          <div v-if="tradeabilityResult" class="result-panel">
            <div class="tradeability-rank" :class="rankClass(tradeabilityResult.rank)">
              <div class="rank-label">Alpha Score</div>
              <div class="rank-value">{{ (tradeabilityResult.alpha_score || 0).toFixed(3) }}</div>
              <div class="rank-grade">{{ tradeabilityResult.rank }}</div>
            </div>

            <div v-if="tradeabilityResult.scores" class="score-bars">
              <div v-for="(score, key) in tradeabilityResult.scores" :key="key" class="score-bar">
                <span class="score-label">{{ key }}</span>
                <el-progress :percentage="Math.round(score * 100)" :stroke-width="18" />
              </div>
            </div>

            <el-row :gutter="12" style="margin-top: 12px">
              <el-col :span="12">
                <el-card v-if="tradeabilityResult.strengths?.length">
                  <template #header>Strengths</template>
                  <ul>
                    <li v-for="s in tradeabilityResult.strengths" :key="s">{{ s }}</li>
                  </ul>
                </el-card>
              </el-col>
              <el-col :span="12">
                <el-card v-if="tradeabilityResult.weaknesses?.length">
                  <template #header>Weaknesses</template>
                  <ul>
                    <li v-for="w in tradeabilityResult.weaknesses" :key="w">{{ w }}</li>
                  </ul>
                </el-card>
              </el-col>
            </el-row>

            <el-alert
              v-if="tradeabilityResult.recommendations?.length"
              title="Recommendations"
              type="info"
              :description="tradeabilityResult.recommendations.join('; ')"
              show-icon
              :closable="false"
              style="margin-top: 12px"
            />
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { MagicStick } from '@element-plus/icons-vue'
import { http } from '@/api/http'
import { ElMessage } from 'element-plus'

const activeTab = ref('realizability')
const evaluating = ref(false)
const allResult = ref<any>(null)

const loading = reactive({
  realazability: false,
  turnover: false,
  liquidity: false,
  sensitivity: false,
  latency: false,
  impact: false,
  adjsharpe: false,
  survival: false,
  features: false,
  tradeability: false,
})

// Forms
const realizabilityForm = reactive({
  ic: 0.05, ic_ir: 1.5, sharpe: 1.5, turnover: 3.0, avg_return: 0.2,
  avg_volume: 1000000, slippage_bps: 2.0,
})

const turnoverInput = ref('0.1, 0.15, 0.12, 0.18, 0.1, 0.2, 0.15, 0.1')
const turnoverForm = reactive({
  capital: 1000000, fee_rate: 0.0004, slippage_bps: 2.0,
})

const liquidityForm = reactive({
  symbol: 'BTCUSDT', avg_volume_24h: 5000000000, avg_spread_bps: 2.0,
  avg_depth_usd: 5000000, volatility: 0.02, impact_cost_bps: 1.0,
})

const sensitivityForm = reactive({
  base_sharpe: 2.0, base_return: 0.3, slippage_sensitivity: 0.3,
})

const latencyForm = reactive({
  base_sharpe: 2.0, alpha_decay_rate: 0.001,
})

const impactForm = reactive({
  paper_sharpe: 2.0, paper_return: 0.3, volume: 1000000, volatility: 0.02,
})

const adjSharpeForm = reactive({
  paper_sharpe: 2.0, annual_return: 0.3, turnover: 5.0,
  fee_rate: 0.0004, slippage_bps: 2.0,
})

const survivalForm = reactive({
  ic_mean: 0.05, ic_ir: 1.5, ic_hit_rate: 0.6, turnover: 3.0,
  slippage_sensitivity: 0.3, breakpoint_multiplier: 2.5,
  liquidity_score: 0.8, real_sharpe: 1.2, paper_sharpe: 2.0,
})

const featureForm = reactive({
  rsi: 65, momentum: 0.05, mean_reversion: -0.03,
})
const featureCtx = reactive({
  volume: 500000, spread_bps: 5.0, depth: 100,
  volatility: 0.03, turnover: 1.0, impact_bps: 1.0,
})

// Results
const realizabilityResult = ref<any>(null)
const turnoverResult = ref<any>(null)
const liquidityResult = ref<any>(null)
const sensitivityResult = ref<any>(null)
const latencyResult = ref<any>(null)
const impactResult = ref<any>(null)
const adjSharpeResult = ref<any>(null)
const survivalResult = ref<any>(null)
const featureResult = ref<any>(null)
const tradeabilityResult = ref<any>(null)

const featureTableData = computed(() => {
  if (!featureResult.value?.features) return []
  return Object.entries(featureResult.value.features).map(([key, val]: [string, any]) => ({
    name: key,
    ...val,
  }))
})

// API calls
async function evalRealizability() {
  loading.realazability = true
  try {
    const { data } = await http.post('/alpha-aware/realizability/evaluate', realizabilityForm)
    realizabilityResult.value = data
  } catch (e: any) {
    ElMessage.error(e.message || '评估失败')
  } finally {
    loading.realazability = false
  }
}

async function evalTurnover() {
  loading.turnover = true
  try {
    const positions = turnoverInput.value.split(',').map(s => parseFloat(s.trim())).filter(n => !isNaN(n))
    const { data } = await http.post('/alpha-aware/turnover/analyze', {
      ...turnoverForm,
      positions,
    })
    turnoverResult.value = data
  } catch (e: any) {
    ElMessage.error(e.message || '分析失败')
  } finally {
    loading.turnover = false
  }
}

async function evalLiquidity() {
  loading.liquidity = true
  try {
    const { data } = await http.post('/alpha-aware/liquidity/filter', liquidityForm)
    liquidityResult.value = data
  } catch (e: any) {
    ElMessage.error(e.message || '过滤失败')
  } finally {
    loading.liquidity = false
  }
}

async function evalSensitivity() {
  loading.sensitivity = true
  try {
    const { data } = await http.post('/alpha-aware/sensitivity/test', sensitivityForm)
    sensitivityResult.value = data
  } catch (e: any) {
    ElMessage.error(e.message || '测试失败')
  } finally {
    loading.sensitivity = false
  }
}

async function evalLatency() {
  loading.latency = true
  try {
    const { data } = await http.post('/alpha-aware/latency/fragility', latencyForm)
    latencyResult.value = data
  } catch (e: any) {
    ElMessage.error(e.message || '测试失败')
  } finally {
    loading.latency = false
  }
}

async function evalImpact() {
  loading.impact = true
  try {
    const { data } = await http.post('/alpha-aware/impact/backtest', impactForm)
    impactResult.value = data
  } catch (e: any) {
    ElMessage.error(e.message || '回测失败')
  } finally {
    loading.impact = false
  }
}

async function evalAdjSharpe() {
  loading.adjsharpe = true
  try {
    const { data } = await http.post('/alpha-aware/sharpe/adjusted', adjSharpeForm)
    adjSharpeResult.value = data
  } catch (e: any) {
    ElMessage.error(e.message || '计算失败')
  } finally {
    loading.adjsharpe = false
  }
}

async function evalSurvival() {
  loading.survival = true
  try {
    const { data } = await http.post('/alpha-aware/survival/evaluate', survivalForm)
    survivalResult.value = data
  } catch (e: any) {
    ElMessage.error(e.message || '评估失败')
  } finally {
    loading.survival = false
  }
}

async function evalFeatures() {
  loading.features = true
  try {
    const { data } = await http.post('/alpha-aware/features/adjust', {
      features: { ...featureForm },
      ...featureCtx,
    })
    featureResult.value = data
  } catch (e: any) {
    ElMessage.error(e.message || '调整失败')
  } finally {
    loading.features = false
  }
}

async function evalTradeability() {
  loading.tradeability = true
  try {
    const payload = {
      ...realizabilityForm,
      ...survivalForm,
      ic_mean: survivalForm.ic_mean,
      ic_hit_rate: survivalForm.ic_hit_rate,
    }
    const { data } = await http.post('/alpha-aware/tradeability/score', payload)
    tradeabilityResult.value = data
  } catch (e: any) {
    ElMessage.error(e.message || '评分失败')
  } finally {
    loading.tradeability = false
  }
}

async function evaluateAll() {
  evaluating.value = true
  try {
    const payload = {
      ...realizabilityForm,
      ...survivalForm,
      ic_mean: survivalForm.ic_mean,
      ic_hit_rate: survivalForm.ic_hit_rate,
    }
    const { data } = await http.post('/alpha-aware/evaluate/all', payload)
    allResult.value = data
    // 同步各 tab 结果
    realizabilityResult.value = data.realizability
    turnoverResult.value = data.turnover
    liquidityResult.value = data.liquidity_filter
    sensitivityResult.value = data.sensitivity
    latencyResult.value = data.latency_fragility
    impactResult.value = data.impact_backtest
    adjSharpeResult.value = data.adjusted_sharpe
    survivalResult.value = data.survival
    featureResult.value = { features: data.features }
    tradeabilityResult.value = data.tradeability
    ElMessage.success('全流程评估完成')
  } catch (e: any) {
    ElMessage.error(e.message || '评估失败')
  } finally {
    evaluating.value = false
  }
}

// Helpers
function verdictClass(verdict?: string): string {
  if (!verdict) return ''
  if (verdict.includes('TRADABLE') || verdict.includes('SURVIVES') || verdict.includes('SCALABLE') || verdict.includes('ROBUST')) return 'good'
  if (verdict.includes('MARGINAL')) return 'warn'
  return 'bad'
}

function rankClass(rank?: string): string {
  if (!rank) return ''
  if (rank === 'S' || rank === 'A') return 'good'
  if (rank === 'B') return 'warn'
  return 'bad'
}

function verdictAlertType(verdict?: string): 'success' | 'warning' | 'error' {
  if (!verdict) return 'warning'
  if (verdict.includes('ROBUST') || verdict.includes('SCALABLE') || verdict.includes('TRADABLE')) return 'success'
  if (verdict.includes('MARGINAL')) return 'warning'
  return 'error'
}

function filterTagType(verdict?: string): 'success' | 'warning' | 'danger' {
  if (!verdict) return 'warning'
  if (verdict === 'PASS') return 'success'
  if (verdict === 'WARN') return 'warning'
  return 'danger'
}
</script>

<style scoped>
.alpha-aware-studio {
  padding: 20px;
}

.studio-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.studio-title {
  font-size: 24px;
  font-weight: 700;
  margin: 0;
}

.studio-subtitle {
  color: var(--q-text-muted);
  font-size: 14px;
  margin-left: 12px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.summary-card {
  text-align: center;
}

.summary-label {
  color: var(--q-text-muted);
  font-size: 12px;
}

.summary-value {
  font-size: 24px;
  font-weight: 700;
  margin-top: 4px;
}

.summary-card.good { border-left: 3px solid #67c23a; }
.summary-card.warn { border-left: 3px solid #e6a23c; }
.summary-card.bad { border-left: 3px solid #f56c6c; }
.summary-card.recommended { border-left: 3px solid #67c23a; background: rgba(103, 194, 58, 0.05); }

.studio-tabs {
  margin-top: 12px;
}

.tab-content {
  padding: 16px 0;
}

.result-panel {
  margin-top: 20px;
}

.score-bars {
  margin-top: 16px;
}

.score-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.score-label {
  width: 180px;
  font-size: 13px;
  color: var(--q-text-secondary);
}

.sharpe-comparison {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24px;
  padding: 20px;
}

.sharpe-box {
  text-align: center;
  padding: 16px 24px;
  border-radius: 8px;
  min-width: 120px;
}

.sharpe-box.paper { background: rgba(64, 158, 255, 0.1); }
.sharpe-box.real { background: rgba(103, 194, 58, 0.1); }
.sharpe-box.grade { background: rgba(230, 162, 60, 0.1); }

.sharpe-label {
  font-size: 12px;
  color: var(--q-text-muted);
}

.sharpe-value {
  font-size: 28px;
  font-weight: 700;
  margin-top: 4px;
}

.grade-value {
  color: #e6a23c;
}

.sharpe-arrow {
  font-size: 24px;
  color: var(--q-text-muted);
}

.survival-verdict {
  text-align: center;
  font-size: 28px;
  font-weight: 800;
  padding: 16px;
  border-radius: 8px;
}

.survival-verdict.survives, .survival-verdict.survives_strong {
  background: rgba(103, 194, 58, 0.1);
  color: #67c23a;
}

.survival-verdict.dies {
  background: rgba(245, 108, 108, 0.1);
  color: #f56c6c;
}

.survival-verdict.marginal {
  background: rgba(230, 162, 60, 0.1);
  color: #e6a23c;
}

.tradeability-rank {
  text-align: center;
  padding: 24px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.tradeability-rank.good { background: rgba(103, 194, 58, 0.1); }
.tradeability-rank.warn { background: rgba(230, 162, 60, 0.1); }
.tradeability-rank.bad { background: rgba(245, 108, 108, 0.1); }

.rank-label {
  font-size: 12px;
  color: var(--q-text-muted);
}

.rank-value {
  font-size: 36px;
  font-weight: 800;
  margin: 4px 0;
}

.rank-grade {
  font-size: 48px;
  font-weight: 900;
}
</style>
