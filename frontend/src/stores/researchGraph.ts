/**
 * Research Graph Pinia Store
 *
 * 管理当前 Graph 状态、节点库、执行结果、缓存统计。
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as api from '@/api/researchGraph'
import type {
  NodeManifest,
  Graph,
  NodeInstance,
  EdgeInstance,
  CompileResult,
  ExecuteResult,
  CacheStats,
} from '@/api/researchGraph'

export const useResearchGraphStore = defineStore('researchGraph', () => {
  // ---- State ----
  const nodes = ref<NodeManifest[]>([])                 // Node Registry 全量
  const currentGraph = ref<Graph | null>(null)
  const graphList = ref<Graph[]>([])
  const selectedNodeId = ref<string>('')                // 画布上选中的节点实例 ID
  const compileResult = ref<CompileResult | null>(null)
  const executeResult = ref<ExecuteResult | null>(null)
  const cacheStats = ref<CacheStats | null>(null)
  const loading = ref(false)
  const error = ref('')

  // ---- Getters ----
  const nodesByCategory = computed(() => {
    const groups: Record<string, NodeManifest[]> = {}
    for (const n of nodes.value) {
      const cat = n.category
      if (!groups[cat]) groups[cat] = []
      groups[cat].push(n)
    }
    return groups
  })

  const selectedManifest = computed<NodeManifest | null>(() => {
    if (!currentGraph.value || !selectedNodeId.value) return null
    const inst = currentGraph.value.nodes.find((n) => n.node_id === selectedNodeId.value)
    if (!inst) return null
    return nodes.value.find((n) => n.id === inst.node_type) || null
  })

  const selectedInstance = computed<NodeInstance | null>(() => {
    if (!currentGraph.value || !selectedNodeId.value) return null
    return currentGraph.value.nodes.find((n) => n.node_id === selectedNodeId.value) || null
  })

  // ---- Actions ----
  async function fetchNodes() {
    try {
      nodes.value = await api.listNodes()
    } catch (e: any) {
      error.value = `Failed to load nodes: ${e.message}`
    }
  }

  async function fetchGraphs() {
    try {
      graphList.value = await api.listGraphs()
    } catch (e: any) {
      error.value = `Failed to load graphs: ${e.message}`
    }
  }

  async function loadGraph(graphId: string) {
    loading.value = true
    try {
      currentGraph.value = await api.getGraph(graphId)
      selectedNodeId.value = ''
      compileResult.value = null
      executeResult.value = null
    } catch (e: any) {
      error.value = `Failed to load graph: ${e.message}`
    } finally {
      loading.value = false
    }
  }

  async function createGraph(name: string, description?: string) {
    const { graph_id } = await api.createGraph(name, description)
    await fetchGraphs()
    await loadGraph(graph_id)
    return graph_id
  }

  async function addNode(nodeType: string, nodeId?: string): Promise<void> {
    if (!currentGraph.value) return
    const id = nodeId || `${nodeType}_${currentGraph.value.nodes.length + 1}`
    await api.addNode(currentGraph.value.graph_id, id, nodeType)
    await loadGraph(currentGraph.value.graph_id)
    selectedNodeId.value = id
  }

  async function removeNodeInstance(nodeId: string): Promise<void> {
    if (!currentGraph.value) return
    await api.removeNode(currentGraph.value.graph_id, nodeId)
    if (selectedNodeId.value === nodeId) selectedNodeId.value = ''
    await loadGraph(currentGraph.value.graph_id)
  }

  async function addEdge(edge: EdgeInstance): Promise<void> {
    if (!currentGraph.value) return
    await api.addEdge(currentGraph.value.graph_id, edge)
    await loadGraph(currentGraph.value.graph_id)
  }

  async function compile(): Promise<void> {
    if (!currentGraph.value) return
    try {
      compileResult.value = await api.compileGraph(currentGraph.value.graph_id)
    } catch (e: any) {
      compileResult.value = {
        graph_id: currentGraph.value.graph_id,
        ok: false,
        topological_order: [],
        errors: [String(e.message || e)],
        warnings: [],
      }
    }
  }

  async function execute(datasetId: string, mode: 'sequential' | 'parallel' = 'sequential'): Promise<void> {
    if (!currentGraph.value) return
    executeResult.value = await api.executeGraph(currentGraph.value.graph_id, datasetId, mode)
  }

  async function refreshCache(graphId?: string): Promise<void> {
    cacheStats.value = await api.getCacheStats(graphId)
  }

  async function invalidate(nodeId?: string): Promise<void> {
    await api.invalidateCache(nodeId)
    if (currentGraph.value) await refreshCache(currentGraph.value.graph_id)
  }

  return {
    // state
    nodes,
    currentGraph,
    graphList,
    selectedNodeId,
    compileResult,
    executeResult,
    cacheStats,
    loading,
    error,
    // getters
    nodesByCategory,
    selectedManifest,
    selectedInstance,
    // actions
    fetchNodes,
    fetchGraphs,
    loadGraph,
    createGraph,
    addNode,
    removeNodeInstance,
    addEdge,
    compile,
    execute,
    refreshCache,
    invalidate,
  }
})
