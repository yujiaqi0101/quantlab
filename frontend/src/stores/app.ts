import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export type ThemeMode = 'dark' | 'light'

const THEME_KEY = 'quantlab.theme.v1'

function loadTheme(): ThemeMode {
  try {
    const raw = localStorage.getItem(THEME_KEY)
    if (raw === 'light' || raw === 'dark') return raw
  } catch {
    // ignore
  }
  return 'dark'
}

function applyTheme(theme: ThemeMode) {
  if (typeof document === 'undefined') return
  const html = document.documentElement
  if (theme === 'dark') {
    html.classList.add('dark')
    html.classList.remove('light')
  } else {
    html.classList.add('light')
    html.classList.remove('dark')
  }
}

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const theme = ref<ThemeMode>(loadTheme())

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function toggleTheme() {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
  }

  function setTheme(t: ThemeMode) {
    theme.value = t
  }

  // Apply theme on change and on init
  watch(
    theme,
    (t) => {
      applyTheme(t)
      try {
        localStorage.setItem(THEME_KEY, t)
      } catch {
        // ignore
      }
    },
    { immediate: true },
  )

  return {
    sidebarCollapsed,
    theme,
    toggleSidebar,
    toggleTheme,
    setTheme,
  }
})
