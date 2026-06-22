import { http } from './http'

export interface DatasetSchema {
  columns: { name: string; dtype: string; role: string; description: string }[]
  column_names: string[]
  has_ohlcv: boolean
}

export interface DatasetInfo {
  dataset_id: string
  name: string
  symbol: string
  frequency: string
  asset_type: string
  start_time: string
  end_time: string
  rows: number
  storage_path: string
  storage_format: string
  schema: DatasetSchema
  tags: string[]
  is_ohlcv: boolean
  coverage: string
  scope_type: string
  universe_id: string
}

export interface PreviewData {
  dataset_id: string
  symbols: string[]
  preview: Record<string, {
    columns: string[]
    dtypes: Record<string, string>
    rows: any[][]
    index: string[]
  }>
}

export async function getDatasets(q?: string, tag?: string): Promise<DatasetInfo[]> {
  const params: Record<string, string> = {}
  if (q) params.q = q
  if (tag) params.tag = tag
  const resp = await http.get<DatasetInfo[]>('/datasets', { params })
  return resp.data
}

export async function getDataset(id: string): Promise<DatasetInfo> {
  const resp = await http.get<DatasetInfo>(`/datasets/${id}`)
  return resp.data
}

export async function getDatasetPreview(id: string, n: number = 100, symbol?: string): Promise<PreviewData> {
  const params: Record<string, any> = { n }
  if (symbol) params.symbol = symbol
  const resp = await http.get<PreviewData>(`/datasets/${id}/preview`, { params })
  return resp.data
}

export async function getDatasetSymbols(id: string): Promise<string[]> {
  const resp = await http.get<string[]>(`/datasets/${id}/symbols`)
  return resp.data
}

export async function getDatasetStats(id: string): Promise<Record<string, any>> {
  const resp = await http.get(`/datasets/${id}/stats`)
  return resp.data
}
