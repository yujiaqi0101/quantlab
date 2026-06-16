import { http } from './http'

// ==================== Types ====================

export interface SignalInfo {
  name: string
  description: string
  type: string
  factor_name?: string
  lower?: number
  upper?: number
  fast_factor?: string
  slow_factor?: string
  sub_signals?: string[]
  logic?: string
}

export interface OperatorInfo {
  value: string
  label: string
  type: string
}

export interface SignalPreview {
  signal_name: string
  dataset_id: string
  symbol: string
  total_bars: number
  long_count: number
  short_count: number
  neutral_count: number
  coverage: number
  long_pct: number
  short_pct: number
}

export interface CandleData {
  t: string
  o: number
  h: number
  l: number
  c: number
  v: number
}

export interface SignalValue {
  t: string
  v: number
}

export interface SignalVisualizeResult {
  signal_name: string
  dataset_id: string
  symbol: string
  candles: CandleData[]
  signal: SignalValue[]
}

export interface ForwardReturnDetail {
  mean: number
  median: number
  win_rate: number
  count: number
  std: number
}

export interface ForwardReturnAll {
  mean: number
  win_rate: number
  count: number
}

export interface ForwardReturnPeriod {
  long: ForwardReturnDetail
  short: ForwardReturnDetail
  all: ForwardReturnAll
}

export interface ForwardReturnResult {
  signal_name: string
  dataset_id: string
  symbol: string
  forward_returns: Record<string, ForwardReturnPeriod>
}

export interface CombineResult {
  name: string
  description: string
  type: string
  sub_signals: string[]
  logic: string
  preview?: SignalPreview
}

// ==================== API ====================

export async function getSignalList(): Promise<SignalInfo[]> {
  const resp = await http.get<SignalInfo[]>('/signals')
  return resp.data
}

export async function getOperators(): Promise<OperatorInfo[]> {
  const resp = await http.get<OperatorInfo[]>('/signals/operators')
  return resp.data
}

export async function buildThresholdSignal(
  factorName: string,
  operator: string,
  value: number,
  direction: string = 'long',
  signalName?: string,
): Promise<{ name: string; description: string; type: string }> {
  const resp = await http.post('/signals/build', {
    factor_name: factorName,
    operator,
    value,
    direction,
    signal_name: signalName,
  })
  return resp.data
}

export async function buildCrossoverSignal(
  fastFactor: string,
  slowFactor: string,
  signalName?: string,
): Promise<{ name: string; description: string; type: string }> {
  const resp = await http.post('/signals/build/crossover', {
    fast_factor: fastFactor,
    slow_factor: slowFactor,
    signal_name: signalName,
  })
  return resp.data
}

export async function buildZeroCrossSignal(
  factorName: string,
  signalName?: string,
): Promise<{ name: string; description: string; type: string }> {
  const resp = await http.post('/signals/build/zero-cross', {
    factor_name: factorName,
    signal_name: signalName,
  })
  return resp.data
}

export async function previewSignal(
  signalName: string,
  datasetId: string,
  symbol: string = '',
): Promise<SignalPreview> {
  const resp = await http.post<SignalPreview>('/signals/preview', {
    signal_name: signalName,
    dataset_id: datasetId,
    symbol,
  })
  return resp.data
}

export async function visualizeSignal(
  signalName: string,
  datasetId: string,
  symbol: string = '',
  nPoints: number = 500,
): Promise<SignalVisualizeResult> {
  const resp = await http.post<SignalVisualizeResult>('/signals/visualize', {
    signal_name: signalName,
    dataset_id: datasetId,
    symbol,
    n_points: nPoints,
  })
  return resp.data
}

export async function getForwardReturn(
  signalName: string,
  datasetId: string,
  symbol: string = '',
  forwardPeriods: number[] = [1, 5, 10, 20],
): Promise<ForwardReturnResult> {
  const resp = await http.post<ForwardReturnResult>('/signals/forward-return', {
    signal_name: signalName,
    dataset_id: datasetId,
    symbol,
    forward_periods: forwardPeriods,
  })
  return resp.data
}

export async function combineSignals(
  signalNames: string[],
  logic: string = 'AND',
  signalName?: string,
  datasetId: string = '',
  symbol: string = '',
): Promise<CombineResult> {
  const resp = await http.post<CombineResult>('/signals/combine', {
    signal_names: signalNames,
    logic,
    signal_name: signalName,
    dataset_id: datasetId,
    symbol,
  })
  return resp.data
}
