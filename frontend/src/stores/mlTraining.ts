import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * ML 训练预填充状态
 *
 * 用于 Model Arena → TrainingCenter 的联动：
 * Arena 横评选出最优模型后，调用 setPrefill 写入配置，
 * MLLab watch prefill.ready 切到 training tab，
 * TrainingCenter watch prefill.ready 填充表单并打开训练对话框，
 * 消费后调用 consume 重置 ready。
 */
export interface TrainingPrefill {
  dataset_id: string
  feature_set_id: string
  label_set_id: string
  model_type: string
  ready: boolean
}

export const useMlTrainingStore = defineStore('mlTraining', () => {
  const prefill = ref<TrainingPrefill>({
    dataset_id: '',
    feature_set_id: '',
    label_set_id: '',
    model_type: '',
    ready: false,
  })

  function setPrefill(data: Omit<TrainingPrefill, 'ready'>) {
    prefill.value = { ...data, ready: true }
  }

  function consume() {
    prefill.value.ready = false
  }

  return { prefill, setPrefill, consume }
})
