<template>
  <div class="ml-lab">
    <!-- 顶部 Pipeline 流程导航 -->
    <div class="pipeline-banner">
      <div class="pipeline-step" :class="{ active: activeStage === 'dataset' }" @click="activeStage = 'dataset'">
        <span class="step-num">1</span>
        <span class="step-name">Dataset Registry</span>
      </div>
      <div class="pipeline-arrow">→</div>
      <div class="pipeline-step" :class="{ active: activeStage === 'feature' }" @click="activeStage = 'feature'">
        <span class="step-num">2</span>
        <span class="step-name">Feature Registry</span>
      </div>
      <div class="pipeline-arrow">→</div>
      <div class="pipeline-step" :class="{ active: activeStage === 'label' }" @click="activeStage = 'label'">
        <span class="step-num">3</span>
        <span class="step-name">Label Registry</span>
      </div>
      <div class="pipeline-arrow">→</div>
      <div class="pipeline-step" :class="{ active: activeStage === 'training' }" @click="activeStage = 'training'">
        <span class="step-num">4</span>
        <span class="step-name">Training Center</span>
      </div>
      <div class="pipeline-arrow">→</div>
      <div class="pipeline-step highlight" :class="{ active: activeStage === 'validation' }" @click="activeStage = 'validation'">
        <span class="step-num">5</span>
        <span class="step-name">★ Validation Center</span>
      </div>
      <div class="pipeline-arrow">→</div>
      <div class="pipeline-step" :class="{ active: activeStage === 'registry' }" @click="activeStage = 'registry'">
        <span class="step-num">6</span>
        <span class="step-name">Model Registry</span>
      </div>
      <div class="pipeline-arrow">→</div>
      <div class="pipeline-step" :class="{ active: activeStage === 'strategy' }" @click="activeStage = 'strategy'">
        <span class="step-num">7</span>
        <span class="step-name">Strategy Builder</span>
      </div>
    </div>

    <!-- 阶段内容 -->
    <el-tabs v-model="activeSubTab" type="border-card">
      <!-- Stage 1: Dataset Registry -->
      <template v-if="activeStage === 'dataset'">
        <el-tab-pane label="数据集 Datasets" name="datasets" lazy>
          <DatasetCenter />
        </el-tab-pane>
      </template>

      <!-- Stage 2: Feature Registry -->
      <template v-else-if="activeStage === 'feature'">
        <el-tab-pane label="特征 Features" name="features" lazy>
          <FeatureLab />
        </el-tab-pane>
        <el-tab-pane label="特征集 Feature Sets" name="feature-sets" lazy>
          <FeatureSets />
        </el-tab-pane>
        <el-tab-pane label="特征诊断 Diagnostics" name="feature-diagnostics" lazy>
          <FeatureDiagnostics />
        </el-tab-pane>
        <el-tab-pane label="特征分析 Analysis" name="analysis" lazy>
          <FeatureAnalysis />
        </el-tab-pane>
        <el-tab-pane label="特征重要性 Importance" name="importance" lazy>
          <FeatureImportance />
        </el-tab-pane>
      </template>

      <!-- Stage 3: Label Registry -->
      <template v-else-if="activeStage === 'label'">
        <el-tab-pane label="标签 Labels" name="labels" lazy>
          <LabelLab />
        </el-tab-pane>
        <el-tab-pane label="标签集 Label Sets" name="label-sets" lazy>
          <LabelSets />
        </el-tab-pane>
        <el-tab-pane label="标签诊断 Diagnostics" name="label-diagnostics" lazy>
          <LabelDiagnostics />
        </el-tab-pane>
      </template>

      <!-- Stage 4: Training Center -->
      <template v-else-if="activeStage === 'training'">
        <el-tab-pane label="训练任务 Training Jobs" name="training" lazy>
          <TrainingCenter />
        </el-tab-pane>
        <el-tab-pane label="实验 Experiments" name="experiments" lazy>
          <Experiments />
        </el-tab-pane>
        <el-tab-pane label="超参搜索 Hyperparameter Search" name="search" lazy>
          <HyperparameterSearch />
        </el-tab-pane>
      </template>

      <!-- Stage 5: Validation Center (Quality Control) -->
      <template v-else-if="activeStage === 'validation'">
        <el-tab-pane label="★ 验证流水线 Validation Pipeline" name="validation" lazy>
          <ValidationCenter />
        </el-tab-pane>
        <el-tab-pane label="泄漏检测 Leakage Detector" name="leakage" lazy>
          <LeakageDetector />
        </el-tab-pane>
      </template>

      <!-- Stage 6: Model Registry -->
      <template v-else-if="activeStage === 'registry'">
        <el-tab-pane label="★ 资产浏览器 Asset Explorer" name="explorer" lazy>
          <AssetExplorer />
        </el-tab-pane>
        <el-tab-pane label="模型仓库 Model Registry" name="registry" lazy>
          <ModelRegistry />
        </el-tab-pane>
        <el-tab-pane label="模型竞技场 Model Arena" name="arena" lazy>
          <ModelArena />
        </el-tab-pane>
      </template>

      <!-- Stage 7: Strategy Builder -->
      <template v-else-if="activeStage === 'strategy'">
        <el-tab-pane label="策略构建 Strategy Builder" name="strategy" lazy>
          <StrategyBuilder />
        </el-tab-pane>
      </template>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import DatasetCenter from './panels/DatasetCenter.vue'
import FeatureLab from './panels/FeatureLab.vue'
import FeatureSets from './panels/FeatureSets.vue'
import LabelLab from './panels/LabelLab.vue'
import LabelSets from './panels/LabelSets.vue'
import FeatureDiagnostics from './panels/FeatureDiagnostics.vue'
import LabelDiagnostics from './panels/LabelDiagnostics.vue'
import FeatureAnalysis from './panels/FeatureAnalysis.vue'
import FeatureImportance from './panels/FeatureImportance.vue'
import TrainingCenter from './panels/TrainingCenter.vue'
import Experiments from './panels/Experiments.vue'
import HyperparameterSearch from './panels/HyperparameterSearch.vue'
import ValidationCenter from './panels/ValidationCenter.vue'
import ModelArena from './panels/ModelArena.vue'
import LeakageDetector from './panels/LeakageDetector.vue'
import ModelRegistry from './panels/ModelRegistry.vue'
import StrategyBuilder from './panels/StrategyBuilder.vue'
import AssetExplorer from './panels/AssetExplorer.vue'

const activeStage = ref<'dataset' | 'feature' | 'label' | 'training' | 'validation' | 'registry' | 'strategy'>('dataset')
const activeSubTab = ref('datasets')

// 切换 stage 时自动选中第一个 sub-tab
const stageFirstTab: Record<string, string> = {
  dataset: 'datasets',
  feature: 'features',
  label: 'labels',
  training: 'training',
  validation: 'validation',
  registry: 'explorer',
  strategy: 'strategy',
}

watch(activeStage, (newStage) => {
  activeSubTab.value = stageFirstTab[newStage] || 'datasets'
})
</script>

<style scoped>
.ml-lab {
  padding: 16px;
}

.pipeline-banner {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 16px;
  margin-bottom: 16px;
  background: linear-gradient(135deg, #f5f7fa 0%, #e8f1ff 100%);
  border: 1px solid #d9e6ff;
  border-radius: 8px;
}

.pipeline-step {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  background: #fff;
  border: 1px solid #e0e0e0;
  font-size: 13px;
  color: #606266;
}

.pipeline-step:hover {
  border-color: #409eff;
  color: #409eff;
}

.pipeline-step.active {
  background: #409eff;
  border-color: #409eff;
  color: #fff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
}

.pipeline-step.highlight {
  border-color: #e6a23c;
  color: #e6a23c;
  font-weight: bold;
}

.pipeline-step.highlight.active {
  background: #e6a23c;
  border-color: #e6a23c;
  color: #fff;
}

.step-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.08);
  font-size: 12px;
  font-weight: bold;
}

.pipeline-step.active .step-num {
  background: rgba(255, 255, 255, 0.3);
}

.pipeline-arrow {
  color: #c0c4cc;
  font-size: 14px;
}
</style>
