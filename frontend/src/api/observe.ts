import { http } from './http'

export interface OverviewData {
  equity: number
  cash: number
  today_pnl: number
  today_pnl_pct: number
  total_pnl: number
  total_pnl_pct: number
  max_drawdown: number
  active_strategies: number
  n_positions: number
  timestamp: string
}

export interface Position {
  symbol: string
  qty: number
  avg_price: number
  current_price: number
  unrealized_pnl: number
  pnl_pct: number
  side?: string
}

export interface Order {
  order_id: string
  symbol: string
  side: string
  type: string
  qty: number
  price?: number
  status: string
  created_at: string
  filled_qty?: number
  filled_price?: number
}

export interface Trade {
  trade_id: string
  symbol: string
  side: string
  qty: number
  price: number
  fee: number
  pnl: number
  timestamp: string
  strategy_id?: string
}

export interface TradeAnalytics {
  n_trades: number
  n_wins: number
  n_losses: number
  win_rate: number
  profit_factor: number
  expectancy: number
  avg_win: number
  avg_loss: number
  total_pnl: number
  largest_win: number
  largest_loss: number
}

export interface TradesResponse {
  trades: Trade[]
  analytics: TradeAnalytics
  n: number
}

export interface RiskStatus {
  status: string  // NORMAL / WARNING / CRITICAL
  max_position_pct: number
  daily_loss: number
  max_daily_loss: number
  max_drawdown: number
  kill_switch_active: boolean
}

export interface StrategyHealth {
  strategy_id: string
  status: string  // healthy / low_activity / stalled / no_fills / losing / stopped
  signals_24h: number
  fills_24h: number
  pnl_24h: number
  n_wins_24h: number
  n_losses_24h: number
  last_signal_time: string | null
  last_fill_time: string | null
  started_at: string | null
  stopped_at: string | null
  total_signals: number
  total_fills: number
  total_pnl: number
  alerts: string[]
}

export interface TimelineEntry {
  timestamp: number
  timestamp_str: string
  trace_id: string
  label: string
  category: string
  payload: Record<string, any>
  duration_ms: number
}

export interface JournalEntry {
  type: string
  message: string
  timestamp: number
  strategy_id: string
  symbol: string
  order_id: string
  signal_id: string
  data: Record<string, any>
  tags: string[]
}

export interface JournalResponse {
  entries: JournalEntry[]
  n: number
}

export interface ReplaySession {
  session_id: string
  events: any[]
}

// ------------------------------------------------------------------
// Replay V2 Types
// ------------------------------------------------------------------

export interface StoredEvent {
  event_id: string
  timestamp: number
  event_type: string
  source: string
  trace_id: string
  session_id: string
  payload: Record<string, any>
}

export interface SessionInfo {
  session_id: string
  strategy: string
  symbol: string
  start_time: number
  end_time: number
  n_events: number
  meta: Record<string, any>
  is_active?: boolean
}

export interface TimelineItem {
  event_id: string
  timestamp: number
  timestamp_str: string
  event_type: string
  source: string
  trace_id: string
  session_id: string
  payload: Record<string, any>
  category: string
  label: string
  summary: string
}

export interface ReplayPosition {
  symbol: string
  qty: number
  avg_price: number
  realized_pnl: number
  current_price: number
  unrealized_pnl: number
  market_value: number
}

export interface ReplayOrder {
  order_id: string
  symbol: string
  side: string
  qty: number
  price: number | null
  status: string
  filled_qty: number
  filled_price: number
  timestamp: number
}

export interface ReplayState {
  initial_cash: number
  cash: number
  equity: number
  unrealized_pnl: number
  realized_pnl: number
  total_pnl: number
  n_positions: number
  n_open_orders: number
  n_processed: number
  current_event_idx: number
  current_timestamp: number
  positions: ReplayPosition[]
  orders: ReplayOrder[]
  last_prices: Record<string, number>
}

export interface ReplaySnapshot {
  status: string  // IDLE / PLAYING / PAUSED / STOPPED / FINISHED
  session_id: string
  position: number
  total_events: number
  progress: number
  speed: number
  current_event: StoredEvent | null
  state: ReplayState
  advanced?: boolean
}

export interface TradeChainNode {
  event_id: string
  timestamp: number
  event_type: string
  source: string
  trace_id: string
  session_id: string
  payload: Record<string, any>
}

export interface TradeChain {
  trace_id: string
  symbol: string
  session_id: string
  nodes: TradeChainNode[]
  summary: string
  pnl: number | null
  duration_ms: number
}

// ==================================================================
// Analysis V3 — Root Cause Analysis
// ==================================================================

export interface TradeLeg {
  side: string
  price: number
  qty: number
  timestamp: number
  order_id: string
  signal_score: number | null
  signal_strategy: string
  order_price: number | null
  slippage: number
  slippage_bps: number
  signal_event: StoredEvent | null
  order_event: StoredEvent | null
  fill_event: StoredEvent | null
}

export interface TradeTrace {
  trace_id: string
  symbol: string
  session_id: string
  strategy: string
  entry: TradeLeg | null
  exit: TradeLeg | null
  pnl: number | null
  pnl_pct: number | null
  fee: number
  holding_ms: number
  holding_seconds: number
  holding_minutes: number
  entry_price: number
  exit_price: number
  max_price: number
  min_price: number
  market_change: number
  is_closed: boolean
  is_win: boolean
  is_loss: boolean
  n_events: number
  n_risk_events: number
  events: StoredEvent[]
  risk_events: StoredEvent[]
}

export type CauseType =
  | 'SIGNAL_ERROR'
  | 'EXECUTION_ERROR'
  | 'RISK_EXIT'
  | 'MARKET_SHOCK'
  | 'OVEREXPOSURE'
  | 'UNKNOWN'

export type CauseSeverity = 'INFO' | 'WARNING' | 'CRITICAL'

export interface RootCause {
  type: CauseType
  severity: CauseSeverity
  confidence: number
  title: string
  description: string
  evidence: string[]
  metrics: Record<string, any>
}

export interface Explanation {
  summary: string
  paragraphs: string[]
  key_metrics: Record<string, any>
  root_cause_labels: string[]
  suggestions: string[]
}

export interface TraceReport {
  trace: TradeTrace
  causes: RootCause[]
  explanation: Explanation | null
}

export interface Anomaly {
  type: string
  severity: CauseSeverity
  title: string
  description: string
  data: Record<string, any>
}

export interface AnomalyReport {
  session_id: string
  n_traces: number
  n_anomalies: number
  anomalies: Anomaly[]
}

export interface AnalysisExplainResponse {
  trace_id: string
  summary: string
  paragraphs: string[]
  key_metrics: Record<string, any>
  root_cause_labels: string[]
  suggestions: string[]
  text: string
}

class ObserveAPI {
  async getOverview(): Promise<OverviewData> {
    const { data } = await http.get('/observe/overview')
    return data
  }

  async getPositions(): Promise<Position[]> {
    const { data } = await http.get('/observe/positions')
    return data
  }

  async getOrders(params?: { status?: string; hours?: number }): Promise<Order[]> {
    const { data } = await http.get('/observe/orders', { params })
    return data
  }

  async getTrades(hours: number = 24): Promise<TradesResponse> {
    const { data } = await http.get('/observe/trades', { params: { hours } })
    return data
  }

  async getRisk(): Promise<RiskStatus> {
    const { data } = await http.get('/observe/risk')
    return data
  }

  async getHealth(): Promise<StrategyHealth[]> {
    const { data } = await http.get('/observe/health')
    return data
  }

  async getTimeline(params?: { limit?: number; category?: string }): Promise<TimelineEntry[]> {
    const { data } = await http.get('/observe/timeline', { params })
    return data
  }

  async getReplaySessions(): Promise<any[]> {
    const { data } = await http.get('/observe/replay/sessions')
    return data
  }

  async getReplaySession(sessionId: string): Promise<ReplaySession> {
    const { data } = await http.get(`/observe/replay/${sessionId}`)
    return data
  }

  async getJournal(params?: { category?: string; strategy?: string; limit?: number }): Promise<JournalResponse> {
    const { data } = await http.get('/observe/journal', { params })
    return data
  }

  async getJournalStats(): Promise<any> {
    const { data } = await http.get('/observe/journal/stats')
    return data
  }

  async addJournalEntry(entry: {
    category: string
    title: string
    content: string
    strategy?: string
    symbol?: string
  }): Promise<any> {
    const { data } = await http.post('/observe/journal', entry)
    return data
  }

  async getStats(): Promise<any> {
    const { data } = await http.get('/observe/stats')
    return data
  }

  // ----------------------------------------------------------------
  // Replay V2 API
  // ----------------------------------------------------------------

  // EventStore
  async queryEvents(params?: {
    session_id?: string
    event_type?: string
    trace_id?: string
    source?: string
    start_ts?: number
    end_ts?: number
    limit?: number
    offset?: number
    order?: string
  }): Promise<{ events: StoredEvent[]; n: number; total: number }> {
    const { data } = await http.get('/observe/events', { params })
    return data
  }

  async getEvent(eventId: string): Promise<StoredEvent> {
    const { data } = await http.get(`/observe/events/${eventId}`)
    return data
  }

  async getEventStoreStats(): Promise<any> {
    const { data } = await http.get('/observe/events/stats/summary')
    return data
  }

  // Sessions
  async listSessions(params?: { strategy?: string; limit?: number }): Promise<{ sessions: SessionInfo[]; n: number }> {
    const { data } = await http.get('/observe/sessions', { params })
    return data
  }

  async listActiveSessions(): Promise<{ sessions: SessionInfo[]; n: number }> {
    const { data } = await http.get('/observe/sessions/active')
    return data
  }

  async getSession(sessionId: string): Promise<SessionInfo> {
    const { data } = await http.get(`/observe/sessions/${sessionId}`)
    return data
  }

  async createSession(params: { strategy?: string; symbol?: string; meta?: Record<string, any> }): Promise<SessionInfo> {
    const { data } = await http.post('/observe/sessions', params)
    return data
  }

  async endSession(sessionId: string): Promise<any> {
    const { data } = await http.post(`/observe/sessions/${sessionId}/end`)
    return data
  }

  async deleteSession(sessionId: string): Promise<any> {
    const { data } = await http.delete(`/observe/sessions/${sessionId}`)
    return data
  }

  // Timeline V2
  async getTimelineV2(params?: {
    session_id?: string
    event_type?: string
    trace_id?: string
    start_ts?: number
    end_ts?: number
    limit?: number
    offset?: number
  }): Promise<{ items: TimelineItem[]; n: number }> {
    const { data } = await http.get('/observe/timeline/v2', { params })
    return data
  }

  async getTimelineCategories(sessionId?: string): Promise<Record<string, number>> {
    const { data } = await http.get('/observe/timeline/v2/categories', { params: { session_id: sessionId } })
    return data
  }

  // Replay Controller
  async replayLoad(sessionId: string): Promise<{ session_id: string; n_events: number }> {
    const { data } = await http.post(`/observe/replay/v2/load/${sessionId}`)
    return data
  }

  async replaySnapshot(): Promise<ReplaySnapshot> {
    const { data } = await http.get('/observe/replay/v2/snapshot')
    return data
  }

  async replayPlay(speed: number = 1.0): Promise<ReplaySnapshot> {
    const { data } = await http.post('/observe/replay/v2/play', null, { params: { speed } })
    return data
  }

  async replayPause(): Promise<ReplaySnapshot> {
    const { data } = await http.post('/observe/replay/v2/pause')
    return data
  }

  async replayResume(): Promise<ReplaySnapshot> {
    const { data } = await http.post('/observe/replay/v2/resume')
    return data
  }

  async replayStop(): Promise<ReplaySnapshot> {
    const { data } = await http.post('/observe/replay/v2/stop')
    return data
  }

  async replayNext(): Promise<ReplaySnapshot> {
    const { data } = await http.post('/observe/replay/v2/next')
    return data
  }

  async replayPrev(): Promise<ReplaySnapshot> {
    const { data } = await http.post('/observe/replay/v2/prev')
    return data
  }

  async replaySeek(position: number): Promise<ReplaySnapshot> {
    const { data } = await http.post('/observe/replay/v2/seek', null, { params: { position } })
    return data
  }

  async replayEvents(params?: { start?: number; limit?: number }): Promise<{
    events: StoredEvent[]
    n: number
    position: number
    total: number
  }> {
    const { data } = await http.get('/observe/replay/v2/events', { params })
    return data
  }

  // Root Cause Analysis
  async rcaByTrace(traceId: string): Promise<TradeChain> {
    const { data } = await http.get(`/observe/rca/trace/${traceId}`)
    return data
  }

  async rcaByEvent(eventId: string): Promise<TradeChain> {
    const { data } = await http.get(`/observe/rca/event/${eventId}`)
    return data
  }

  async rcaSessionTraces(sessionId: string, symbol?: string): Promise<{ chains: TradeChain[]; n: number }> {
    const { data } = await http.get(`/observe/rca/session/${sessionId}`, { params: { symbol } })
    return data
  }

  async rcaSessionLosses(sessionId: string, topN: number = 10): Promise<{ chains: TradeChain[]; n: number }> {
    const { data } = await http.get(`/observe/rca/session/${sessionId}/losses`, { params: { top_n: topN } })
    return data
  }

  async rcaSessionAnomalies(sessionId: string): Promise<any> {
    const { data } = await http.get(`/observe/rca/session/${sessionId}/anomalies`)
    return data
  }

  // ----------------------------------------------------------------
  // Analysis V3 — Root Cause Analysis
  // ----------------------------------------------------------------

  async analysisTrace(traceId: string): Promise<TraceReport> {
    const { data } = await http.get(`/observe/analysis/trace/${traceId}`)
    return data
  }

  async analysisEvent(eventId: string): Promise<TraceReport> {
    const { data } = await http.get(`/observe/analysis/event/${eventId}`)
    return data
  }

  async analysisSession(
    sessionId: string,
    params?: { only_closed?: boolean; only_losses?: boolean; top_n?: number },
  ): Promise<{ session_id: string; n: number; reports: TraceReport[] }> {
    const { data } = await http.get(`/observe/analysis/session/${sessionId}`, { params })
    return data
  }

  async analysisLosses(
    sessionId: string,
    topN: number = 10,
  ): Promise<{ session_id: string; n: number; reports: TraceReport[] }> {
    const { data } = await http.get(`/observe/analysis/session/${sessionId}/losses`, {
      params: { top_n: topN },
    })
    return data
  }

  async analysisAnomalies(
    sessionId: string,
    params?: {
      consecutive_losses?: number
      slippage_bps?: number
      no_signal_hours?: number
    },
  ): Promise<AnomalyReport> {
    const { data } = await http.get(`/observe/analysis/session/${sessionId}/anomalies`, { params })
    return data
  }

  async analysisExplain(traceId: string): Promise<AnalysisExplainResponse> {
    const { data } = await http.get(`/observe/analysis/explain/${traceId}`)
    return data
  }

  async analysisCauses(
    traceId: string,
  ): Promise<{ trace_id: string; n: number; causes: RootCause[] }> {
    const { data } = await http.get(`/observe/analysis/causes/${traceId}`)
    return data
  }

  // ----------------------------------------------------------------
  // Attribution V4 — Performance Attribution（绩效归因）
  // ----------------------------------------------------------------

  async attributionStrategy(sessionId: string): Promise<StrategyAttributionReport> {
    const { data } = await http.get(`/observe/attribution/strategy/${sessionId}`)
    return data
  }

  async attributionSymbol(sessionId: string): Promise<SymbolAttributionReport> {
    const { data } = await http.get(`/observe/attribution/symbol/${sessionId}`)
    return data
  }

  async attributionTime(sessionId: string): Promise<TimeAttributionReport> {
    const { data } = await http.get(`/observe/attribution/time/${sessionId}`)
    return data
  }

  async attributionRisk(sessionId: string): Promise<RiskAttributionReport> {
    const { data } = await http.get(`/observe/attribution/risk/${sessionId}`)
    return data
  }

  async attributionFactor(sessionId: string): Promise<FactorAttributionReport> {
    const { data } = await http.get(`/observe/attribution/factor/${sessionId}`)
    return data
  }

  async attributionOverview(sessionId: string): Promise<AttributionOverview> {
    const { data } = await http.get(`/observe/attribution/overview/${sessionId}`)
    return data
  }

  async attributionRange(params: {
    start_ts: number
    end_ts: number
    session_id?: string
  }): Promise<AttributionRangeResponse> {
    const { data } = await http.get('/observe/attribution/range', { params })
    return data
  }

  // Monthly Review
  async attributionMonthly(params: {
    year: number
    month: number
    session_id?: string
  }): Promise<MonthlyReport> {
    const { data } = await http.get('/observe/attribution/monthly', { params })
    return data
  }

  async attributionMonthlyMd(params: {
    year: number
    month: number
    session_id?: string
  }): Promise<{ year: number; month: number; period_label: string; markdown: string }> {
    const { data } = await http.get('/observe/attribution/monthly/md', { params })
    return data
  }

  async attributionMonthlyHtml(params: {
    year: number
    month: number
    session_id?: string
  }): Promise<{ year: number; month: number; period_label: string; html: string }> {
    const { data } = await http.get('/observe/attribution/monthly/html', { params })
    return data
  }
}

export const observeApi = new ObserveAPI()

// ==================================================================
// Attribution V4 Types — Performance Attribution
// ==================================================================

// ---- Strategy Attribution ----
export interface StrategyMetric {
  strategy: string
  pnl: number
  pnl_pct: number
  n_trades: number
  n_wins: number
  n_losses: number
  win_rate: number
  gross_profit: number
  gross_loss: number
  profit_factor: number
  risk_pct: number
  avg_pnl: number
  max_win: number
  max_loss: number
}

export interface StrategyAttributionReport {
  start_ts: number
  end_ts: number
  total_pnl: number
  total_trades: number
  strategies: StrategyMetric[]
  best_strategy: string
  worst_strategy: string
  concentration: number
}

// ---- Symbol Attribution ----
export interface SymbolMetric {
  symbol: string
  pnl: number
  pnl_pct: number
  n_trades: number
  n_wins: number
  n_losses: number
  win_rate: number
  gross_profit: number
  gross_loss: number
  profit_factor: number
  long_pnl: number
  short_pnl: number
  n_long: number
  n_short: number
  avg_pnl: number
}

export interface LongShortMetric {
  long_pnl: number
  short_pnl: number
  total_pnl: number
  long_pct: number
  short_pct: number
  n_long: number
  n_short: number
  n_total: number
  long_win_rate: number
  short_win_rate: number
  bias: string  // long_only / short_only / long_bias / short_bias / balanced
  note: string
}

export interface SymbolAttributionReport {
  start_ts: number
  end_ts: number
  total_pnl: number
  total_trades: number
  symbols: SymbolMetric[]
  best_symbol: string
  worst_symbol: string
  long_short: LongShortMetric
}

// ---- Time Attribution ----
export interface TimeSlotMetric {
  slot: string       // asia / europe / america
  label: string      // 亚洲 / 欧洲 / 美洲
  pnl: number
  pnl_pct: number
  n_trades: number
  n_wins: number
  win_rate: number
}

export interface RegimeMetric {
  regime: string     // bull / bear / sideways
  label: string      // 牛市 / 熊市 / 震荡
  pnl: number
  pnl_pct: number
  n_trades: number
  n_wins: number
  win_rate: number
  duration_pct: number
}

export interface TimeAttributionReport {
  start_ts: number
  end_ts: number
  total_pnl: number
  total_trades: number
  time_slots: TimeSlotMetric[]
  best_slot: string
  worst_slot: string
  regimes: RegimeMetric[]
  best_regime: string
  worst_regime: string
  regime_note: string
}

// ---- Risk Attribution ----
export interface RiskContribution {
  strategy: string
  pnl: number
  pnl_pct: number
  pnl_std: number
  risk_pct: number
  quality_ratio: number
  quality_label: string  // good / bad / neutral
  sharpe: number
  n_trades: number
}

export interface DrawdownContribution {
  strategy: string
  max_drawdown: number
  drawdown_pct: number
  peak_ts: number
  trough_ts: number
  duration_ms: number
  n_trades: number
}

export interface RiskAttributionReport {
  start_ts: number
  end_ts: number
  total_pnl: number
  total_trades: number
  risk_contributions: RiskContribution[]
  best_quality_strategy: string
  worst_quality_strategy: string
  overall_max_drawdown: number
  drawdown_contributions: DrawdownContribution[]
  drawdown_culprit: string
}

// ---- Factor Attribution (预留) ----
export interface FactorContribution {
  factor: string
  label: string
  pnl: number
  pnl_pct: number
  n_trades: number
  avg_factor_value: number
}

export interface FactorAttributionReport {
  start_ts: number
  end_ts: number
  total_pnl: number
  total_trades: number
  factors: FactorContribution[]
  implemented: boolean
  note: string
}

// ---- 综合归因 ----
export interface AttributionOverview {
  session_id: string
  strategy: StrategyAttributionReport
  symbol: SymbolAttributionReport
  time: TimeAttributionReport
  risk: RiskAttributionReport
  factor: FactorAttributionReport
}

export interface AttributionRangeResponse {
  start_ts: number
  end_ts: number
  session_id: string | null
  strategy: StrategyAttributionReport
  symbol: SymbolAttributionReport
  time: TimeAttributionReport
  risk: RiskAttributionReport
}

// ---- Monthly Review ----
export interface TradeSummary {
  trace_id: string
  symbol: string
  strategy: string
  pnl: number
  pnl_pct: number
  timestamp: number
}

export interface MonthlyReport {
  year: number
  month: number
  period_label: string
  start_ts: number
  end_ts: number
  total_pnl: number
  total_trades: number
  n_wins: number
  n_losses: number
  win_rate: number
  max_drawdown: number
  profit_factor: number
  avg_pnl: number
  strategy_attribution: StrategyAttributionReport | null
  symbol_attribution: SymbolAttributionReport | null
  time_attribution: TimeAttributionReport | null
  risk_attribution: RiskAttributionReport | null
  best_trade: TradeSummary | null
  worst_trade: TradeSummary | null
  summary: string
  suggestions: string[]
}
