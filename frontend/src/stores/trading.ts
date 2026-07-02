/**
 * Trading Studio Store
 *
 * 管理交易会话、Mode 切换、当前 Workspace 和数据缓存。
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  tradingApi,
  type TradingMode,
  type TradingSession,
  type CreateSessionRequest,
  type OverviewData,
  type OrderItem,
  type PositionItem,
  type ManualOrderRequest,
  type WorkspaceName,
} from '@/api/trading'
import { ElMessage } from 'element-plus'

export const useTradingStore = defineStore('trading', () => {
  // ---- State ----
  const mode = ref<TradingMode>('paper')
  const sessions = ref<TradingSession[]>([])
  const currentSessionId = ref<string>('')
  const currentWorkspace = ref<WorkspaceName>('overview')
  const overview = ref<OverviewData | null>(null)
  const sessionStatus = ref<TradingSession | null>(null)
  const orders = ref<OrderItem[]>([])
  const positions = ref<PositionItem[]>([])
  const loading = ref(false)
  let pollTimer: ReturnType<typeof setInterval> | null = null

  // ---- Getters ----
  const currentSession = computed(() =>
    sessions.value.find(s => s.sid === currentSessionId.value) || null
  )
  const hasActiveSession = computed(() => !!currentSessionId.value)

  // ---- Actions ----
  async function fetchSessions(modeFilter?: TradingMode) {
    try {
      const res = await tradingApi.listSessions(modeFilter)
      sessions.value = res.sessions || []
      // 自动选中第一个活跃会话
      if (!currentSessionId.value && sessions.value.length > 0) {
        const active = sessions.value.find(s => s.is_active) || sessions.value[0]
        currentSessionId.value = active.sid
      }
    } catch (e: any) {
      console.error('fetchSessions error', e)
    }
  }

  async function createSession(req: CreateSessionRequest) {
    try {
      const sess = await tradingApi.createSession(req)
      sessions.value.unshift(sess)
      currentSessionId.value = sess.sid
      mode.value = req.mode
      await startSession(sess.sid)
      ElMessage.success(`会话已创建: ${sess.sid}`)
      return sess
    } catch (e: any) {
      ElMessage.error('创建会话失败: ' + (e?.response?.data?.detail || e.message))
      throw e
    }
  }

  function switchMode(m: TradingMode) {
    mode.value = m
  }

  async function startSession(sid: string) {
    try {
      const s = await tradingApi.startSession(sid)
      await fetchSessions()
      return s
    } catch (e: any) {
      ElMessage.error('启动会话失败: ' + (e?.response?.data?.detail || e.message))
    }
  }

  async function pauseSession(sid: string) {
    try {
      await tradingApi.pauseSession(sid)
      await fetchSessions()
      ElMessage.success('会话已暂停')
    } catch (e: any) {
      ElMessage.error('暂停失败: ' + e.message)
    }
  }

  async function resumeSession(sid: string) {
    try {
      await tradingApi.resumeSession(sid)
      await fetchSessions()
      ElMessage.success('会话已恢复')
    } catch (e: any) {
      ElMessage.error('恢复失败: ' + e.message)
    }
  }

  async function stopSession(sid: string) {
    try {
      await tradingApi.stopSession(sid)
      await fetchSessions()
      ElMessage.success('会话已停止')
    } catch (e: any) {
      ElMessage.error('停止失败: ' + e.message)
    }
  }

  async function deleteSession(sid: string) {
    try {
      await tradingApi.deleteSession(sid)
      sessions.value = sessions.value.filter(s => s.sid !== sid)
      if (currentSessionId.value === sid) currentSessionId.value = ''
      ElMessage.success('会话已删除')
    } catch (e: any) {
      ElMessage.error('删除失败: ' + e.message)
    }
  }

  async function fetchOverview(sid?: string) {
    const id = sid || currentSessionId.value
    if (!id) return
    try {
      overview.value = await tradingApi.getOverview(id)
    } catch (e) {
      console.error('fetchOverview error', e)
    }
  }

  async function fetchStatus(sid?: string) {
    const id = sid || currentSessionId.value
    if (!id) return
    try {
      sessionStatus.value = await tradingApi.getSessionStatus(id)
    } catch (e) {
      console.error('fetchStatus error', e)
    }
  }

  async function fetchOrders(sid?: string, status?: string) {
    const id = sid || currentSessionId.value
    if (!id) return
    try {
      const res = await tradingApi.getOrders(id, status)
      orders.value = res.orders || []
    } catch (e) {
      console.error('fetchOrders error', e)
    }
  }

  async function fetchPositions(sid?: string) {
    const id = sid || currentSessionId.value
    if (!id) return
    try {
      const res = await tradingApi.getPositions(id)
      positions.value = res.positions || []
    } catch (e) {
      console.error('fetchPositions error', e)
    }
  }

  async function manualOrder(req: ManualOrderRequest) {
    const id = currentSessionId.value
    if (!id) {
      ElMessage.warning('请先创建会话')
      return
    }
    try {
      await tradingApi.manualOrder(id, req)
      ElMessage.success('下单成功')
      await Promise.all([fetchOverview(), fetchOrders(), fetchPositions()])
    } catch (e: any) {
      ElMessage.error('下单失败: ' + (e?.response?.data?.detail || e.message))
    }
  }

  async function cancelOrder(orderId: string) {
    const id = currentSessionId.value
    if (!id) return
    try {
      await tradingApi.cancelOrder(id, orderId)
      ElMessage.success('撤单成功')
      await fetchOrders()
    } catch (e: any) {
      ElMessage.error('撤单失败: ' + e.message)
    }
  }

  async function killSwitch() {
    const id = currentSessionId.value
    if (!id) return
    try {
      await tradingApi.killSwitch(id)
      ElMessage.warning('Kill Switch 已触发')
      await fetchSessions()
    } catch (e: any) {
      ElMessage.error('Kill Switch 失败: ' + e.message)
    }
  }

  function startPolling(intervalMs = 5000) {
    stopPolling()
    pollTimer = setInterval(async () => {
      if (currentSessionId.value) {
        await Promise.all([fetchOverview(), fetchStatus()])
      }
    }, intervalMs)
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  return {
    // state
    mode, sessions, currentSessionId, currentWorkspace,
    overview, sessionStatus, orders, positions, loading,
    // getters
    currentSession, hasActiveSession,
    // actions
    fetchSessions, createSession, switchMode,
    startSession, pauseSession, resumeSession, stopSession, deleteSession,
    fetchOverview, fetchStatus, fetchOrders, fetchPositions,
    manualOrder, cancelOrder, killSwitch,
    startPolling, stopPolling,
  }
})
