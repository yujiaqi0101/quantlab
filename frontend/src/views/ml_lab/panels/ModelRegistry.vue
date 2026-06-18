<template>
  <div class="model-registry">
    <div class="panel-header">
      <h2>Model Registry</h2>
      <el-button type="primary" @click="showRegisterDialog = true">Register Version</el-button>
    </div>

    <el-table :data="versions" v-loading="loading" border>
      <el-table-column prop="version_id" label="Version ID" width="120" />
      <el-table-column prop="name" label="Name" width="150" />
      <el-table-column prop="model_type" label="Model" width="150" />
      <el-table-column prop="dataset_id" label="Dataset" width="120" />
      <el-table-column prop="label_id" label="Label" width="150" />
      <el-table-column label="Features" width="200">
        <template #default="{ row }">
          <el-tag v-for="f in row.feature_ids" :key="f" size="small" style="margin-right: 4px">{{ f }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="Metrics" width="200">
        <template #default="{ row }">
          <span v-if="row.metrics">
            IC: {{ row.metrics.ic?.toFixed(4) }}, Sharpe: {{ row.metrics.sharpe?.toFixed(2) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="Created" width="180" />
    </el-table>

    <el-dialog v-model="showRegisterDialog" title="Register Model Version" width="500px">
      <el-form :model="registerForm" label-width="120px">
        <el-form-item label="Name">
          <el-input v-model="registerForm.name" placeholder="e.g. LGBM_v1" />
        </el-form-item>
        <el-form-item label="Model Type">
          <el-select v-model="registerForm.model_type" style="width: 100%">
            <el-option label="Linear Regression" value="LINEAR_REGRESSION" />
            <el-option label="Logistic Regression" value="LOGISTIC_REGRESSION" />
            <el-option label="Random Forest" value="RANDOM_FOREST" />
            <el-option label="XGBoost" value="XGBOOST" />
            <el-option label="LightGBM" value="LIGHTGBM" />
          </el-select>
        </el-form-item>
        <el-form-item label="Description">
          <el-input v-model="registerForm.description" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRegisterDialog = false">Cancel</el-button>
        <el-button type="primary" @click="register">Register</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getModelVersions, registerModelVersion, type ModelVersion } from '@/api/ml'

const versions = ref<ModelVersion[]>([])
const loading = ref(false)
const showRegisterDialog = ref(false)

const registerForm = ref({
  name: '',
  model_type: 'LIGHTGBM',
  description: '',
})

async function loadData() {
  loading.value = true
  try {
    const resp = await getModelVersions()
    versions.value = resp.versions || []
  } catch (e) {
    ElMessage.error('Failed to load versions')
  } finally {
    loading.value = false
  }
}

async function register() {
  if (!registerForm.value.name) {
    ElMessage.warning('Name is required')
    return
  }
  try {
    await registerModelVersion(registerForm.value)
    ElMessage.success('Version registered')
    showRegisterDialog.value = false
    loadData()
  } catch (e) {
    ElMessage.error('Failed to register')
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
