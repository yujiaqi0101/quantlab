import { http } from './http'

// ==================================================================
// Types
// ==================================================================

export interface PackageManifest {
  id: string
  name: string
  version: string
  type: string
  description: string
  status: string
  created_at: string
  created_by: string
  tags: string[]
  hash: string
  config: Record<string, any>
}

export interface ComposeRequest {
  name: string
  family?: string
  version?: string
  description?: string
  model_ref: string
  signal_ref: string
  position_ref: string
  risk_ref: string
  execution_ref: string
  observe_ref: string
  auto_validate?: boolean
}

export interface ComposeResult {
  success: boolean
  strategy_id: string
  strategy: PackageManifest | null
  validation: {
    passed: boolean
    errors: string[]
    warnings: string[]
    graph: any
  } | null
  errors: string[]
}

export interface ValidationReport {
  strategy_id: string
  passed: boolean
  dependency_check: any
  smoke_test: any
  errors: string[]
  warnings: string[]
}

export interface DependencyGraph {
  root: any
  all_refs: string[]
  missing_refs: string[]
}

export interface DatasetInfo {
  dataset_id: string
  name: string
  symbols_count: number
  frequency: string
  start_date: string
  end_date: string
  rows: number
  asset_type: string
  is_multi_symbol: boolean
}

export interface BacktestRequest {
  name: string
  version: string
  dataset_id?: string
  symbol?: string
  bars?: number
  initial_capital?: number
  seed?: number
  max_symbols?: number
  start_date?: string
  end_date?: string
}

export interface BacktestMetrics {
  total_return: number
  annual_return: number
  max_drawdown: number
  sharpe_ratio: number
  volatility: number
  total_orders: number
  buy_orders: number
  sell_orders: number
  final_value: number
  max_positions?: number
  avg_positions?: number
  win_rate?: number
}

export interface EquityPoint {
  timestamp: string
  value: number
  cash: number
  n_positions?: number
}

export interface OrderRecord {
  timestamp: string
  symbol: string
  side: 'BUY' | 'SELL' | 'HOLD'
  quantity: number
  price: number
}

export interface PositionSnapshot {
  timestamp: string
  cash: number
  total_value: number
  n_positions: number
  top_positions: Array<{ symbol: string; qty: number; value: number }>
}

export interface BacktestResult {
  ok: boolean
  strategy_id: string
  symbol: string
  dataset_id: string
  dataset_name: string
  bars: number
  symbols_traded: number
  initial_capital: number
  data_source: string
  metrics: BacktestMetrics
  equity_curve: EquityPoint[]
  orders: OrderRecord[]
  total_orders: number
  positions_history: PositionSnapshot[]
  errors: string[]
}

// ==================================================================
// API
// ==================================================================

const BASE = '/strategy-studio'

export async function composeStrategy(data: ComposeRequest): Promise<ComposeResult> {
  const resp = await http.post(`${BASE}/compose`, data, { timeout: 300000 })
  return resp.data
}

export async function validateStrategy(data: {
  name: string
  version: string
  smoke_test_bars?: number
}): Promise<ValidationReport> {
  const resp = await http.post(`${BASE}/validate`, data, { timeout: 300000 })
  return resp.data
}

export async function runBacktest(data: BacktestRequest): Promise<BacktestResult> {
  const resp = await http.post(`${BASE}/run`, data, { timeout: 300000 })
  return resp.data
}

export async function getStrategies(): Promise<{ strategies: PackageManifest[]; count: number }> {
  const resp = await http.get(`${BASE}/strategies`)
  return resp.data
}

export async function getStrategy(name: string, version: string): Promise<PackageManifest> {
  const resp = await http.get(`${BASE}/strategies/${name}/${version}`)
  return resp.data
}

export async function getDependencies(name: string, version: string): Promise<DependencyGraph> {
  const resp = await http.get(`${BASE}/dependencies/${name}/${version}`)
  return resp.data
}

export async function getPackages(pkgType: string): Promise<{ packages: PackageManifest[]; count: number; type: string }> {
  const resp = await http.get(`${BASE}/packages/${pkgType}`)
  return resp.data
}

export async function getDatasets(): Promise<{ datasets: DatasetInfo[]; count: number }> {
  const resp = await http.get(`${BASE}/datasets`)
  return resp.data
}
