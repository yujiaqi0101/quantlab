import { http } from './http'

// ==================== Types ====================

export interface FactorInfo {
  name: string
  category: string
  description: string
  class?: string
}

export interface FactorValue {
  t: string
  v: number
}

export interface ComputeResult {
  factor_name: string
  dataset_id: string
  symbol: string
  count: number
  values: FactorValue[]
}

export interface CandleData {
  t: string
  o: number
  h: number
  l: number
  c: number
  v: number
}

export interface VisualizeResult {
  factor_name: string
  dataset_id: string
  symbol: string
  candles: CandleData[]
  factor: FactorValue[]
}

export interface CorrelationResult {
  labels: string[]
  matrix: (number | null)[][]
  method: string
}

export interface ICStats {
  mean_ic: number
  ic_std: number
  ic_ir: number
  ic_positive: number
  ic_t_stat: number
  count: number
}

export interface ICResult {
  factor_name: string
  dataset_id: string
  symbol: string
  forward_period: number
  ic_stats: ICStats
  rank_ic_stats: ICStats
  turnover: number
  coverage: number
  ic_series: FactorValue[]
  rank_ic_series: FactorValue[]
}

export interface CacheStats {
  memory_entries: number
  disk_entries: number
  total_hits: number
  total_size_mb: number
  max_memory_entries: number
}

// ==================== API ====================

export async function getFactorList(category?: string): Promise<FactorInfo[]> {
  const params: Record<string, string> = {}
  if (category) params.category = category
  const resp = await http.get<FactorInfo[]>('/factors', { params })
  return resp.data
}

export async function getFactorCategories(): Promise<string[]> {
  const resp = await http.get<string[]>('/factors/categories')
  return resp.data
}

export async function getFactorDetail(name: string): Promise<FactorInfo> {
  const resp = await http.get<FactorInfo>(`/factors/${name}`)
  return resp.data
}

export async function computeFactor(
  factorName: string,
  datasetId: string,
  symbol: string = '',
  useCache: boolean = true,
): Promise<ComputeResult> {
  const resp = await http.post<ComputeResult>('/factors/compute', {
    factor_name: factorName,
    dataset_id: datasetId,
    symbol,
    use_cache: useCache,
  })
  return resp.data
}

export async function batchComputeFactors(
  factorNames: string[],
  datasetId: string,
  symbol: string = '',
  useCache: boolean = true,
): Promise<{ dataset_id: string; symbol: string; factors: Record<string, FactorValue[]> }> {
  const resp = await http.post('/factors/batch-compute', {
    factor_names: factorNames,
    dataset_id: datasetId,
    symbol,
    use_cache: useCache,
  })
  return resp.data
}

export async function visualizeFactor(
  factorName: string,
  datasetId: string,
  symbol: string = '',
  nPoints: number = 500,
): Promise<VisualizeResult> {
  const resp = await http.post<VisualizeResult>('/factors/visualize', {
    factor_name: factorName,
    dataset_id: datasetId,
    symbol,
    n_points: nPoints,
  })
  return resp.data
}

export async function getFactorCorrelation(
  factorNames: string[],
  datasetId: string,
  symbol: string = '',
  method: string = 'spearman',
): Promise<CorrelationResult> {
  const resp = await http.post<CorrelationResult>('/factors/correlation', {
    factor_names: factorNames,
    dataset_id: datasetId,
    symbol,
    method,
  })
  return resp.data
}

export async function getFactorIC(
  factorName: string,
  datasetId: string,
  symbol: string = '',
  forwardPeriod: number = 1,
  method: string = 'spearman',
): Promise<ICResult> {
  const resp = await http.post<ICResult>('/factors/ic', {
    factor_name: factorName,
    dataset_id: datasetId,
    symbol,
    forward_period: forwardPeriod,
    method,
  })
  return resp.data
}

export async function getFactorCacheStats(): Promise<CacheStats> {
  const resp = await http.get<CacheStats>('/factors/cache/stats')
  return resp.data
}
