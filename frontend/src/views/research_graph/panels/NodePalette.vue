<template>
  <div class="palette">
    <div class="palette-header">
      <span class="palette-glyph">▦</span>
      <span class="palette-title">NODE LIBRARY</span>
    </div>
    <div class="palette-search">
      <input
        v-model="keyword"
        class="palette-input"
        placeholder="search nodes..."
      />
    </div>

    <div class="palette-list">
      <div v-for="(list, cat) in filteredNodes" :key="cat" class="palette-group">
        <div class="palette-cat">
          <span class="palette-cat-glyph">{{ categoryGlyph(cat) }}</span>
          {{ cat }}
          <span class="palette-cat-count">{{ list.length }}</span>
        </div>
        <div
          v-for="n in list"
          :key="n.id"
          class="palette-item"
          draggable="true"
          @dragstart="emit('drag-start', n.id)"
          @click="emit('drag-start', n.id)"
        >
          <span class="palette-item-id">{{ n.id }}</span>
          <span class="palette-item-ver">v{{ n.version }}</span>
        </div>
      </div>
      <div v-if="!Object.keys(filteredNodes).length" class="palette-empty">
        No nodes found
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useResearchGraphStore } from '@/stores/researchGraph'

const store = useResearchGraphStore()
const emit = defineEmits<{ (e: 'drag-start', nodeType: string): void }>()

const keyword = ref('')

const filteredNodes = computed(() => {
  const groups = store.nodesByCategory
  const result: Record<string, any[]> = {}
  const kw = keyword.value.toLowerCase()
  for (const [cat, list] of Object.entries(groups)) {
    const filtered = kw
      ? list.filter((n) => n.id.toLowerCase().includes(kw) || cat.toLowerCase().includes(kw))
      : list
    if (filtered.length) result[cat] = filtered
  }
  return result
})

function categoryGlyph(cat: string): string {
  const map: Record<string, string> = {
    DATA: '◆',
    TRANSFORM: '⟳',
    INDICATOR: '∿',
    ALPHA: 'α',
    AGGREGATION: '∑',
    RANKING: '#',
    SELECTION: '▢',
    LABEL: '◎',
    CUSTOM: '✱',
  }
  return map[cat] || '•'
}
</script>

<style scoped>
.palette {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #0f141c;
}

.palette-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 14px 8px;
  border-bottom: 1px solid #1f2630;
}

.palette-glyph { color: #ff6b35; font-size: 14px; }

.palette-title {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 2px;
  color: #c9d1d9;
}

.palette-search {
  padding: 8px 12px;
  border-bottom: 1px solid #1f2630;
}

.palette-input {
  width: 100%;
  padding: 6px 10px;
  background: #0a0e14;
  border: 1px solid #1f2630;
  color: #c9d1d9;
  font-family: inherit;
  font-size: 12px;
  outline: none;
}

.palette-input:focus { border-color: #ff6b35; }

.palette-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.palette-group { margin-bottom: 8px; }

.palette-cat {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px 4px;
  font-size: 10px;
  letter-spacing: 1.5px;
  color: #6e7681;
  text-transform: uppercase;
}

.palette-cat-glyph { color: #ff6b35; }

.palette-cat-count {
  margin-left: auto;
  background: #161c26;
  padding: 1px 6px;
  border-radius: 8px;
  font-size: 9px;
}

.palette-item {
  display: flex;
  align-items: center;
  padding: 6px 14px 6px 32px;
  cursor: grab;
  font-size: 12px;
  color: #c9d1d9;
  border-left: 2px solid transparent;
  transition: all 0.1s;
}

.palette-item:hover {
  background: #161c26;
  border-left-color: #ff6b35;
  color: #fff;
}

.palette-item:active { cursor: grabbing; }

.palette-item-id { flex: 1; }

.palette-item-ver {
  font-size: 10px;
  color: #6e7681;
}

.palette-empty {
  padding: 24px;
  text-align: center;
  color: #6e7681;
  font-size: 12px;
}
</style>
