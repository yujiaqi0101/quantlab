<template>
  <div class="sidebar-logo" @click="$router.push('/')">
    <span class="logo-icon">Q</span>
    <span v-if="!collapsed" class="logo-text">QuantLab</span>
  </div>

  <el-menu
    :default-active="activeRoute"
    :collapse="collapsed"
    :collapse-transition="false"
    router
    class="sidebar-menu"
    background-color="#0d1117"
    text-color="#8b949e"
    active-text-color="#58a6ff"
  >
    <el-menu-item index="/strategies">
      <el-icon><Odometer /></el-icon>
      <template #title>Strategies</template>
    </el-menu-item>

    <el-menu-item index="/datasets">
      <el-icon><Coin /></el-icon>
      <template #title>Datasets</template>
    </el-menu-item>

    <el-menu-item index="/backtests">
      <el-icon><DataLine /></el-icon>
      <template #title>Backtests</template>
    </el-menu-item>

    <el-menu-item index="/experiments">
      <el-icon><Files /></el-icon>
      <template #title>Experiments</template>
    </el-menu-item>
  </el-menu>

  <div class="sidebar-toggle" @click="appStore.toggleSidebar()">
    <el-icon :size="16">
      <Fold v-if="!collapsed" />
      <Expand v-else />
    </el-icon>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { Odometer, Coin, DataLine, Files, Fold, Expand } from '@element-plus/icons-vue'

const route = useRoute()
const appStore = useAppStore()

const activeRoute = computed(() => route.path)
const collapsed = computed(() => appStore.sidebarCollapsed)
</script>

<style scoped>
.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 20px;
  cursor: pointer;
  border-bottom: 1px solid #1b2332;
  height: 52px;
  box-sizing: border-box;
}

.logo-icon {
  width: 28px;
  height: 28px;
  background: linear-gradient(135deg, #58a6ff 0%, #1f6feb 100%);
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 16px;
  color: #fff;
  flex-shrink: 0;
}

.logo-text {
  font-size: 16px;
  font-weight: 700;
  color: #e6edf3;
  letter-spacing: -0.3px;
  white-space: nowrap;
}

.sidebar-menu {
  border-right: none !important;
  padding-top: 8px;
}

.sidebar-menu .el-menu-item {
  height: 44px;
  line-height: 44px;
  margin: 2px 8px;
  border-radius: 6px;
}

.sidebar-menu .el-menu-item:hover {
  background-color: #161b22 !important;
}

.sidebar-menu .el-menu-item.is-active {
  background-color: #1f2937 !important;
  color: #58a6ff !important;
}

.sidebar-toggle {
  position: absolute;
  bottom: 16px;
  left: 0;
  right: 0;
  display: flex;
  justify-content: center;
  padding: 12px;
  cursor: pointer;
  color: #484f58;
  transition: color 0.2s;
}

.sidebar-toggle:hover {
  color: #8b949e;
}
</style>
