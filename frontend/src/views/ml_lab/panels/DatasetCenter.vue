<template>
  <div class="dataset-center">
    <div class="panel-header">
      <h2>数据集中心 Dataset Center</h2>
      <el-button type="primary" @click="showCreateDialog = true">创建数据集 Create</el-button>
    </div>

    <!-- 数据集列表 -->
    <el-table :data="datasets" v-loading="loading" border style="width: 100%">
      <el-table-column prop="dataset_id" label="ID" width="120" />
      <el-table-column prop="name" label="名称 Name" width="150" />
      <el-table-column prop="symbols" label="标的 Symbols" width="200">
        <template #default="{ row }">
          <template v-if="row.scope_type === 'universe'">
            <el-tag type="warning" size="small">Universe: {{ row.universe_id }}</el-tag>
          </template>
          <template v-else>
            <el-tag v-for="s in row.symbols" :key="s" size="small" style="margin-right: 4px">{{ s }}</el-tag>
          </template>
        </template>
      </el-table-column>
      <el-table-column prop="frequency" label="频率 Frequency" width="100" />
      <el-table-column prop="start_date" label="开始 Start" width="120" />
      <el-table-column prop="end_date" label="结束 End" width="120" />
      <el-table-column prop="description" label="描述 Description" />
      <el-table-column label="操作 Actions" width="260">
        <template #default="{ row }">
          <el-button size="small" @click="viewStats(row)">统计 Stats</el-button>
          <el-upload
            :show-file-list="false"
            :before-upload="(file: File) => uploadCSV(row.dataset_id, file)"
            accept=".csv"
          >
            <el-button size="small" type="success">上传 Upload</el-button>
          </el-upload>
          <el-button size="small" type="danger" @click="confirmDelete(row)">删除 Delete</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 创建数据集对话框 -->
    <el-dialog v-model="showCreateDialog" title="创建数据集 Create Dataset" width="500px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="名称 Name">
          <el-input v-model="createForm.name" placeholder="e.g. Crypto_1H" />
        </el-form-item>
        <el-form-item label="范围 Scope">
          <el-radio-group v-model="createForm.scope_type">
            <el-radio value="single">单标的 Single</el-radio>
            <el-radio value="universe">股票池 Universe</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="createForm.scope_type === 'single'" label="标的 Symbols">
          <el-input v-model="symbolsInput" placeholder="BTC, ETH, SOL" />
        </el-form-item>
        <el-form-item v-else label="股票池 Universe">
          <el-input v-model="createForm.universe_id" placeholder="e.g. CSI300, CSI500, ALL_A" />
        </el-form-item>
        <el-form-item label="频率 Frequency">
          <el-select v-model="createForm.frequency">
            <el-option label="1m" value="1m" />
            <el-option label="5m" value="5m" />
            <el-option label="15m" value="15m" />
            <el-option label="1h" value="1h" />
            <el-option label="4h" value="4h" />
            <el-option label="1d" value="1d" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述 Description">
          <el-input v-model="createForm.description" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消 Cancel</el-button>
        <el-button type="primary" @click="createDataset">创建 Create</el-button>
      </template>
    </el-dialog>

    <!-- 统计对话框 -->
    <el-dialog v-model="showStatsDialog" title="数据集统计 Dataset Statistics" width="600px">
      <pre v-if="statsData">{{ JSON.stringify(statsData, null, 2) }}</pre>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getMLDatasets, createMLDataset, getMLDatasetStats, loadMLDatasetCSV, deleteMLDataset, type MLDataset } from '@/api/ml'

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
  scope_type: 'single',
  universe_id: '',
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

async function confirmDelete(row: MLDataset) {
  try {
    await ElMessageBox.confirm(
      `确定删除数据集 "${row.name}" (${row.dataset_id})？此操作不可恢复。`,
      '删除确认 Delete Confirm',
      { confirmButtonText: '删除 Delete', cancelButtonText: '取消 Cancel', type: 'warning' },
    )
    await deleteMLDataset(row.dataset_id)
    ElMessage.success('Dataset deleted')
    loadData()
  } catch (e: any) {
    if (e !== 'cancel') {
      ElMessage.error('Failed to delete dataset')
    }
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
