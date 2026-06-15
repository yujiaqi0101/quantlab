import { http } from './http'

export interface ExperimentInfo {
  id: string
  name: string
  strategy: string
  created_at: string
  tag: string
  note: string
  dataset_id: string
  dataset_version: string
  strategy_version: string
  final_equity: number
  total_return: number
  sharpe: number
  max_drawdown: number
  trade_count: number
  win_rate: number
  source: string
  params: Record<string, any>
  tags_json?: string
}

export interface EquityData {
  experiment_id: string
  timestamps: string[]
  equity: number[]
}

export interface TradeInfo {
  entry_time: string
  exit_time: string
  symbol: string
  side: string
  entry_price: number
  exit_price: number
  qty: number
  pnl: number
  return_pct: number
}

export interface CompareResult {
  experiments: ExperimentInfo[]
  equity_curves: Record<string, EquityData>
  param_diff: Record<string, any>
  metrics_comparison: Record<string, any>
}

export async function getExperiments(params?: {
  strategy?: string
  dataset_id?: string
  tag?: string
  sharpe_min?: number
  max_dd_max?: number
  return_min?: number
  limit?: number
}): Promise<ExperimentInfo[]> {
  const resp = await http.get<ExperimentInfo[]>('/experiments', { params })
  return resp.data
}

export async function searchExperiments(req: {
  q?: string
  strategy?: string
  dataset_id?: string
  sharpe_gt?: number
  sharpe_lt?: number
  return_gt?: number
  return_lt?: number
  max_dd_lt?: number
  trade_count_gt?: number
  tags?: string[]
  limit?: number
}): Promise<ExperimentInfo[]> {
  const resp = await http.post<ExperimentInfo[]>('/experiments/search', req)
  return resp.data
}

export async function getExperiment(id: string): Promise<ExperimentInfo> {
  const resp = await http.get<ExperimentInfo>(`/experiments/${id}`)
  return resp.data
}

export async function deleteExperiment(id: string): Promise<void> {
  await http.delete(`/experiments/${id}`)
}

export async function getEquityCurve(id: string): Promise<EquityData> {
  const resp = await http.get<EquityData>(`/experiments/${id}/equity`)
  return resp.data
}

export async function getTrades(id: string): Promise<TradeInfo[]> {
  const resp = await http.get<TradeInfo[]>(`/experiments/${id}/trades`)
  return resp.data
}

export async function compareExperiments(
  ids: string[],
  includeEquity = true,
  includeTrades = false,
): Promise<CompareResult> {
  const resp = await http.post<CompareResult>('/experiments/compare', {
    experiment_ids: ids,
    include_equity: includeEquity,
    include_trades: includeTrades,
  })
  return resp.data
}

export async function getExperimentTags(id: string): Promise<string[]> {
  const resp = await http.get<string[]>(`/experiments/${id}/tags`)
  return resp.data
}

export async function addExperimentTag(id: string, tag: string): Promise<string[]> {
  const resp = await http.post<{ tags: string[] }>(`/experiments/${id}/tags`, { tag })
  return resp.data.tags
}

export async function removeExperimentTag(id: string, tag: string): Promise<string[]> {
  const resp = await http.delete<{ tags: string[] }>(`/experiments/${id}/tags`, { data: { tag } })
  return resp.data.tags
}

export async function getAvailableTags(): Promise<Record<string, string>> {
  const resp = await http.get<Record<string, string>>('/experiments/tags/list')
  return resp.data
}
