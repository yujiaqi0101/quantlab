<template>
  <div class="label-sets">
    <div class="panel-header">
      <h2>Label Sets</h2>
      <el-button type="primary" @click="showCreateDialog = true">Create LabelSet</el-button>
    </div>

    <el-table :data="sets" v-loading="loading" border style="width: 100%">
      <el-table-column prop="ls_id" label="ID" width="120" />
      <el-table-column prop="name" label="Name" width="180" />
      <el-table-column prop="label_id" label="Label" width="180" />
      <el-table-column prop="label_type" label="Type" width="120">
        <template #default="{ row }">
          <el-tag :type="row.label_type === 'classification' ? 'warning' : 'success'" size="small">
            {{ row.label_type }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="version" label="Version" width="80" />
      <el-table-column label="Classes" width="200">
        <template #default="{ row }">
          <el-tag v-for="c in row.classes" :key="c" size="small" style="margin-right: 4px">{{ c }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="Description" min-width="150" />
    </el-table>

    <el-dialog v-model="showCreateDialog" title="Create LabelSet" width="600px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="Name">
          <el-input v-model="createForm.name" placeholder="e.g. return_10d" />
        </el-form-item>
        <el-form-item label="Label">
          <el-select v-model="createForm.label_id" filterable placeholder="Select label" style="width: 100%">
            <el-option v-for="l in availableLabels" :key="l.label_id" :label="`${l.name} (${l.label_id})`" :value="l.label_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Type">
          <el-select v-model="createForm.label_type">
            <el-option label="Regression" value="regression" />
            <el-option label="Classification" value="classification" />
          </el-select>
        </el-form-item>
        <el-form-item label="Version">
          <el-input v-model="createForm.version" placeholder="1.0" />
        </el-form-item>
        <el-form-item label="Description">
          <el-input v-model="createForm.description" type="textarea" />
        </el-form-item>
        <el-form-item label="Tags">
          <el-input v-model="tagsInput" placeholder="return, v1" />
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
import { getLabelSets, createLabelSet, getMLLabels, type MLLabelSet, type MLLabel } from '@/api/ml'

const sets = ref<MLLabelSet[]>([])
const availableLabels = ref<MLLabel[]>([])
const loading = ref(false)
const showCreateDialog = ref(false)
const tagsInput = ref('')

const createForm = ref({
  name: '',
  label_id: '',
  label_type: 'regression',
  version: '1.0',
  description: '',
  tags: [] as string[],
})

async function loadData() {
  loading.value = true
  try {
    const [setsResp, labelsResp] = await Promise.all([getLabelSets(), getMLLabels()])
    sets.value = setsResp.sets
    availableLabels.value = labelsResp.labels
  } catch (e: any) {
    ElMessage.error(e.message || 'Failed to load')
  } finally {
    loading.value = false
  }
}

async function createSet() {
  try {
    const tags = tagsInput.value.split(',').map((t) => t.trim()).filter(Boolean)
    await createLabelSet({
      name: createForm.value.name,
      label_id: createForm.value.label_id,
      label_type: createForm.value.label_type,
      version: createForm.value.version,
      description: createForm.value.description,
      tags,
    })
    ElMessage.success('LabelSet created')
    showCreateDialog.value = false
    createForm.value = { name: '', label_id: '', label_type: 'regression', version: '1.0', description: '', tags: [] }
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
