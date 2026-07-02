<template>
  <div class="orders-workspace">
    <template v-if="!store.currentSessionId">
      <el-empty description="请先创建会话" :image-size="120" />
    </template>
    <template v-else>
      <!-- 工具栏 -->
      <div class="toolbar">
        <div class="toolbar-left">
          <span class="page-title">Orders</span>
          <span class="page-sub">订单全生命周期 Order Lifecycle</span>
        </div>
        <div class="toolbar-right">
          <span class="session-tag">SID: {{ store.currentSessionId }}</span>
          <el-button :icon="Refresh" size="small" @click="store.fetchOrders()" :loading="loading">刷新</el-button>
          <el-button type="primary" size="small" :icon="Plus" @click="openOrderDialog">手动下单</el-button>
        </div>
      </div>

      <!-- 状态分组 Tabs -->
      <el-tabs v-model="activeTab" class="status-tabs">
        <el-tab-pane label="All" name="all" />
        <el-tab-pane label="Submitted" name="SUBMITTED" />
        <el-tab-pane label="Filled" name="FILLED" />
        <el-tab-pane label="Cancelled" name="CANCELLED" />
        <el-tab-pane label="Rejected" name="REJECTED" />
      </el-tabs>

      <!-- 订单表格 -->
      <el-card class="table-card" shadow="never">
        <el-table :data="filteredOrders" stripe size="small" height="100%" v-loading="loading" empty-text="暂无订单">
          <el-table-column label="Time" width="170">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="Order ID" min-width="150" show-overflow-tooltip>
            <template #default="{ row }">{{ row.order_id }}</template>
          </el-table-column>
          <el-table-column label="Symbol" width="120">
            <template #default="{ row }"><span class="symbol-text">{{ row.symbol }}</span></template>
          </el-table-column>
          <el-table-column label="Side" width="80">
            <template #default="{ row }">
              <el-tag :type="sideType(row.side)" size="small" effect="dark">{{ row.side }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="Type" width="90">
            <template #default="{ row }">{{ row.order_type }}</template>
          </el-table-column>
          <el-table-column label="Qty" width="100" align="right">
            <template #default="{ row }"><span class="num">{{ formatNum(row.quantity) }}</span></template>
          </el-table-column>
          <el-table-column label="Price" width="100" align="right">
            <template #default="{ row }"><span class="num">{{ row.price != null ? formatNum(row.price) : '-' }}</span></template>
          </el-table-column>
          <el-table-column label="Filled Qty" width="100" align="right">
            <template #default="{ row }"><span class="num">{{ formatNum(row.filled_qty) }}</span></template>
          </el-table-column>
          <el-table-column label="Filled Price" width="110" align="right">
            <template #default="{ row }"><span class="num">{{ row.filled_price ? formatNum(row.filled_price) : '-' }}</span></template>
          </el-table-column>
          <el-table-column label="Status" width="110">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" size="small" effect="dark">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="90" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="canCancel(row.status)"
                type="danger"
                size="small"
                text
                @click="handleCancel(row.order_id)"
              >撤单</el-button>
              <span v-else class="muted">-</span>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 手动下单对话框 -->
      <el-dialog v-model="dialogVisible" title="手动下单 Manual Order" width="480px">
        <el-form :model="orderForm" label-width="100px" size="default">
          <el-form-item label="Symbol">
            <el-input v-model="orderForm.symbol" placeholder="如 000001.SZ" />
          </el-form-item>
          <el-form-item label="Side">
            <el-radio-group v-model="orderForm.side">
              <el-radio value="buy">买入 Buy</el-radio>
              <el-radio value="sell">卖出 Sell</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="Quantity">
            <el-input-number v-model="orderForm.quantity" :min="1" :step="100" />
          </el-form-item>
          <el-form-item label="Order Type">
            <el-radio-group v-model="orderForm.order_type">
              <el-radio value="market">市价 Market</el-radio>
              <el-radio value="limit">限价 Limit</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="orderForm.order_type === 'limit'" label="Price">
            <el-input-number v-model="orderForm.price" :min="0" :step="0.01" :precision="2" />
          </el-form-item>
          <el-form-item label="Reason">
            <el-input v-model="orderForm.reason" type="textarea" :rows="2" placeholder="备注（可选）" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="submitOrder">提交订单</el-button>
        </template>
      </el-dialog>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { useTradingStore } from '@/stores/trading'
import type { ManualOrderRequest } from '@/api/trading'

const store = useTradingStore()
const loading = computed(() => store.loading)

const activeTab = ref('all')
const dialogVisible = ref(false)
const submitting = ref(false)

const orderForm = ref<ManualOrderRequest>({
  symbol: '',
  side: 'buy',
  quantity: 100,
  order_type: 'limit',
  price: null,
  reason: '',
})

// ---- 过滤 ----
const filteredOrders = computed(() => {
  if (activeTab.value === 'all') return store.orders
  return store.orders.filter(o => o.status === activeTab.value)
})

// ---- 格式化 ----
function formatNum(v: number | undefined | null): string {
  if (v == null) return '-'
  return Number(v).toLocaleString('en-US', { maximumFractionDigits: 4 })
}
function formatTime(t: string | undefined): string {
  if (!t) return '-'
  return t.replace('T', ' ').slice(0, 19)
}

// ---- Tag 类型 ----
function sideType(side: string): 'success' | 'danger' | 'info' {
  const s = (side || '').toUpperCase()
  if (s === 'BUY') return 'success'
  if (s === 'SELL') return 'danger'
  return 'info'
}
function statusType(status: string): 'success' | 'warning' | 'danger' | 'info' {
  switch ((status || '').toUpperCase()) {
    case 'FILLED': return 'success'
    case 'SUBMITTED':
    case 'ACCEPTED':
    case 'PARTIAL': return 'warning'
    case 'CANCELLED': return 'info'
    case 'REJECTED': return 'danger'
    default: return 'info'
  }
}
function canCancel(status: string): boolean {
  return ['SUBMITTED', 'ACCEPTED', 'PARTIAL'].includes((status || '').toUpperCase())
}

// ---- 操作 ----
async function handleCancel(orderId: string) {
  try {
    await ElMessageBox.confirm('确定要撤销该订单吗？', '撤单确认', {
      type: 'warning',
      confirmButtonText: '撤单',
      cancelButtonText: '取消',
    })
    await store.cancelOrder(orderId)
  } catch {}
}

function openOrderDialog() {
  orderForm.value = {
    symbol: '', side: 'buy', quantity: 100,
    order_type: 'limit', price: null, reason: '',
  }
  dialogVisible.value = true
}

async function submitOrder() {
  if (!orderForm.value.symbol.trim()) {
    orderForm.value.symbol = ''
    return
  }
  submitting.value = true
  try {
    const req: ManualOrderRequest = {
      symbol: orderForm.value.symbol.trim(),
      side: orderForm.value.side,
      quantity: orderForm.value.quantity,
      order_type: orderForm.value.order_type,
      price: orderForm.value.order_type === 'limit' ? orderForm.value.price : null,
      reason: orderForm.value.reason || undefined,
    }
    await store.manualOrder(req)
    dialogVisible.value = false
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  store.fetchOrders()
})
</script>

<style scoped>
.orders-workspace {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 12px;
  font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', 'JetBrains Mono', ui-monospace, monospace;
}

/* 工具栏 */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-shrink: 0;
}
.toolbar-left {
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.page-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--q-text-primary, #e6edf3);
}
.page-sub {
  font-size: 11px;
  color: var(--q-text-muted, #8b949e);
}
.session-tag {
  font-size: 11px;
  color: var(--q-text-muted, #8b949e);
  background: var(--q-bg-tertiary, #161b22);
  border: 1px solid var(--q-border, #21262d);
  padding: 4px 10px;
  border-radius: 4px;
}

/* Tabs 暗色 */
.status-tabs {
  flex-shrink: 0;
}
:deep(.el-tabs__nav-wrap::after) {
  background-color: var(--q-border, #21262d);
}
:deep(.el-tabs__item) {
  color: var(--q-text-secondary, #8b949e);
  font-size: 12px;
  font-family: 'SF Mono', 'Cascadia Code', monospace;
}
:deep(.el-tabs__item:hover) {
  color: var(--q-text-primary, #e6edf3);
}
:deep(.el-tabs__item.is-active) {
  color: var(--q-accent, #58a6ff);
}
:deep(.el-tabs__active-bar) {
  background-color: var(--q-accent, #58a6ff);
}

/* 表格卡片 */
.table-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--q-bg-secondary, #0d1117);
  border: 1px solid var(--q-border, #21262d);
  border-radius: 6px;
  overflow: hidden;
}
.table-card :deep(.el-card__body) {
  flex: 1;
  padding: 0;
  overflow: hidden;
}
:deep(.el-table) {
  background: transparent;
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: var(--q-bg-tertiary, #161b22);
  --el-table-border-color: var(--q-border, #21262d);
  --el-table-header-text-color: var(--q-text-secondary, #8b949e);
  --el-table-text-color: var(--q-text-primary, #e6edf3);
  --el-table-row-hover-bg-color: rgba(88, 166, 255, 0.06);
}
:deep(.el-table th.el-table__cell) {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* 单元格 */
.symbol-text {
  font-weight: 600;
  color: var(--q-text-primary, #e6edf3);
}
.num {
  font-variant-numeric: tabular-nums;
  font-feature-settings: 'tnum';
}
.muted {
  color: var(--q-text-muted, #8b949e);
}
</style>
