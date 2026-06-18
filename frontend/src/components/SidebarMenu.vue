<template>
  <div class="sidebar-logo" @click="$router.push('/studio')">
    <span class="logo-icon">Q</span>
    <span v-if="!collapsed" class="logo-text">QuantLab</span>
  </div>

  <el-menu
    :default-active="activeRoute"
    :collapse="collapsed"
    :collapse-transition="false"
    router
    class="sidebar-menu"
    :background-color="menuBg"
    :text-color="menuText"
    active-text-color="#58a6ff"
  >
    <el-menu-item index="/studio">
      <el-icon><DataLine /></el-icon>
      <template #title>Dashboard</template>
    </el-menu-item>

    <el-menu-item index="/experiments">
      <el-icon><Files /></el-icon>
      <template #title>Experiments</template>
    </el-menu-item>

    <el-menu-item index="/factors">
      <el-icon><Histogram /></el-icon>
      <template #title>Factors</template>
    </el-menu-item>

    <el-menu-item index="/signals">
      <el-icon><Switch /></el-icon>
      <template #title>Signals</template>
    </el-menu-item>

    <el-menu-item index="/research">
      <el-icon><Cpu /></el-icon>
      <template #title>Research Lab</template>
    </el-menu-item>

    <el-menu-item index="/ml-lab">
      <el-icon><Cpu /></el-icon>
      <template #title>ML Lab</template>
    </el-menu-item>

    <el-menu-item index="/production">
      <el-icon><Monitor /></el-icon>
      <template #title>Production</template>
    </el-menu-item>

    <el-menu-item index="/fidelity">
      <el-icon><Aim /></el-icon>
      <template #title>Fidelity</template>
    </el-menu-item>

    <el-menu-item index="/alpha-aware">
      <el-icon><Connection /></el-icon>
      <template #title>Alpha-Aware</template>
    </el-menu-item>

    <el-sub-menu index="/observe">
      <template #title>
        <el-icon><View /></el-icon>
        <span>Observe</span>
      </template>
      <el-menu-item index="/observe/overview">
        <el-icon><DataLine /></el-icon>
        <template #title>Overview</template>
      </el-menu-item>
      <el-menu-item index="/observe/positions">
        <el-icon><Wallet /></el-icon>
        <template #title>Positions</template>
      </el-menu-item>
      <el-menu-item index="/observe/orders">
        <el-icon><List /></el-icon>
        <template #title>Orders</template>
      </el-menu-item>
      <el-menu-item index="/observe/trades">
        <el-icon><Tickets /></el-icon>
        <template #title>Trades</template>
      </el-menu-item>
      <el-menu-item index="/observe/risk">
        <el-icon><Warning /></el-icon>
        <template #title>Risk</template>
      </el-menu-item>
      <el-menu-item index="/observe/health">
        <el-icon><Bell /></el-icon>
        <template #title>Health</template>
      </el-menu-item>
      <el-menu-item index="/observe/timeline">
        <el-icon><Timer /></el-icon>
        <template #title>Timeline</template>
      </el-menu-item>
      <el-menu-item index="/observe/replay">
        <el-icon><VideoPlay /></el-icon>
        <template #title>Replay</template>
      </el-menu-item>
      <el-menu-item index="/observe/analysis">
        <el-icon><Aim /></el-icon>
        <template #title>Root Cause</template>
      </el-menu-item>
      <el-menu-item index="/observe/performance">
        <el-icon><TrendCharts /></el-icon>
        <template #title>Performance</template>
      </el-menu-item>
      <el-menu-item index="/observe/journal">
        <el-icon><Notebook /></el-icon>
        <template #title>Journal</template>
      </el-menu-item>
    </el-sub-menu>

    <el-sub-menu index="/live">
      <template #title>
        <el-icon><VideoCamera /></el-icon>
        <span>Live Studio</span>
      </template>
      <el-menu-item index="/live">
        <el-icon><DataLine /></el-icon>
        <template #title>Strategies</template>
      </el-menu-item>
    </el-sub-menu>

    <el-menu-item index="/compare">
      <el-icon><TrendCharts /></el-icon>
      <template #title>Compare</template>
    </el-menu-item>

    <el-menu-item index="/leaderboard">
      <el-icon><Trophy /></el-icon>
      <template #title>Leaderboard</template>
    </el-menu-item>

    <el-menu-item index="/strategies">
      <el-icon><Odometer /></el-icon>
      <template #title>Strategies</template>
    </el-menu-item>

    <el-menu-item index="/strategy-builder">
      <el-icon><SetUp /></el-icon>
      <template #title>Builder</template>
    </el-menu-item>

    <el-menu-item index="/datasets">
      <el-icon><Coin /></el-icon>
      <template #title>Datasets</template>
    </el-menu-item>

    <el-menu-item index="/backtests">
      <el-icon><DataAnalysis /></el-icon>
      <template #title>Backtest</template>
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
import { Odometer, Coin, DataLine, Files, Fold, Expand, TrendCharts, Trophy, Histogram, Switch, Cpu, SetUp, Monitor, Aim, DataAnalysis, View, Wallet, List, Tickets, Warning, Bell, Timer, VideoPlay, Notebook, VideoCamera } from '@element-plus/icons-vue'

const route = useRoute()
const appStore = useAppStore()

const activeRoute = computed(() => {
  if (route.path === '/' || route.path === '/studio') return '/studio'
  if (route.path.startsWith('/experiments')) return '/experiments'
  if (route.path.startsWith('/factors')) return '/factors'
  if (route.path.startsWith('/signals')) return '/signals'
  if (route.path.startsWith('/research')) return '/research'
  if (route.path.startsWith('/ml-lab')) return '/ml-lab'
  if (route.path.startsWith('/production')) return '/production'
  if (route.path.startsWith('/fidelity')) return '/fidelity'
  if (route.path.startsWith('/alpha-aware')) return '/alpha-aware'
  if (route.path.startsWith('/observe')) return '/observe/overview'
  if (route.path.startsWith('/live')) return '/live'
  if (route.path.startsWith('/strategy-builder')) return '/strategy-builder'
  if (route.path.startsWith('/backtests')) return '/backtests'
  return route.path
})
const collapsed = computed(() => appStore.sidebarCollapsed)

const menuBg = computed(() => (appStore.theme === 'dark' ? '#0d1117' : '#ffffff'))
const menuText = computed(() => (appStore.theme === 'dark' ? '#8b949e' : '#656d76'))
</script>

<style scoped>
.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 20px;
  cursor: pointer;
  border-bottom: 1px solid var(--q-border);
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
  color: var(--q-text-primary);
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
  background-color: var(--q-bg-tertiary) !important;
}

.sidebar-menu .el-menu-item.is-active {
  background-color: #1f2937 !important;
  color: #58a6ff !important;
}

html.light .sidebar-menu .el-menu-item.is-active {
  background-color: rgba(9, 105, 218, 0.1) !important;
  color: var(--q-accent) !important;
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
  color: var(--q-text-muted);
  transition: color 0.2s;
}

.sidebar-toggle:hover {
  color: var(--q-text-secondary);
}
</style>
