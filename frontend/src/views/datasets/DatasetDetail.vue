<template>
  <div class="detail-container">
    <!-- Back -->
    <div class="detail-back" @click="router.push('/datasets')">
      <el-icon :size="14"><ArrowLeft /></el-icon>
      <span>返回数据集 Back to Datasets</span>
    </div>

    <!-- Loading -->
    <div v-if="store.loading" class="loading-state">
      <el-icon class="is-loading" :size="24"><Loading /></el-icon>
      <span>加载数据集中 Loading dataset...</span>
    </div>

    <!-- Error -->
    <div v-else-if="store.error" class="error-state">
      <el-icon :size="24" color="#f85149"><CircleCloseFilled /></el-icon>
      <p>{{ store.error }}</p>
    </div>

    <!-- Content -->
    <template v-else-if="dataset">
      <!-- Header -->
      <div class="detail-header">
        <div>
          <h1 class="detail-title">{{ dataset.name }}</h1>
          <p class="detail-id">{{ dataset.dataset_id }}</p>
        </div>
        <div class="detail-meta">
          <el-tag effect="dark" class="freq-tag">{{ dataset.frequency }}</el-tag>
          <el-tag effect="dark" class="type-tag">{{ dataset.asset_type }}</el-tag>
          <el-tag v-if="dataset.is_ohlcv" effect="dark" class="ohlcv-tag">OHLCV</el-tag>
        </div>
      </div>

      <!-- Info Grid -->
      <div class="info-grid">
        <div class="info-card">
          <span class="info-label">标的 Symbol</span>
          <span class="info-value mono">{{ dataset.symbol }}</span>
        </div>
        <div class="info-card">
          <span class="info-label">频率 Frequency</span>
          <span class="info-value mono">{{ dataset.frequency }}</span>
        </div>
        <div class="info-card">
          <span class="info-label">行数 Rows</span>
          <span class="info-value mono highlight">{{ formatNumber(dataset.rows) }}</span>
        </div>
        <div class="info-card">
          <span class="info-label">开始 Start</span>
          <span class="info-value mono">{{ formatDate(dataset.start_time) }}</span>
        </div>
        <div class="info-card">
          <span class="info-label">结束 End</span>
          <span class="info-value mono">{{ formatDate(dataset.end_time) }}</span>
        </div>
        <div class="info-card">
          <span class="info-label">格式 Format</span>
          <span class="info-value mono">{{ dataset.storage_format }}</span>
        </div>
      </div>

      <!-- Candlestick Chart -->
      <div v-if="dataset.is_ohlcv && previewData" class="detail-section">
        <h3 class="section-title">价格图表 Price Chart</h3>
        <CandlestickChart :preview="previewData" />
      </div>

      <!-- Data Preview -->
      <div v-if="previewData" class="detail-section">
        <h3 class="section-title">数据预览 Data Preview</h3>
        <div class="preview-tabs">
          <div
            v-for="sym in previewData.symbols"
            :key="sym"
            class="preview-tab"
            :class="{ active: activeSymbol === sym }"
            @click="activeSymbol = sym"
          >
            {{ sym }}
          </div>
        </div>
        <el-table
          :data="previewRows"
          class="q-table"
          size="small"
          :header-cell-style="{ background: '#161b22', color: '#8b949e', borderBottom: '1px solid #1b2332' }"
          :cell-style="{ borderBottom: '1px solid #1b2332' }"
          max-height="400"
        >
          <el-table-column label="日期 Date" width="160">
            <template #default="{ $index }">
              <span class="cell-date">{{ previewIndex[$index] }}</span>
            </template>
          </el-table-column>
          <el-table-column
            v-for="col in previewColumns"
            :key="col"
            :label="col"
            min-width="100"
            align="right"
          >
            <template #default="{ $index }">
              <span class="cell-num">{{ formatCell(previewRows[$index]?.[col]) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- Schema -->
      <div v-if="dataset.schema?.columns?.length" class="detail-section">
        <h3 class="section-title">模式 Schema</h3>
        <div class="schema-grid">
          <div
            v-for="col in dataset.schema.columns"
            :key="col.name"
            class="schema-item"
          >
            <span class="schema-name">{{ col.name }}</span>
            <span class="schema-dtype">{{ col.dtype }}</span>
            <span v-if="col.role && col.role !== 'other'" class="schema-role">{{ col.role }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDatasetStore } from '@/stores/dataset'
import { ArrowLeft, Loading, CircleCloseFilled } from '@element-plus/icons-vue'
import CandlestickChart from '@/components/charts/CandlestickChart.vue'

const route = useRoute()
const router = useRouter()
const store = useDatasetStore()

const dataset = computed(() => store.current)
const previewData = computed(() => store.preview)
const activeSymbol = ref('')

const previewColumns = computed(() => {
  if (!previewData.value || !activeSymbol.value) return []
  return previewData.value.preview[activeSymbol.value]?.columns || []
})

const previewRows = computed(() => {
  if (!previewData.value || !activeSymbol.value) return []
  const symData = previewData.value.preview[activeSymbol.value]
  if (!symData) return []
  return symData.rows.map((row: any[]) => {
    const obj: Record<string, any> = {}
    symData.columns.forEach((col: string, i: number) => {
      obj[col] = row[i]
    })
    return obj
  })
})

const previewIndex = computed(() => {
  if (!previewData.value || !activeSymbol.value) return []
  return previewData.value.preview[activeSymbol.value]?.index || []
})

function formatNumber(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(2) + 'M'
  if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K'
  return String(n)
}

function formatDate(dt: string): string {
  if (!dt) return '-'
  return dt.split(' ')[0]
}

function formatCell(v: any): string {
  if (v === null || v === undefined) return '-'
  if (typeof v === 'number') {
    if (Number.isInteger(v)) return v.toLocaleString()
    return v.toFixed(2)
  }
  return String(v)
}

onMounted(async () => {
  const id = route.params.id as string
  if (id) {
    await store.loadDetail(id)
    // Set default active symbol
    if (store.preview?.symbols?.length) {
      activeSymbol.value = store.preview.symbols[0]
    }
  }
})
</script>

<style scoped>
.detail-container {
  max-width: 1000px;
}

.detail-back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #58a6ff;
  font-size: 13px;
  cursor: pointer;
  margin-bottom: 24px;
  transition: color 0.2s;
}

.detail-back:hover {
  color: #79c0ff;
}

.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  color: #8b949e;
  font-size: 14px;
  gap: 12px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.detail-title {
  font-size: 28px;
  font-weight: 700;
  color: #e6edf3;
  margin: 0 0 4px 0;
  letter-spacing: -0.5px;
}

.detail-id {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 14px;
  color: #484f58;
  margin: 0;
}

.detail-meta {
  display: flex;
  gap: 6px;
}

.freq-tag {
  background: #1f2937;
  border-color: #1f2937;
  color: #58a6ff;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
}

.type-tag {
  background: #1b2332;
  border-color: #1b2332;
  color: #8b949e;
}

.ohlcv-tag {
  background: #0d2818;
  border-color: #0d2818;
  color: #3fb950;
}

/* Info Grid */
.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
  margin-bottom: 32px;
}

.info-card {
  background: #161b22;
  border: 1px solid #1b2332;
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 11px;
  color: #484f58;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-value {
  font-size: 14px;
  color: #e6edf3;
}

.info-value.mono {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
}

.info-value.highlight {
  color: #bc8cff;
}

/* Sections */
.detail-section {
  margin-bottom: 28px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #8b949e;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 12px 0;
}

/* Preview Tabs */
.preview-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 12px;
}

.preview-tab {
  padding: 6px 14px;
  font-size: 13px;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  color: #8b949e;
  background: #161b22;
  border: 1px solid #1b2332;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.preview-tab.active {
  color: #58a6ff;
  border-color: #1f6feb;
  background: #1f2937;
}

.preview-tab:hover {
  color: #e6edf3;
}

/* Table */
.q-table {
  --el-table-bg-color: #0d1117;
  --el-table-tr-bg-color: #0d1117;
  --el-table-row-hover-bg-color: #161b22;
  --el-table-text-color: #e6edf3;
  --el-table-border-color: #1b2332;
  --el-table-header-text-color: #8b949e;
}

.cell-date {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 12px;
  color: #8b949e;
}

.cell-num {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 12px;
  color: #c9d1d9;
}

/* Schema */
.schema-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.schema-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: #161b22;
  border: 1px solid #1b2332;
  border-radius: 6px;
}

.schema-name {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  color: #e6edf3;
  font-weight: 500;
}

.schema-dtype {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 11px;
  color: #bc8cff;
  background: #1b2332;
  padding: 1px 5px;
  border-radius: 3px;
}

.schema-role {
  font-size: 11px;
  color: #3fb950;
  background: #0d2818;
  padding: 1px 5px;
  border-radius: 3px;
}
</style>
