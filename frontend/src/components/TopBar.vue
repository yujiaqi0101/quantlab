<template>
  <div class="topbar">
    <div class="topbar-left">
      <span class="topbar-title">{{ route.meta.title || 'QuantLab Studio' }}</span>
      <span class="topbar-divider" />
      <span class="topbar-subtitle">研究平台 Research Platform</span>
    </div>

    <div class="topbar-right">
      <!-- Workspace preset switcher (only on Studio) -->
      <el-select
        v-if="isStudio"
        :model-value="wsStore.activeId"
        @change="onPresetChange"
        class="preset-select"
        size="small"
      >
        <el-option
          v-for="p in wsStore.presets"
          :key="p.id"
          :label="p.name"
          :value="p.id"
        >
          <div class="preset-option">
            <span class="preset-name">{{ p.name }}</span>
            <span class="preset-desc">{{ p.description }}</span>
          </div>
        </el-option>
      </el-select>

      <!-- Theme switcher -->
      <el-tooltip :content="appStore.theme === 'dark' ? '切换亮色 Switch to Light' : '切换暗色 Switch to Dark'" placement="bottom">
        <div class="theme-toggle" @click="onToggleTheme">
          <el-icon :size="16">
            <Moon v-if="appStore.theme === 'dark'" />
            <Sunny v-else />
          </el-icon>
        </div>
      </el-tooltip>

      <!-- System status -->
      <div class="topbar-status">
        <span class="status-dot" />
        <span class="status-text">系统在线 System Online</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useWorkspaceStore } from '@/stores/workspace'
import { Moon, Sunny } from '@element-plus/icons-vue'

const route = useRoute()
const appStore = useAppStore()
const wsStore = useWorkspaceStore()

const isStudio = computed(() => route.path === '/' || route.path === '/studio')

function onToggleTheme() {
  appStore.toggleTheme()
}

function onPresetChange(id: string) {
  wsStore.setActive(id)
}
</script>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  height: 100%;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.topbar-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--q-text-primary);
  letter-spacing: -0.2px;
}

.topbar-divider {
  width: 1px;
  height: 16px;
  background: var(--q-border);
}

.topbar-subtitle {
  font-size: 13px;
  color: var(--q-text-muted);
  font-weight: 400;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.preset-select {
  width: 140px;
}

.preset-select :deep(.el-input__wrapper) {
  background: var(--q-input-bg);
  box-shadow: 0 0 0 1px var(--q-input-border);
}

.preset-select :deep(.el-input__inner) {
  color: var(--q-text-primary);
  font-size: 12px;
}

.preset-option {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 2px 0;
}

.preset-name {
  font-size: 13px;
  color: var(--q-text-primary);
  font-weight: 500;
}

.preset-desc {
  font-size: 11px;
  color: var(--q-text-muted);
}

.theme-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  cursor: pointer;
  color: var(--q-text-secondary);
  transition: background 0.2s, color 0.2s;
}

.theme-toggle:hover {
  background: var(--q-bg-tertiary);
  color: var(--q-text-primary);
}

.topbar-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: var(--q-bg-secondary);
  border: 1px solid var(--q-border);
  border-radius: 4px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--q-green);
  box-shadow: 0 0 6px var(--q-green);
}

.status-text {
  font-size: 12px;
  color: var(--q-text-secondary);
}
</style>
