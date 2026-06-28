/**
 * Signal Engine API — ML Lab 信号引擎
 *
 * 对应后端 /api/v1/signal-engine/*
 */
import http from './http'

// ---------- 类型定义 ----------

export interface Prediction {
  symbol: string
  datetime: string
  value: number
  probability: number
  model_type: string
  metadata: Record<string, any>
}

export interface Signal {
  signal_id: string
  symbol: string
  datetime: string
  direction: 'LONG' | 'SHORT' | 'NEUTRAL'
  score: number
  confidence: number
  expected_return: number
  suggested_weight: number
  holding_period: number
  source_model: string
  generator: string
  metadata: Record<string, any>
}

export interface SignalSet {
  set_id: string
  generated_at: string
  signals: Signal[]
  pipeline_config: Record<string, any>
  summary: {
    total: number
    n_long: number
    n_short: number
    n_neutral: number
    avg_score: number
    avg_confidence: number
    total_weight: number
  }
  metadata: Record<string, any>
}

export interface PipelineConfig {
  generator?: Record<string, any>
  calibrator?: Record<string, any>
  filters?: Record<string, any>[]
  ranker?: Record<string, any>
  scorer?: Record<string, any>
  allocator?: Record<string, any>
  holding_period?: number
  save_to_registry?: boolean
  model_version?: string
  dataset_id?: string
}

export interface SignalTemplate {
  name: string
  description: string
  pipeline_config: Record<string, any>
  required_model_type: string
}

export interface SignalVersion {
  version_id: string
  signal_id: string
  version: number
  generator_config: Record<string, any>
  model_version: string
  dataset_id: string
  validation_summary: Record<string, any>
  pipeline_config: Record<string, any>
  created_at: string
}

export interface ValidationReport {
  hit_rate: number
  precision: number
  recall: number
  avg_return: number
  turnover: number
  avg_holding_days: number
  ic: number
  rank_ic: number
  win_rate: number
  n_signals: number
  period: string
  details: Record<string, any>
}

export interface ExplainTrace {
  prediction: Record<string, any>
  after_calibration: Record<string, any>
  after_generator: Record<string, any>
  after_filter: Record<string, any>
  after_ranker: Record<string, any>
  after_scorer: Record<string, any>
  after_allocator: Record<string, any>
  final_signal: Record<string, any>
}

// ---------- API 调用 ----------

/** 运行 pipeline 生成信号 */
export async function runPipeline(data: {
  predictions: Prediction[]
  config?: PipelineConfig
  market_data?: Record<string, any>
  save_to_registry?: boolean
  model_version?: string
  dataset_id?: string
}): Promise<SignalSet> {
  const res = await http.post('/signal-engine/generate', data)
  return res.data
}

/** 模板列表 */
export async function getTemplates(): Promise<{ templates: SignalTemplate[]; total: number }> {
  const res = await http.get('/signal-engine/templates')
  return res.data
}

/** 单个模板详情 */
export async function getTemplate(name: string): Promise<SignalTemplate> {
  const res = await http.get(`/signal-engine/templates/${name}`)
  return res.data
}

/** 信号列表 */
export async function getSignals(params?: {
  symbol?: string
  direction?: string
  limit?: number
  offset?: number
}): Promise<{ signals: Signal[]; total: number }> {
  const res = await http.get('/signal-engine/signals', { params })
  return res.data
}

/** 单个信号详情 */
export async function getSignal(signalId: string): Promise<Signal> {
  const res = await http.get(`/signal-engine/signals/${signalId}`)
  return res.data
}

/** 版本列表 */
export async function getVersions(signalId: string): Promise<{ versions: SignalVersion[]; total: number }> {
  const res = await http.get('/signal-engine/registry/versions', { params: { signal_id: signalId } })
  return res.data
}

/** 单个版本详情 */
export async function getVersion(versionId: string): Promise<SignalVersion> {
  const res = await http.get(`/signal-engine/registry/versions/${versionId}`)
  return res.data
}

/** 验证信号 */
export async function validateSignals(data: {
  signal_ids: string[]
  returns_data: Record<string, number[]>
  returns_index: string[]
}): Promise<ValidationReport> {
  const res = await http.post('/signal-engine/validate', data)
  return res.data
}

/** 信号解释 */
export async function explainSignal(signalId: string): Promise<ExplainTrace> {
  const res = await http.get(`/signal-engine/explain/${signalId}`)
  return res.data
}

/** 手动调 Adapter（调试用） */
export async function adaptPredictions(data: {
  model_type: string
  outputs: any[]
  symbols: string[]
  datetime: string
  y_probas?: number[][]
}): Promise<{ predictions: Prediction[]; total: number }> {
  const res = await http.post('/signal-engine/adapt', data)
  return res.data
}
