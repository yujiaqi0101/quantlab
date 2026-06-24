import { http } from './http'

// ==================================================================
// Types
// ==================================================================

export interface PackageManifest {
  id: string
  name: string
  version: string
  type: string  // MODEL / SIGNAL / POSITION / RISK / EXECUTION / OBSERVE / STRATEGY
  description: string
  status: string
  created_at: string
  created_by: string
  tags: string[]
  hash: string
  config: Record<string, any>
}

export interface ComposeRequest {
  name: string
  family?: string
  version?: string
  description?: string
  model_ref: string
  signal_ref: string
  position_ref: string
  risk_ref: string
  execution_ref: string
  observe_ref: string
  auto_validate?: boolean
}

export interface ComposeResult {
  success: boolean
  strategy_id: string
  strategy: PackageManifest | null
  validation: {
    passed: boolean
    errors: string[]
    warnings: string[]
    graph: any
  } | null
  errors: string[]
}

export interface ValidationReport {
  strategy_id: string
  passed: boolean
  dependency_check: any
  smoke_test: any
  errors: string[]
  warnings: string[]
}

export interface DependencyGraph {
  root: any
  all_refs: string[]
  missing_refs: string[]
}

// ==================================================================
// API
// ==================================================================

// Strategy Studio 路由前缀（与 http.ts baseURL /api/v1 拼接）
const BASE = '/strategy-studio'

export async function composeStrategy(data: ComposeRequest): Promise<ComposeResult> {
  const resp = await http.post(`${BASE}/compose`, data, { timeout: 300000 })
  return resp.data
}

export async function validateStrategy(data: {
  name: string
  version: string
  smoke_test_bars?: number
}): Promise<ValidationReport> {
  const resp = await http.post(`${BASE}/validate`, data, { timeout: 300000 })
  return resp.data
}

export async function getStrategies(): Promise<{ strategies: PackageManifest[]; count: number }> {
  const resp = await http.get(`${BASE}/strategies`)
  return resp.data
}

export async function getStrategy(name: string, version: string): Promise<PackageManifest> {
  const resp = await http.get(`${BASE}/strategies/${name}/${version}`)
  return resp.data
}

export async function getDependencies(name: string, version: string): Promise<DependencyGraph> {
  const resp = await http.get(`${BASE}/dependencies/${name}/${version}`)
  return resp.data
}

export async function getPackages(pkgType: string): Promise<{ packages: PackageManifest[]; count: number; type: string }> {
  const resp = await http.get(`${BASE}/packages/${pkgType}`)
  return resp.data
}
