<template>
  <div class="inspector">
    <div class="insp-header">
      <span class="insp-glyph">◉</span>
      <span class="insp-title">INSPECTOR</span>
    </div>

    <div v-if="!store.selectedInstance" class="insp-empty">
      <div class="insp-empty-glyph">◇</div>
      <div class="insp-empty-text">Select a node to inspect</div>
    </div>

    <div v-else class="insp-body">
      <!-- 节点基本信息 -->
      <section class="insp-section">
        <div class="insp-section-title">Node Instance</div>
        <div class="insp-row">
          <span class="insp-key">node_id</span>
          <span class="insp-val">{{ store.selectedInstance.node_id }}</span>
        </div>
        <div class="insp-row">
          <span class="insp-key">node_type</span>
          <span class="insp-val insp-val-accent">{{ store.selectedInstance.node_type }}</span>
        </div>
        <div class="insp-row" v-if="store.selectedInstance.version">
          <span class="insp-key">version</span>
          <span class="insp-val">v{{ store.selectedInstance.version }}</span>
        </div>
      </section>

      <!-- Manifest 信息 -->
      <section class="insp-section" v-if="store.selectedManifest">
        <div class="insp-section-title">Manifest</div>
        <div class="insp-row">
          <span class="insp-key">category</span>
          <span class="insp-val insp-tag" :class="`cat-${store.selectedManifest.category.toLowerCase()}`">
            {{ store.selectedManifest.category }}
          </span>
        </div>
        <div class="insp-row" v-if="store.selectedManifest.metadata.description">
          <span class="insp-key">desc</span>
          <span class="insp-val insp-val-desc">{{ store.selectedManifest.metadata.description }}</span>
        </div>

        <!-- Inputs -->
        <div class="insp-ports" v-if="store.selectedManifest.inputs.length">
          <div class="insp-ports-title">Inputs ({{ store.selectedManifest.inputs.length }})</div>
          <div
            v-for="p in store.selectedManifest.inputs"
            :key="p.name"
            class="insp-port"
          >
            <span class="insp-port-glyph">▸</span>
            <span class="insp-port-name">{{ p.name }}</span>
            <span class="insp-port-type">{{ p.port_type }}</span>
          </div>
        </div>

        <!-- Outputs -->
        <div class="insp-ports" v-if="store.selectedManifest.outputs.length">
          <div class="insp-ports-title">Outputs ({{ store.selectedManifest.outputs.length }})</div>
          <div
            v-for="p in store.selectedManifest.outputs"
            :key="p.name"
            class="insp-port insp-port-out"
          >
            <span class="insp-port-glyph">◂</span>
            <span class="insp-port-name">{{ p.name }}</span>
            <span class="insp-port-type">{{ p.port_type }}</span>
          </div>
        </div>
      </section>

      <!-- Parameters -->
      <section class="insp-section" v-if="paramKeys.length">
        <div class="insp-section-title">Parameters</div>
        <div class="insp-row" v-for="k in paramKeys" :key="k">
          <span class="insp-key">{{ k }}</span>
          <input
            :value="store.selectedInstance.params?.[k]"
            @input="updateParam(k, ($event.target as HTMLInputElement).value)"
            class="insp-param-input"
          />
        </div>
      </section>

      <!-- Actions -->
      <section class="insp-section">
        <button class="insp-remove-btn" @click="removeNode">
          <span>✕</span> Remove Node
        </button>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useResearchGraphStore } from '@/stores/researchGraph'

const store = useResearchGraphStore()

const paramKeys = computed<string[]>(() => {
  return Object.keys(store.selectedInstance?.params || {})
})

function updateParam(key: string, value: string) {
  if (!store.currentGraph || !store.selectedInstance) return
  // 简化：仅更新本地，未提交后端
  const inst = store.currentGraph.nodes.find((n) => n.node_id === store.selectedNodeId)
  if (inst) {
    if (!inst.params) inst.params = {}
    inst.params[key] = value
  }
}

async function removeNode() {
  if (!store.selectedNodeId) return
  await store.removeNodeInstance(store.selectedNodeId)
}
</script>

<style scoped>
.inspector {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #0f141c;
}

.insp-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px;
  border-bottom: 1px solid #1f2630;
  flex-shrink: 0;
}

.insp-glyph { color: #ff6b35; font-size: 14px; }

.insp-title {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 2px;
  color: #c9d1d9;
}

.insp-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #6e7681;
}

.insp-empty-glyph { font-size: 32px; color: #1f2630; margin-bottom: 8px; }
.insp-empty-text { font-size: 11px; }

.insp-body {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.insp-section {
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #1f2630;
}

.insp-section:last-child { border-bottom: none; }

.insp-section-title {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.5px;
  color: #6e7681;
  text-transform: uppercase;
  margin-bottom: 8px;
}

.insp-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 4px 0;
  font-size: 12px;
}

.insp-key {
  min-width: 70px;
  color: #6e7681;
  flex-shrink: 0;
}

.insp-val {
  color: #c9d1d9;
  word-break: break-all;
  flex: 1;
}

.insp-val-accent { color: #ff6b35; font-weight: 600; }
.insp-val-desc { color: #6e7681; font-style: italic; }

.insp-tag {
  display: inline-block;
  padding: 2px 8px;
  background: #161c26;
  font-size: 10px;
  letter-spacing: 1px;
  border-radius: 0;
}

.insp-tag.cat-data { color: #4ec9b0; }
.insp-tag.cat-alpha { color: #ff6b35; }
.insp-tag.cat-label { color: #ffb347; }
.insp-tag.cat-indicator { color: #569cd6; }
.insp-tag.cat-transform { color: #c586c0; }

.insp-ports { margin-top: 10px; }

.insp-ports-title {
  font-size: 10px;
  color: #6e7681;
  letter-spacing: 1px;
  margin-bottom: 6px;
}

.insp-port {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  font-size: 11px;
  background: #0a0e14;
  border-left: 2px solid #ff6b35;
  margin-bottom: 2px;
}

.insp-port-out { border-left-color: #4ec9b0; }

.insp-port-glyph { color: #ff6b35; }
.insp-port-out .insp-port-glyph { color: #4ec9b0; }

.insp-port-name { flex: 1; color: #c9d1d9; }

.insp-port-type {
  font-size: 9px;
  color: #6e7681;
  letter-spacing: 1px;
}

.insp-param-input {
  flex: 1;
  padding: 3px 6px;
  background: #0a0e14;
  border: 1px solid #1f2630;
  color: #fff;
  font-family: inherit;
  font-size: 11px;
  outline: none;
}

.insp-param-input:focus { border-color: #ff6b35; }

.insp-remove-btn {
  width: 100%;
  padding: 8px;
  background: transparent;
  border: 1px solid #f85149;
  color: #f85149;
  font-family: inherit;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.15s;
}

.insp-remove-btn:hover {
  background: #f85149;
  color: #000;
}
</style>
