<template>
  <div class="console">
    <div class="console-toolbar">
      <button class="console-btn" @click="clear">
        <span class="console-btn-glyph">✕</span> Clear
      </button>
      <span class="console-meta">{{ logs.length }} lines</span>
    </div>
    <div class="console-body" ref="bodyRef">
      <div
        v-for="(log, i) in logs"
        :key="i"
        class="console-line"
        :class="`log-${log.level}`"
      >
        <span class="console-time">{{ log.time }}</span>
        <span class="console-level">{{ log.level.toUpperCase() }}</span>
        <span class="console-msg">{{ log.msg }}</span>
      </div>
      <div v-if="!logs.length" class="console-empty">No logs</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, onMounted } from 'vue'
import { useResearchGraphStore } from '@/stores/researchGraph'

const store = useResearchGraphStore()
const bodyRef = ref<HTMLElement>()
const logs = ref<{ time: string; level: string; msg: string }[]>([])

function push(level: string, msg: string) {
  const now = new Date()
  const time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`
  logs.value.push({ time, level, msg })
  nextTick(() => {
    if (bodyRef.value) bodyRef.value.scrollTop = bodyRef.value.scrollHeight
  })
}

function clear() {
  logs.value = []
}

// 监听状态变化推日志
watch(() => store.currentGraph, (g) => {
  if (g) push('info', `Graph loaded: ${g.name} (${g.graph_id.slice(0, 8)})`)
})

watch(() => store.compileResult, (r) => {
  if (!r) return
  if (r.ok) {
    push('ok', `Compile OK · ${r.topological_order.length} nodes`)
  } else {
    push('error', `Compile FAILED · ${r.errors.length} errors`)
    r.errors.forEach((e) => push('error', e))
  }
})

watch(() => store.executeResult, (r) => {
  if (!r) return
  push(r.status === 'OK' ? 'ok' : r.status === 'ERROR' ? 'error' : 'info',
    `Execute ${r.status} · ${r.duration_ms}ms · ${r.executed_nodes.length} executed / ${r.cached_nodes.length} cached`)
})

onMounted(() => {
  push('info', 'Research Graph Studio v3.0 ready')
  push('info', 'Drag nodes from left palette to build graph')
})
</script>

<style scoped>
.console {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.console-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.console-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  background: transparent;
  border: 1px solid #1f2630;
  color: #6e7681;
  font-family: inherit;
  font-size: 11px;
  cursor: pointer;
}

.console-btn:hover { color: #fff; border-color: #ff6b35; }
.console-btn-glyph { color: #ff6b35; }

.console-meta { margin-left: auto; font-size: 11px; color: #6e7681; }

.console-body {
  flex: 1;
  overflow-y: auto;
  background: #0a0e14;
  border: 1px solid #1f2630;
  padding: 8px;
  font-size: 11px;
  line-height: 1.6;
}

.console-line {
  display: flex;
  gap: 8px;
  padding: 1px 0;
}

.console-time { color: #6e7681; flex-shrink: 0; }

.console-level {
  width: 50px;
  flex-shrink: 0;
  font-weight: 700;
  letter-spacing: 1px;
}

.log-info .console-level { color: #569cd6; }
.log-ok .console-level { color: #3fb950; }
.log-warn .console-level { color: #ffb347; }
.log-error .console-level { color: #f85149; }

.log-error .console-msg { color: #f85149; }
.log-ok .console-msg { color: #3fb950; }
.log-warn .console-msg { color: #ffb347; }
.log-info .console-msg { color: #c9d1d9; }

.console-empty {
  color: #6e7681;
  padding: 16px;
  text-align: center;
}
</style>
