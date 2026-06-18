import { http } from './http'

// ==================================================================
// Live Studio V1 Types — 实时交易工作室
// ==================================================================

// ---- Strategy Registry ----
export interface StrategyParameter {
  name: string
  type: string         // int / float / bool / str / choice
  default: any
  min?: number
  max?: number
  choices?: string[]
  description: string
}

export interface StrategyInfo {
  strategy_id: string
  name: string
  description: string
  category: string
  tags: string[]
  parameters: StrategyParameter[]
  symbols: string[]
  timeframe: string
  author: string
  version: string
  enabled: boolean
}

export interface StrategyListResponse {
  total: number
  strategies: StrategyInfo[]
  categories: string[]
  tags: string[]
}

// ---- Deployment ----
export interface DeployRequest {
  strategy_id: string
  symbols: string[]
  params?: Record<string, any>
  initial_capital?: number
  broker_type?: string
  strategy_name?: string
}

export interface DeployResult {
  deploy_id: string
  strategy_id: string
  status: string       // PENDING / RUNNING / STOPPED / FAILED
  message: string
  deployed_at: number
  runtime_status: Record<string, any>
}

export interface DeploymentRecord {
  deploy_id: string
  strategy_id: string
  request: DeployRequest
  result: DeployResult
  created_at: number
}

export interface DeploymentListResponse {
  total: number
  deployments: DeploymentRecord[]
}

// ---- Runtime Status ----
export interface RuntimeStatus {
  runtime: {
    state: string
    tick_count: number
    error_count: number
    readonly: boolean
    last_tick: number
    uptime_seconds: number
  }
  broker: Record<string, any>
  oms: {
    n_orders: number
    n_active: number
  }
  portfolio: PortfolioBook
  strategies: StrategyRunnerStatus[]
  scheduler: any[]
}

export interface StrategyRunnerStatus {
  strategy_id: string
  state: string
  tick_count: number
  signal_count: number
  error_count: number
  last_signal: any
}

// ---- Portfolio Book ----
export interface PortfolioBook {
  initial_capital: number
  cash: number
  equity: number
  invested_value: number
  net_invested: number
  margin: number
  exposure: number
  long_exposure: number
  short_exposure: number
  realized_pnl: number
  unrealized_pnl: number
  total_pnl: number
  total_return: number
  max_drawdown: number
  current_drawdown: number
  n_open_positions: number
  positions: Record<string, Position>
}

export interface Position {
  symbol: string
  qty: number
  avg_price: number
  market_price: number
  market_value: number
  realized_pnl: number
  unrealized_pnl: number
  side: string
  strategy_id: string
  n_fills: number
  updated_at: number
}

// ---- Orders ----
export interface Order {
  id: string
  client_order_id: string
  broker_order_id: string
  symbol: string
  side: string
  quantity: number
  order_type: string
  price: number | null
  state: string
  filled_qty: number
  avg_fill_price: number
  reject_reason: string
  strategy_id: string
  created_at: number
  updated_at: number
}

export interface OrdersResponse {
  total: number
  orders: Order[]
}

export interface PositionsResponse {
  total: number
  positions: Position[]
}

// ---- Risk ----
export interface RiskStatus {
  equity: number
  exposure: number
  long_exposure: number
  short_exposure: number
  margin: number
  max_drawdown: number
  current_drawdown: number
  n_open_positions: number
  initial_capital: number
  total_pnl: number
  total_return: number
}

// ---- Manual Order ----
export interface ManualOrderRequest {
  symbol: string
  side: string          // BUY / SELL
  qty: number
  order_type?: string   // MARKET / LIMIT
  price?: number | null
  strategy_id?: string
}

// ==================================================================
// API Client
// ==================================================================

class LiveAPI {
  // ----------------------------------------------------------------
  // Live Studio 总览
  // ----------------------------------------------------------------
  async status(): Promise<{
    deployment_manager: any
    strategy_registry: any
  }> {
    const { data } = await http.get('/live/status')
    return data
  }

  // ----------------------------------------------------------------
  // 策略库
  // ----------------------------------------------------------------
  async listStrategies(params?: {
    category?: string
    tag?: string
    enabled_only?: boolean
  }): Promise<StrategyListResponse> {
    const { data } = await http.get('/live/strategies', { params })
    return data
  }

  async getStrategy(strategyId: string): Promise<StrategyInfo> {
    const { data } = await http.get(`/live/strategies/${strategyId}`)
    return data
  }

  // ----------------------------------------------------------------
  // 部署
  // ----------------------------------------------------------------
  async deploy(req: DeployRequest): Promise<DeployResult> {
    const { data } = await http.post('/live/deploy', req)
    return data
  }

  async undeploy(deployId: string): Promise<{ deploy_id: string; undeployed: boolean }> {
    const { data } = await http.post(`/live/undeploy/${deployId}`)
    return data
  }

  async listDeployments(status?: string): Promise<DeploymentListResponse> {
    const { data } = await http.get('/live/deployments', { params: { status } })
    return data
  }

  // ----------------------------------------------------------------
  // 部署详情
  // ----------------------------------------------------------------
  async deploymentStatus(deployId: string): Promise<RuntimeStatus> {
    const { data } = await http.get(`/live/deployments/${deployId}/status`)
    return data
  }

  async deploymentOrders(deployId: string, activeOnly = false): Promise<OrdersResponse> {
    const { data } = await http.get(`/live/deployments/${deployId}/orders`, {
      params: { active_only: activeOnly },
    })
    return data
  }

  async deploymentPositions(deployId: string): Promise<PositionsResponse> {
    const { data } = await http.get(`/live/deployments/${deployId}/positions`)
    return data
  }

  async deploymentPortfolio(deployId: string): Promise<PortfolioBook> {
    const { data } = await http.get(`/live/deployments/${deployId}/portfolio`)
    return data
  }

  async deploymentRisk(deployId: string): Promise<RiskStatus> {
    const { data } = await http.get(`/live/deployments/${deployId}/risk`)
    return data
  }

  // ----------------------------------------------------------------
  // 运行时控制
  // ----------------------------------------------------------------
  async pauseDeployment(deployId: string): Promise<{ deploy_id: string; paused: boolean }> {
    const { data } = await http.post(`/live/deployments/${deployId}/pause`)
    return data
  }

  async resumeDeployment(deployId: string): Promise<{ deploy_id: string; resumed: boolean }> {
    const { data } = await http.post(`/live/deployments/${deployId}/resume`)
    return data
  }

  // ----------------------------------------------------------------
  // 手动交易
  // ----------------------------------------------------------------
  async manualOrder(deployId: string, req: ManualOrderRequest): Promise<Order> {
    const { data } = await http.post(`/live/deployments/${deployId}/order`, req)
    return data
  }

  async cancelOrder(deployId: string, orderId: string): Promise<{ order_id: string; cancelled: boolean }> {
    const { data } = await http.post(`/live/deployments/${deployId}/cancel/${orderId}`)
    return data
  }
}

export const liveApi = new LiveAPI()
