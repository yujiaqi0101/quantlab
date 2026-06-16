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
  status?: 'normal' | 'candidate' | 'production' | 'paper_trading'
  folder?: string
  favorite?: number
  parent_id?: string
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

// ---- Status / Favorite / Folder ----

export async function setExperimentStatus(id: string, status: string): Promise<{ status: string }> {
  const resp = await http.put<{ status: string }>(`/experiments/${id}/status`, { status })
  return resp.data
}

export async function setExperimentFavorite(id: string, favorite: boolean): Promise<{ favorite: boolean }> {
  const resp = await http.put<{ favorite: boolean }>(`/experiments/${id}/favorite`, { favorite })
  return resp.data
}

export async function setExperimentFolder(id: string, folder: string): Promise<{ folder: string }> {
  const resp = await http.put<{ folder: string }>(`/experiments/${id}/folder`, { folder })
  return resp.data
}

export async function listFolders(): Promise<string[]> {
  const resp = await http.get<string[]>('/experiments/folders/list')
  return resp.data
}

export interface AnalyticsData {
  drawdown_curve: number[]
  monthly_returns: Record<string, Record<string, number>>
  annual_returns: Record<string, number>
  rolling_sharpe: number[]
  rolling_drawdown: number[]
  rolling_volatility: number[]
  rolling_start_index: number
  extended_metrics: {
    sortino?: number
    calmar?: number
    volatility?: number
    profit_factor?: number
  }
  pnl_distribution: {
    counts: number[]
    edges: number[]
  }
  holding_stats: {
    avg_days: number
    max_days: number
    min_days: number
    median_days: number
  }
  top_winners: TradeInfo[]
  top_losers: TradeInfo[]
}

export async function getExperimentAnalytics(id: string): Promise<AnalyticsData> {
  const resp = await http.get<AnalyticsData>(`/experiments/${id}/analytics`)
  return resp.data
}

// ---- Rank / Leaderboard ----

export interface RankItem {
  rank: number
  id: string
  name: string
  strategy: string
  sharpe: number
  total_return: number
  max_drawdown: number
  win_rate: number
  trade_count: number
  final_equity: number
  created_at: string
  status?: string
  folder?: string
  favorite?: number
}

export async function getLeaderboard(
  metric: string = 'sharpe',
  top: number = 20,
  strategy?: string,
): Promise<RankItem[]> {
  const resp = await http.get<RankItem[]>('/experiments/rank', {
    params: { metric, top, strategy },
  })
  return resp.data
}

// ---- Research Journal ----

export interface LineageNode {
  id: string
  name: string
  strategy: string
  params: Record<string, any>
  created_at: string
  parent_id: string
  status: string
  children?: LineageNode[]
}

export interface LineageData {
  experiment_id: string
  ancestors: LineageNode[]
  children: LineageNode[]
  siblings: LineageNode[]
  family: LineageNode
}

export interface ActivityItem {
  id: number
  experiment_id: string
  action: string
  detail: string
  created_at: string
  name?: string
  strategy?: string
  status?: string
}

export async function setExperimentNote(id: string, note: string): Promise<{ note: string }> {
  const resp = await http.put<{ note: string }>(`/experiments/${id}/note`, { note })
  return resp.data
}

export async function setExperimentParent(id: string, parentId: string): Promise<{ parent_id: string }> {
  const resp = await http.put<{ parent_id: string }>(`/experiments/${id}/parent`, { parent_id: parentId })
  return resp.data
}

export async function getExperimentLineage(id: string): Promise<LineageData> {
  const resp = await http.get<LineageData>(`/experiments/${id}/lineage`)
  return resp.data
}

export async function getExperimentActivity(id: string, limit: number = 50): Promise<ActivityItem[]> {
  const resp = await http.get<ActivityItem[]>(`/experiments/${id}/activity`, { params: { limit } })
  return resp.data
}

export async function getGlobalTimeline(limit: number = 50): Promise<ActivityItem[]> {
  const resp = await http.get<ActivityItem[]>('/experiments/timeline/global', { params: { limit } })
  return resp.data
}
