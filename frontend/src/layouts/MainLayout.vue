<template>
  <el-container class="studio-layout">
    <el-aside :width="sidebarCollapsed ? '64px' : '220px'" class="studio-aside">
      <SidebarMenu />
    </el-aside>

    <el-container class="studio-main-container">
      <el-header class="studio-header" height="52px">
        <TopBar />
      </el-header>

      <el-main class="studio-main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAppStore } from '@/stores/app'
import SidebarMenu from '@/components/SidebarMenu.vue'
import TopBar from '@/components/TopBar.vue'

const appStore = useAppStore()
const sidebarCollapsed = computed(() => appStore.sidebarCollapsed)
</script>

<style scoped>
.studio-layout {
  height: 100vh;
  overflow: hidden;
  background: #0a0e17;
}

.studio-aside {
  background: #0d1117;
  border-right: 1px solid #1b2332;
  transition: width 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.studio-main-container {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.studio-header {
  background: #0d1117;
  border-bottom: 1px solid #1b2332;
  padding: 0 20px;
  display: flex;
  align-items: center;
}

.studio-main {
  background: #0a0e17;
  overflow-y: auto;
  padding: 24px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
