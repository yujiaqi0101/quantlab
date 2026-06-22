<template>
  <div class="label-lab">
    <div class="panel-header">
      <h2>标签实验室 Label Lab</h2>
    </div>

    <el-table :data="labels" v-loading="loading" border>
      <el-table-column prop="label_id" label="ID" width="200" />
      <el-table-column prop="name" label="名称 Name" width="200" />
      <el-table-column prop="label_type" label="类型 Type" width="120">
        <template #default="{ row }">
          <el-tag :type="row.label_type === 'classification' ? 'warning' : 'success'" size="small">
            {{ row.label_type }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="classes" label="类别 Classes" width="200">
        <template #default="{ row }">
          <el-tag v-for="c in row.classes" :key="c" size="small" style="margin-right: 4px">{{ c }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述 Description" />
      <el-table-column label="参数 Params" width="200">
        <template #default="{ row }">
          <code>{{ JSON.stringify(row.params) }}</code>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getMLLabels, type MLLabel } from '@/api/ml'

const labels = ref<MLLabel[]>([])
const loading = ref(false)

async function loadData() {
  loading.value = true
  try {
    const resp = await getMLLabels()
    labels.value = resp.labels || []
  } catch (e) {
    ElMessage.error('Failed to load labels')
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
  margin: 0;
}
</style>
