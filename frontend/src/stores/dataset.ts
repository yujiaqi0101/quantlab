import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getDatasets, getDataset, getDatasetPreview, type DatasetInfo, type PreviewData } from '@/api/dataset'

export const useDatasetStore = defineStore('dataset', () => {
  const items = ref<DatasetInfo[]>([])
  const current = ref<DatasetInfo | null>(null)
  const preview = ref<PreviewData | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function load(q?: string, tag?: string) {
    loading.value = true
    error.value = null
    try {
      items.value = await getDatasets(q, tag)
    } catch (e: any) {
      error.value = e.message || 'Failed to load datasets'
      console.error('[DatasetStore] load error:', e)
    } finally {
      loading.value = false
    }
  }

  async function loadDetail(id: string) {
    loading.value = true
    error.value = null
    try {
      const [detail, previewData] = await Promise.all([
        getDataset(id),
        getDatasetPreview(id, 100),
      ])
      current.value = detail
      preview.value = previewData
    } catch (e: any) {
      error.value = e.message || 'Failed to load dataset detail'
      console.error('[DatasetStore] loadDetail error:', e)
    } finally {
      loading.value = false
    }
  }

  return {
    items,
    current,
    preview,
    loading,
    error,
    load,
    loadDetail,
  }
})
