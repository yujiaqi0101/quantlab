import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  getExperiments,
  getExperiment,
  getEquityCurve,
  getTrades,
  type ExperimentInfo,
  type EquityData,
  type TradeInfo,
} from '@/api/experiment'

export const useExperimentStore = defineStore('experiment', () => {
  const items = ref<ExperimentInfo[]>([])
  const current = ref<ExperimentInfo | null>(null)
  const equity = ref<EquityData | null>(null)
  const trades = ref<TradeInfo[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function load(params?: {
    strategy?: string
    tag?: string
    sharpe_min?: number
    limit?: number
  }) {
    loading.value = true
    error.value = null
    try {
      items.value = await getExperiments(params)
    } catch (e: any) {
      error.value = e.message || 'Failed to load experiments'
      console.error('[ExperimentStore] load error:', e)
    } finally {
      loading.value = false
    }
  }

  async function loadDetail(id: string) {
    loading.value = true
    error.value = null
    equity.value = null
    trades.value = []
    try {
      const [detail, eq, tr] = await Promise.allSettled([
        getExperiment(id),
        getEquityCurve(id),
        getTrades(id),
      ])
      if (detail.status === 'fulfilled') current.value = detail.value
      if (eq.status === 'fulfilled') equity.value = eq.value
      if (tr.status === 'fulfilled') trades.value = tr.value
    } catch (e: any) {
      error.value = e.message || 'Failed to load experiment detail'
      console.error('[ExperimentStore] loadDetail error:', e)
    } finally {
      loading.value = false
    }
  }

  return {
    items,
    current,
    equity,
    trades,
    loading,
    error,
    load,
    loadDetail,
  }
})
