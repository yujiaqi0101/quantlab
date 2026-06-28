<template>
  <div class="rgs">
    <!-- 顶部工具栏 -->
    <header class="rgs-toolbar">
      <div class="rgs-brand">
        <span class="rgs-logo">R/G</span>
        <div class="rgs-title-block">
          <div class="rgs-title">RESEARCH GRAPH STUDIO</div>
          <div class="rgs-subtitle">Quant Research Compiler · v3.0</div>
        </div>
      </div>

      <div class="rgs-graph-meta" v-if="store.currentGraph">
        <span class="rgs-glyph">◆</span>
        <input
          v-model="store.currentGraph.name"
          class="rgs-name-input"
          @change="renameGraph"
        />
        <span class="rgs-gid">{{ store.currentGraph.graph_id.slice(0, 8) }}</span>
      </div>

      <div class="rgs-toolbar-actions">
        <button class="rgs-btn" @click="showNewGraph = true">
          <span class="rgs-btn-glyph">+</span> New Graph
        </button>
        <button class="rgs-btn rgs-btn-ghost" @click="loadGraphPicker">
          <span class="rgs-btn-glyph">↻</span> Open
        </button>
        <div class="rgs-sep" />
        <button
          class="rgs-btn rgs-btn-action"
          :class="{ 'is-busy': compiling }"
          :disabled="!store.currentGraph || compiling"
          @click="doCompile"
        >
          <span class="rgs-btn-glyph">⚙</span> Compile
        </button>
        <button
          class="rgs-btn rgs-btn-run"
          :class="{ 'is-busy': executing }"
          :disabled="!store.currentGraph || executing"
          @click="doExecute"
        >
          <span class="rgs-btn-glyph">▶</span> Execute
        </button>
      </div>
    </header>

    <!-- 主体三栏 -->
    <div class="rgs-body">
      <!-- 左：Node Palette -->
      <aside class="rgs-pane rgs-pane-left">
        <NodePalette @drag-start="onDragStart" />
      </aside>

      <!-- 中：Graph Canvas -->
      <section class="rgs-pane rgs-pane-center">
        <GraphCanvas
          :drag-payload="dragPayload"
          @node-select="onNodeSelect"
          @edge-create="onEdgeCreate"
          @node-remove="onNodeRemove"
        />
      </section>

      <!-- 右：Inspector -->
      <aside class="rgs-pane rgs-pane-right">
        <Inspector />
      </aside>
    </div>

    <!-- 底：Tabs -->
    <footer class="rgs-bottom">
      <div class="rgs-tab-strip">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="rgs-tab"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >
          <span class="rgs-tab-glyph">{{ tab.glyph }}</span>
          {{ tab.label }}
          <span class="rgs-tab-badge" v-if="tab.badge">{{ tab.badge }}</span>
        </button>
      </div>
      <div class="rgs-tab-body">
        <ExecutionView v-if="activeTab === 'execution'" />
        <CacheView v-else-if="activeTab === 'cache'" />
        <ValidationView v-else-if="activeTab === 'validation'" />
        <ConsolePanel v-else-if="activeTab === 'console'" />
      </div>
    </footer>

    <!-- 新建 Graph 弹层 -->
    <div v-if="showNewGraph" class="rgs-modal" @click.self="showNewGraph = false">
      <div class="rgs-modal-body">
        <div class="rgs-modal-title">New Research Graph</div>
        <input
          v-model="newGraphName"
          class="rgs-input"
          placeholder="graph name (e.g. alpha101_returns)"
          autofocus
        />
        <textarea
          v-model="newGraphDesc"
          class="rgs-input rgs-textarea"
          placeholder="description (optional)"
          rows="2"
        />
        <div class="rgs-modal-actions">
          <button class="rgs-btn rgs-btn-ghost" @click="showNewGraph = false">Cancel</button>
          <button class="rgs-btn rgs-btn-run" @click="doCreateGraph">Create</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useResearchGraphStore } from '@/stores/researchGraph'
import NodePalette from './panels/NodePalette.vue'
import GraphCanvas from './panels/GraphCanvas.vue'
import Inspector from './panels/Inspector.vue'
import ExecutionView from './panels/ExecutionView.vue'
import CacheView from './panels/CacheView.vue'
import ValidationView from './panels/ValidationView.vue'
import ConsolePanel from './panels/ConsolePanel.vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const store = useResearchGraphStore()

// ---- 状态 ----
const showNewGraph = ref(false)
const newGraphName = ref('')
const newGraphDesc = ref('')
const compiling = ref(false)
const executing = ref(false)
const dragPayload = ref('')
const activeTab = ref<'execution' | 'cache' | 'validation' | 'console'>('execution')

const tabs = computed(() => [
  { id: 'execution' as const, glyph: '▶', label: 'Execution', badge: '' },
  {
    id: 'cache' as const,
    glyph: '▤',
    label: 'Cache',
    badge: store.cacheStats ? `${store.cacheStats.total_entries}` : '',
  },
  {
    id: 'validation' as const,
    glyph: '✓',
    label: 'Validation',
    badge: store.compileResult ? (store.compileResult.ok ? 'OK' : `${store.compileResult.errors.length}e`) : '',
  },
  { id: 'console' as const, glyph: '⟩_', label: 'Console', badge: '' },
])

// ---- 生命周期 ----
onMounted(async () => {
  try {
    await store.fetchNodes()
  } catch (e: any) {
    ElMessage.error(`Failed to load nodes: ${e.message}`)
  }
  try {
    await store.fetchGraphs()
  } catch (e: any) {
    ElMessage.error(`Failed to load graphs: ${e.message}`)
  }
  await store.refreshCache()
})

// ---- 交互 ----
function onDragStart(nodeType: string) {
  dragPayload.value = nodeType
}

function onNodeSelect(id: string) {
  store.selectedNodeId = id
}

async function onEdgeCreate(edge: any) {
  try {
    await store.addEdge(edge)
  } catch (e: any) {
    ElMessage.error(`Add edge failed: ${e.message}`)
  }
}

async function onNodeRemove(id: string) {
  try {
    await store.removeNodeInstance(id)
  } catch (e: any) {
    ElMessage.error(`Remove node failed: ${e.message}`)
  }
}

async function doCompile() {
  compiling.value = true
  try {
    await store.compile()
    if (store.compileResult?.ok) {
      activeTab.value = 'validation'
      ElMessage.success('Compile OK')
    } else {
      activeTab.value = 'validation'
      ElMessage.error(`Compile failed: ${store.compileResult?.errors.length} errors`)
    }
  } finally {
    compiling.value = false
  }
}

async function doExecute() {
  executing.value = true
  activeTab.value = 'execution'
  try {
    // 默认 dataset，生产应让用户选
    await store.execute('default', 'sequential')
    await store.refreshCache(store.currentGraph?.graph_id)
    ElMessage.success('Execute done')
  } catch (e: any) {
    ElMessage.error(`Execute failed: ${e.message}`)
  } finally {
    executing.value = false
  }
}

async function loadGraphPicker() {
  try {
    await store.fetchGraphs()
  } catch (e: any) {
    ElMessage.error(`Failed to fetch graphs: ${e.message}`)
    return
  }
  if (!store.graphList.length) {
    ElMessage.info('No saved graphs yet. Create one first.')
    return
  }
  const options = store.graphList.map((g, i) => `${i + 1}. ${g.name} (${g.graph_id.slice(0, 8)})`).join('\n')
  try {
    const { value } = await ElMessageBox.prompt(
      `Select a graph to open:\n\n${options}\n\nEnter graph ID or number:`,
      'Open Graph',
      {
        confirmButtonText: 'Open',
        cancelButtonText: 'Cancel',
        inputPlaceholder: 'e.g. graph-abc123 or 1',
        customClass: 'rgs-messagebox',
      },
    )
    const choice = (value || '').trim()
    if (!choice) return
    let graphId = choice
    const numMatch = choice.match(/^(\d+)$/)
    if (numMatch) {
      const idx = parseInt(numMatch[1], 10) - 1
      if (idx >= 0 && idx < store.graphList.length) {
        graphId = store.graphList[idx].graph_id
      }
    }
    await store.loadGraph(graphId)
    if (store.currentGraph) {
      ElMessage.success(`Loaded: ${store.currentGraph.name}`)
    }
  } catch {
    // 用户取消
  }
}

async function doCreateGraph() {
  if (!newGraphName.value.trim()) {
    ElMessage.warning('Name required')
    return
  }
  try {
    await store.createGraph(newGraphName.value.trim(), newGraphDesc.value.trim())
    showNewGraph.value = false
    newGraphName.value = ''
    newGraphDesc.value = ''
    ElMessage.success('Graph created')
  } catch (e: any) {
    ElMessage.error(`Create failed: ${e.message}`)
  }
}

function renameGraph() {
  // TODO: 调用后端 PATCH
}
</script>

<style scoped>
.rgs {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #0a0e14;
  color: #c9d1d9;
  font-family: 'JetBrains Mono', 'Fira Code', 'SF Mono', Consolas, monospace;
  font-size: 13px;
  --rgs-bg: #0a0e14;
  --rgs-bg-2: #0f141c;
  --rgs-bg-3: #161c26;
  --rgs-border: #1f2630;
  --rgs-accent: #ff6b35;
  --rgs-accent-2: #4ec9b0;
  --rgs-warn: #ffb347;
  --rgs-error: #f85149;
  --rgs-ok: #3fb950;
}

/* ============ Toolbar ============ */
.rgs-toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  height: 56px;
  padding: 0 16px;
  background: linear-gradient(180deg, #0f141c 0%, #0a0e14 100%);
  border-bottom: 1px solid var(--rgs-border);
  flex-shrink: 0;
}

.rgs-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}

.rgs-logo {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: var(--rgs-accent);
  color: #000;
  font-weight: 900;
  font-size: 11px;
  letter-spacing: 0.5px;
  clip-path: polygon(0 0, 100% 0, 100% 70%, 70% 100%, 0 100%);
}

.rgs-title-block { line-height: 1.1; }

.rgs-title {
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 2px;
  color: #fff;
}

.rgs-subtitle {
  font-size: 10px;
  color: #6e7681;
  letter-spacing: 1px;
}

.rgs-graph-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: var(--rgs-bg-3);
  border: 1px solid var(--rgs-border);
  border-radius: 2px;
}

.rgs-glyph { color: var(--rgs-accent); font-size: 10px; }

.rgs-name-input {
  background: transparent;
  border: none;
  color: #fff;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  outline: none;
  width: 200px;
}

.rgs-gid {
  font-size: 10px;
  color: #6e7681;
  letter-spacing: 1px;
}

.rgs-toolbar-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 6px;
}

.rgs-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--rgs-bg-3);
  border: 1px solid var(--rgs-border);
  color: #c9d1d9;
  font-family: inherit;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}

.rgs-btn:hover {
  background: #1f2630;
  border-color: #2d3440;
  color: #fff;
}

.rgs-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.rgs-btn-glyph { color: var(--rgs-accent); font-weight: 700; }

.rgs-btn-ghost { background: transparent; }

.rgs-btn-action {
  background: #1a2332;
  border-color: #2d4a6b;
}
.rgs-btn-action:hover { background: #233247; border-color: #3d5a80; }

.rgs-btn-run {
  background: var(--rgs-accent);
  border-color: var(--rgs-accent);
  color: #000;
  font-weight: 700;
}
.rgs-btn-run:hover { background: #ff7d4d; color: #000; }
.rgs-btn-run .rgs-btn-glyph { color: #000; }

.rgs-btn.is-busy {
  pointer-events: none;
  opacity: 0.7;
}
.rgs-btn.is-busy::after {
  content: '⟳';
  display: inline-block;
  animation: rgs-spin 0.8s linear infinite;
  margin-left: 4px;
}
@keyframes rgs-spin { to { transform: rotate(360deg); } }

.rgs-sep { width: 1px; height: 22px; background: var(--rgs-border); margin: 0 4px; }

/* ============ Body 三栏 ============ */
.rgs-body {
  flex: 1;
  display: flex;
  min-height: 0;
}

.rgs-pane {
  display: flex;
  flex-direction: column;
  background: var(--rgs-bg);
  overflow: hidden;
}

.rgs-pane-left {
  width: 240px;
  border-right: 1px solid var(--rgs-border);
  background: var(--rgs-bg-2);
}

.rgs-pane-center {
  flex: 1;
  min-width: 0;
}

.rgs-pane-right {
  width: 320px;
  border-left: 1px solid var(--rgs-border);
  background: var(--rgs-bg-2);
}

/* ============ Bottom Tabs ============ */
.rgs-bottom {
  height: 220px;
  border-top: 1px solid var(--rgs-border);
  background: var(--rgs-bg-2);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.rgs-tab-strip {
  display: flex;
  border-bottom: 1px solid var(--rgs-border);
  background: var(--rgs-bg);
  flex-shrink: 0;
}

.rgs-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: transparent;
  border: none;
  border-right: 1px solid var(--rgs-border);
  color: #6e7681;
  font-family: inherit;
  font-size: 11px;
  letter-spacing: 1px;
  text-transform: uppercase;
  cursor: pointer;
  transition: all 0.15s;
}

.rgs-tab:hover { color: #c9d1d9; }

.rgs-tab.active {
  color: #fff;
  background: var(--rgs-bg-2);
  border-bottom: 2px solid var(--rgs-accent);
}

.rgs-tab-glyph { color: var(--rgs-accent); }

.rgs-tab-badge {
  padding: 1px 6px;
  background: var(--rgs-bg-3);
  border-radius: 8px;
  font-size: 10px;
  color: #6e7681;
}

.rgs-tab.active .rgs-tab-badge {
  background: var(--rgs-accent);
  color: #000;
}

.rgs-tab-body {
  flex: 1;
  overflow: auto;
  padding: 12px;
}

/* ============ Modal ============ */
.rgs-modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.rgs-modal-body {
  background: var(--rgs-bg-2);
  border: 1px solid var(--rgs-border);
  padding: 24px;
  min-width: 400px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6);
}

.rgs-modal-title {
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 2px;
  margin-bottom: 16px;
  color: #fff;
}

.rgs-input {
  width: 100%;
  padding: 8px 10px;
  background: var(--rgs-bg);
  border: 1px solid var(--rgs-border);
  color: #fff;
  font-family: inherit;
  font-size: 13px;
  outline: none;
  margin-bottom: 12px;
}

.rgs-input:focus { border-color: var(--rgs-accent); }

.rgs-textarea {
  resize: vertical;
  min-height: 50px;
}

.rgs-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}
</style>
