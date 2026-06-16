import { http } from './http'

export interface BacktestSubmitRequest {
  strategy: string
  parameters: Record<string, any>
  dataset: string
  symbols?: string[]
  start?: string
  end?: string
  initial_cash?: number
  commission_bps?: number
  slippage_bps?: number
  engine?: string
  top_n?: number
  save_experiment?: boolean
  experiment_name?: string
}

export interface BacktestMetrics {
  total_return: number
  annualized_return: number
  sharpe: number
  max_drawdown: number
  win_rate: number
  profit_factor: number
  n_trades: number
  avg_trade: number
  final_equity: number
}

export interface BacktestResponse {
  task_id: string
  status: string
  experiment_id?: string | null
  metrics?: BacktestMetrics | null
  message?: string | null
}

export interface TaskInfo {
  task_id: string
  type: string
  status: string
  progress: number
  result?: any
  error?: string | null
  created_at?: string
  finished_at?: string
}

export async function submitBacktest(req: BacktestSubmitRequest): Promise<BacktestResponse> {
  const resp = await http.post<BacktestResponse>('/backtests', req)
  return resp.data
}

export async function getTask(taskId: string): Promise<TaskInfo> {
  const resp = await http.get<TaskInfo>(`/tasks/${taskId}`)
  return resp.data
}

export async function getTasks(status?: string): Promise<TaskInfo[]> {
  const params: Record<string, string> = {}
  if (status) params.status = status
  const resp = await http.get<TaskInfo[]>('/tasks', { params })
  return resp.data
}
