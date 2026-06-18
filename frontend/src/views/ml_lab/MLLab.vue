<template>
  <div class="ml-lab">
    <!-- 顶部导航 -->
    <div class="ml-tabs">
      <el-tabs v-model="activeTab" type="card">
        <el-tab-pane label="Datasets" name="datasets">
          <DatasetCenter />
        </el-tab-pane>
        <el-tab-pane label="Features" name="features">
          <FeatureLab />
        </el-tab-pane>
        <el-tab-pane label="Feature Sets" name="feature-sets">
          <FeatureSets />
        </el-tab-pane>
        <el-tab-pane label="Labels" name="labels">
          <LabelLab />
        </el-tab-pane>
        <el-tab-pane label="Label Sets" name="label-sets">
          <LabelSets />
        </el-tab-pane>
        <el-tab-pane label="Feature Diagnostics" name="feature-diagnostics">
          <FeatureDiagnostics />
        </el-tab-pane>
        <el-tab-pane label="Label Diagnostics" name="label-diagnostics">
          <LabelDiagnostics />
        </el-tab-pane>
        <el-tab-pane label="Feature Analysis" name="analysis">
          <FeatureAnalysis />
        </el-tab-pane>
        <el-tab-pane label="Feature Importance" name="importance">
          <FeatureImportance />
        </el-tab-pane>
        <el-tab-pane label="Training Jobs" name="training">
          <TrainingCenter />
        </el-tab-pane>
        <el-tab-pane label="Experiments" name="experiments">
          <Experiments />
        </el-tab-pane>
        <el-tab-pane label="Hyperparameter Search" name="search">
          <HyperparameterSearch />
        </el-tab-pane>
        <el-tab-pane label="Validation" name="validation">
          <ValidationCenter />
        </el-tab-pane>
        <el-tab-pane label="Model Arena" name="arena">
          <ModelArena />
        </el-tab-pane>
        <el-tab-pane label="Leakage Detector" name="leakage">
          <LeakageDetector />
        </el-tab-pane>
        <el-tab-pane label="Model Registry" name="registry">
          <ModelRegistry />
        </el-tab-pane>
        <el-tab-pane label="Strategy Builder" name="strategy">
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
