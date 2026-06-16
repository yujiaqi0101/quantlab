<template>
  <div class="tree-node" :class="{ 'is-current': node.id === currentId }">
    <div class="node-row" @click="$emit('navigate', node.id)">
      <span class="node-dot" :class="dotClass"></span>
      <span class="node-name">{{ node.name || node.id }}</span>
      <span class="node-strategy">{{ node.strategy }}</span>
      <el-tag v-if="node.status && node.status !== 'normal'" :type="statusType" effect="dark" size="small">{{ node.status }}</el-tag>
    </div>
    <div v-if="node.children?.length" class="node-children">
      <LineageTreeNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :current-id="currentId"
        @navigate="$emit('navigate', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { LineageNode } from '@/api/experiment'

const props = defineProps<{
  node: LineageNode
  currentId: string
}>()

defineEmits<{
  navigate: [id: string]
}>()

const dotClass = computed(() => {
  if (props.node.id === props.currentId) return 'current'
  if (props.node.status === 'production') return 'production'
  if (props.node.status === 'candidate') return 'candidate'
  return ''
})

const statusType = computed(() => {
  if (props.node.status === 'candidate') return 'warning'
  if (props.node.status === 'production') return 'success'
  if (props.node.status === 'paper_trading') return 'info'
  return 'info'
})
</script>

<style scoped>
.tree-node {
  padding-left: 20px;
  position: relative;
}

.tree-node::before {
  content: '';
  position: absolute;
  left: 6px;
  top: 0;
  bottom: 0;
  width: 1px;
  background: #1b2332;
}

.tree-node > .node-children > .tree-node::after {
  content: '';
  position: absolute;
  left: -14px;
  top: 14px;
  width: 12px;
  height: 1px;
  background: #1b2332;
}

.node-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.node-row:hover {
  background: #161b22;
}

.is-current > .node-row {
  background: rgba(88, 166, 255, 0.08);
  border: 1px solid rgba(88, 166, 255, 0.2);
}

.node-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #484f58;
  flex-shrink: 0;
}

.node-dot.current {
  background: #58a6ff;
  box-shadow: 0 0 6px rgba(88, 166, 255, 0.4);
}

.node-dot.candidate {
  background: #d29922;
}

.node-dot.production {
  background: #3fb950;
}

.node-name {
  font-size: 13px;
  font-weight: 500;
  color: #e6edf3;
}

.is-current > .node-row .node-name {
  color: #58a6ff;
}

.node-strategy {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 11px;
  color: #8b949e;
}

.node-children {
  margin-top: 2px;
}
</style>
