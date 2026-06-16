import { http } from './http'

// ==================== Types ====================

export interface SweepResultItem {
  params: Record<string, number | string>
  sharpe: number
  total_return: number
  max_drawdown: number
  trade_count: number
  win_rate: number
  final_equity: number
}

export interface SweepResult {
  sweep_id: string
  strategy_id: string
  dataset_id: string
  total_combos: number
  completed: number
  errors: number
  status: string
  results: SweepResultItem[]
  param_space?: Record<string, (number | string)[]>
  created_at?: string
}

export interface SweepSummary {
  sweep_id: string
  strategy_id: string
  dataset_id: string
  total_combos: number
  completed: number
  errors: number
  status: string
  created_at: string
}

export interface HeatmapData {
  x_label: string
  y_label: string
  x_values: (number | string)[]
  y_values: (number | string)[]
  matrix: (number | null)[][]
  metric: string
}

export interface RobustnessResult {
  best_params: Record<string, number | string>
  best_metric: number
  neighbor_count: number
  neighbor_metrics?: number[]
  neighbor_std: number
  robustness: number
}

export interface CandidateItem {
  params: Record<string, number | string>
  sharpe: number
  max_drawdown: number
  trade_count: number
  total_return: number
  win_rate: number
}

export interface CandidateResult {
  sweep_id: string
  criteria: {
    min_sharpe: number
    max_drawdown: number
    min_trades: number
  }
  count: number
  candidates: CandidateItem[]
}

export interface WalkForwardWindow {
  window_id: number
  train_period: string
  test_period: string
  best_params: Record<string, number>
  train_sharpe: number
  test_sharpe: number
  test_return: number
  test_max_dd: number
}

export interface WalkForwardResult {
  strategy_id: string
  dataset_id: string
  train_years: number
  test_years: number
  n_windows: number
  windows: WalkForwardWindow[]
  avg_test_sharpe: number
  avg_test_return: number
  stability_score: number
}

export interface ResearchReport {
  sweep_id: string
  strategy_id: string
  dataset_id: string
  total_combos: number
  completed: number
  generated_at: string
  overview: {
    best_sharpe: number
    best_return: number
    worst_sharpe: number
    avg_sharpe: number
  }
  heatmap?: HeatmapData
  robustness?: RobustnessResult
  candidates?: {
    count: number
    top5: CandidateItem[]
  }
}

// ==================== API Functions ====================

export async function runSweep(
  strategyId: string,
  paramSpace: Record<string, (number | string)[]>,
  datasetId: string = 'default',
  useMock: boolean = true,
): Promise<SweepResult> {
  const resp = await http.post<SweepResult>('/research/sweep', {
    strategy_id: strategyId,
    param_space: paramSpace,
    dataset_id: datasetId,
    use_mock: useMock,
  })
  return resp.data
}

export async function listSweeps(): Promise<SweepSummary[]> {
  const resp = await http.get<SweepSummary[]>('/research/sweeps')
  return resp.data
}

export async function getSweep(sweepId: string): Promise<SweepResult> {
  const resp = await http.get<SweepResult>(`/research/sweeps/${sweepId}`)
  return resp.data
}

export async function getHeatmap(
  sweepId: string,
  xParam: string,
  yParam: string,
  metric: string = 'sharpe',
): Promise<HeatmapData> {
  const resp = await http.post<HeatmapData>('/research/heatmap', {
    sweep_id: sweepId,
    x_param: xParam,
    y_param: yParam,
    metric,
  })
  return resp.data
}

export async function getRobustness(
  sweepId: string,
  params: string[],
  metric: string = 'sharpe',
): Promise<RobustnessResult> {
  const resp = await http.post<RobustnessResult>('/research/robustness', {
    sweep_id: sweepId,
    params,
    metric,
  })
  return resp.data
}

export async function getCandidates(
  sweepId: string,
  minSharpe: number = 1.5,
  maxDrawdown: number = 0.2,
  minTrades: number = 50,
): Promise<CandidateResult> {
  const resp = await http.post<CandidateResult>('/research/candidates', {
    sweep_id: sweepId,
    min_sharpe: minSharpe,
    max_drawdown: maxDrawdown,
    min_trades: minTrades,
  })
  return resp.data
}

export async function runWalkForward(
  strategyId: string,
  paramSpace: Record<string, (number | string)[]>,
  datasetId: string = 'default',
  trainYears: number = 3,
  testYears: number = 1,
  useMock: boolean = true,
): Promise<WalkForwardResult> {
  const resp = await http.post<WalkForwardResult>('/research/walk-forward', {
    strategy_id: strategyId,
    param_space: paramSpace,
    dataset_id: datasetId,
    train_years: trainYears,
    test_years: testYears,
    use_mock: useMock,
  })
  return resp.data
}

export async function generateReport(
  sweepId: string,
  includeHeatmap: boolean = true,
  includeRobustness: boolean = true,
  includeCandidates: boolean = true,
  minSharpe: number = 1.5,
): Promise<ResearchReport> {
  const resp = await http.post<ResearchReport>('/research/report', {
    sweep_id: sweepId,
    include_heatmap: includeHeatmap,
    include_robustness: includeRobustness,
    include_candidates: includeCandidates,
    min_sharpe: minSharpe,
  })
  return resp.data
}
