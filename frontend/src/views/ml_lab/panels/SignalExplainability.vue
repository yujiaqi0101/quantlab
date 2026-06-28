<template>
  <div class="signal-explainability">
    <div class="header">
      <h2>Signal Explainability</h2>
      <p class="desc">信号溯源解释 — 点击信号查看 Prediction → Threshold → Filter → Ranking → Score → Weight 的完整链路</p>
    </div>

    <el-card class="section-card">
      <el-row :gutter="16">
        <el-col :span="20">
          <el-input v-model="signalId" placeholder="输入 Signal ID" clearable @keyup.enter="explain" />
        </el-col>
        <el-col :span="4">
          <el-button type="primary" :loading="loading" @click="explain" style="width:100%">
            解释
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <el-card v-if="trace" class="section-card">
      <template #header><span>溯源链</span></template>
      <el-timeline>
        <el-timeline-item
          v-for="(step, idx) in steps"
          :key="idx"
          :timestamp="step.label"
          placement="top"
          :type="step.color"
        >
          <el-card shadow="hover">
            <div class="step-content">
              <pre>{{ JSON.stringify(step.data, null, 2) }}</pre>
            </div>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </el-card>

    <el-empty v-else description="输入 Signal ID 查看溯源链" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { explainSignal, type ExplainTrace } from '@/api/signalEngine'

const signalId = ref('')
const loading = ref(false)
const trace = ref<ExplainTrace | null>(null)

const steps = computed(() => {
  if (!trace.value) return []
  const t = trace.value
  return [
    { label: '1. Prediction (原始预测)', data: t.prediction, color: 'primary' },
    { label: '2. After Calibration (校准后)', data: t.after_calibration, color: 'primary' },
    { label: '3. After Generator (生成方向)', data: t.after_generator, color: 'success' },
    { label: '4. After Filter (过滤后)', data: t.after_filter, color: 'warning' },
    { label: '5. After Ranker (排名)', data: t.after_ranker, color: 'primary' },
    { label: '6. After Scorer (评分)', data: t.after_scorer, color: 'primary' },
    { label: '7. After Allocator (建议权重)', data: t.after_allocator, color: 'success' },
    { label: '8. Final Signal (最终信号)', data: t.final_signal, color: 'success' },
  ].filter(s => s.data && Object.keys(s.data).length > 0)
})

async function explain() {
  if (!signalId.value) {
    ElMessage.warning('请输入 Signal ID')
    return
  }
  loading.value = true
  try {
    trace.value = await explainSignal(signalId.value)
    if (!trace.value || Object.keys(trace.value).length === 0) {
      ElMessage.info('该信号无溯源信息')
    }
  } catch (e: any) {
    ElMessage.error('解释失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.signal-explainability { padding: 16px; }
.header h2 { margin: 0 0 4px 0; }
.header .desc { color: #888; margin: 0 0 16px 0; font-size: 13px; }
.section-card { margin-bottom: 16px; }
.step-content pre { margin: 0; font-size: 12px; line-height: 1.5; }
</style>
