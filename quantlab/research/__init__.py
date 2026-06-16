# Research Pipeline
#
# 一次研究的标准流程：
#   Signal → Backtest → Optimization → Validation
#          → Walk Forward → Report
#
# V2.3 加：
#   - ExperimentRecord   实验元数据 dataclass
#   - ExperimentResultV2 一次实验 + 全部结果
#   - Database           SQLite 持久化
#   - ExperimentRepository CRUD / search / leaderboard
#   - ExperimentTracker  自动跑 + 自动入库
#
# V4.5 Research IDE：
#   - ResearchSession    研究会话（类似 Jupyter Kernel）
#   - Cell               代码/标记单元
#   - ResearchCache      LRU + 磁盘缓存
#   - FeatureStore       特征存储（计算一次，永久复用）
#   - FeatureMetadata    特征元数据
#   - FactorRegistry     因子注册中心
#   - FactorInfo         因子元信息
#   - ArtifactStore      研究产物存储
#   - Artifact           产物元数据
#   - ResearchPipeline   链式流水线（数据→因子→信号→回测）
#   - PipelineStep       流水线步骤
#
# 这一切只为一个目标：
#   不再"我相信这个策略能赚钱"
#   而是"机器已经证明这个策略能赚钱"

from .result import (
    ExperimentResult
)

from .experiment import (
    Experiment
)

from .report import (
    Report
)

from .walk_forward import (
    WalkForward,
    WalkForwardResult,
    WalkForwardWindow,
)

from .validation import (
    ValidationRunner,
    ValidationResult
)

# V2.3 Experiment Tracking
from .tracker import (
    ExperimentRecord,
    ExperimentResultV2,
    ExperimentTracker,
)

from .repository import (
    ExperimentRepository,
)

from .database import (
    Database,
)

# V4.5 Research IDE
from .cache import (
    ResearchCache,
    CacheEntry,
)

from .feature_store import (
    FeatureStore,
    FeatureMetadata,
)

from .factor import (
    FactorRegistry,
    FactorInfo,
)

from .artifact import (
    ArtifactStore,
    Artifact,
)

from .notebook import (
    ResearchSession,
    Cell,
)

from .pipeline import (
    ResearchPipeline,
    PipelineStepResult,
    PipelineType,
    PipelineResult,
    ResearchContext,
    FactorConfig,
    SignalConfig,
    StrategyConfig,
    SweepConfig,
    AlphaBatchConfig,
    PipelineRegistry,
    PipelineExecutor,
)

# 兼容旧代码
PipelineStep = PipelineStepResult


__all__ = [
    "ExperimentResult",
    "Experiment",
    "Report",
    "WalkForward",
    "WalkForwardResult",
    "WalkForwardWindow",
    "ValidationRunner",
    "ValidationResult",
    # V2.3
    "ExperimentRecord",
    "ExperimentResultV2",
    "ExperimentTracker",
    "ExperimentRepository",
    "Database",
    # V4.5
    "ResearchCache",
    "CacheEntry",
    "FeatureStore",
    "FeatureMetadata",
    "FactorRegistry",
    "FactorInfo",
    "ArtifactStore",
    "Artifact",
    "ResearchSession",
    "Cell",
    "ResearchPipeline",
    "PipelineStep",
    # V2 Pipeline
    "PipelineType",
    "PipelineResult",
    "PipelineStepResult",
    "ResearchContext",
    "FactorConfig",
    "SignalConfig",
    "StrategyConfig",
    "SweepConfig",
    "AlphaBatchConfig",
    "PipelineRegistry",
    "PipelineExecutor",
]
