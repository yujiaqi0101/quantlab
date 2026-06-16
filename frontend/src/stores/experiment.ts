import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  getExperiments,
  getExperiment,
  getEquityCurve,
  getTrades,
  setExperimentStatus,
  setExperimentFavorite,
  setExperimentFolder,
  setExperimentNote,
  setExperimentParent,
  listFolders,
  getExperimentAnalytics,
  getExperimentLineage,
  getExperimentActivity,
  getGlobalTimeline,
  type ExperimentInfo,
  type EquityData,
  type TradeInfo,
  type AnalyticsData,
  type LineageData,
  type ActivityItem,
} from '@/api/experiment'

export const useExperimentStore = defineStore('experiment', () => {
  const items = ref<ExperimentInfo[]>([])
  const current = ref<ExperimentInfo | null>(null)
  const equity = ref<EquityData | null>(null)
  const trades = ref<TradeInfo[]>([])
  const analytics = ref<AnalyticsData | null>(null)
  const lineage = ref<LineageData | null>(null)
  const activity = ref<ActivityItem[]>([])
  const timeline = ref<ActivityItem[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const folders = ref<string[]>([])

  async function load(params?: {
    strategy?: string
    tag?: string
    sharpe_min?: number
    limit?: number
    status?: string
    favorite?: boolean
    folder?: string
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
    analytics.value = null
    lineage.value = null
    activity.value = []
    try {
      const [detail, eq, tr, an, lin, act] = await Promise.allSettled([
        getExperiment(id),
        getEquityCurve(id),
        getTrades(id),
        getExperimentAnalytics(id),
        getExperimentLineage(id),
        getExperimentActivity(id),
      ])
      if (detail.status === 'fulfilled') current.value = detail.value
      if (eq.status === 'fulfilled') equity.value = eq.value
      if (tr.status === 'fulfilled') trades.value = tr.value
      if (an.status === 'fulfilled') analytics.value = an.value
      if (lin.status === 'fulfilled') lineage.value = lin.value
      if (act.status === 'fulfilled') activity.value = act.value
    } catch (e: any) {
      error.value = e.message || 'Failed to load experiment detail'
      console.error('[ExperimentStore] loadDetail error:', e)
    } finally {
      loading.value = false
    }
  }

  async function updateStatus(id: string, status: string) {
    await setExperimentStatus(id, status)
    const item = items.value.find((e) => e.id === id)
    if (item) item.status = status as any
    if (current.value?.id === id) current.value.status = status as any
  }

  async function updateFavorite(id: string, favorite: boolean) {
    await setExperimentFavorite(id, favorite)
    const item = items.value.find((e) => e.id === id)
    if (item) item.favorite = favorite ? 1 : 0
    if (current.value?.id === id) current.value.favorite = favorite ? 1 : 0
  }

  async function updateFolder(id: string, folder: string) {
    await setExperimentFolder(id, folder)
    const item = items.value.find((e) => e.id === id)
    if (item) item.folder = folder
    if (current.value?.id === id) current.value.folder = folder
  }

  async function updateNote(id: string, note: string) {
    await setExperimentNote(id, note)
    if (current.value?.id === id) current.value.note = note
    const item = items.value.find((e) => e.id === id)
    if (item) item.note = note
  }

  async function updateParent(id: string, parentId: string) {
    await setExperimentParent(id, parentId)
    if (current.value?.id === id) current.value.parent_id = parentId
    // 重新加载 lineage
    try {
      lineage.value = await getExperimentLineage(id)
    } catch { /* ignore */ }
  }

  async function loadFolders() {
    try {
      folders.value = await listFolders()
    } catch {
      folders.value = []
    }
  }

  async function loadTimeline(limit: number = 50) {
    try {
      timeline.value = await getGlobalTimeline(limit)
    } catch {
      timeline.value = []
    }
  }

  return {
    items,
    current,
    equity,
    trades,
    analytics,
    lineage,
    activity,
    timeline,
    loading,
    error,
    folders,
    load,
    loadDetail,
    updateStatus,
    updateFavorite,
    updateFolder,
    updateNote,
    updateParent,
    loadFolders,
    loadTimeline,
  }
})
