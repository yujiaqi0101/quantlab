<template>
  <div class="leaderboard-page">
    <div class="lb-header">
      <div>
        <h1 class="lb-title">策略排行榜 Strategy Leaderboard</h1>
        <p class="lb-sub">按关键指标排名的顶级实验 Top performing experiments ranked by key metrics</p>
      </div>
      <div class="lb-actions">
        <el-select v-model="metric" class="metric-select" @change="onRefresh">
          <el-option label="夏普比率 Sharpe Ratio" value="sharpe" />
          <el-option label="总收益 Total Return" value="total_return" />
          <el-option label="最大回撤 Max Drawdown" value="max_drawdown" />
          <el-option label="胜率 Win Rate" value="win_rate" />
        </el-select>
        <el-select v-model="topN" class="top-select" @change="onRefresh">
          <el-option label="前10 Top 10" :value="10" />
          <el-option label="前20 Top 20" :value="20" />
          <el-option label="前50 Top 50" :value="50" />
        </el-select>
        <el-button :icon="Refresh" circle @click="onRefresh" :loading="loading" />
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading && !items.length" class="loading-state">
      <el-icon class="is-loading" :size="24"><Loading /></el-icon>
      <span>加载排行榜中 Loading leaderboard...</span>
    </div>

    <!-- Leaderboard Cards -->
    <div v-else class="lb-grid">
      <div
        v-for="item in items"
        :key="item.id"
        class="lb-card"
        :class="{ 'lb-card-top': item.rank <= 3 }"
        @click="router.push(`/experiments/${item.id}`)"
      >
        <div class="lb-card-rank">
          <span v-if="item.rank === 1" class="rank-gold">1</span>
          <span v-else-if="item.rank === 2" class="rank-silver">2</span>
          <span v-else-if="item.rank === 3" class="rank-bronze">3</span>
          <span v-else class="rank-num">{{ item.rank }}</span>
        </div>
        <div class="lb-card-body">
          <div class="lb-card-name">{{ item.name || item.id }}</div>
          <div class="lb-card-strategy">{{ item.strategy }}</div>
        </div>
        <div class="lb-card-metrics">
          <div class="lb-metric">
            <span class="lb-metric-label">收益 Return</span>
            <span :class="item.total_return >= 0 ? 'lb-positive' : 'lb-negative'">
              {{ item.total_return >= 0 ? '+' : '' }}{{ item.total_return?.toFixed(2) }}%
            </span>
          </div>
          <div class="lb-metric">
            <span class="lb-metric-label">夏普 Sharpe</span>
            <span class="lb-metric-value">{{ item.sharpe?.toFixed(3) }}</span>
          </div>
          <div class="lb-metric">
            <span class="lb-metric-label">MaxDD</span>
            <span class="lb-negative">{{ item.max_drawdown?.toFixed(2) }}%</span>
          </div>
        </div>
        <div class="lb-card-badges">
          <el-tag v-if="item.status === 'candidate'" type="warning" effect="dark" size="small">Candidate</el-tag>
          <el-tag v-if="item.status === 'production'" type="success" effect="dark" size="small">Production</el-tag>
          <span v-if="item.favorite === 1" class="fav-star">★</span>
        </div>
      </div>
    </div>

    <!-- Empty -->
    <div v-if="!loading && !items.length" class="empty-state">
      <p>No experiments found. Run some backtests first!</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getLeaderboard, type RankItem } from '@/api/experiment'
import { Refresh, Loading } from '@element-plus/icons-vue'

const router = useRouter()
const loading = ref(false)
const items = ref<RankItem[]>([])
const metric = ref('sharpe')
const topN = ref(20)

async function onRefresh() {
  loading.value = true
  try {
    items.value = await getLeaderboard(metric.value, topN.value)
  } catch (e) {
    console.error('[Leaderboard] load error:', e)
    items.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  onRefresh()
})
</script>

<style scoped>
.leaderboard-page {
  max-width: 1200px;
}

.lb-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.lb-title {
  font-size: 24px;
  font-weight: 700;
  color: #e6edf3;
  margin: 0 0 4px 0;
  letter-spacing: -0.5px;
}

.lb-sub {
  font-size: 14px;
  color: #484f58;
  margin: 0;
}

.lb-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.metric-select {
  width: 160px;
}

.metric-select :deep(.el-input__wrapper) {
  background: #161b22;
  border: 1px solid #1b2332;
  box-shadow: none;
}

.metric-select :deep(.el-input__inner) {
  color: #e6edf3;
}

.top-select {
  width: 110px;
}

.top-select :deep(.el-input__wrapper) {
  background: #161b22;
  border: 1px solid #1b2332;
  box-shadow: none;
}

.top-select :deep(.el-input__inner) {
  color: #e6edf3;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 0;
  color: #8b949e;
  font-size: 14px;
  gap: 12px;
}

.lb-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.lb-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 20px;
  background: #0d1117;
  border: 1px solid #1b2332;
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}

.lb-card:hover {
  border-color: #30363d;
  background: #161b22;
}

.lb-card-top {
  border-color: #1f2937;
}

.lb-card-rank {
  width: 36px;
  text-align: center;
  flex-shrink: 0;
}

.rank-gold {
  font-size: 20px;
  font-weight: 800;
  color: #e3b341;
}

.rank-silver {
  font-size: 20px;
  font-weight: 800;
  color: #8b949e;
}

.rank-bronze {
  font-size: 20px;
  font-weight: 800;
  color: #d2a8ff;
}

.rank-num {
  font-size: 16px;
  font-weight: 600;
  color: #484f58;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
}

.lb-card-body {
  flex: 1;
  min-width: 0;
}

.lb-card-name {
  font-weight: 600;
  color: #e6edf3;
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.lb-card-strategy {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 12px;
  color: #58a6ff;
  margin-top: 2px;
}

.lb-card-metrics {
  display: flex;
  gap: 24px;
  flex-shrink: 0;
}

.lb-metric {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.lb-metric-label {
  font-size: 10px;
  color: #484f58;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.lb-metric-value {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 14px;
  font-weight: 600;
  color: #c9d1d9;
}

.lb-positive {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 14px;
  font-weight: 600;
  color: #3fb950;
}

.lb-negative {
  font-family: 'SF Mono', 'Cascadia Code', monospace;
  font-size: 14px;
  font-weight: 600;
  color: #f85149;
}

.lb-card-badges {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.fav-star {
  color: #e3b341;
  font-size: 16px;
}
</style>
