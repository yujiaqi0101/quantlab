<template>
  <div class="canvas-wrapper" @drop="onDrop" @dragover.prevent>
    <div class="canvas-toolbar">
      <div class="canvas-toolbar-left">
        <span class="canvas-glyph">⟀</span>
        <span class="canvas-title">GRAPH CANVAS</span>
        <span class="canvas-meta" v-if="store.currentGraph">
          {{ store.currentGraph.nodes.length }} nodes · {{ store.currentGraph.edges.length }} edges
        </span>
      </div>
      <div class="canvas-toolbar-right">
        <button class="canvas-tool-btn" @click="autoLayout" title="Auto Layout">
          <span>⊞</span> Layout
        </button>
        <button class="canvas-tool-btn" @click="fitView" title="Fit View">
          <span>⛶</span> Fit
        </button>
      </div>
    </div>

    <div class="canvas-area" v-if="store.currentGraph">
      <VueFlow
        v-model:nodes="flowNodes"
        v-model:edges="flowEdges"
        :default-viewport="{ x: 0, y: 0, zoom: 1 }"
        :min-zoom="0.2"
        :max-zoom="2.5"
        fit-view-on-init
        @connect="onConnect"
        @node-click="onNodeClick"
      >
        <Background pattern-color="#1f2630" :gap="20" />
        <Controls />
        <MiniMap pannable zoomable :node-color="miniMapColor" />
      </VueFlow>
    </div>

    <div v-else class="canvas-empty">
      <div class="canvas-empty-glyph">◇</div>
      <div class="canvas-empty-title">No Graph Loaded</div>
      <div class="canvas-empty-desc">
        Create or open a graph to start building.<br />
        Drag nodes from the left palette.
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { VueFlow, type Node, type Edge, type Connection } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import { useResearchGraphStore } from '@/stores/researchGraph'

const props = defineProps<{ dragPayload?: string }>()
const emit = defineEmits<{
  (e: 'node-select', id: string): void
  (e: 'edge-create', edge: any): void
  (e: 'node-remove', id: string): void
}>()

const store = useResearchGraphStore()

const flowNodes = ref<Node[]>([])
const flowEdges = ref<Edge[]>([])

// ---- sync graph -> vue-flow ----
watch(
  () => store.currentGraph,
  (g) => {
    if (!g) {
      flowNodes.value = []
      flowEdges.value = []
      return
    }
    flowNodes.value = g.nodes.map((n, i) => ({
      id: n.node_id,
      type: 'default',
      position: autoPosition(i, g.nodes.length),
      data: { label: `${n.node_type}\n(${n.node_id})`, nodeType: n.node_type },
      class: `rgs-node rgs-node-${(store.nodes.find((m) => m.id === n.node_type)?.category || 'CUSTOM').toLowerCase()}`,
    }))
    flowEdges.value = g.edges.map((e, i) => ({
      id: `e${i}_${e.src_node}_${e.dst_node}`,
      source: e.src_node,
      sourceHandle: e.src_port,
      target: e.dst_node,
      targetHandle: e.dst_port,
      animated: true,
      style: { stroke: '#ff6b35', strokeWidth: 2 },
    }))
  },
  { immediate: true, deep: true },
)

// ---- interaction ----
function onDrop(e: DragEvent) {
  if (!store.currentGraph) return
  const nodeType = props.dragPayload || e.dataTransfer?.getData('text/plain')
  if (!nodeType) return
  store.addNode(nodeType)
}

function onConnect(conn: Connection) {
  emit('edge-create', {
    src_node: conn.source,
    src_port: conn.sourceHandle || 'out',
    dst_node: conn.target,
    dst_port: conn.targetHandle || 'in',
  })
}

function onNodeClick(evt: any) {
  const id = evt.node?.id || ''
  emit('node-select', id)
}

// ---- layout ----
function autoPosition(i: number, _total?: number) {
  // 简易分层布局：按 index 分行
  const perRow = 4
  const row = Math.floor(i / perRow)
  const col = i % perRow
  return { x: 100 + col * 220, y: 80 + row * 140 }
}

function autoLayout() {
  // 简化：重新生成位置
  if (!flowNodes.value.length) return
  const newNodes: Node[] = []
  flowNodes.value.forEach((n, i) => {
    const pos = autoPosition(i, flowNodes.value.length)
    newNodes.push({
      id: n.id,
      type: n.type,
      position: { x: pos.x, y: pos.y },
      data: n.data,
      class: n.class,
    })
  })
  flowNodes.value = newNodes
}

function fitView() {
  // VueFlow 内部 fitView，通过 key 触发
  // 简化：重新设置位置触发视图刷新
  autoLayout()
}

function miniMapColor(node: Node) {
  const cls = node.class
  const classStr = typeof cls === 'string' ? cls : ''
  if (classStr.includes('data')) return '#4ec9b0'
  if (classStr.includes('alpha')) return '#ff6b35'
  if (classStr.includes('label')) return '#ffb347'
  if (classStr.includes('indicator')) return '#569cd6'
  return '#6e7681'
}
</script>

<style scoped>
.canvas-wrapper {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #0a0e14;
}

.canvas-toolbar {
  display: flex;
  align-items: center;
  height: 36px;
  padding: 0 12px;
  background: #0f141c;
  border-bottom: 1px solid #1f2630;
  flex-shrink: 0;
}

.canvas-toolbar-left,
.canvas-toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.canvas-toolbar-right { margin-left: auto; }

.canvas-glyph { color: #ff6b35; font-size: 14px; }

.canvas-title {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 2px;
  color: #c9d1d9;
}

.canvas-meta {
  font-size: 11px;
  color: #6e7681;
  padding: 2px 8px;
  background: #161c26;
  border-radius: 2px;
}

.canvas-tool-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: transparent;
  border: 1px solid #1f2630;
  color: #6e7681;
  font-family: inherit;
  font-size: 11px;
  cursor: pointer;
}

.canvas-tool-btn:hover {
  border-color: #ff6b35;
  color: #fff;
}

.canvas-area {
  flex: 1;
  min-height: 0;
  position: relative;
}

.canvas-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #6e7681;
}

.canvas-empty-glyph {
  font-size: 64px;
  color: #1f2630;
  margin-bottom: 16px;
}

.canvas-empty-title {
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 2px;
  color: #c9d1d9;
  margin-bottom: 8px;
}

.canvas-empty-desc {
  font-size: 12px;
  text-align: center;
  line-height: 1.8;
}
</style>

<style>
/* VueFlow 全局样式覆盖 */
@import '@vue-flow/core/dist/style.css';
@import '@vue-flow/core/dist/theme-default.css';
@import '@vue-flow/controls/dist/style.css';
@import '@vue-flow/minimap/dist/style.css';

.vue-flow__node {
  font-family: 'JetBrains Mono', Consolas, monospace !important;
}

.vue-flow__node-default {
  background: #0f141c !important;
  border: 1px solid #ff6b35 !important;
  color: #fff !important;
  padding: 8px 12px !important;
  font-size: 11px !important;
  border-radius: 0 !important;
}

.vue-flow__node.rgs-node-data { border-color: #4ec9b0 !important; }
.vue-flow__node.rgs-node-alpha { border-color: #ff6b35 !important; }
.vue-flow__node.rgs-node-label { border-color: #ffb347 !important; }
.vue-flow__node.rgs-node-indicator { border-color: #569cd6 !important; }
.vue-flow__node.rgs-node-transform { border-color: #c586c0 !important; }

.vue-flow__handle {
  background: #ff6b35 !important;
  border: 1px solid #000 !important;
  width: 8px !important;
  height: 8px !important;
}

.vue-flow__edge-path {
  stroke: #ff6b35 !important;
}

.vue-flow__controls {
  background: #0f141c !important;
  border: 1px solid #1f2630 !important;
}

.vue-flow__controls-button {
  background: #0f141c !important;
  border-bottom: 1px solid #1f2630 !important;
  color: #c9d1d9 !important;
  fill: #c9d1d9 !important;
}

.vue-flow__controls-button:hover {
  background: #161c26 !important;
}

.vue-flow__minimap {
  background: #0f141c !important;
  border: 1px solid #1f2630 !important;
}
</style>
