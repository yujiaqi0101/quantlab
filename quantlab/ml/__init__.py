"""
ML Lab — Alpha 生产线

完整闭环：
  DataHub → FeatureSet → LabelSet → TrainingDataset
  → Model Training → Walk Forward → Backtest → Deploy

10 层架构：
  L1. ML Data Pipeline      — TrainingDataset 统一数据容器
  L2. FeatureSet            — 特征集合可复用、版本化
  L3. LabelSet              — 标签集合版本化
  L4. Training Job System   — dataset + feature_set + label_set + model
  L5. Experiment Tracker    — 完整实验追溯
  L6. Hyperparameter Search — GridSearch + RandomSearch
  L7. Walk Forward Engine   — 滚动验证（量化灵魂）
  L8. Feature Importance    — Gain / Permutation / SHAP
  L9. Model Comparison      — Model Arena 模型对比
  L10. ML Strategy Generator — FeatureSet + LabelSet + Model → Strategy

模块：
  1. Dataset Center       — 训练数据管理
  2. Feature Lab          — 特征工程 + FeatureSet
  3. Label Lab            — 标签工程 + LabelSet
  4. Feature Analysis     — 特征分析（IC/MI）+ Feature Importance
  5. Model Lab            — 模型（Linear/RF/XGBoost/LGBM）
  6. Training Center      — 训练任务（L4 升级）
  7. Validation Center    — Walk Forward 验证（L7 升级）
  8. Leakage Detector     — 数据泄漏检测
  9. Model Registry       — 模型版本管理
 10. ML Strategy Builder  — ML 策略生成（L10 升级）
"""

# L1: Pipeline
from .pipeline import TrainingDataset, MLPipeline, get_pipeline

# Dataset Center（基础模块）
from .dataset import Dataset, DatasetManager, get_dataset_manager

# L2: Feature + FeatureSet
from .feature import (
    Feature, FeatureRegistry, get_feature_registry,
    FeatureSet, FeatureSetRegistry, get_feature_set_registry,
)

# L3: Label + LabelSet
from .label import (
    Label, LabelRegistry, get_label_registry,
    LabelSet, LabelSetRegistry, get_label_set_registry,
)

# L4: Feature Analysis + Importance (L8)
from .feature_analysis import (
    FeatureAnalyzer, FeatureAnalysisResult,
    ImportanceResult, FeatureImportanceAnalyzer,
    compute_gain_importance, compute_permutation_importance, compute_shap_importance,
)

# L4.5: Diagnostics (M1 必做：Feature Diagnostics + Label Diagnostics)
from .diagnostics import (
    FeatureDiagnostics, FeatureDiagnosticResult, FeatureDiagnosticsReport,
    run_feature_diagnostics,
    LabelDiagnostics, LabelDiagnosticResult, LabelDiagnosticsReport,
    run_label_diagnostics,
)

# L5: Model
from .model import Model, ModelType

# L6: Training (L4 升级)
from .training import (
    TrainingJob, TrainingManager, get_training_manager,
    TrainingQueue, QueueEntry, get_training_queue,
)

# L7: Validation (L7 升级 + M3 全模块)
from .validation import (
    WalkForward, WalkForwardEngine, ValidationConfig, WalkForwardResult,
    StabilityAnalyzer, StabilityResult, YearlyStat,
    RegimeValidator, RegimeResult, RegimeStat, MarketRegime,
    RobustnessTester, RobustnessResult, PerturbationResult,
    NoiseTester, NoiseTestResult, NoiseTestItem,
    BenchmarkEngine, BenchmarkReport, BenchmarkResult,
    ValidationReport, ValidationItem, ValidationStatus,
    build_validation_report,
)

# L8: Experiment Tracker (L5)
from .experiment import Experiment, ExperimentTracker, get_experiment_tracker

# L9: Hyperparameter Search (L6)
from .search import (
    GridSearch, RandomSearch, TrialResult, SearchResult,
    run_grid_search, run_random_search,
)

# L10: Model Comparison (L9)
from .comparison import ModelArena, ModelResult, compare_models, get_model_arena

# L11: Leakage
from .leakage import (
    LeakageDetector, LeakageReport, LeakageType, LeakageIssue,
    FeatureLeakageScanner,
)

# L12: Model Registry (M4 升级 + M6 Model Package 架构)
from .registry import (
    ModelVersion, ModelRegistry, LifecycleStatus, get_model_registry,
    ModelStore, get_model_store, DEFAULT_MODELS_DIR,
    ModelLineage, LineageNode, LineageChange,
    ChampionManager, ChampionResult,
    ModelComparator, ComparisonRow, ComparisonReport,
    LifecycleManager, LifecycleEvent, VALID_TRANSITIONS,
    ModelAuditLog, AuditEntry, AuditAction, get_audit_log,
    # M6 新增
    ModelPackage, ModelManifest,
    FeatureSetSnapshot, LabelSetSnapshot,
    SnapshotManager, get_snapshot_manager,
    ArtifactStore,
    ChampionPointer, ChampionHistoryEntry,
    ModelPackageBuilder, get_package_builder,
    export_package, export_from_store,
    import_package, import_to_registry,
    QLMODEL_EXTENSION,
)

# L13: Strategy Builder (L10 升级)
from .strategy_builder import MLStrategy, MLStrategyBuilder, MLStrategyConfig

# L13b: ML Strategy (M5 — Champion Model → ML Strategy)
from .strategy import (
    Signal, SignalSide, SignalRule, SignalGenerator,
    PositionSizer, PositionSizeConfig, SizingMode,
    RiskOverlay, RiskConfig, RiskState,
    MLStrategyV2, MLStrategyConfigV2,
    StrategyBuilder as MLStrategyBuilderV2, StrategyBuildRequest, get_strategy_builder,
    DeploymentProfile, DeploymentEnv, DeploymentStatus,
    DeploymentManager, get_deployment_manager,
    MLBacktestAdapter, BacktestResult, get_backtest_adapter,
)

# L14: Storage — SQLite + Parquet 持久化（M2）
from .storage import (
    MLStore, get_ml_store, DEFAULT_DB_PATH,
    ParquetStore, get_parquet_store,
)

# L15: Metrics Engine — 量化指标（M2）
from .metrics import (
    compute_ic, compute_rank_ic, compute_sharpe,
    compute_precision, compute_recall, compute_accuracy, compute_auc,
    compute_regression_metrics, compute_classification_metrics,
    compute_all_metrics, MetricsResult,
)

# L8 升级: Experiment Comparator（M2 第六部分）
from .experiment import (
    ExperimentComparator, ComparisonRow, ComparisonReport, compare_experiments,
)

# L16: Validation Pipeline（质量控制中心）
from .validation import (
    ValidationPipeline, ValidationContext, PipelineResult,
    ValidationGate, GateResult, GateStatus, ValidationLevel,
    ValidationScore, OverallScore,
    ValidationArtifactStore, generate_html_report,
    create_default_pipeline, get_gate_registry,
    DataGate, TrainingGate, LeakageGate,
    WalkForwardGate, TradingGate, RobustnessGate, BenchmarkGate,
)

# L17: Champion Challenge（冠军挑战）
from .challenge import (
    ChampionChallenge, ChallengeResult, ChallengeDecision,
    ComparisonMetric, MetricComparison,
    ChallengeComparator, DecisionEngine,
    get_champion_challenge,
)

__all__ = [
    # L1: Pipeline
    "TrainingDataset", "MLPipeline", "get_pipeline",
    # Dataset Center
    "Dataset", "DatasetManager", "get_dataset_manager",
    # L2: Feature + FeatureSet
    "Feature", "FeatureRegistry", "get_feature_registry",
    "FeatureSet", "FeatureSetRegistry", "get_feature_set_registry",
    # L3: Label + LabelSet
    "Label", "LabelRegistry", "get_label_registry",
    "LabelSet", "LabelSetRegistry", "get_label_set_registry",
    # L4: Feature Analysis + Importance
    "FeatureAnalyzer", "FeatureAnalysisResult",
    "ImportanceResult", "FeatureImportanceAnalyzer",
    "compute_gain_importance", "compute_permutation_importance", "compute_shap_importance",
    # L4.5: Diagnostics
    "FeatureDiagnostics", "FeatureDiagnosticResult", "FeatureDiagnosticsReport",
    "run_feature_diagnostics",
    "LabelDiagnostics", "LabelDiagnosticResult", "LabelDiagnosticsReport",
    "run_label_diagnostics",
    # L5: Model
    "Model", "ModelType",
    # L6: Training
    "TrainingJob", "TrainingManager", "get_training_manager",
    "TrainingQueue", "QueueEntry", "get_training_queue",
    # L7: Validation (M3)
    "WalkForward", "WalkForwardEngine", "ValidationConfig", "WalkForwardResult",
    "StabilityAnalyzer", "StabilityResult", "YearlyStat",
    "RegimeValidator", "RegimeResult", "RegimeStat", "MarketRegime",
    "RobustnessTester", "RobustnessResult", "PerturbationResult",
    "NoiseTester", "NoiseTestResult", "NoiseTestItem",
    "BenchmarkEngine", "BenchmarkReport", "BenchmarkResult",
    "ValidationReport", "ValidationItem", "ValidationStatus",
    "build_validation_report",
    # L8: Experiment Tracker
    "Experiment", "ExperimentTracker", "get_experiment_tracker",
    # L9: Hyperparameter Search
    "GridSearch", "RandomSearch", "TrialResult", "SearchResult",
    "run_grid_search", "run_random_search",
    # L10: Model Comparison
    "ModelArena", "ModelResult", "compare_models", "get_model_arena",
    # L11: Leakage
    "LeakageDetector", "LeakageReport", "LeakageType", "LeakageIssue",
    "FeatureLeakageScanner",
    # L12: Model Registry (M4 + M6)
    "ModelVersion", "ModelRegistry", "LifecycleStatus", "get_model_registry",
    "ModelStore", "get_model_store", "DEFAULT_MODELS_DIR",
    "ModelLineage", "LineageNode", "LineageChange",
    "ChampionManager", "ChampionResult",
    "ModelComparator", "ComparisonRow", "ComparisonReport",
    "LifecycleManager", "LifecycleEvent", "VALID_TRANSITIONS",
    "ModelAuditLog", "AuditEntry", "AuditAction", "get_audit_log",
    # M6: Model Package 架构
    "ModelPackage", "ModelManifest",
    "FeatureSetSnapshot", "LabelSetSnapshot",
    "SnapshotManager", "get_snapshot_manager",
    "ArtifactStore",
    "ChampionPointer", "ChampionHistoryEntry",
    "ModelPackageBuilder", "get_package_builder",
    "export_package", "export_from_store",
    "import_package", "import_to_registry",
    "QLMODEL_EXTENSION",
    # L13: Strategy Builder
    "MLStrategy", "MLStrategyBuilder", "MLStrategyConfig",
    # L13b: ML Strategy (M5)
    "Signal", "SignalSide", "SignalRule", "SignalGenerator",
    "PositionSizer", "PositionSizeConfig", "SizingMode",
    "RiskOverlay", "RiskConfig", "RiskState",
    "MLStrategyV2", "MLStrategyConfigV2",
    "MLStrategyBuilderV2", "StrategyBuildRequest", "get_strategy_builder",
    "DeploymentProfile", "DeploymentEnv", "DeploymentStatus",
    "DeploymentManager", "get_deployment_manager",
    "MLBacktestAdapter", "BacktestResult", "get_backtest_adapter",
    # L14: Storage
    "MLStore", "get_ml_store", "DEFAULT_DB_PATH",
    "ParquetStore", "get_parquet_store",
    # L15: Metrics Engine
    "compute_ic", "compute_rank_ic", "compute_sharpe",
    "compute_precision", "compute_recall", "compute_accuracy", "compute_auc",
    "compute_regression_metrics", "compute_classification_metrics",
    "compute_all_metrics", "MetricsResult",
    # Experiment Comparator
    "ExperimentComparator", "ComparisonRow", "ComparisonReport", "compare_experiments",
    # L16: Validation Pipeline
    "ValidationPipeline", "ValidationContext", "PipelineResult",
    "ValidationGate", "GateResult", "GateStatus", "ValidationLevel",
    "ValidationScore", "OverallScore",
    "ValidationArtifactStore", "generate_html_report",
    "create_default_pipeline", "get_gate_registry",
    "DataGate", "TrainingGate", "LeakageGate",
    "WalkForwardGate", "TradingGate", "RobustnessGate", "BenchmarkGate",
    # L17: Champion Challenge
    "ChampionChallenge", "ChallengeResult", "ChallengeDecision",
    "ComparisonMetric", "MetricComparison",
    "ChallengeComparator", "DecisionEngine",
    "get_champion_challenge",
]
