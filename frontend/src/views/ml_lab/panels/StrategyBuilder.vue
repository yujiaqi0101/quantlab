<template>
  <div class="strategy-builder">
    <div class="panel-header">
      <h2>ML Strategy Builder</h2>
      <p class="hint">Feature Set + Label + Model → ML Strategy</p>
    </div>

    <el-card>
      <template #header>Strategy Pipeline</template>
      <el-steps :active="3" align-center>
        <el-step title="Features" description="RSI, Momentum, Volume" />
        <el-step title="Label" description="FutureReturn10" />
        <el-step title="Model" description="LightGBM" />
        <el-step title="ML Strategy" description="predict() / signal() / position()" />
      </el-steps>
    </el-card>

    <el-card style="margin-top: 16px">
      <template #header>Strategies</template>
      <el-table :data="strategies" v-loading="loading" border>
        <el-table-column prop="strategy_id" label="ID" width="120" />
        <el-table-column prop="name" label="Name" width="200" />
        <el-table-column label="Features" width="300">
          <template #default="{ row }">
            <el-tag v-for="f in row.config?.feature_ids" :key="f" size="small" style="margin-right: 4px">{{ f }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="config.label_id" label="Label" width="150" />
        <el-table-column prop="config.model_type" label="Model" width="150" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getMLStrategies, type MLStrategy } from '@/api/ml'

const strategies = ref<MLStrategy[]>([])
const loading = ref(false)

async function loadData() {
  loading.value = true
  try {
    const resp = await getMLStrategies()
    strategies.value = resp.strategies || []
  } catch (e) {
    ElMessage.error('Failed to load strategies')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.panel-header {
  margin-bottom: 16px;
}

.panel-header h2 {
  margin: 0 0 8px 0;
}

.hint {
  color: #909399;
  font-size: 13px;
  margin: 0;
}
</style>
