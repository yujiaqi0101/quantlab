<template>
  <div class="cache-view">
    <div class="cache-toolbar">
      <button class="cache-btn" @click="refresh">
        <span class="cache-btn-glyph">↻</span> Refresh
      </button>
      <button class="cache-btn cache-btn-warn" @click="invalidateAll">
        <span class="cache-btn-glyph">✕</span> Invalidate All
      </button>
      <span class="cache-meta" v-if="store.cacheStats">
        {{ store.cacheStats.total_entries }} entries · {{ formatBytes(store.cacheStats.total_size_bytes) }}
      </span>
    </div>

    <div v-if="!store.cacheStats" class="cache-empty">
      No cache data. Click Refresh.
    </div>

    <div v-else class="cache-body">
      <!-- 命中率 -->
      <div class="cache-hitrate">
        <div class="cache-hitrate-label">HIT RATE</div>
        <div class="cache-hitrate-val">
          {{ (store.cacheStats.hit_rate * 100).toFixed(1) }}<span class="cache-pct">%</span>
        </div>
        <div class="cache-hitrate-bar">
          <div
            class="cache-hitrate-fill"
            :style="{ width: `${store.cacheStats.hit_rate * 100}%` }"
          />
        </div>
      </div>

      <!-- 分级 -->
      <div class="cache-section">
        <div class="cache-section-title">
          <span class="cache-glyph">▤</span> BY LEVEL
        </div>
        <div class="cache-levels">
          <div
            v-for="(stat, level) in store.cacheStats.by_level"
            :key="level"
            class="cache-level"
          >
            <span class="cache-level-name">{{ level.toUpperCase() }}</span>
            <div class="cache-level-bar-wrap">
              <div
                class="cache-level-bar"
                :style="{ width: `${levelPercent(stat.count, store.cacheStats.total_entries)}%` }"
                :class="`bar-${level}`"
              />
            </div>
            <span class="cache-level-count">{{ stat.count }}</span>
            <span class="cache-level-size">{{ formatBytes(stat.size_bytes) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useResearchGraphStore } from '@/stores/researchGraph'

const store = useResearchGraphStore()

onMounted(() => {
  if (!store.cacheStats) store.refreshCache()
})

function refresh() {
  store.refreshCache(store.currentGraph?.graph_id)
}

async function invalidateAll() {
  await store.invalidate()
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`
  return `${(n / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

function levelPercent(count: number, total: number): number {
  if (!total) return 0
  return (count / total) * 100
}
</script>

<style scoped>
.cache-view { font-size: 12px; }

.cache-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.cache-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: transparent;
  border: 1px solid #1f2630;
  color: #c9d1d9;
  font-family: inherit;
  font-size: 11px;
  cursor: pointer;
}

.cache-btn:hover { border-color: #ff6b35; color: #fff; }

.cache-btn-warn { color: #f85149; border-color: #f85149; }
.cache-btn-warn:hover { background: #f85149; color: #000; }

.cache-btn-glyph { color: #ff6b35; }
.cache-btn-warn .cache-btn-glyph { color: #f85149; }

.cache-meta {
  margin-left: auto;
  font-size: 11px;
  color: #6e7681;
}

.cache-empty {
  color: #6e7681;
  padding: 8px 0;
}

.cache-body { display: flex; flex-direction: column; gap: 16px; }

.cache-hitrate {
  padding: 12px;
  background: #0a0e14;
  border: 1px solid #1f2630;
}

.cache-hitrate-label {
  font-size: 10px;
  letter-spacing: 1.5px;
  color: #6e7681;
  margin-bottom: 4px;
}

.cache-hitrate-val {
  font-size: 32px;
  font-weight: 700;
  color: #4ec9b0;
  line-height: 1;
  margin-bottom: 8px;
}

.cache-pct { font-size: 16px; color: #6e7681; }

.cache-hitrate-bar {
  height: 4px;
  background: #161c26;
  overflow: hidden;
}

.cache-hitrate-fill {
  height: 100%;
  background: linear-gradient(90deg, #4ec9b0, #ff6b35);
  transition: width 0.5s ease;
}

.cache-section-title {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.5px;
  color: #6e7681;
  margin-bottom: 8px;
}

.cache-glyph { color: #ff6b35; }

.cache-levels { display: flex; flex-direction: column; gap: 6px; }

.cache-level {
  display: grid;
  grid-template-columns: 100px 1fr 50px 80px;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  background: #0a0e14;
  font-size: 11px;
}

.cache-level-name { color: #c9d1d9; font-weight: 600; }

.cache-level-bar-wrap {
  height: 6px;
  background: #161c26;
  overflow: hidden;
}

.cache-level-bar { height: 100%; }

.bar-memory { background: #4ec9b0; }
.bar-parquet { background: #ff6b35; }
.bar-featurestore { background: #569cd6; }
.bar-artifact { background: #c586c0; }
.bar-redis { background: #f85149; }

.cache-level-count { color: #c9d1d9; text-align: right; }
.cache-level-size { color: #6e7681; text-align: right; }
</style>
