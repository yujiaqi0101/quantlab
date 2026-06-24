import { http } from './http'

// ML 计算密集型请求的超时配置（5分钟）
// 大数据集 + SHAP 等方法训练可能超过 30s，需要更长超时
const ML_TIMEOUT = 300000

// ==================================================================
// Types
// ==================================================================

export interface MLDataset {
  dataset_id: string
  name: string
  symbols: string[]
  start_date: string
  end_date: string
  frequency: string
  description: string
  tags: string[]
  created_at: string
  scope_type: string
  universe_id: string
}

export interface MLFeature {
  feature_id: string
  name: string
  description: string
  category: string
  tags: string[]
  params: Record<string, any>
  required_columns: string[]
}

export interface MLLabel {
  label_id: string
  name: string
  description: string
  label_type: string
  classes: string[]
  params: Record<string, any>
  required_columns: string[]
}

export interface FeatureAnalysisResult {
  feature_name: string
  ic: number
  rank_ic: number
  mutual_info: number
  n_samples: number
  ic_std: number
  ic_ir: number
}

export interface MLModel {
  type: string
  name: string
  is_classifier: boolean
  description: string
}

export interface TrainingJobInfo {
  job_id: string
  dataset_id: string
  feature_ids: string[]
  label_id: string
  model_type: string
  model_params: Record<string, any>
  is_classifier: boolean
  status: string
  metrics: any
}

export interface TrainingResult {
  job_id: string
  status: string
  metrics: any
  feature_importance: Record<string, number>
  n_train_samples: number
  n_test_samples: number
  train_time: number
  error: string
}

export interface WalkForwardResult {
  n_splits: number
  metrics_per_fold: any[]
  avg_ic: number
  avg_rank_ic: number
  avg_rmse: number
  ic_stability: number
  fold_details: any[]
}

export interface LeakageReport {
  passed: boolean
  n_critical: number
  n_warning: number
  n_info: number
  issues: any[]
}

export interface ModelVersion {
  version_id: string
  name: string
  model_type: string
  params: Record<string, any>
  metrics: Record<string, any>
  dataset_id: string
  feature_ids: string[]
  label_id: string
  is_classifier: boolean
  created_at: string
  description: string
  tags: string[]
}

export interface MLStrategy {
  strategy_id: string
  name: string
  config: any
  model: any
}

// ==================================================================
// Dataset Center
// ==================================================================

export async function getMLDatasets(): Promise<{ datasets: MLDataset[] }> {
  const resp = await http.get('/ml/datasets')
  return resp.data
}

export async function createMLDataset(data: {
  name: string
  symbols: string[]
  frequency: string
  description?: string
  tags?: string[]
}): Promise<MLDataset> {
  const resp = await http.post('/ml/datasets', data)
  return resp.data
}

export async function getMLDataset(id: string): Promise<MLDataset> {
  const resp = await http.get(`/ml/datasets/${id}`)
  return resp.data
}

export async function getMLDatasetStats(id: string): Promise<any> {
  const resp = await http.get(`/ml/datasets/${id}/stats`)
  return resp.data
}

export async function loadMLDatasetCSV(id: string, file: File): Promise<any> {
  const formData = new FormData()
  formData.append('file', file)
  const resp = await http.post(`/ml/datasets/${id}/load_csv`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: ML_TIMEOUT,
  })
  return resp.data
}

export async function deleteMLDataset(id: string): Promise<any> {
  const resp = await http.delete(`/ml/datasets/${id}`)
  return resp.data
}

// ==================================================================
// Feature Lab
// ==================================================================

export async function getMLFeatures(): Promise<{ total: number; features: MLFeature[]; categories: string[] }> {
  const resp = await http.get('/ml/features')
  return resp.data
}

export async function computeMLFeatures(featureIds: string[], data: any[]): Promise<any> {
  const resp = await http.post('/ml/features/compute', { feature_ids: featureIds, data }, { timeout: ML_TIMEOUT })
  return resp.data
}

// ==================================================================
// Label Lab
// ==================================================================

export async function getMLLabels(): Promise<{ total: number; labels: MLLabel[] }> {
  const resp = await http.get('/ml/labels')
  return resp.data
}

export async function generateMLLabel(labelId: string, data: any[]): Promise<any> {
  const resp = await http.post('/ml/labels/generate', { label_id: labelId, data }, { timeout: ML_TIMEOUT })
  return resp.data
}

// ==================================================================
// Feature Analysis
// ==================================================================

export async function analyzeFeatures(data: {
  feature_data: Record<string, number[]>
  label_data: number[]
  index?: string[]
}): Promise<{ results: FeatureAnalysisResult[]; correlation_matrix: any }> {
  const resp = await http.post('/ml/feature-analysis', data, { timeout: ML_TIMEOUT })
  return resp.data
}

// ==================================================================
// Model Lab
// ==================================================================

export async function getMLModels(): Promise<{ models: MLModel[] }> {
  const resp = await http.get('/ml/models')
  return resp.data
}

// ==================================================================
// Training Center
// ==================================================================

export async function submitTraining(data: {
  dataset_id: string
  feature_ids?: string[]
  label_id?: string
  feature_set_id?: string
  label_set_id?: string
  model_type: string
  model_params?: Record<string, any>
  is_classifier?: boolean
  train_ratio?: number
  val_ratio?: number
  methods?: string[]
}): Promise<TrainingResult> {
  const resp = await http.post('/ml/training/jobs', data, { timeout: ML_TIMEOUT })
  return resp.data
}

export async function getTrainingJobs(): Promise<{ jobs: any[]; status: any }> {
  const resp = await http.get('/ml/training/jobs')
  return resp.data
}

export async function getTrainingJob(jobId: string): Promise<{ job: any; result: any }> {
  const resp = await http.get(`/ml/training/jobs/${jobId}`)
  return resp.data
}

// ==================================================================
// Validation Center
// ==================================================================

export async function runWalkForward(data: {
  feature_data: Record<string, number[]>
  label_data: number[]
  index?: string[]
  model_type: string
  model_params?: Record<string, any>
  is_classifier?: boolean
  n_splits?: number
  train_size?: number
  test_size?: number
  step_size?: number
  gap?: number
}): Promise<WalkForwardResult> {
  const resp = await http.post('/ml/validation/walk-forward', data, { timeout: ML_TIMEOUT })
  return resp.data
}

// ==================================================================
// Leakage Detector
// ==================================================================

export async function checkLeakageData(data: {
  feature_data: Record<string, number[]>
  label_data: number[]
  index?: string[]
}): Promise<LeakageReport> {
  const resp = await http.post('/ml/leakage/check-data', data, { timeout: ML_TIMEOUT })
  return resp.data
}

export async function checkLeakageOverlap(data: {
  train_index: string[]
  test_index: string[]
}): Promise<LeakageReport> {
  const resp = await http.post('/ml/leakage/check-overlap', data, { timeout: ML_TIMEOUT })
  return resp.data
}

export async function checkLeakageDataset(data: {
  dataset_id: string
  feature_set_id?: string
  label_set_id?: string
  feature_ids?: string[]
  label_id?: string
}): Promise<LeakageReport> {
  const resp = await http.post('/ml/leakage/check-dataset', data, { timeout: ML_TIMEOUT })
  return resp.data
}

// ==================================================================
// Model Registry
// ==================================================================

export async function getModelVersions(modelType?: string): Promise<{ versions: ModelVersion[] }> {
  const params: Record<string, string> = {}
  if (modelType) params.model_type = modelType
  const resp = await http.get('/ml/registry/versions', { params })
  return resp.data
}

export async function registerModelVersion(data: {
  name: string
  model_type: string
  params?: Record<string, any>
  metrics?: Record<string, any>
  dataset_id?: string
  feature_ids?: string[]
  label_id?: string
  is_classifier?: boolean
  description?: string
  tags?: string[]
}): Promise<{ version_id: string; status: string }> {
  const resp = await http.post('/ml/registry/versions', data)
  return resp.data
}

export async function getModelVersion(versionId: string): Promise<ModelVersion> {
  const resp = await http.get(`/ml/registry/versions/${versionId}`)
  return resp.data
}

// ==================================================================
// ML Strategy Builder
// ==================================================================

export async function buildMLStrategy(data: {
  feature_ids: string[]
  label_id: string
  model_type: string
  model_params?: Record<string, any>
  is_classifier?: boolean
  long_threshold?: number
  short_threshold?: number
  use_short?: boolean
  position_scale?: number
  name?: string
  train_data: any[]
}): Promise<MLStrategy> {
  const resp = await http.post('/ml/strategies', data, { timeout: ML_TIMEOUT })
  return resp.data
}

export async function predictMLStrategy(strategyId: string, data: any[]): Promise<{
  predictions: number[]
  signals: number[]
  positions: number[]
  index: string[]
}> {
  const resp = await http.post('/ml/strategies/predict', { strategy_id: strategyId, data })
  return resp.data
}

export async function getMLStrategies(): Promise<{ strategies: MLStrategy[] }> {
  const resp = await http.get('/ml/strategies')
  return resp.data
}

export async function getMLStrategy(strategyId: string): Promise<MLStrategy> {
  const resp = await http.get(`/ml/strategies/${strategyId}`)
  return resp.data
}

// ==================================================================
// L2: FeatureSet — 特征集合
// ==================================================================

export interface MLFeatureSet {
  fs_id: string
  name: string
  feature_ids: string[]
  description: string
  version: string
  tags: string[]
  created_at: string
}

export async function getFeatureSets(tag?: string): Promise<{ total: number; sets: MLFeatureSet[] }> {
  const params: Record<string, string> = {}
  if (tag) params.tag = tag
  const resp = await http.get('/ml/feature-sets', { params })
  return resp.data
}

export async function createFeatureSet(data: {
  name: string
  feature_ids: string[]
  description?: string
  version?: string
  tags?: string[]
}): Promise<MLFeatureSet> {
  const resp = await http.post('/ml/feature-sets', data)
  return resp.data
}

export async function getFeatureSet(name: string): Promise<MLFeatureSet> {
  const resp = await http.get(`/ml/feature-sets/${name}`)
  return resp.data
}

// ==================================================================
// L3: LabelSet — 标签集合
// ==================================================================

export interface MLLabelSet {
  ls_id: string
  name: string
  label_id: string
  description: string
  version: string
  label_type: string
  classes: string[]
  tags: string[]
  created_at: string
}

export async function getLabelSets(tag?: string): Promise<{ total: number; sets: MLLabelSet[] }> {
  const params: Record<string, string> = {}
  if (tag) params.tag = tag
  const resp = await http.get('/ml/label-sets', { params })
  return resp.data
}

export async function createLabelSet(data: {
  name: string
  label_id: string
  description?: string
  version?: string
  label_type?: string
  classes?: string[]
  tags?: string[]
}): Promise<MLLabelSet> {
  const resp = await http.post('/ml/label-sets', data)
  return resp.data
}

export async function getLabelSet(name: string): Promise<MLLabelSet> {
  const resp = await http.get(`/ml/label-sets/${name}`)
  return resp.data
}

// ==================================================================
// L5: Experiment Tracker — 实验追踪
// ==================================================================

export interface MLExperiment {
  experiment_id: string
  name: string
  dataset_id: string
  feature_set_id: string
  label_set_id: string
  model_type: string
  model_params: Record<string, any>
  is_classifier: boolean
  metrics: Record<string, any>
  feature_importance: Record<string, number>
  status: string
  tags: string[]
  created_at: string
  job_id?: string
  model_version_id?: string
}

export async function getExperiments(params?: {
  tag?: string
  status?: string
  model_type?: string
}): Promise<{ total: number; experiments: MLExperiment[] }> {
  const resp = await http.get('/ml/experiments', { params })
  return resp.data
}

export async function getExperiment(experimentId: string): Promise<MLExperiment> {
  const resp = await http.get(`/ml/experiments/${experimentId}`)
  return resp.data
}

export async function getExperimentLeaderboard(metric?: string, limit?: number): Promise<{
  metric: string
  leaderboard: any[]
}> {
  const params: Record<string, any> = {}
  if (metric) params.metric = metric
  if (limit) params.limit = limit
  const resp = await http.get('/ml/experiments/leaderboard', { params })
  return resp.data
}

export async function getExperimentSummary(): Promise<Record<string, any>> {
  const resp = await http.get('/ml/experiments/summary')
  return resp.data
}

// ==================================================================
// L6: Hyperparameter Search — 超参搜索
// ==================================================================

export interface SearchTrial {
  trial_id: number
  params: Record<string, any>
  metric_value: number
  metrics: Record<string, any>
  status: string
}

export interface SearchResult {
  best_params: Record<string, any>
  best_metric: number
  best_trial_id: number
  n_trials: number
  trials: SearchTrial[]
}

export async function runGridSearch(data: {
  dataset_id: string
  feature_set_id?: string
  label_set_id?: string
  feature_ids?: string[]
  label_id?: string
  model_type: string
  param_grid: Record<string, any[]>
  metric?: string
  is_classifier?: boolean
  train_ratio?: number
  val_ratio?: number
}): Promise<SearchResult> {
  const resp = await http.post('/ml/search/grid', data, { timeout: ML_TIMEOUT })
  return resp.data
}

export async function runRandomSearch(data: {
  dataset_id: string
  feature_set_id?: string
  label_set_id?: string
  feature_ids?: string[]
  label_id?: string
  model_type: string
  param_space: Record<string, any>
  n_trials?: number
  metric?: string
  is_classifier?: boolean
  train_ratio?: number
  val_ratio?: number
}): Promise<SearchResult> {
  const resp = await http.post('/ml/search/random', data, { timeout: ML_TIMEOUT })
  return resp.data
}

// ==================================================================
// L9: Model Comparison — Model Arena
// ==================================================================

export interface ModelLeaderboardEntry {
  result_id: string
  name: string
  model_type: string
  metrics: Record<string, any>
  train_time: number
  status: string
}

export async function runModelComparison(data: {
  dataset_id: string
  feature_set_id?: string
  label_set_id?: string
  feature_ids?: string[]
  label_id?: string
  model_types: string[]
  is_classifier?: boolean
  train_ratio?: number
  val_ratio?: number
}): Promise<{ leaderboard: ModelLeaderboardEntry[]; total: number }> {
  const resp = await http.post('/ml/comparison/run', data, { timeout: ML_TIMEOUT })
  return resp.data
}

export async function getModelArena(): Promise<{ results: any[] }> {
  const resp = await http.get('/ml/comparison/arena')
  return resp.data
}

export async function getArenaLeaderboard(metric?: string, ascending?: boolean): Promise<{
  metric: string
  leaderboard: ModelLeaderboardEntry[]
}> {
  const params: Record<string, any> = {}
  if (metric) params.metric = metric
  if (ascending !== undefined) params.ascending = ascending
  const resp = await http.get('/ml/comparison/leaderboard', { params })
  return resp.data
}

// ==================================================================
// L8: Feature Importance — 特征重要性
// ==================================================================

export interface ImportanceResult {
  method: string
  feature_names: string[]
  importances: number[]
  normalized: number[]
  ranking: number[]
  details: Array<{
    feature: string
    importance: number
    normalized: number
    rank: number
  }>
}

export async function computeFeatureImportance(data: {
  feature_data: Record<string, number[]>
  label_data: number[]
  index?: string[]
  model_type: string
  model_params?: Record<string, any>
  is_classifier?: boolean
  methods?: string[]
  train_ratio?: number
}): Promise<{ method: string[]; results: Record<string, ImportanceResult> }> {
  const resp = await http.post('/ml/feature-importance', data, { timeout: ML_TIMEOUT })
  return resp.data
}

// ==================================================================
// M1: Diagnostics — 特征诊断 + 标签诊断
// ==================================================================

export interface FeatureDiagnosticResult {
  feature_name: string
  n_samples: number
  n_missing: number
  missing_rate: number
  n_inf: number
  inf_count: number
  n_zero: number
  zero_rate: number
  variance: number | null
  n_unique: number
  dtype: string
  is_bad: boolean
  issues: string[]
}

export interface FeatureDiagnosticsReport {
  n_features: number
  n_samples: number
  n_bad: number
  bad_features: string[]
  results: FeatureDiagnosticResult[]
  summary: {
    n_features: number
    n_samples: number
    n_bad: number
    bad_ratio: number
    issue_counts: Record<string, number>
    var_threshold: number
    missing_threshold: number
    zero_threshold: number
  }
}

export interface LabelDiagnosticResult {
  label_name: string
  label_type: string
  n_samples: number
  n_missing: number
  missing_rate: number
  n_inf: number
  inf_count: number
  variance: number | null
  mean: number | null
  std: number | null
  n_unique: number
  class_distribution: Record<string, number>
  n_classes: number
  max_class_ratio: number
  min_class_ratio: number
  is_bad: boolean
  is_imbalanced: boolean
  issues: string[]
}

export interface LabelDiagnosticsReport {
  label_name: string
  label_type: string
  n_samples: number
  is_bad: boolean
  is_imbalanced: boolean
  issues: string[]
  result: LabelDiagnosticResult
  summary: {
    label_name: string
    label_type: string
    n_samples: number
    is_bad: boolean
    is_imbalanced: boolean
    n_issues: number
    issues: string[]
    n_classes: number
    max_class_ratio: number
    min_class_ratio: number
    imbalance_threshold: number
    min_class_threshold: number
  }
}

export async function runFeatureDiagnostics(data: {
  feature_data: Record<string, number[]>
  index?: string[]
}): Promise<FeatureDiagnosticsReport> {
  const resp = await http.post('/ml/diagnostics/features', data, { timeout: ML_TIMEOUT })
  return resp.data
}

export async function runLabelDiagnostics(data: {
  label_data: number[]
  index?: string[]
  label_type?: string
}): Promise<LabelDiagnosticsReport> {
  const resp = await http.post('/ml/diagnostics/labels', data, { timeout: ML_TIMEOUT })
  return resp.data
}

export async function runTrainingDatasetDiagnostics(data: {
  dataset_id: string
  feature_ids: string[]
  label_id: string
  model_type?: string
  is_classifier?: boolean
}): Promise<{
  n_samples: number
  n_features: number
  feature_diagnostics: FeatureDiagnosticsReport
  label_diagnostics: LabelDiagnosticsReport
}> {
  const resp = await http.post('/ml/diagnostics/training-dataset', data, { timeout: ML_TIMEOUT })
  return resp.data
}

// ==================================================================
// L16: Validation Pipeline — 质量控制中心
// ==================================================================

export interface GateConfig {
  name: string
  level: string
  enabled: boolean
  weight: number
  description: string
}

export interface GateResult {
  gate_name: string
  level: string
  status: 'PASS' | 'WARNING' | 'FAIL' | 'SKIP' | 'ERROR'
  score: number
  grade: string
  summary: string
  details: Record<string, any>
  artifacts: string[]
  execution_time: number
  error: string
}

export interface PipelineResult {
  validation_id: string
  gate_results: GateResult[]
  overall_score: number
  overall_grade: string
  overall_status: 'PASS' | 'WARNING' | 'FAIL' | 'SKIP' | 'ERROR'
  passed: boolean
  stopped_at: string
  context_summary: Record<string, any>
  created_at: string
  total_execution_time: number
}

export async function runValidationPipeline(data: {
  feature_data: Record<string, number[]>
  label_data: number[]
  index?: string[]
  model_type: string
  model_params?: Record<string, any>
  is_classifier?: boolean
  predictions?: number[]
  gates_config?: Record<string, { enabled?: boolean; weight?: number }>
  stop_on_fail?: boolean
  n_splits?: number
  train_size?: number
  test_size?: number
  step_size?: number
  gap?: number
  dataset_id?: string
  feature_ids?: string[]
  feature_set_id?: string
  label_id?: string
  label_set_id?: string
  name?: string
  experiment_id?: string
}): Promise<PipelineResult> {
  const resp = await http.post('/ml/validation/pipeline/run', data, { timeout: ML_TIMEOUT })
  return resp.data
}

export async function getPipelineConfig(): Promise<{
  name: string
  stop_on_fail: boolean
  stop_on_error: boolean
  gates: GateConfig[]
}> {
  const resp = await http.get('/ml/validation/pipeline/config')
  return resp.data
}

export async function updatePipelineConfig(gates_config: Record<string, { enabled?: boolean; weight?: number }>): Promise<any> {
  const resp = await http.put('/ml/validation/pipeline/config', gates_config)
  return resp.data
}

export async function listGates(): Promise<{ gates: GateConfig[] }> {
  const resp = await http.get('/ml/validation/gates')
  return resp.data
}

// ==================================================================
// L17: Champion Challenge — 冠军挑战
// ==================================================================

export interface MetricComparison {
  metric: string
  candidate_value: number
  champion_value: number
  delta: number
  higher_is_better: boolean
  candidate_wins: boolean
}

export interface ChallengeResult {
  challenge_id: string
  family: string
  candidate_id: string
  champion_id: string
  comparisons: MetricComparison[]
  decision: 'PROMOTE' | 'REJECT' | 'INCONCLUSIVE'
  reason: string
  n_wins: number
  n_total: number
  win_ratio: number
  threshold: number
  created_at: string
}

export async function runChampionChallenge(data: {
  candidate_id: string
  family?: string
  candidate_metrics: Record<string, number>
  champion_metrics?: Record<string, number>
  metrics?: string[]
  threshold?: number
  win_threshold?: number
  auto_promote?: boolean
}): Promise<ChallengeResult> {
  const resp = await http.post('/ml/challenge/run', data)
  return resp.data
}

export async function getChallengeHistory(family?: string): Promise<{ total: number; challenges: ChallengeResult[] }> {
  const params: Record<string, string> = {}
  if (family) params.family = family
  const resp = await http.get('/ml/challenge/history', { params })
  return resp.data
}

export async function getLatestChallenge(family?: string): Promise<ChallengeResult> {
  const params: Record<string, string> = {}
  if (family) params.family = family
  const resp = await http.get('/ml/challenge/latest', { params })
  return resp.data
}
