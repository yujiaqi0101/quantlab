/**
 * QuantLab Studio — Unified chart base option.
 *
 * Provides consistent visual style for all chart widgets.
 * Reads the current theme from <html> so dark/light switch seamlessly.
 */

export interface BaseTheme {
  bg: string
  text: string
  textMuted: string
  border: string
  grid: string
  tooltipBg: string
  accent: string
  positive: string
  negative: string
  warning: string
  isDark: boolean
}

function readTheme(): BaseTheme {
  if (typeof document === 'undefined') {
    return darkTheme()
  }
  return document.documentElement.classList.contains('light')
    ? lightTheme()
    : darkTheme()
}

function darkTheme(): BaseTheme {
  return {
    bg: 'transparent',
    text: '#e6edf3',
    textMuted: '#484f58',
    border: '#1b2332',
    grid: '#1b2332',
    tooltipBg: '#161b22',
    accent: '#58a6ff',
    positive: '#3fb950',
    negative: '#f85149',
    warning: '#d29922',
    isDark: true,
  }
}

function lightTheme(): BaseTheme {
  return {
    bg: 'transparent',
    text: '#1f2328',
    textMuted: '#656d76',
    border: '#d0d7de',
    grid: '#d8dee4',
    tooltipBg: '#ffffff',
    accent: '#0969da',
    positive: '#1a7f37',
    negative: '#cf222e',
    warning: '#9a6700',
    isDark: false,
  }
}

const MONO = 'SF Mono, Cascadia Code, Fira Code, JetBrains Mono, ui-monospace, monospace'

/**
 * Returns a base option to spread into any chart's option.
 * The theme is read at call time, so theme switches take effect on next render.
 */
export function buildBaseOption(): Record<string, any> {
  const t = readTheme()
  return {
    backgroundColor: t.bg,
    animation: false,
    textStyle: {
      color: t.text,
      fontFamily: MONO,
    },
    tooltip: {
      backgroundColor: t.tooltipBg,
      borderColor: t.border,
      textStyle: { color: t.text, fontSize: 12, fontFamily: MONO },
      axisPointer: {
        lineStyle: { color: t.border },
        crossStyle: { color: t.border },
      },
    },
    legend: {
      textStyle: { color: t.textMuted, fontSize: 11, fontFamily: MONO },
    },
  }
}

export function getTheme(): BaseTheme {
  return readTheme()
}

export const COLORS = {
  blue: '#58a6ff',
  green: '#3fb950',
  red: '#f85149',
  yellow: '#d29922',
  purple: '#bc8cff',
  orange: '#ff8c42',
  cyan: '#39c5cf',
}
