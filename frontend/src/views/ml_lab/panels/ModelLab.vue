<template>
  <div class="model-lab">
    <div class="panel-header">
      <h2>模型实验室 Model Lab</h2>
      <p class="hint">支持的模型：线性回归、随机森林、XGBoost、LightGBM</p>
    </div>

    <el-row :gutter="16">
      <el-col :span="8" v-for="model in models" :key="model.type">
        <el-card class="model-card">
          <template #header>
            <div class="card-header">
              <span>{{ model.name }}</span>
              <el-tag :type="model.is_classifier ? 'warning' : 'success'" size="small">
                {{ model.is_classifier ? '分类 Classification' : '回归 Regression' }}
              </el-tag>
            </div>
          </template>
          <p>{{ model.description }}</p>
          <p class="model-type"><code>{{ model.type }}</code></p>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getMLModels, type MLModel } from '@/api/ml'

const models = ref<MLModel[]>([])

async function loadData() {
  try {
    const resp = await getMLModels()
    models.value = resp.models || []
  } catch (e) {
    ElMessage.error('加载模型失败 Failed to load models')
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

.model-card {
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.model-type {
  color: #909399;
  font-size: 12px;
  margin: 8px 0 0 0;
}
</style>
