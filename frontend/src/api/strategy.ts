import { http } from './http'

export interface StrategyParam {
  name: string
  type: string
  default: any
  min_value?: number | null
  max_value?: number | null
  step?: number | null
  choices?: any[]
  description?: string
  required?: boolean
}

export interface StrategyInfo {
  id: string
  name: string
  description: string
  version: string
  tags: string[]
  parameters: StrategyParam[]
  param_space: Record<string, any[]>
  class_path: string
}

export async function getStrategies(q?: string, tags?: string): Promise<StrategyInfo[]> {
  const params: Record<string, string> = {}
  if (q) params.q = q
  if (tags) params.tags = tags
  const resp = await http.get<StrategyInfo[]>('/strategies', { params })
  return resp.data
}

export async function getStrategy(id: string): Promise<StrategyInfo> {
  const resp = await http.get<StrategyInfo>(`/strategies/${id}`)
  return resp.data
}

export async function validateStrategyParams(
  id: string,
  params: Record<string, any>,
): Promise<{ ok: boolean; errors: string[] }> {
  const resp = await http.post<{ ok: boolean; errors: string[] }>(
    `/strategies/${id}/validate`,
    params,
  )
  return resp.data
}
