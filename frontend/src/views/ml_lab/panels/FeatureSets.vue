<template>
  <div class="feature-sets">
    <div class="panel-header">
      <h2>Feature Sets</h2>
      <el-button type="primary" @click="showCreateDialog = true">Create FeatureSet</el-button>
    </div>

    <el-table :data="sets" v-loading="loading" border style="width: 100%">
      <el-table-column prop="fs_id" label="ID" width="120" />
      <el-table-column prop="name" label="Name" width="180" />
      <el-table-column prop="version" label="Version" width="80" />
      <el-table-column label="Features" min-width="250">
        <template #default="{ row }">
          <el-tag v-for="f in row.feature_ids" :key="f" size="small" style="margin-right: 4px; margin-bottom: 2px">{{ f }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="Description" min-width="150" />
      <el-table-column label="Tags" width="150">
        <template #default="{ row }">
          <el-tag v-for="t in row.tags" :key="t" size="small" type="info" style="margin-right: 4px">{{ t }}</el-tag>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showCreateDialog" title="Create FeatureSet" width="600px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="Name">
          <el-input v-model="createForm.name" placeholder="e.g. momentum_v1" />
        </el-form-item>
        <el-form-item label="Features">
          <el-select v-model="createForm.feature_ids" multiple filterable placeholder="Select features" style="width: 100%">
            <el-option v-for="f in availableFeatures" :key="f.feature_id" :label="`${f.name} (${f.feature_id})`" :value="f.feature_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Version">
          <el-input v-model="createForm.version" placeholder="1.0" />
        </el-form-item>
        <el-form-item label="Description">
          <el-input v-model="createForm.description" type="textarea" />
        </el-form-item>
        <el-form-item label="Tags">
          <el-input v-model="tagsInput" placeholder="momentum, v1" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">Cancel</el-button>
        <el-button type="primary" @click="createSet">Create</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getFeatureSets, createFeatureSet, getMLFeatures, type MLFeatureSet, type MLFeature } from '@/api/ml'

const sets = ref<MLFeatureSet[]>([])
const availableFeatures = ref<MLFeature[]>([])
const loading = ref(false)
const showCreateDialog = ref(false)
const tagsInput = ref('')

const createForm = ref({
  name: '',
  feature_ids: [] as string[],
  version: '1.0',
  description: '',
  tags: [] as string[],
})

async function loadData() {
  loading.value = true
  try {
    const [setsResp, featResp] = await Promise.all([getFeatureSets(), getMLFeatures()])
    sets.value = setsResp.sets
    availableFeatures.value = featResp.features
  } catch (e: any) {
    ElMessage.error(e.message || 'Failed to load')
  } finally {
    loading.value = false
  }
}

async function createSet() {
  try {
    const tags = tagsInput.value.split(',').map((t) => t.trim()).filter(Boolean)
    await createFeatureSet({
      name: createForm.value.name,
      feature_ids: createForm.value.feature_ids,
      version: createForm.value.version,
      description: createForm.value.description,
      tags,
    })
    ElMessage.success('FeatureSet created')
    showCreateDialog.value = false
    createForm.value = { name: '', feature_ids: [], version: '1.0', description: '', tags: [] }
    tagsInput.value = ''
    await loadData()
  } catch (e: any) {
    ElMessage.error(e.message || 'Failed to create')
  }
}

onMounted(loadData)
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
