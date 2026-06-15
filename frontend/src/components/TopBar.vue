<template>
  <div class="topbar">
    <div class="topbar-left">
      <span class="topbar-title">{{ route.meta.title || 'QuantLab Studio' }}</span>
      <span class="topbar-divider" />
      <span class="topbar-subtitle">Research Platform</span>
    </div>

    <div class="topbar-right">
      <div class="topbar-status">
        <span class="status-dot" />
        <span class="status-text">System Online</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()
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
  color: #e6edf3;
  letter-spacing: -0.2px;
}

.topbar-divider {
  width: 1px;
  height: 16px;
  background: #21262d;
}

.topbar-subtitle {
  font-size: 13px;
  color: #484f58;
  font-weight: 400;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.topbar-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: #0d1117;
  border: 1px solid #1b2332;
  border-radius: 4px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #3fb950;
  box-shadow: 0 0 6px #3fb950;
}

.status-text {
  font-size: 12px;
  color: #8b949e;
}
</style>
