<template>
  <div class="signal-registry">
    <div class="header">
      <h2>Signal Registry</h2>
      <p class="desc">信号仓库 — 所有生成的信号都持久化保存，支持版本追溯</p>
    </div>

    <!-- 筛选 -->
    <el-card class="section-card">
      <el-row :gutter="16">
        <el-col :span="6">
          <el-input v-model="filters.symbol" placeholder="Symbol" clearable @keyup.enter="loadSignals" />
        </el-col>
        <el-col :span="6">
          <el-select v-model="filters.direction" placeholder="Direction" clearable>
            <el-option label="LONG" value="LONG" />
            <el-option label="SHORT" value="SHORT" />
            <el-option label="NEUTRAL" value="NEUTRAL" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-input-number v-model="filters.limit" :min="10" :max="500" />
        </el-col>
        <el-col :span="6">
          <el-button type="primary" @click="loadSignals">查询</el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 信号列表 -->
    <el-card class="section-card">
      <template #header>
        <div class="card-header">
          <span>信号列表 ({{ total }})</span>
        </div>
      </template>
      <el-table :data="signals" stripe v-loading="loading" max-height="500">
        <el-table-column prop="symbol" label="Symbol" width="120" />
        <el-table-column prop="direction" label="Direction" width="100">
          <template #default="{ row }">
            <el-tag :type="dirTagType(row.direction)" size="small">{{ row.direction }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="score" label="Score" width="100">
          <template #default="{ row }">{{ row.score.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="confidence" label="Confidence" width="110">
          <template #default="{ row }">{{ (row.confidence * 100).toFixed(1) }}%</template>
        </el-table-column>
        <el-table-column prop="generator" label="Generator" width="120" />
        <el-table-column prop="source_model" label="Model" width="120" />
        <el-table-column prop="datetime" label="Datetime" width="180" />
        <el-table-column label="操作" width="160">
          <template #default="{ row }">
            <el-button text size="small" @click="showVersions(row)">版本</el-button>
            <el-button text size="small" @click="showExplain(row)">解释</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 版本弹窗 -->
    <el-dialog v-model="versionVisible" title="版本历史" width="70%">
      <el-table :data="versions" stripe>
        <el-table-column prop="version" label="Version" width="100" />
        <el-table-column prop="model_version" label="Model" width="120" />
        <el-table-column prop="dataset_id" label="Dataset" width="120" />
        <el-table-column prop="created_at" label="Created At" width="200" />
        <el-table-column label="Pipeline Config">
          <template #default="{ row }">
            <el-button text size="small" @click="showConfig(row.pipeline_config)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 解释弹窗 -->
    <el-dialog v-model="explainVisible" title="Signal Explainability" width="80%">
      <el-timeline v-if="explainTrace">
        <el-timeline-item v-for="(item, idx) in explainSteps" :key="idx" :timestamp="item.label" placement="top">
          <el-card><pre>{{ item.data }}</pre></el-card>
        </el-timeline-item>
      </el-timeline>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getSignals, getVersions, explainSignal,
  type Signal, type SignalVersion, type ExplainTrace,
} from '@/api/signalEngine'

const loading = ref(false)
const signals = ref<Signal[]>([])
const total = ref(0)
const filters = reactive({ symbol: '', direction: '', limit: 100 })

const versionVisible = ref(false)
const versions = ref<SignalVersion[]>([])

const explainVisible = ref(false)
const explainTrace = ref<ExplainTrace | null>(null)

const explainSteps = computed(() => {
  if (!explainTrace.value) return []
  const t = explainTrace.value
  return [
    { label: 'Prediction', data: t.prediction },
    { label: 'After Generator', data: t.after_generator },
    { label: 'After Filter', data: t.after_filter },
    { label: 'After Ranker', data: t.after_ranker },
    { label: 'After Scorer', data: t.after_scorer },
    { label: 'After Allocator', data: t.after_allocator },
    { label: 'Final', data: t.final_signal },
  ].filter(s => Object.keys(s.data || {}).length > 0)
})

onMounted(() => loadSignals())

async function loadSignals() {
  loading.value = true
  try {
    const res = await getSignals({
      symbol: filters.symbol || undefined,
      direction: filters.direction || undefined,
      limit: filters.limit,
    })
    signals.value = res.signals
    total.value = res.total
  } catch (e: any) {
    ElMessage.error('加载失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function showVersions(signal: Signal) {
  try {
    const res = await getVersions(signal.signal_id)
    versions.value = res.versions
    versionVisible.value = true
  } catch (e: any) {
    ElMessage.error('加载版本失败: ' + e.message)
  }
}

async function showExplain(signal: Signal) {
  try {
    const trace = await explainSignal(signal.signal_id)
    explainTrace.value = trace
    explainVisible.value = true
  } catch (e: any) {
    ElMessage.error('解释失败: ' + e.message)
  }
}

function showConfig(cfg: any) {
  ElMessage.info(JSON.stringify(cfg, null, 2))
}

function dirTagType(dir: string) {
  if (dir === 'LONG') return 'success'
  if (dir === 'SHORT') return 'danger'
  return 'info'
}
</script>

<style scoped>
.signal-registry { padding: 16px; }
.header h2 { margin: 0 0 4px 0; }
.header .desc { color: #888; margin: 0 0 16px 0; font-size: 13px; }
.section-card { margin-bottom: 16px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
</style>
