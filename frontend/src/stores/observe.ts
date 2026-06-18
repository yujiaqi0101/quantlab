import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  observeApi,
  type OverviewData,
  type Position,
  type Order,
  type TradesResponse,
  type RiskStatus,
  type StrategyHealth,
  type TimelineEntry,
  type JournalResponse,
} from '@/api/observe'

export const useObserveStore = defineStore('observe', () => {
  // State
  const overview = ref<OverviewData | null>(null)
  const positions = ref<Position[]>([])
  const orders = ref<Order[]>([])
  const tradesData = ref<TradesResponse | null>(null)
  const risk = ref<RiskStatus | null>(null)
  const healthList = ref<StrategyHealth[]>([])
  const timeline = ref<TimelineEntry[]>([])
  const journal = ref<JournalResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const totalPnl = computed(() => overview.value?.total_pnl ?? 0)
  const todayPnl = computed(() => overview.value?.today_pnl ?? 0)
  const activeStrategies = computed(() => overview.value?.active_strategies ?? 0)
  const nPositions = computed(() => overview.value?.n_positions ?? 0)
  const riskStatus = computed(() => risk.value?.status ?? 'NORMAL')
  const isCritical = computed(() => riskStatus.value === 'CRITICAL')
  const isWarning = computed(() => riskStatus.value === 'WARNING')

  // Actions
  async function fetchOverview() {
    try {
      overview.value = await observeApi.getOverview()
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function fetchPositions() {
    try {
      positions.value = await observeApi.getPositions()
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function fetchOrders(params?: { status?: string; hours?: number }) {
    try {
      orders.value = await observeApi.getOrders(params)
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function fetchTrades(hours: number = 24) {
    try {
      tradesData.value = await observeApi.getTrades(hours)
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function fetchRisk() {
    try {
      risk.value = await observeApi.getRisk()
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function fetchHealth() {
    try {
      healthList.value = await observeApi.getHealth()
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function fetchTimeline(params?: { limit?: number; category?: string }) {
    try {
      timeline.value = await observeApi.getTimeline(params)
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function fetchJournal(params?: { category?: string; strategy?: string; limit?: number }) {
    try {
      journal.value = await observeApi.getJournal(params)
    } catch (e: any) {
      error.value = e.message
    }
  }

  async function fetchAll() {
    loading.value = true
    error.value = null
    try {
      await Promise.all([
        fetchOverview(),
        fetchPositions(),
        fetchRisk(),
        fetchHealth(),
      ])
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    overview,
    positions,
    orders,
    tradesData,
    risk,
    healthList,
    timeline,
    journal,
    loading,
    error,
    // Getters
    totalPnl,
    todayPnl,
    activeStrategies,
    nPositions,
    riskStatus,
    isCritical,
    isWarning,
    // Actions
    fetchOverview,
    fetchPositions,
    fetchOrders,
    fetchTrades,
    fetchRisk,
    fetchHealth,
    fetchTimeline,
    fetchJournal,
    fetchAll,
  }
})
