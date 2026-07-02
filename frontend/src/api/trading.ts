/**
 * Trading Studio API
 *
 * 统一交易工作室 API 封装，对接后端 /api/v1/trading/*。
 * 支持 Paper / Live / Replay 三种模式。
 */
import { http } from './http'

// ----------------------------------------------------------------------
// 类型定义
// ----------------------------------------------------------------------
export type TradingMode = 'paper' | 'live' | 'replay'
export type SessionStatus = 'created' | 'running' | 'paused' | 'stopped'
export type WorkspaceName =
  | 'overview' | 'market' | 'signals' | 'orders' | 'positions'
  | 'portfolio' | 'risk' | 'journal' | 'replay'

export interface TradingSession {
  sid: string
  mode: TradingMode
  strategy_id: string
  strategy_name: string
  status: SessionStatus
  is_active: boolean
  initial_capital: number
  cash: number
  total_value: number
  started_at: string
}

export interface CreateSessionRequest {
  mode: TradingMode
  strategy_id?: string
  strategy_name?: string
  initial_capital?: number
  symbols?: string[]
}

export interface OverviewData {
  sid: string
  today_return: number
  today_pnl: number
  total_pnl: number
  cash: number
  equity: number
  exposure: number
  invested_value: number
  realized_pnl: number
  unrealized_pnl: number
  max_drawdown: number
  current_drawdown: number
  sharpe: number
  n_positions: number
  n_orders: number
  n_open_orders: number
}

export interface Quote {
  symbol: string
  last: number
  change_pct: number
  volume: number
  bid: number
  ask: number
}

export interface SignalItem {
  signal_id: string
  time: string
  symbol: string
  direction: string
  score: number
  confidence: number
  reason: string
  status: string
  order_id: string
}

export interface OrderItem {
  order_id: string
  strategy_id: string
  symbol: string
  side: string
  order_type: string
  quantity: number
  price: number | null
  signal_id: string
  client_order_id: string
  broker_order_id: string
  status: string
  filled_qty: number
  filled_price: number
  reason: string
  created_at: string
  updated_at: string
}

export interface PositionItem {
  symbol: string
  direction: string
  quantity: number
  entry_price: number
  entry_date: string
  current_price: number
  market_value: number
  unrealized_pnl: number
  realized_pnl: number
}

export interface PortfolioData {
  sid: string
  total_equity: number
  cash: number
  invested: number
  exposure: number
  leverage: number
  weights: Array<{ symbol: string; weight: number; market_value: number }>
  n_positions: number
}

export interface RiskData {
  sid: string
  var_95: number
  max_drawdown: number
  current_drawdown: number
  turnover: number
  concentration: number
  exposure: number
  beta: number
  n_positions: number
}

export interface JournalItem {
  time: string
  type: string
  symbol: string
  side: string
  quantity: number
  price: number
  amount: number
  commission: number
  slippage: number
  reason: string
  order_id: string
  trade_id: string
}

export interface EquityPoint {
  time: string
  total_value: number
  cash: number
  daily_return: number
  realized_pnl: number
  unrealized_pnl: number
  max_drawdown: number
}

export interface ReplayTimelineEvent {
  ts: string
  event_type: 'order' | 'trade' | 'snapshot'
  restorable: boolean
  [key: string]: any
}

export interface ManualOrderRequest {
  symbol: string
  side: 'buy' | 'sell'
  quantity: number
  order_type?: 'market' | 'limit'
  price?: number | null
  reason?: string
}

export interface StrategyInfo {
  strategy_id: string
  name: string
  description: string
  category: string
  tags: string[]
  parameters: any[]
  symbols: string[]
  timeframe: string
  author: string
  version: string
  enabled: boolean
}

// ----------------------------------------------------------------------
// API 类
// ----------------------------------------------------------------------
class TradingAPI {
  private base = '/trading'

  // 会话管理
  async listSessions(mode?: TradingMode): Promise<{ sessions: TradingSession[] }> {
    const params = mode ? { mode } : {}
    return http.get(`${this.base}/sessions`, { params }).then(r => r.data)
  }

  async createSession(req: CreateSessionRequest): Promise<TradingSession> {
    return http.post(`${this.base}/sessions`, req).then(r => r.data)
  }

  async getSession(sid: string): Promise<TradingSession> {
    return http.get(`${this.base}/sessions/${sid}`).then(r => r.data)
  }

  async deleteSession(sid: string): Promise<{ sid: string; deleted: boolean }> {
    return http.delete(`${this.base}/sessions/${sid}`).then(r => r.data)
  }

  async startSession(sid: string): Promise<TradingSession> {
    return http.post(`${this.base}/sessions/${sid}/start`).then(r => r.data)
  }

  async pauseSession(sid: string): Promise<TradingSession> {
    return http.post(`${this.base}/sessions/${sid}/pause`).then(r => r.data)
  }

  async resumeSession(sid: string): Promise<TradingSession> {
    return http.post(`${this.base}/sessions/${sid}/resume`).then(r => r.data)
  }

  async stopSession(sid: string): Promise<TradingSession> {
    return http.post(`${this.base}/sessions/${sid}/stop`).then(r => r.data)
  }

  async getSessionStatus(sid: string): Promise<TradingSession> {
    return http.get(`${this.base}/sessions/${sid}/status`).then(r => r.data)
  }

  // 数据查询
  async getOverview(sid: string): Promise<OverviewData> {
    return http.get(`${this.base}/sessions/${sid}/overview`).then(r => r.data)
  }

  async getMarket(sid: string, symbols?: string[]): Promise<{ symbols: string[]; quotes: Quote[] }> {
    const params = symbols?.length ? { symbols: symbols.join(',') } : {}
    return http.get(`${this.base}/sessions/${sid}/market`, { params }).then(r => r.data)
  }

  async getSignals(sid: string, limit = 100): Promise<{ signals: SignalItem[] }> {
    return http.get(`${this.base}/sessions/${sid}/signals`, { params: { limit } }).then(r => r.data)
  }

  async getOrders(sid: string, status?: string, limit = 200): Promise<{ orders: OrderItem[] }> {
    const params: any = { limit }
    if (status) params.status = status
    return http.get(`${this.base}/sessions/${sid}/orders`, { params }).then(r => r.data)
  }

  async getPositions(sid: string): Promise<{ positions: PositionItem[] }> {
    return http.get(`${this.base}/sessions/${sid}/positions`).then(r => r.data)
  }

  async getPortfolio(sid: string): Promise<PortfolioData> {
    return http.get(`${this.base}/sessions/${sid}/portfolio`).then(r => r.data)
  }

  async getRisk(sid: string): Promise<RiskData> {
    return http.get(`${this.base}/sessions/${sid}/risk`).then(r => r.data)
  }

  async getJournal(sid: string, limit = 100): Promise<{ journal: JournalItem[] }> {
    return http.get(`${this.base}/sessions/${sid}/journal`, { params: { limit } }).then(r => r.data)
  }

  async getEquityCurve(sid: string, points = 500): Promise<{ curve: EquityPoint[] }> {
    return http.get(`${this.base}/sessions/${sid}/equity-curve`, { params: { points } }).then(r => r.data)
  }

  // 操作
  async manualOrder(sid: string, req: ManualOrderRequest): Promise<any> {
    return http.post(`${this.base}/sessions/${sid}/order`, req).then(r => r.data)
  }

  async cancelOrder(sid: string, orderId: string): Promise<any> {
    return http.post(`${this.base}/sessions/${sid}/cancel/${orderId}`).then(r => r.data)
  }

  async killSwitch(sid: string): Promise<any> {
    return http.post(`${this.base}/sessions/${sid}/kill-switch`).then(r => r.data)
  }

  // Replay
  async getReplayTimeline(sid: string, limit = 500): Promise<{ timeline: ReplayTimelineEvent[] }> {
    return http.get(`${this.base}/sessions/${sid}/replay/timeline`, { params: { limit } }).then(r => r.data)
  }

  async getReplaySnapshot(sid: string, time: string): Promise<any> {
    return http.get(`${this.base}/sessions/${sid}/replay/snapshot`, { params: { time } }).then(r => r.data)
  }

  async restoreReplay(sid: string, time: string): Promise<any> {
    return http.post(`${this.base}/sessions/${sid}/replay/restore`, { time }).then(r => r.data)
  }

  // 策略库
  async listStrategies(): Promise<{ strategies: StrategyInfo[] }> {
    return http.get(`${this.base}/strategies`).then(r => r.data)
  }

  async getStrategy(strategyId: string): Promise<StrategyInfo> {
    return http.get(`${this.base}/strategies/${strategyId}`).then(r => r.data)
  }
}

export const tradingApi = new TradingAPI()
