<template>
  <div class="observe-orders">
    <div class="page-header">
      <div>
        <h1 class="page-title">订单 Orders</h1>
        <span class="page-subtitle">订单管理 Order management</span>
      </div>
      <div class="header-actions">
        <el-select v-model="filter.status" placeholder="状态 Status" clearable size="small" style="width: 140px">
          <el-option label="Open" value="SUBMITTED" />
          <el-option label="Filled" value="FILLED" />
          <el-option label="Cancelled" value="CANCELLED" />
          <el-option label="Rejected" value="REJECTED" />
        </el-select>
        <el-select v-model="filter.hours" size="small" style="width: 140px">
          <el-option label="最近24小时 Last 24h" :value="24" />
          <el-option label="最近7天 Last 7 days" :value="168" />
          <el-option label="最近30天 Last 30 days" :value="720" />
        </el-select>
        <el-button :icon="Refresh" @click="refresh" :loading="loading">刷新</el-button>
      </div>
    </div>

    <el-card shadow="hover">
      <el-table :data="orders" stripe>
        <el-table-column prop="order_id" label="订单ID" min-width="140" />
        <el-table-column prop="symbol" label="Symbol" width="120" />
        <el-table-column prop="side" label="方向" width="80">
          <template #default="{ row }">
            <el-tag :type="row.side === 'BUY' ? 'success' : 'danger'" size="small">
              {{ row.side }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="100" />
        <el-table-column prop="qty" label="数量" width="100">
          <template #default="{ row }">{{ formatNum(row.qty) }}</template>
        </el-table-column>
        <el-table-column prop="price" label="价格" width="100">
          <template #default="{ row }">{{ row.price ? formatNum(row.price) : '-' }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" min-width="180" />
      </el-table>

      <el-empty v-if="!loading && orders.length === 0" description="暂无订单" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, watch } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { useObserveStore } from '@/stores/observe'

const store = useObserveStore()
const orders = computed(() => store.orders)
const loading = computed(() => store.loading)

const filter = reactive({
  status: '' as string,
  hours: 24,
})

function formatNum(v?: number): string {
  if (v == null) return '-'
  return v.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
}

function statusType(status: string): 'success' | 'warning' | 'danger' | 'info' {
  switch (status) {
    case 'FILLED': return 'success'
    case 'SUBMITTED':
    case 'ACCEPTED':
    case 'PARTIAL': return 'warning'
    case 'CANCELLED':
    case 'REJECTED': return 'danger'
    default: return 'info'
  }
}

async function refresh() {
  await store.fetchOrders({
    status: filter.status || undefined,
    hours: filter.hours,
  })
}

watch(filter, refresh, { deep: true })

onMounted(() => {
  refresh()
})
</script>

<style scoped>
.observe-orders { padding: 20px; }
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.page-title { margin: 0; font-size: 24px; font-weight: 700; }
.page-subtitle { color: var(--q-text-muted); font-size: 13px; }
</style>
