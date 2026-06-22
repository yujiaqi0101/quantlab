<template>
  <div class="label-sets">
    <div class="panel-header">
      <h2>标签集 Label Sets</h2>
      <el-button type="primary" @click="showCreateDialog = true">创建标签集 Create</el-button>
    </div>

    <el-table :data="sets" v-loading="loading" border style="width: 100%">
      <el-table-column prop="ls_id" label="ID" width="120" />
      <el-table-column prop="name" label="名称 Name" width="180" />
      <el-table-column prop="label_id" label="标签 Label" width="180" />
      <el-table-column prop="label_type" label="类型 Type" width="120">
        <template #default="{ row }">
          <el-tag :type="row.label_type === 'classification' ? 'warning' : 'success'" size="small">
            {{ row.label_type }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="version" label="版本 Version" width="80" />
      <el-table-column label="类别 Classes" width="200">
        <template #default="{ row }">
          <el-tag v-for="c in row.classes" :key="c" size="small" style="margin-right: 4px">{{ c }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述 Description" min-width="150" />
    </el-table>

    <el-dialog v-model="showCreateDialog" title="创建标签集 Create LabelSet" width="600px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="名称 Name">
          <el-input v-model="createForm.name" placeholder="例如 return_10d" />
        </el-form-item>
        <el-form-item label="标签 Label">
          <el-select v-model="createForm.label_id" filterable placeholder="选择标签 Select label" style="width: 100%">
            <el-option v-for="l in availableLabels" :key="l.label_id" :label="`${l.name} (${l.label_id})`" :value="l.label_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="类型 Type">
          <el-select v-model="createForm.label_type">
            <el-option label="回归 Regression" value="regression" />
            <el-option label="分类 Classification" value="classification" />
          </el-select>
        </el-form-item>
        <el-form-item label="版本 Version">
          <el-input v-model="createForm.version" placeholder="1.0" />
        </el-form-item>
        <el-form-item label="描述 Description">
          <el-input v-model="createForm.description" type="textarea" />
        </el-form-item>
        <el-form-item label="标签 Tags">
          <el-input v-model="tagsInput" placeholder="return, v1" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消 Cancel</el-button>
        <el-button type="primary" @click="createSet">创建 Create</el-button>
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
    ElMessage.error(e.message || '加载失败 Failed to load')
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
    ElMessage.success('标签集已创建 LabelSet created')
    showCreateDialog.value = false
    createForm.value = { name: '', label_id: '', label_type: 'regression', version: '1.0', description: '', tags: [] }
    tagsInput.value = ''
    await loadData()
  } catch (e: any) {
    ElMessage.error(e.message || '创建失败 Failed to create')
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
