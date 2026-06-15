<template>
  <div class="detail-container">
    <!-- Back -->
    <div class="detail-back" @click="router.push('/strategies')">
      <el-icon :size="14"><ArrowLeft /></el-icon>
      <span>Back to Strategies</span>
    </div>

    <!-- Loading -->
    <div v-if="store.loading" class="loading-state">
      <el-icon class="is-loading" :size="24"><Loading /></el-icon>
      <span>Loading strategy...</span>
    </div>

    <!-- Error -->
    <div v-else-if="store.error" class="error-state">
      <el-icon :size="24" color="#f85149"><CircleCloseFilled /></el-icon>
      <p>{{ store.error }}</p>
    </div>

    <!-- Content -->
    <template v-else-if="strategy">
      <div class="detail-header">
        <div>
          <h1 class="detail-title">{{ strategy.name }}</h1>
          <p class="detail-id">{{ strategy.id }}</p>
        </div>
        <div class="detail-meta">
          <el-tag effect="dark" class="version-tag">v{{ strategy.version }}</el-tag>
          <el-tag
            v-for="tag in strategy.tags || []"
            :key="tag"
            effect="dark"
            class="tag-item"
          >
            {{ tag }}
          </el-tag>
        </div>
      </div>

      <!-- Description -->
      <div v-if="strategy.description" class="detail-section">
        <h3 class="section-title">Description</h3>
        <p class="section-text">{{ strategy.description }}</p>
      </div>

      <!-- Class Path -->
      <div class="detail-section">
        <h3 class="section-title">Class Path</h3>
        <code class="code-block">{{ strategy.class_path }}</code>
      </div>

      <!-- Parameters -->
      <div class="detail-section">
        <h3 class="section-title">Parameters</h3>
        <div v-if="(strategy.parameters || []).length === 0" class="empty-params">
          No configurable parameters
        </div>
        <div v-else class="params-grid">
          <div
            v-for="param in strategy.parameters"
            :key="param.name"
            class="param-card"
          >
            <div class="param-header">
              <span class="param-name">{{ param.name }}</span>
              <span class="param-type">{{ param.type }}</span>
            </div>
            <div class="param-body">
              <div class="param-row">
                <span class="param-label">Default</span>
                <span class="param-value">{{ formatDefault(param) }}</span>
              </div>
              <div v-if="param.min_value !== undefined && param.min_value !== null" class="param-row">
                <span class="param-label">Min</span>
                <span class="param-value">{{ param.min_value }}</span>
              </div>
              <div v-if="param.max_value !== undefined && param.max_value !== null" class="param-row">
                <span class="param-label">Max</span>
                <span class="param-value">{{ param.max_value }}</span>
              </div>
              <div v-if="param.choices" class="param-row">
                <span class="param-label">Choices</span>
                <span class="param-value">{{ param.choices.join(', ') }}</span>
              </div>
              <div v-if="param.description" class="param-desc">
                {{ param.description }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Param Space -->
      <div v-if="strategy.param_space && Object.keys(strategy.param_space).length > 0" class="detail-section">
        <h3 class="section-title">Parameter Space</h3>
        <div class="param-space-grid">
          <div v-for="(values, key) in strategy.param_space" :key="key" class="param-space-item">
            <span class="ps-key">{{ key }}</span>
            <span class="ps-values">{{ JSON.stringify(values) }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useStrategyStore } from '@/stores/strategy'
import { ArrowLeft, Loading, CircleCloseFilled } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const store = useStrategyStore()

const strategy = computed(() => store.current)

function formatDefault(param: any) {
  if (param.default === null || param.default === undefined) return 'N/A'
  return String(param.default)
}

onMounted(() => {
  const id = route.params.id as string
  if (id) {
    store.loadDetail(id)
  }
})
</script>

<style scoped>
.detail-container {
  max-width: 900px;
}

.detail-back {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #58a6ff;
  font-size: 13px;
  cursor: pointer;
  margin-bottom: 24px;
  transition: color 0.2s;
}

.detail-back:hover {
  color: #79c0ff;
}

.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  color: #8b949e;
  font-size: 14px;
  gap: 12px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
}

.detail-title {
  font-size: 28px;
  font-weight: 700;
  color: #e6edf3;
  margin: 0 0 4px 0;
  letter-spacing: -0.5px;
}

.detail-id {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 14px;
  color: #484f58;
  margin: 0;
}

.detail-meta {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.version-tag {
  background: #1f2937;
  border-color: #1f2937;
  color: #58a6ff;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
}

.tag-item {
  background: #1b2332;
  border-color: #1b2332;
  color: #8b949e;
  font-size: 12px;
}

.detail-section {
  margin-bottom: 28px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #8b949e;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 12px 0;
}

.section-text {
  font-size: 14px;
  color: #c9d1d9;
  line-height: 1.6;
  margin: 0;
}

.code-block {
  display: block;
  padding: 12px 16px;
  background: #161b22;
  border: 1px solid #1b2332;
  border-radius: 6px;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  color: #79c0ff;
  overflow-x: auto;
}

.empty-params {
  color: #484f58;
  font-size: 13px;
  padding: 16px 0;
}

.params-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}

.param-card {
  background: #161b22;
  border: 1px solid #1b2332;
  border-radius: 8px;
  overflow: hidden;
}

.param-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  border-bottom: 1px solid #1b2332;
  background: #0d1117;
}

.param-name {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  font-weight: 600;
  color: #e6edf3;
}

.param-type {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 11px;
  color: #bc8cff;
  background: #1b2332;
  padding: 2px 6px;
  border-radius: 3px;
}

.param-body {
  padding: 10px 14px;
}

.param-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 3px 0;
}

.param-label {
  font-size: 12px;
  color: #484f58;
}

.param-value {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  color: #c9d1d9;
}

.param-desc {
  font-size: 12px;
  color: #484f58;
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px solid #1b2332;
}

.param-space-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.param-space-item {
  display: flex;
  gap: 12px;
  padding: 8px 14px;
  background: #161b22;
  border: 1px solid #1b2332;
  border-radius: 6px;
}

.ps-key {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  color: #58a6ff;
  min-width: 120px;
}

.ps-values {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  color: #8b949e;
}
</style>
