import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  submitBacktest,
  getTask,
  type BacktestSubmitRequest,
  type BacktestResponse,
} from '@/api/backtest'

export const useBacktestStore = defineStore('backtest', () => {
  const running = ref(false)
  const taskId = ref<string | null>(null)
  const taskStatus = ref<string | null>(null)
  const taskProgress = ref(0)
  const experimentId = ref<string | null>(null)
  const error = ref<string | null>(null)
  const result = ref<BacktestResponse | null>(null)

  let _pollTimer: ReturnType<typeof setInterval> | null = null

  async function runBacktest(req: BacktestSubmitRequest) {
    running.value = true
    error.value = null
    result.value = null
    taskId.value = null
    taskStatus.value = 'PENDING'
    taskProgress.value = 0
    experimentId.value = null

    try {
      const resp = await submitBacktest(req)
      taskId.value = resp.task_id
      result.value = resp

      // If already completed (synchronous backtest)
      if (resp.status === 'SUCCESS') {
        taskStatus.value = 'SUCCESS'
        taskProgress.value = 100
        experimentId.value = resp.experiment_id || null
        running.value = false
        return resp
      }

      // Start polling
      startPolling(resp.task_id)
      return resp
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || 'Failed to submit backtest'
      running.value = false
      throw e
    }
  }

  function startPolling(tid: string) {
    stopPolling()
    _pollTimer = setInterval(async () => {
      try {
        const task = await getTask(tid)
        taskStatus.value = task.status
        taskProgress.value = task.progress || 0

        if (task.status === 'SUCCESS') {
          taskProgress.value = 100
          experimentId.value = task.result?.experiment_id || null
          result.value = task.result
          stopPolling()
          running.value = false
        } else if (task.status === 'FAILED') {
          error.value = task.error || 'Backtest failed'
          stopPolling()
          running.value = false
        }
      } catch {
        // Polling error, keep trying
      }
    }, 1500)
  }

  function stopPolling() {
    if (_pollTimer) {
      clearInterval(_pollTimer)
      _pollTimer = null
    }
  }

  function reset() {
    stopPolling()
    running.value = false
    taskId.value = null
    taskStatus.value = null
    taskProgress.value = 0
    experimentId.value = null
    error.value = null
    result.value = null
  }

  return {
    running,
    taskId,
    taskStatus,
    taskProgress,
    experimentId,
    error,
    result,
    runBacktest,
    reset,
    stopPolling,
  }
})
