<template>
  <div class="exec-view">
    <div v-if="!store.executeResult" class="exec-empty">
      <span class="exec-empty-glyph">▶</span>
      No execution yet. Click <strong>Execute</strong> to run the graph.
    </div>

    <div v-else class="exec-body">
      <!-- 状态摘要 -->
      <div class="exec-summary">
        <div class="exec-summary-item">
          <span class="exec-label">STATUS</span>
          <span class="exec-val" :class="`exec-status-${store.executeResult.status.toLowerCase()}`">
            {{ store.executeResult.status }}
          </span>
        </div>
        <div class="exec-summary-item">
          <span class="exec-label">RUN ID</span>
          <span class="exec-val exec-mono">{{ store.executeResult.run_id.slice(0, 12) }}</span>
        </div>
        <div class="exec-summary-item">
          <span class="exec-label">DURATION</span>
          <span class="exec-val exec-mono">{{ store.executeResult.duration_ms }} ms</span>
        </div>
        <div class="exec-summary-item">
          <span class="exec-label">EXECUTED</span>
          <span class="exec-val exec-mono">{{ store.executeResult.executed_nodes.length }} nodes</span>
        </div>
        <div class="exec-summary-item">
          <span class="exec-label">CACHED</span>
          <span class="exec-val exec-mono exec-cached">{{ store.executeResult.cached_nodes.length }} nodes</span>
        </div>
      </div>

      <!-- 执行顺序 -->
      <div class="exec-section">
        <div class="exec-section-title">
          <span class="exec-glyph">▸</span> EXECUTION ORDER (TOPOLOGICAL)
        </div>
        <div class="exec-flow">
          <template v-for="(nid, i) in store.executeResult.executed_nodes" :key="nid">
            <span class="exec-flow-node" :class="{ cached: store.executeResult.cached_nodes.includes(nid) }">
              {{ nid }}
            </span>
            <span v-if="i < store.executeResult.executed_nodes.length - 1" class="exec-flow-arrow">→</span>
          </template>
        </div>
      </div>

      <!-- 输出 -->
      <div class="exec-section" v-if="outputKeys.length">
        <div class="exec-section-title">
          <span class="exec-glyph">▣</span> OUTPUTS
        </div>
        <div class="exec-output-grid">
          <div v-for="k in outputKeys" :key="k" class="exec-output-item">
            <div class="exec-output-key">{{ k }}</div>
            <div class="exec-output-val">{{ formatOutput(store.executeResult!.outputs[k]) }}</div>
          </div>
        </div>
      </div>

      <!-- 错误 -->
      <div class="exec-section exec-errors" v-if="errorKeys.length">
        <div class="exec-section-title exec-section-error">
          <span class="exec-glyph">✕</span> ERRORS ({{ errorKeys.length }})
        </div>
        <div v-for="k in errorKeys" :key="k" class="exec-error-item">
          <span class="exec-error-node">{{ k }}</span>
          <span class="exec-error-msg">{{ store.executeResult!.errors[k] }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useResearchGraphStore } from '@/stores/researchGraph'

const store = useResearchGraphStore()

const outputKeys = computed(() => Object.keys(store.executeResult?.outputs || {}))
const errorKeys = computed(() => Object.keys(store.executeResult?.errors || {}))

function formatOutput(v: any): string {
  if (v === null || v === undefined) return 'null'
  if (typeof v === 'object') {
    return JSON.stringify(v).slice(0, 200)
  }
  return String(v)
}
</script>

<style scoped>
.exec-view {
  font-size: 12px;
  height: 100%;
  overflow-y: auto;
}

.exec-empty {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #6e7681;
  padding: 8px 0;
}

.exec-empty-glyph { color: #ff6b35; font-size: 16px; }

.exec-body { display: flex; flex-direction: column; gap: 16px; }

.exec-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 8px;
}

.exec-summary-item {
  padding: 8px 12px;
  background: #0a0e14;
  border: 1px solid #1f2630;
}

.exec-label {
  display: block;
  font-size: 9px;
  letter-spacing: 1.5px;
  color: #6e7681;
  margin-bottom: 4px;
}

.exec-val {
  font-size: 13px;
  color: #c9d1d9;
  font-weight: 600;
}

.exec-mono { font-family: inherit; }

.exec-cached { color: #4ec9b0; }

.exec-status-ok { color: #3fb950; }
.exec-status-error { color: #f85149; }
.exec-status-running { color: #ffb347; }
.exec-status-pending { color: #6e7681; }

.exec-section-title {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.5px;
  color: #6e7681;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.exec-section-error { color: #f85149; }

.exec-glyph { color: #ff6b35; }

.exec-section-error .exec-glyph { color: #f85149; }

.exec-flow {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  padding: 8px;
  background: #0a0e14;
  border: 1px solid #1f2630;
}

.exec-flow-node {
  padding: 3px 8px;
  background: #161c26;
  border: 1px solid #ff6b35;
  color: #fff;
  font-size: 11px;
}

.exec-flow-node.cached {
  border-color: #4ec9b0;
  color: #4ec9b0;
}

.exec-flow-arrow { color: #6e7681; font-size: 11px; }

.exec-output-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 6px;
}

.exec-output-item {
  padding: 8px;
  background: #0a0e14;
  border-left: 2px solid #4ec9b0;
}

.exec-output-key {
  font-size: 11px;
  color: #4ec9b0;
  margin-bottom: 4px;
}

.exec-output-val {
  font-size: 11px;
  color: #c9d1d9;
  word-break: break-all;
}

.exec-error-item {
  padding: 8px;
  background: rgba(248, 81, 73, 0.08);
  border-left: 2px solid #f85149;
  margin-bottom: 4px;
}

.exec-error-node {
  display: block;
  color: #f85149;
  font-size: 11px;
  font-weight: 600;
  margin-bottom: 2px;
}

.exec-error-msg {
  font-size: 11px;
  color: #c9d1d9;
  word-break: break-all;
}
</style>
