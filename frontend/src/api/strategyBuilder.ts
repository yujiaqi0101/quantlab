import { http } from './http'

// ==================== Types ====================

export interface SignalRuleData {
  type: string       // "threshold" / "crossover" / "zero_cross"
  factor: string
  op: string
  value: number
  direction: string  // "long" / "short" / "both"
  fast_factor: string
  slow_factor: string
}

export interface PositionConfig {
  type: string       // "target" / "equal_weight" / "risk_parity"
  value: number
  max_position: number
  min_position: number
}

export interface RiskConfig {
  stop_loss: number
  take_profit: number
  max_drawdown: number
  trailing_stop: number
}

export interface StrategySpecData {
  name: string
  signals: SignalRuleData[]
  signal_logic: string
  position: PositionConfig
  risk: RiskConfig
  description: string
  tags: string[]
  created_at: string
  spec_id: string
}

export interface StrategySpecSummary {
  spec_id: string
  name: string
  description: string
  signal_count: number
  signal_logic: string
  position_type: string
  position_value: number
  tags: string[]
  created_at: string
}

export interface StrategyTemplate {
  key: string
  name: string
  description: string
  signals: SignalRuleData[]
  signal_logic: string
  position: PositionConfig
  risk: RiskConfig
  tags: string[]
}

export interface CompileResult {
  spec_id: string
  name: string
  class_name: string
  compiled: boolean
  signal_count: number
  signal_logic: string
  position: PositionConfig
  risk: RiskConfig
  message: string
}

export interface PreviewResult {
  spec_id: string
  name: string
  total_bars: number
  long_count: number
  short_count: number
  neutral_count: number
  long_pct: number
  short_pct: number
  signal_timeline: number[]
  signal_logic: string
  position: PositionConfig
  risk: RiskConfig
}

// ==================== API Functions ====================

export async function listTemplates(): Promise<StrategyTemplate[]> {
  const resp = await http.get<StrategyTemplate[]>('/strategy-builder/templates')
  return resp.data
}

export async function createStrategy(
  name: string,
  signals: SignalRuleData[],
  signalLogic: string = 'AND',
  position?: Partial<PositionConfig>,
  risk?: Partial<RiskConfig>,
  description: string = '',
  tags: string[] = [],
): Promise<StrategySpecData> {
  const resp = await http.post<StrategySpecData>('/strategy-builder/create', {
    name,
    signals,
    signal_logic: signalLogic,
    position: position || { type: 'target', value: 1.0, max_position: 1.0, min_position: 0.0 },
    risk: risk || { stop_loss: 0, take_profit: 0, max_drawdown: 0, trailing_stop: 0 },
    description,
    tags,
  })
  return resp.data
}

export async function listSpecs(): Promise<StrategySpecSummary[]> {
  const resp = await http.get<StrategySpecSummary[]>('/strategy-builder/specs')
  return resp.data
}

export async function getSpec(specId: string): Promise<StrategySpecData> {
  const resp = await http.get<StrategySpecData>(`/strategy-builder/specs/${specId}`)
  return resp.data
}

export async function deleteSpec(specId: string): Promise<{ deleted: boolean; spec_id: string }> {
  const resp = await http.delete<{ deleted: boolean; spec_id: string }>(`/strategy-builder/specs/${specId}`)
  return resp.data
}

export async function compileStrategy(specId: string): Promise<CompileResult> {
  const resp = await http.post<CompileResult>('/strategy-builder/compile', {
    spec_id: specId,
  })
  return resp.data
}

export async function previewStrategy(
  specId: string,
  datasetId: string = 'default',
  symbol: string = '',
  bars: number = 200,
): Promise<PreviewResult> {
  const resp = await http.post<PreviewResult>('/strategy-builder/preview', {
    spec_id: specId,
    dataset_id: datasetId,
    symbol,
    bars,
  })
  return resp.data
}

export async function createFromTemplate(
  templateKey: string,
  name?: string,
): Promise<StrategySpecData> {
  const resp = await http.post<StrategySpecData>('/strategy-builder/from-template', null, {
    params: { template_key: templateKey, name: name || undefined },
  })
  return resp.data
}
