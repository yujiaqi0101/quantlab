<template>
  <div class="asset-explorer">
    <!-- 顶部摘要 -->
    <el-row :gutter="12" class="summary-row">
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-value">{{ summary.total_assets }}</div>
            <div class="stat-label">总资产</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-value">{{ summary.n_families }}</div>
            <div class="stat-label">资产族</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-value champion-color">{{ summary.n_champions }}</div>
            <div class="stat-label">Champions</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div class="stat-card">
            <div class="stat-value">{{ summary.n_lineage_edges }}</div>
            <div class="stat-label">血缘关系</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="12" class="main-row">
      <!-- 左侧：资产树 -->
      <el-col :span="6">
        <el-card shadow="hover" class="tree-card">
          <template #header>
            <div class="card-header">
              <span>资产浏览器</span>
              <el-input
                v-model="searchQuery"
                placeholder="搜索..."
                size="small"
                clearable
                style="width: 140px"
                @keyup.enter="handleSearch"
              />
            </div>
          </template>

          <el-radio-group v-model="filterType" size="small" @change="loadAssets">
            <el-radio-button label="">全部</el-radio-button>
            <el-radio-button label="DATASET">数据</el-radio-button>
            <el-radio-button label="FEATURE_SET">特征</el-radio-button>
            <el-radio-button label="LABEL_SET">标签</el-radio-button>
            <el-radio-button label="MODEL_PACKAGE">模型</el-radio-button>
            <el-radio-button label="STRATEGY_PACKAGE">策略</el-radio-button>
          </el-radio-group>

          <el-divider />

          <el-tree
            :data="assetTree"
            :props="treeProps"
            node-key="asset_id"
            highlight-current
            default-expand-all
            @node-click="handleNodeClick"
          >
            <template #default="{ data }">
              <span class="tree-node">
                <span class="node-icon" :class="typeColor(data.asset_type)">
                  {{ typeIcon(data.asset_type) }}
                </span>
                <span class="node-label">{{ data.name }}</span>
                <span class="node-version">v{{ data.version }}</span>
                <el-tag v-if="isChampion(data.asset_id)" type="warning" size="small" effect="dark">
                  ★
                </el-tag>
              </span>
            </template>
          </el-tree>
        </el-card>
      </el-col>

      <!-- 右侧：详情 -->
      <el-col :span="18">
        <el-card shadow="hover" v-loading="loading">
          <template v-if="selectedAsset">
            <el-tabs v-model="detailTab">
              <!-- Manifest -->
              <el-tab-pane label="Manifest" name="manifest">
                <el-descriptions :column="2" border>
                  <el-descriptions-item label="Asset ID">{{ selectedAsset.asset_id }}</el-descriptions-item>
                  <el-descriptions-item label="Name">{{ selectedAsset.name }}</el-descriptions-item>
                  <el-descriptions-item label="Family">{{ selectedAsset.family }}</el-descriptions-item>
                  <el-descriptions-item label="Version">{{ selectedAsset.version }}</el-descriptions-item>
                  <el-descriptions-item label="Type">{{ selectedAsset.asset_type }}</el-descriptions-item>
                  <el-descriptions-item label="Status">
                    <el-tag :type="statusTagType(selectedAsset.status)" size="small">
                      {{ selectedAsset.status }}
                    </el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="Created">{{ selectedAsset.created_at }}</el-descriptions-item>
                  <el-descriptions-item label="Hash">
                    <code>{{ selectedAsset.hash || '-' }}</code>
                  </el-descriptions-item>
                  <el-descriptions-item label="Tags" :span="2">
                    <el-tag v-for="t in selectedAsset.tags" :key="t" size="small" class="tag-item">
                      {{ t }}
                    </el-tag>
                    <span v-if="!selectedAsset.tags?.length">-</span>
                  </el-descriptions-item>
                  <el-descriptions-item label="Description" :span="2">
                    {{ selectedAsset.description || '-' }}
                  </el-descriptions-item>
                </el-descriptions>
              </el-tab-pane>

              <!-- Validation（仅 MODEL_PACKAGE） -->
              <el-tab-pane
                v-if="selectedAsset.asset_type === 'MODEL_PACKAGE'"
                label="Validation"
                name="validation"
              >
                <el-descriptions :column="2" border>
                  <el-descriptions-item label="Validation Passed">
                    <el-tag :type="selectedAsset.validation_passed ? 'success' : 'danger'" size="small">
                      {{ selectedAsset.validation_passed ? 'PASS' : 'FAIL' }}
                    </el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="Score">
                    {{ selectedAsset.validation_score ?? '-' }}
                  </el-descriptions-item>
                  <el-descriptions-item label="Grade">
                    <el-tag :type="gradeTagType(selectedAsset.validation_grade)" size="small">
                      {{ selectedAsset.validation_grade || '-' }}
                    </el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="Algorithm">
                    {{ selectedAsset.algorithm || '-' }}
                  </el-descriptions-item>
                  <el-descriptions-item label="Dataset">{{ selectedAsset.dataset_id || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="FeatureSet">{{ selectedAsset.feature_set_id || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="LabelSet">{{ selectedAsset.label_set_id || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="Model Type">{{ selectedAsset.model_type || '-' }}</el-descriptions-item>
                </el-descriptions>
              </el-tab-pane>

              <!-- Metrics -->
              <el-tab-pane label="Metrics" name="metrics">
                <pre class="json-view">{{ JSON.stringify(selectedAsset.metrics || selectedAsset.params || {}, null, 2) }}</pre>
              </el-tab-pane>

              <!-- Lineage -->
              <el-tab-pane label="Lineage" name="lineage">
                <div v-if="lineage">
                  <h4>祖先 (Ancestors)</h4>
                  <el-tag
                    v-for="a in lineage.ancestors"
                    :key="a.asset_id"
                    class="lineage-tag"
                    :type="ancestorTagType(a.asset_type)"
                    size="small"
                    @click="selectAsset(a.asset_id)"
                  >
                    {{ typeIcon(a.asset_type) }} {{ a.name }} v{{ a.version }}
                  </el-tag>

                  <h4>后代 (Descendants)</h4>
                  <el-tag
                    v-for="d in lineage.descendants"
                    :key="d.asset_id"
                    class="lineage-tag"
                    :type="descendantTagType(d.asset_type)"
                    size="small"
                    @click="selectAsset(d.asset_id)"
                  >
                    {{ typeIcon(d.asset_type) }} {{ d.name }} v{{ d.version }}
                  </el-tag>

                  <h4>依赖链 (Dependency Chain)</h4>
                  <div class="chain-view">
                    <template v-for="(node, idx) in lineage.dependency_chain" :key="node.asset_id">
                      <el-tag size="small" @click="selectAsset(node.asset_id)" class="chain-node">
                        {{ typeIcon(node.asset_type) }} {{ node.name }}
                      </el-tag>
                      <span v-if="idx < lineage.dependency_chain.length - 1" class="chain-arrow">→</span>
                    </template>
                  </div>
                </div>
                <el-empty v-else description="无血缘数据" />
              </el-tab-pane>
            </el-tabs>
          </template>

          <el-empty v-else description="请从左侧选择资产" />
        </el-card>
      </el-col>
    </el-row>

    <!-- Champions 面板 -->
    <el-card shadow="hover" class="champions-card">
      <template #header>
        <span>★ Champions（每 Family 一个）</span>
      </template>
      <el-table :data="championList" stripe size="small">
        <el-table-column prop="family" label="Family" width="200" />
        <el-table-column prop="name" label="Champion" />
        <el-table-column prop="version" label="Version" width="100" />
        <el-table-column prop="validation_score" label="Score" width="100">
          <template #default="{ row }">
            <el-tag :type="row.validation_score >= 80 ? 'success' : 'warning'" size="small">
              {{ row.validation_score ?? '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="validation_grade" label="Grade" width="80" />
        <el-table-column prop="promoted_at" label="Promoted At" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { assetApi, type AssetSummary, type AssetIndex, type AssetDetail, type AssetLineage } from '@/api/asset'
import { ElMessage } from 'element-plus'

const summary = ref<AssetSummary>({
  total_assets: 0,
  by_type: {},
  n_families: 0,
  n_champions: 0,
  n_lineage_edges: 0,
})

const assets = ref<AssetIndex[]>([])
const filterType = ref('')
const searchQuery = ref('')
const selectedAsset = ref<AssetDetail | null>(null)
const lineage = ref<AssetLineage | null>(null)
const detailTab = ref('manifest')
const loading = ref(false)
const champions = ref<Record<string, AssetIndex>>({})

const championIds = computed(() => new Set(Object.values(champions.value).map((a) => a.asset_id)))

const championList = computed(() =>
  Object.entries(champions.value).map(([family, asset]) => ({
    ...asset,
    family,
  })),
)

// 按 family 分组构建树
const assetTree = computed(() => {
  const filtered = assets.value.filter((a) => {
    if (filterType.value && a.asset_type !== filterType.value) return false
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase()
      return (
        a.name.toLowerCase().includes(q) ||
        a.family.toLowerCase().includes(q) ||
        a.tags?.some((t: string) => t.toLowerCase().includes(q))
      )
    }
    return true
  })

  // 按 family 分组
  const familyMap: Record<string, AssetIndex[]> = {}
  for (const a of filtered) {
    if (!familyMap[a.family]) familyMap[a.family] = []
    familyMap[a.family].push(a)
  }

  return Object.entries(familyMap).map(([family, items]) => ({
    asset_id: `family-${family}`,
    name: family,
    asset_type: 'FAMILY',
    version: '',
    children: items.sort((a, b) => b.version.localeCompare(a.version)),
  }))
})

const treeProps = { children: 'children', label: 'name' }

function typeIcon(t: string): string {
  const icons: Record<string, string> = {
    DATASET: '📊',
    FEATURE_SET: '🔧',
    LABEL_SET: '🏷️',
    MODEL_PACKAGE: '🤖',
    STRATEGY_PACKAGE: '⚡',
    RISK_PROFILE: '⚠️',
    DEPLOYMENT_PROFILE: '🚀',
    FAMILY: '📁',
  }
  return icons[t] || '📄'
}

function typeColor(t: string): string {
  const colors: Record<string, string> = {
    DATASET: 'type-dataset',
    FEATURE_SET: 'type-feature',
    LABEL_SET: 'type-label',
    MODEL_PACKAGE: 'type-model',
    STRATEGY_PACKAGE: 'type-strategy',
    FAMILY: 'type-family',
  }
  return colors[t] || ''
}

function statusTagType(s: string) {
  const map: Record<string, string> = {
    DRAFT: 'info',
    ACTIVE: 'success',
    ARCHIVED: 'warning',
    DEPRECATED: 'danger',
  }
  return map[s] || 'info'
}

function gradeTagType(g?: string) {
  if (!g) return 'info'
  if (g === 'A' || g === 'A+') return 'success'
  if (g === 'B') return 'primary'
  if (g === 'C') return 'warning'
  return 'danger'
}

function ancestorTagType(t: string) {
  return t === 'DATASET' ? 'primary' : t === 'FEATURE_SET' ? 'success' : 'info'
}

function descendantTagType(t: string) {
  return t === 'STRATEGY_PACKAGE' ? 'danger' : t === 'MODEL_PACKAGE' ? 'warning' : 'info'
}

function isChampion(assetId: string): boolean {
  return championIds.value.has(assetId)
}

async function loadSummary() {
  try {
    summary.value = await assetApi.getSummary()
  } catch (e) {
    ElMessage.error('加载摘要失败')
  }
}

async function loadAssets() {
  try {
    const resp = await assetApi.listAssets(
      filterType.value ? { asset_type: filterType.value as any } : undefined,
    )
    assets.value = resp.assets
  } catch (e) {
    ElMessage.error('加载资产失败')
  }
}

async function loadChampions() {
  try {
    const resp = await assetApi.getAllChampions()
    champions.value = resp.champions
  } catch (e) {
    // 忽略
  }
}

async function handleNodeClick(data: any) {
  if (data.asset_type === 'FAMILY') return
  await selectAsset(data.asset_id)
}

async function selectAsset(assetId: string) {
  loading.value = true
  try {
    selectedAsset.value = await assetApi.getAsset(assetId)
    detailTab.value = 'manifest'
    // 加载血缘
    try {
      lineage.value = await assetApi.getLineage(assetId)
    } catch {
      lineage.value = null
    }
  } catch (e) {
    ElMessage.error('加载资产详情失败')
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  // 触发 computed 重新计算
  assets.value = [...assets.value]
}

onMounted(async () => {
  await Promise.all([loadSummary(), loadAssets(), loadChampions()])
})
</script>

<style scoped>
.asset-explorer {
  padding: 16px;
}

.summary-row {
  margin-bottom: 12px;
}

.stat-card {
  text-align: center;
  padding: 8px 0;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #409eff;
}

.stat-value.champion-color {
  color: #e6a23c;
}

.stat-label {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.main-row {
  margin-bottom: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tree-card {
  height: 600px;
  overflow-y: auto;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 6px;
}

.node-icon {
  font-size: 14px;
}

.node-label {
  flex: 1;
}

.node-version {
  font-size: 11px;
  color: #909399;
}

.tag-item {
  margin-right: 4px;
}

.json-view {
  background: #f5f7fa;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  max-height: 400px;
  overflow-y: auto;
}

.lineage-tag {
  margin: 4px;
  cursor: pointer;
}

.chain-view {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.chain-node {
  cursor: pointer;
}

.chain-arrow {
  color: #c0c4cc;
}

.champions-card {
  margin-top: 12px;
}

.type-dataset { color: #409eff; }
.type-feature { color: #67c23a; }
.type-label { color: #e6a23c; }
.type-model { color: #f56c6c; }
.type-strategy { color: #9c27b0; }
.type-family { color: #909399; }
</style>
