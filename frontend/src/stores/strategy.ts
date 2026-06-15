import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getStrategies, getStrategy, type StrategyInfo } from '@/api/strategy'

export const useStrategyStore = defineStore('strategy', () => {
  const items = ref<StrategyInfo[]>([])
  const current = ref<StrategyInfo | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function load(q?: string, tags?: string) {
    loading.value = true
    error.value = null
    try {
      items.value = await getStrategies(q, tags)
    } catch (e: any) {
      error.value = e.message || 'Failed to load strategies'
      console.error('[StrategyStore] load error:', e)
    } finally {
      loading.value = false
    }
  }

  async function loadDetail(id: string) {
    loading.value = true
    error.value = null
    try {
      current.value = await getStrategy(id)
    } catch (e: any) {
      error.value = e.message || 'Failed to load strategy detail'
      console.error('[StrategyStore] loadDetail error:', e)
    } finally {
      loading.value = false
    }
  }

  return {
    items,
    current,
    loading,
    error,
    load,
    loadDetail,
  }
})
