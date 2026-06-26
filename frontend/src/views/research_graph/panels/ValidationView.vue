<template>
  <div class="val-view">
    <div v-if="!store.compileResult" class="val-empty">
      <span class="val-empty-glyph">✓</span>
      No compile result. Click <strong>Compile</strong> to validate.
    </div>

    <div v-else class="val-body">
      <!-- 状态 -->
      <div class="val-status" :class="store.compileResult.ok ? 'is-ok' : 'is-error'">
        <span class="val-status-glyph">{{ store.compileResult.ok ? '✓' : '✕' }}</span>
        <span class="val-status-text">
          {{ store.compileResult.ok ? 'COMPILE OK' : 'COMPILE FAILED' }}
        </span>
        <span class="val-status-meta" v-if="store.compileResult.topological_order.length">
          · {{ store.compileResult.topological_order.length }} nodes in topo order
        </span>
      </div>

      <!-- 拓扑排序 -->
      <div class="val-section" v-if="store.compileResult.topological_order.length">
        <div class="val-section-title">
          <span class="val-glyph">▸</span> TOPOLOGICAL ORDER
        </div>
        <div class="val-topo">
          <template v-for="(nid, i) in store.compileResult.topological_order" :key="nid">
            <span class="val-topo-node" :class="`topo-${i % 3}`">{{ nid }}</span>
            <span v-if="i < store.compileResult.topological_order.length - 1" class="val-topo-arrow">→</span>
          </template>
        </div>
      </div>

      <!-- 错误 -->
      <div class="val-section" v-if="store.compileResult.errors.length">
        <div class="val-section-title val-section-error">
          <span class="val-glyph">✕</span> ERRORS ({{ store.compileResult.errors.length }})
        </div>
        <div class="val-error-list">
          <div v-for="(e, i) in store.compileResult.errors" :key="i" class="val-error-item">
            <span class="val-error-num">E{{ String(i + 1).padStart(2, '0') }}</span>
            <span class="val-error-msg">{{ e }}</span>
          </div>
        </div>
      </div>

      <!-- 警告 -->
      <div class="val-section" v-if="store.compileResult.warnings.length">
        <div class="val-section-title val-section-warn">
          <span class="val-glyph">!</span> WARNINGS ({{ store.compileResult.warnings.length }})
        </div>
        <div class="val-warn-list">
          <div v-for="(w, i) in store.compileResult.warnings" :key="i" class="val-warn-item">
            <span class="val-warn-num">W{{ String(i + 1).padStart(2, '0') }}</span>
            <span class="val-warn-msg">{{ w }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useResearchGraphStore } from '@/stores/researchGraph'

const store = useResearchGraphStore()
</script>

<style scoped>
.val-view { font-size: 12px; }

.val-empty {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #6e7681;
  padding: 8px 0;
}

.val-empty-glyph { color: #4ec9b0; font-size: 16px; }

.val-body { display: flex; flex-direction: column; gap: 16px; }

.val-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border: 1px solid;
}

.val-status.is-ok {
  background: rgba(63, 185, 80, 0.08);
  border-color: #3fb950;
  color: #3fb950;
}

.val-status.is-error {
  background: rgba(248, 81, 73, 0.08);
  border-color: #f85149;
  color: #f85149;
}

.val-status-glyph { font-size: 18px; font-weight: 700; }

.val-status-text { font-weight: 700; letter-spacing: 1.5px; }

.val-status-meta { color: #6e7681; font-size: 11px; }

.val-section-title {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.5px;
  color: #6e7681;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.val-section-error { color: #f85149; }
.val-section-warn { color: #ffb347; }

.val-glyph { color: #ff6b35; }
.val-section-error .val-glyph { color: #f85149; }
.val-section-warn .val-glyph { color: #ffb347; }

.val-topo {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  padding: 8px;
  background: #0a0e14;
  border: 1px solid #1f2630;
}

.val-topo-node {
  padding: 3px 8px;
  background: #161c26;
  border: 1px solid;
  color: #c9d1d9;
  font-size: 11px;
}

.topo-0 { border-color: #4ec9b0; color: #4ec9b0; }
.topo-1 { border-color: #ff6b35; color: #ff6b35; }
.topo-2 { border-color: #569cd6; color: #569cd6; }

.val-topo-arrow { color: #6e7681; }

.val-error-list,
.val-warn-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.val-error-item,
.val-warn-item {
  display: flex;
  gap: 8px;
  padding: 6px 8px;
  background: #0a0e14;
}

.val-error-item { border-left: 2px solid #f85149; }
.val-warn-item { border-left: 2px solid #ffb347; }

.val-error-num,
.val-warn-num {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1px;
  flex-shrink: 0;
}

.val-error-num { color: #f85149; }
.val-warn-num { color: #ffb347; }

.val-error-msg,
.val-warn-msg {
  color: #c9d1d9;
  font-size: 11px;
  word-break: break-all;
}
</style>
