<template>
  <div class="feature-lab">
    <div class="panel-header">
      <h2>Feature Lab</h2>
      <el-select v-model="selectedCategory" placeholder="Filter by category" clearable style="width: 200px">
        <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
      </el-select>
    </div>

    <el-table :data="filteredFeatures" v-loading="loading" border>
      <el-table-column prop="feature_id" label="ID" width="180" />
      <el-table-column prop="name" label="Name" width="180" />
      <el-table-column prop="category" label="Category" width="150">
        <template #default="{ row }">
          <el-tag size="small">{{ row.category }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="Description" />
      <el-table-column label="Params" width="200">
        <template #default="{ row }">
          <code>{{ JSON.stringify(row.params) }}</code>
        </template>
      </el-table-column>
      <el-table-column label="Required" width="200">
        <template #default="{ row }">
          <el-tag v-for="c in row.required_columns" :key="c" size="small" type="info" style="margin-right: 4px">{{ c }}</el-tag>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getMLFeatures, type MLFeature } from '@/api/ml'

const features = ref<MLFeature[]>([])
const categories = ref<string[]>([])
const loading = ref(false)
const selectedCategory = ref('')

const filteredFeatures = computed(() => {
  if (!selectedCategory.value) return features.value
  return features.value.filter(f => f.category === selectedCategory.value)
})

async function loadData() {
  loading.value = true
  try {
    const resp = await getMLFeatures()
    features.value = resp.features || []
    categories.value = resp.categories || []
  } catch (e) {
    ElMessage.error('Failed to load features')
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
</style>
