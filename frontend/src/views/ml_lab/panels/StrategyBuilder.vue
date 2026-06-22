<template>
  <div class="strategy-builder">
    <div class="panel-header">
      <h2>ML策略构建器 ML Strategy Builder</h2>
      <p class="hint">特征集 + 标签 + 模型 → ML策略</p>
    </div>

    <el-card>
      <template #header>策略流水线 Strategy Pipeline</template>
      <el-steps :active="3" align-center>
        <el-step title="特征 Features" description="RSI, Momentum, Volume" />
        <el-step title="标签 Label" description="FutureReturn10" />
        <el-step title="模型 Model" description="LightGBM" />
        <el-step title="ML策略 ML Strategy" description="predict() / signal() / position()" />
      </el-steps>
    </el-card>

    <el-card style="margin-top: 16px">
      <template #header>策略列表 Strategies</template>
      <el-table :data="strategies" v-loading="loading" border>
        <el-table-column prop="strategy_id" label="ID" width="120" />
        <el-table-column prop="name" label="名称 Name" width="200" />
        <el-table-column label="特征 Features" width="300">
          <template #default="{ row }">
            <el-tag v-for="f in row.config?.feature_ids" :key="f" size="small" style="margin-right: 4px">{{ f }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="config.label_id" label="标签 Label" width="150" />
        <el-table-column prop="config.model_type" label="模型 Model" width="150" />
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
    ElMessage.error('加载策略失败 Failed to load strategies')
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
