<template>
  <div class="ml-lab">
    <!-- 顶部导航 -->
    <div class="ml-tabs">
      <el-tabs v-model="activeTab" type="card">
        <el-tab-pane label="数据集 Datasets" name="datasets">
          <DatasetCenter />
        </el-tab-pane>
        <el-tab-pane label="特征 Features" name="features">
          <FeatureLab />
        </el-tab-pane>
        <el-tab-pane label="特征集 Feature Sets" name="feature-sets">
          <FeatureSets />
        </el-tab-pane>
        <el-tab-pane label="标签 Labels" name="labels">
          <LabelLab />
        </el-tab-pane>
        <el-tab-pane label="标签集 Label Sets" name="label-sets">
          <LabelSets />
        </el-tab-pane>
        <el-tab-pane label="特征诊断 Feature Diagnostics" name="feature-diagnostics">
          <FeatureDiagnostics />
        </el-tab-pane>
        <el-tab-pane label="标签诊断 Label Diagnostics" name="label-diagnostics">
          <LabelDiagnostics />
        </el-tab-pane>
        <el-tab-pane label="特征分析 Feature Analysis" name="analysis">
          <FeatureAnalysis />
        </el-tab-pane>
        <el-tab-pane label="特征重要性 Feature Importance" name="importance">
          <FeatureImportance />
        </el-tab-pane>
        <el-tab-pane label="训练任务 Training Jobs" name="training">
          <TrainingCenter />
        </el-tab-pane>
        <el-tab-pane label="实验 Experiments" name="experiments">
          <Experiments />
        </el-tab-pane>
        <el-tab-pane label="超参搜索 Hyperparameter Search" name="search">
          <HyperparameterSearch />
        </el-tab-pane>
        <el-tab-pane label="验证 Validation" name="validation">
          <ValidationCenter />
        </el-tab-pane>
        <el-tab-pane label="模型竞技场 Model Arena" name="arena">
          <ModelArena />
        </el-tab-pane>
        <el-tab-pane label="泄漏检测 Leakage Detector" name="leakage">
          <LeakageDetector />
        </el-tab-pane>
        <el-tab-pane label="模型仓库 Model Registry" name="registry">
          <ModelRegistry />
        </el-tab-pane>
        <el-tab-pane label="策略构建 Strategy Builder" name="strategy">
          <StrategyBuilder />
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
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

const activeTab = ref('datasets')
</script>

<style scoped>
.ml-lab {
  padding: 16px;
}

.ml-tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
}
</style>
