<template>
  <div class="dataset-center">
    <div class="panel-header">
      <h2>Dataset Center</h2>
      <el-button type="primary" @click="showCreateDialog = true">Create Dataset</el-button>
    </div>

    <!-- 数据集列表 -->
    <el-table :data="datasets" v-loading="loading" border style="width: 100%">
      <el-table-column prop="dataset_id" label="ID" width="120" />
      <el-table-column prop="name" label="Name" width="150" />
      <el-table-column prop="symbols" label="Symbols" width="200">
        <template #default="{ row }">
          <el-tag v-for="s in row.symbols" :key="s" size="small" style="margin-right: 4px">{{ s }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="frequency" label="Frequency" width="100" />
      <el-table-column prop="start_date" label="Start" width="120" />
      <el-table-column prop="end_date" label="End" width="120" />
      <el-table-column prop="description" label="Description" />
      <el-table-column label="Actions" width="200">
        <template #default="{ row }">
          <el-button size="small" @click="viewStats(row)">Stats</el-button>
          <el-upload
            :show-file-list="false"
            :before-upload="(file: File) => uploadCSV(row.dataset_id, file)"
            accept=".csv"
          >
            <el-button size="small" type="success">Upload CSV</el-button>
          </el-upload>
        </template>
      </el-table-column>
    </el-table>

    <!-- 创建数据集对话框 -->
    <el-dialog v-model="showCreateDialog" title="Create Dataset" width="500px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="Name">
          <el-input v-model="createForm.name" placeholder="e.g. Crypto_1H" />
        </el-form-item>
        <el-form-item label="Symbols">
          <el-input v-model="symbolsInput" placeholder="BTC, ETH, SOL" />
        </el-form-item>
        <el-form-item label="Frequency">
          <el-select v-model="createForm.frequency">
            <el-option label="1m" value="1m" />
            <el-option label="5m" value="5m" />
            <el-option label="15m" value="15m" />
            <el-option label="1h" value="1h" />
            <el-option label="4h" value="4h" />
            <el-option label="1d" value="1d" />
          </el-select>
        </el-form-item>
        <el-form-item label="Description">
          <el-input v-model="createForm.description" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">Cancel</el-button>
        <el-button type="primary" @click="createDataset">Create</el-button>
      </template>
    </el-dialog>

    <!-- 统计对话框 -->
    <el-dialog v-model="showStatsDialog" title="Dataset Statistics" width="600px">
      <pre v-if="statsData">{{ JSON.stringify(statsData, null, 2) }}</pre>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getMLDatasets, createMLDataset, getMLDatasetStats, loadMLDatasetCSV, type MLDataset } from '@/api/ml'

const datasets = ref<MLDataset[]>([])
const loading = ref(false)
const showCreateDialog = ref(false)
const showStatsDialog = ref(false)
const statsData = ref<any>(null)
const symbolsInput = ref('')

const createForm = ref({
  name: '',
  symbols: [] as string[],
  frequency: '1d',
  description: '',
})

async function loadData() {
  loading.value = true
  try {
    const resp = await getMLDatasets()
    datasets.value = resp.datasets || []
  } catch (e) {
    ElMessage.error('Failed to load datasets')
  } finally {
    loading.value = false
  }
}

async function createDataset() {
  createForm.value.symbols = symbolsInput.value.split(',').map(s => s.trim()).filter(Boolean)
  try {
    await createMLDataset(createForm.value)
    ElMessage.success('Dataset created')
    showCreateDialog.value = false
    loadData()
  } catch (e) {
    ElMessage.error('Failed to create dataset')
  }
}

async function viewStats(row: MLDataset) {
  try {
    statsData.value = await getMLDatasetStats(row.dataset_id)
    showStatsDialog.value = true
  } catch (e) {
    ElMessage.error('Failed to load stats')
  }
}

async function uploadCSV(datasetId: string, file: File) {
  try {
    await loadMLDatasetCSV(datasetId, file)
    ElMessage.success('CSV uploaded')
    loadData()
  } catch (e) {
    ElMessage.error('Failed to upload CSV')
  }
  return false
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
