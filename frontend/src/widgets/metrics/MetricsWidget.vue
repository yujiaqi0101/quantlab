<template>
  <div class="metrics-widget">
    <div class="metrics-grid">
      <div class="metric-cell" v-for="m in cards" :key="m.key">
        <span class="metric-label">{{ m.label }}</span>
        <span
          class="metric-value"
          :class="m.tone"
        >
          {{ m.value }}
        </span>
        <span v-if="m.hint" class="metric-hint">{{ m.hint }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

// Loose payload type — any object that may carry these metric fields.
export type MetricsPayload = Record<string, any> | null

const props = withDefaults(defineProps<{
  metrics: MetricsPayload
  compact?: boolean
}>(), {
  compact: false,
})

function fmtPct(v?: number): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '-'
  const sign = v >= 0 ? '+' : ''
  return `${sign}${v.toFixed(2)}%`
}

function fmtNum(v?: number, digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '-'
  return v.toFixed(digits)
}

function fmtMoney(v?: number): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '-'
  if (Math.abs(v) >= 1_000_000) return `$${(v / 1_000_000).toFixed(2)}M`
  if (Math.abs(v) >= 1_000) return `$${(v / 1_000).toFixed(1)}K`
  return `$${v.toFixed(0)}`
}

const cards = computed(() => {
  const m = props.metrics || {}
  const totalReturn = m.total_return
  const maxDD = m.max_drawdown
  const trades = m.trade_count ?? m.n_trades
  return [
    {
      key: 'return',
      label: 'Total Return',
      value: fmtPct(totalReturn),
      tone: totalReturn === undefined ? '' : totalReturn >= 0 ? 'positive' : 'negative',
    },
    {
      key: 'sharpe',
      label: 'Sharpe',
      value: fmtNum(m.sharpe, 3),
      tone: m.sharpe !== undefined && m.sharpe >= 1 ? 'positive' : '',
    },
    {
      key: 'maxdd',
      label: 'Max Drawdown',
      value: fmtPct(maxDD),
      tone: 'negative',
    },
    {
      key: 'winrate',
      label: 'Win Rate',
      value: fmtPct(m.win_rate),
      tone: '',
    },
    {
      key: 'trades',
      label: 'Trades',
      value: trades !== undefined ? String(trades) : '-',
      tone: '',
    },
    {
      key: 'equity',
      label: 'Final Equity',
      value: fmtMoney(m.final_equity),
      tone: 'highlight',
    },
    {
      key: 'pf',
      label: 'Profit Factor',
      value: fmtNum(m.profit_factor, 2),
      tone: '',
      hint: 'avg win / avg loss',
    },
  ]
})
</script>

<style scoped>
.metrics-widget {
  width: 100%;
  height: 100%;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 10px;
  width: 100%;
  height: 100%;
}

.metric-cell {
  background: #0d1117;
  border: 1px solid #1b2332;
  border-radius: 8px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  transition: border-color 0.2s;
}

.metric-cell:hover {
  border-color: #30363d;
}

.metric-label {
  font-size: 11px;
  color: #484f58;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  font-weight: 500;
}

.metric-value {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 20px;
  font-weight: 700;
  color: #e6edf3;
  line-height: 1.2;
}

.metric-value.positive {
  color: #3fb950;
}

.metric-value.negative {
  color: #f85149;
}

.metric-value.highlight {
  color: #bc8cff;
}

.metric-hint {
  font-size: 10px;
  color: #484f58;
  margin-top: 2px;
}
</style>
