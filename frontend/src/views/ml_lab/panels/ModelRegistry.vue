<template>
  <div class="model-registry">
    <div class="panel-header">
      <h2>模型注册表 Model Registry</h2>
      <span class="hint">模型由 Validation Pipeline PASS 后自动注册</span>
    </div>

    <el-table :data="versions" v-loading="loading" border>
      <el-table-column prop="version_id" label="版本ID Version ID" width="120" />
      <el-table-column prop="name" label="名称 Name" width="150" />
      <el-table-column prop="model_type" label="模型 Model" width="150" />
      <el-table-column prop="dataset_id" label="数据集 Dataset" width="120" />
      <el-table-column prop="label_id" label="标签 Label" width="150" />
      <el-table-column label="特征 Features" width="200">
        <template #default="{ row }">
          <el-tag v-for="f in row.feature_ids" :key="f" size="small" style="margin-right: 4px">{{ f }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="指标 Metrics" width="200">
        <template #default="{ row }">
          <span v-if="row.metrics">
            IC: {{ row.metrics.ic?.toFixed(4) }}, Sharpe: {{ row.metrics.sharpe?.toFixed(2) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间 Created" width="180" />
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getModelVersions, type ModelVersion } from '@/api/ml'

const versions = ref<ModelVersion[]>([])
const loading = ref(false)

async function loadData() {
  loading.value = true
  try {
    const resp = await getModelVersions()
    versions.value = resp.versions || []
  } catch (e) {
    ElMessage.error('加载版本失败 Failed to load versions')
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
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.panel-header h2 {
  margin: 0;
}

.hint {
  color: #909399;
  font-size: 12px;
}
</style>
