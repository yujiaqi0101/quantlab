/**
 * QuantLab Studio — Workspace Engine.
 *
 * Holds the active workspace preset and the widget configuration.
 * v1 uses fixed layouts (no drag-and-drop).
 * Presets are stored in `localStorage` and can be switched at runtime.
 */

import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

export type WidgetType = 'metrics' | 'equity' | 'trades' | 'dataset' | 'strategy'

export interface WidgetConfig {
  id: string
  type: WidgetType
  title: string
  x: number
  y: number
  w: number
  h: number
}

export interface WorkspacePreset {
  id: string
  name: string
  description: string
  layout: WidgetConfig[]
}

const STORAGE_KEY = 'quantlab.workspace.v1'

/* ─── Built-in Presets ─────────────────────────────────────────── */

const researchPreset: WorkspacePreset = {
  id: 'research',
  name: 'Research',
  description: 'Equity curve, metrics and trades — full research view',
  layout: [
    { id: 'metrics', type: 'metrics', title: 'Metrics', x: 0, y: 0, w: 8, h: 2 },
    { id: 'equity', type: 'equity', title: 'Equity Curve', x: 0, y: 2, w: 12, h: 5 },
    { id: 'trades', type: 'trades', title: 'Trades', x: 0, y: 7, w: 12, h: 5 },
  ],
}

const analysisPreset: WorkspacePreset = {
  id: 'analysis',
  name: 'Analysis',
  description: 'Side-by-side metrics and equity for quick inspection',
  layout: [
    { id: 'equity', type: 'equity', title: 'Equity Curve', x: 0, y: 0, w: 8, h: 6 },
    { id: 'metrics', type: 'metrics', title: 'Metrics', x: 8, y: 0, w: 4, h: 6 },
  ],
}

const defaultPreset: WorkspacePreset = {
  id: 'default',
  name: 'Default',
  description: 'Compact metrics-only view',
  layout: [
    { id: 'metrics', type: 'metrics', title: 'Metrics', x: 0, y: 0, w: 12, h: 4 },
    { id: 'equity', type: 'equity', title: 'Equity Curve', x: 0, y: 4, w: 12, h: 5 },
  ],
}

const builtInPresets: WorkspacePreset[] = [defaultPreset, researchPreset, analysisPreset]

/* ─── Store ─────────────────────────────────────────────────────── */

function loadActiveId(): string {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (parsed?.activeId) return parsed.activeId
    }
  } catch {
    // ignore
  }
  return 'research'
}

function saveActiveId(id: string) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ activeId: id }))
  } catch {
    // ignore
  }
}

export const useWorkspaceStore = defineStore('workspace', () => {
  const activeId = ref<string>(loadActiveId())
  const activePreset = computed<WorkspacePreset>(() => {
    return builtInPresets.find((p) => p.id === activeId.value) || researchPreset
  })

  const presets = computed<WorkspacePreset[]>(() => builtInPresets)

  const widgets = computed<WidgetConfig[]>(() => activePreset.value.layout)

  function setActive(id: string) {
    const exists = builtInPresets.find((p) => p.id === id)
    if (exists) {
      activeId.value = id
      saveActiveId(id)
    }
  }

  // Persist on change
  watch(activeId, (v) => saveActiveId(v))

  return {
    activeId,
    activePreset,
    presets,
    widgets,
    setActive,
  }
})
