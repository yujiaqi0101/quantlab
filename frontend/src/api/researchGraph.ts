/**
 * Research Graph API — 新 Research OS 接口封装
 *
 * 对接后端 quantlab/api/research.py：
 *   - Node Registry 查询
 *   - Graph CRUD（创建/查询/节点/边）
 *   - Compile / Execute
 *   - Cache 管理
 *   - Materialize（生成训练集）
 */
import { http } from './http'

// ==================== Types ====================

export interface PortType {
  type: 'SERIES' | 'FRAME' | 'PANEL' | 'SCALAR' | 'REFERENCE'
}

export interface NodeManifest {
  id: string
  version: string
  category: 'DATA' | 'TRANSFORM' | 'INDICATOR' | 'ALPHA' | 'AGGREGATION' | 'RANKING' | 'SELECTION' | 'LABEL' | 'CUSTOM'
  inputs: { name: string; port_type: PortType['type'] }[]
  outputs: { name: string; port_type: PortType['type'] }[]
  params_schema: Record<string, any>
  metadata: {
    description: string
    author: string
    cost: number
    deprecated: boolean
    tags: string[]
  }
}

export interface NodeInstance {
  node_id: string
  node_type: string
  version?: string
  params?: Record<string, any>
}

export interface EdgeInstance {
  src_node: string
  src_port: string
  dst_node: string
  dst_port: string
}

export interface Graph {
  graph_id: string
  name: string
  description?: string
  nodes: NodeInstance[]
  edges: EdgeInstance[]
  created_at?: string
  updated_at?: string
}

export interface CompileResult {
  graph_id: string
  ok: boolean
  topological_order: string[]
  errors: string[]
  warnings: string[]
}

export interface ExecuteResult {
  run_id: string
  graph_id: string
  status: 'PENDING' | 'RUNNING' | 'OK' | 'ERROR'
  outputs: Record<string, any>
  executed_nodes: string[]
  cached_nodes: string[]
  errors: Record<string, string>
  duration_ms: number
}

export interface CacheStats {
  total_entries: number
  total_size_bytes: number
  hit_rate: number
  by_level: Record<string, { count: number; size_bytes: number }>
}

export interface MaterializeResult {
  graph_id: string
  n_features: number
  n_train: number
  n_val: number
  n_test: number
  label_name: string
  feature_names: string[]
}

// ==================== API Functions ====================

const BASE = '/research'

// ---- Node Registry ----
export async function listNodes(category?: string): Promise<NodeManifest[]> {
  const params = category ? { category } : {}
  const resp = await http.get<NodeManifest[]>(`${BASE}/nodes`, { params })
  return resp.data
}

export async function getNode(nodeId: string, version?: string): Promise<NodeManifest> {
  const params = version ? { version } : {}
  const resp = await http.get<NodeManifest>(`${BASE}/nodes/${nodeId}`, { params })
  return resp.data
}

// ---- Graph CRUD ----
export async function createGraph(name: string, description?: string): Promise<{ graph_id: string }> {
  const resp = await http.post<{ graph_id: string }>(`${BASE}/graphs`, {
    name,
    description: description || '',
  })
  return resp.data
}

export async function listGraphs(): Promise<Graph[]> {
  const resp = await http.get<Graph[]>(`${BASE}/graphs`)
  return resp.data
}

export async function getGraph(graphId: string): Promise<Graph> {
  const resp = await http.get<Graph>(`${BASE}/graphs/${graphId}`)
  return resp.data
}

export async function deleteGraph(graphId: string): Promise<void> {
  await http.delete(`${BASE}/graphs/${graphId}`)
}

export async function addNode(
  graphId: string,
  nodeId: string,
  nodeType: string,
  params?: Record<string, any>,
): Promise<{ ok: boolean }> {
  const resp = await http.post<{ ok: boolean }>(`${BASE}/graphs/${graphId}/nodes`, {
    node_id: nodeId,
    node_type: nodeType,
    params: params || {},
  })
  return resp.data
}

export async function removeNode(graphId: string, nodeId: string): Promise<void> {
  await http.delete(`${BASE}/graphs/${graphId}/nodes/${nodeId}`)
}

export async function addEdge(graphId: string, edge: EdgeInstance): Promise<{ ok: boolean }> {
  const resp = await http.post<{ ok: boolean }>(`${BASE}/graphs/${graphId}/edges`, edge)
  return resp.data
}

export async function removeEdge(
  graphId: string,
  srcNode: string,
  srcPort: string,
  dstNode: string,
  dstPort: string,
): Promise<void> {
  await http.delete(`${BASE}/graphs/${graphId}/edges`, {
    params: { src_node: srcNode, src_port: srcPort, dst_node: dstNode, dst_port: dstPort },
  })
}

// ---- Compile / Execute ----
export async function compileGraph(graphId: string): Promise<CompileResult> {
  const resp = await http.post<CompileResult>(`${BASE}/graphs/${graphId}/compile`)
  return resp.data
}

export async function executeGraph(
  graphId: string,
  datasetId: string,
  mode: 'sequential' | 'parallel' = 'sequential',
): Promise<ExecuteResult> {
  const resp = await http.post<ExecuteResult>(`${BASE}/graphs/${graphId}/execute`, {
    dataset_id: datasetId,
    mode,
  })
  return resp.data
}

// ---- Cache ----
export async function getCacheStats(graphId?: string): Promise<CacheStats> {
  const params = graphId ? { graph_id: graphId } : {}
  const resp = await http.get<CacheStats>(`${BASE}/cache/stats`, { params })
  return resp.data
}

export async function invalidateCache(nodeId?: string): Promise<{ invalidated: number }> {
  const resp = await http.post<{ invalidated: number }>(`${BASE}/cache/invalidate`, {
    node_id: nodeId,
  })
  return resp.data
}

// ---- Materialize ----
export async function materialize(
  graphId: string,
  datasetId: string,
  labelNodeId: string,
  featureNodeIds?: string[],
  options?: {
    normalize?: boolean
    train_ratio?: number
    val_ratio?: number
    test_ratio?: number
  },
): Promise<MaterializeResult> {
  const resp = await http.post<MaterializeResult>(`${BASE}/graphs/${graphId}/materialize`, {
    dataset_id: datasetId,
    label_node_id: labelNodeId,
    feature_node_ids: featureNodeIds || [],
    normalize: options?.normalize ?? true,
    train_ratio: options?.train_ratio ?? 0.7,
    val_ratio: options?.val_ratio ?? 0.15,
    test_ratio: options?.test_ratio ?? 0.15,
  })
  return resp.data
}
