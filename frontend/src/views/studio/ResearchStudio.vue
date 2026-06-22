<template>
  <div class="dashboard-page">
    <!-- Header -->
    <div class="dash-header">
      <div>
        <h1 class="dash-title">研究仪表盘 Research Dashboard</h1>
        <p class="dash-sub">研究一览 Your research at a glance</p>
      </div>
      <div class="dash-actions">
        <el-button type="primary" :icon="DataLine" @click="router.push('/backtests')">新建回测 New Backtest</el-button>
      </div>
    </div>

    <!-- Stats Row -->
    <div class="stats-row">
      <div class="stat-card">
        <span class="stat-value">{{ allExperiments.length }}</span>
        <span class="stat-label">总实验 Total Experiments</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{{ favorites.length }}</span>
        <span class="stat-label">收藏 Favorites</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{{ candidates.length }}</span>
        <span class="stat-label">候选 Candidates</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{{ productionCount }}</span>
        <span class="stat-label">生产 Production</span>
      </div>
    </div>

    <!-- Dashboard Sections -->
    <div class="dash-sections">
      <!-- Recent Experiments -->
      <div class="dash-section">
        <div class="section-header">
          <span class="section-title">最近实验 Recent Experiments</span>
          <el-button text size="small" @click="router.push('/experiments')">查看全部 View All</el-button>
        </div>
        <div class="section-body">
          <div v-if="recentExperiments.length === 0" class="section-empty">
            暂无实验，运行回测以开始 No experiments yet. Run a backtest to get started.
          </div>
          <div v-else class="exp-list">
            <div
              v-for="exp in recentExperiments"
              :key="exp.id"
              class="exp-item"
              @click="router.push(`/experiments/${exp.id}`)"
            >
              <div class="exp-item-left">
                <span
                  class="exp-fav"
                  :class="{ active: exp.favorite === 1 }"
                  @click.stop="toggleFav(exp)"
                >★</span>
                <div class="exp-item-info">
                  <span class="exp-item-name">{{ exp.name || exp.id }}</span>
                  <span class="exp-item-strategy">{{ exp.strategy }}</span>
                </div>
              </div>
              <div class="exp-item-metrics">
                <span :class="exp.total_return >= 0 ? 'metric-positive' : 'metric-negative'">
                  {{ exp.total_return >= 0 ? '+' : '' }}{{ exp.total_return?.toFixed(1) }}%
                </span>
                <span class="metric-sharpe">{{ exp.sharpe?.toFixed(2) }}</span>
              </div>
              <div class="exp-item-badges">
                <el-tag v-if="exp.status === 'candidate'" type="warning" effect="dark" size="small">候选 Candidate</el-tag>
                <el-tag v-if="exp.status === 'production'" type="success" effect="dark" size="small">生产 Production</el-tag>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Favorites -->
      <div v-if="favorites.length" class="dash-section">
        <div class="section-header">
          <span class="section-title">★ 收藏 Favorites</span>
        </div>
        <div class="section-body">
          <div class="exp-list">
            <div
              v-for="exp in favorites"
              :key="exp.id"
              class="exp-item"
              @click="router.push(`/experiments/${exp.id}`)"
            >
              <div class="exp-item-left">
                <div class="exp-item-info">
                  <span class="exp-item-name">{{ exp.name || exp.id }}</span>
                  <span class="exp-item-strategy">{{ exp.strategy }}</span>
                </div>
              </div>
              <div class="exp-item-metrics">
                <span :class="exp.total_return >= 0 ? 'metric-positive' : 'metric-negative'">
                  {{ exp.total_return >= 0 ? '+' : '' }}{{ exp.total_return?.toFixed(1) }}%
                </span>
                <span class="metric-sharpe">{{ exp.sharpe?.toFixed(2) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Candidates -->
      <div v-if="candidates.length" class="dash-section">
        <div class="section-header">
          <span class="section-title">候选 Candidates</span>
          <el-button
            v-if="candidates.length >= 2"
            text
            size="small"
            @click="router.push({ path: '/compare', query: { ids: candidates.map(c => c.id).join(',') } })"
          >全部对比 Compare All</el-button>
        </div>
        <div class="section-body">
          <div class="exp-list">
            <div
              v-for="exp in candidates"
              :key="exp.id"
              class="exp-item"
              @click="router.push(`/experiments/${exp.id}`)"
            >
              <div class="exp-item-left">
                <div class="exp-item-info">
                  <span class="exp-item-name">{{ exp.name || exp.id }}</span>
                  <span class="exp-item-strategy">{{ exp.strategy }}</span>
                </div>
              </div>
              <div class="exp-item-metrics">
                <span :class="exp.total_return >= 0 ? 'metric-positive' : 'metric-negative'">
                  {{ exp.total_return >= 0 ? '+' : '' }}{{ exp.total_return?.toFixed(1) }}%
                </span>
                <span class="metric-sharpe">{{ exp.sharpe?.toFixed(2) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Leaderboard Preview -->
      <div class="dash-section">
        <div class="section-header">
          <span class="section-title">夏普排行 Top by Sharpe</span>
          <el-button text size="small" @click="router.push('/leaderboard')">完整排行 Full Leaderboard</el-button>
        </div>
        <div class="section-body">
          <div v-if="topBySharpe.length === 0" class="section-empty">
            暂无夏普数据 No experiments with Sharpe data yet.
          </div>
          <div v-else class="lb-preview">
            <div
              v-for="(item, i) in topBySharpe"
              :key="item.id"
              class="lb-row"
              @click="router.push(`/experiments/${item.id}`)"
            >
              <span class="lb-rank" :class="{ gold: i === 0, silver: i === 1, bronze: i === 2 }">{{ i + 1 }}</span>
              <span class="lb-name">{{ item.name || item.id }}</span>
              <span class="lb-strategy">{{ item.strategy }}</span>
              <span class="lb-sharpe">{{ item.sharpe?.toFixed(3) }}</span>
              <span :class="item.total_return >= 0 ? 'lb-positive' : 'lb-negative'">
                {{ item.total_return >= 0 ? '+' : '' }}{{ item.total_return?.toFixed(1) }}%
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Research Timeline -->
      <div class="dash-section">
        <div class="section-header">
          <span class="section-title">研究时间线 Research Timeline</span>
        </div>
        <div class="section-body">
          <div v-if="store.timeline.length === 0" class="section-empty">
            暂无活动 No activity yet. Interact with experiments to build your timeline.
          </div>
          <div v-else class="timeline-list">
            <div v-for="item in store.timeline" :key="item.id" class="timeline-item" @click="item.experiment_id && router.push(`/experiments/${item.experiment_id}`)">
              <div class="timeline-dot" :class="timelineDotClass(item.action)"></div>
              <div class="timeline-content">
                <div class="timeline-main">
                  <span class="timeline-action">{{ formatAction(item.action) }}</span>
                  <span v-if="item.name" class="timeline-exp-name">{{ item.name }}</span>
                  <span v-if="item.strategy" class="timeline-exp-strategy">{{ item.strategy }}</span>
                </div>
                <div v-if="item.detail" class="timeline-detail">{{ item.detail }}</div>
                <div class="timeline-time">{{ formatTimelineDate(item.created_at) }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useExperimentStore } from '@/stores/experiment'
import { getLeaderboard, type RankItem, type ExperimentInfo } from '@/api/experiment'
import { DataLine } from '@element-plus/icons-vue'

const router = useRouter()
const store = useExperimentStore()

const topBySharpe = ref<RankItem[]>([])

const allExperiments = computed(() => store.items)

const recentExperiments = computed(() => {
  return [...store.items]
    .sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''))
    .slice(0, 8)
})

const favorites = computed(() => {
  return store.items.filter((e) => e.favorite === 1)
})

const candidates = computed(() => {
  return store.items.filter((e) => e.status === 'candidate')
})

const productionCount = computed(() => {
  return store.items.filter((e) => e.status === 'production').length
})

async function toggleFav(exp: ExperimentInfo) {
  await store.updateFavorite(exp.id, exp.favorite !== 1)
}

// Timeline helpers
function timelineDotClass(action: string): string {
  if (action === 'status_changed') return 'status'
  if (action === 'note_updated') return 'note'
  if (action === 'parent_set') return 'lineage'
  return ''
}

function formatAction(action: string): string {
  const map: Record<string, string> = {
    status_changed: '状态变更 Status Changed',
    note_updated: '笔记更新 Note Updated',
    parent_set: '谱系设置 Lineage Set',
  }
  return map[action] || action
}

function formatTimelineDate(dt: string): string {
  if (!dt) return ''
  return dt.replace('T', ' ').substring(0, 16)
}

onMounted(async () => {
  await store.load({ limit: 200 })
  await store.loadTimeline(30)
  try {
    topBySharpe.value = await getLeaderboard('sharpe', 5)
  } catch {
    topBySharpe.value = []
  }
})
</script>

<style scoped>
.dashboard-page {
  max-width: 1200px;
}

.dash-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.dash-title {
  font-size: 24px;
  font-weight: 700;
  color: #e6edf3;
  margin: 0 0 4px 0;
  letter-spacing: -0.5px;
}

.dash-sub {
  font-size: 14px;
  color: #484f58;
  margin: 0;
}

/* Stats Row */
.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}

.stat-card {
  background: #0d1117;
  border: 1px solid #1b2332;
  border-radius: 8px;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-value {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 28px;
  font-weight: 700;
  color: #e6edf3;
}

.stat-label {
  font-size: 12px;
  color: #484f58;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Sections */
.dash-sections {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.dash-section {
  background: #0d1117;
  border: 1px solid #1b2332;
  border-radius: 8px;
  padding: 16px 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #8b949e;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.section-empty {
  color: #484f58;
  font-size: 13px;
  padding: 16px 0;
}

/* Exp List */
.exp-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.exp-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.exp-item:hover {
  background: #161b22;
}

.exp-item-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.exp-fav {
  color: #484f58;
  font-size: 14px;
  cursor: pointer;
  user-select: none;
  transition: color 0.2s;
}

.exp-fav.active {
  color: #e3b341;
}

.exp-fav:hover {
  color: #e3b341;
}

.exp-item-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.exp-item-name {
  font-weight: 500;
  color: #e6edf3;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.exp-item-strategy {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 11px;
  color: #58a6ff;
}

.exp-item-metrics {
  display: flex;
  gap: 16px;
  flex-shrink: 0;
}

.metric-positive {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  color: #3fb950;
  font-weight: 600;
}

.metric-negative {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  color: #f85149;
  font-weight: 600;
}

.metric-sharpe {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  color: #c9d1d9;
}

.exp-item-badges {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

/* Leaderboard Preview */
.lb-preview {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.lb-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.lb-row:hover {
  background: #161b22;
}

.lb-rank {
  width: 24px;
  text-align: center;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 14px;
  font-weight: 700;
  color: #484f58;
  flex-shrink: 0;
}

.lb-rank.gold { color: #e3b341; }
.lb-rank.silver { color: #8b949e; }
.lb-rank.bronze { color: #d2a8ff; }

.lb-name {
  font-weight: 500;
  color: #e6edf3;
  font-size: 13px;
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.lb-strategy {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 12px;
  color: #58a6ff;
  width: 120px;
  flex-shrink: 0;
}

.lb-sharpe {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  color: #c9d1d9;
  width: 60px;
  text-align: right;
  flex-shrink: 0;
}

.lb-positive {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  color: #3fb950;
  width: 70px;
  text-align: right;
  flex-shrink: 0;
}

.lb-negative {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 13px;
  color: #f85149;
  width: 70px;
  text-align: right;
  flex-shrink: 0;
}

/* Timeline */
.timeline-list {
  display: flex;
  flex-direction: column;
  gap: 0;
  position: relative;
  padding-left: 20px;
}

.timeline-list::before {
  content: '';
  position: absolute;
  left: 7px;
  top: 8px;
  bottom: 8px;
  width: 1px;
  background: #1b2332;
}

.timeline-item {
  display: flex;
  gap: 12px;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
  position: relative;
}

.timeline-item:hover {
  background: #161b22;
}

.timeline-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #484f58;
  flex-shrink: 0;
  margin-top: 5px;
  position: absolute;
  left: -17px;
}

.timeline-dot.status {
  background: #d29922;
}

.timeline-dot.note {
  background: #58a6ff;
}

.timeline-dot.lineage {
  background: #bc8cff;
}

.timeline-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.timeline-main {
  display: flex;
  align-items: center;
  gap: 8px;
}

.timeline-action {
  font-size: 12px;
  font-weight: 500;
  color: #58a6ff;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.timeline-exp-name {
  font-size: 13px;
  font-weight: 500;
  color: #e6edf3;
}

.timeline-exp-strategy {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 11px;
  color: #8b949e;
}

.timeline-detail {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 11px;
  color: #8b949e;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.timeline-time {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 11px;
  color: #484f58;
}
</style>
