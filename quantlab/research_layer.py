"""
QuantLab V2.0 — Research Layer

研究能力：实验/优化/分析/回测验证

依赖：core + infra
不依赖：services / studio
"""

# --- Experiment ---
from .research.experiment import Experiment, ExperimentResult
from .research.database import Database
from .research.result import ExperimentResult as ResearchExperimentResult

# --- Optimization ---
from .optimizer import Optimizer, generate_param_grid
from .parallel_optimizer import ParallelOptimizer
from .research.sweeper import ParameterSweeper, SweepResult, HeatmapData

# --- Walk Forward ---
from .research.walk_forward import WalkForward, WalkForwardResult
from .research.walk_forward import WalkForwardRunner, WalkForwardResultV2

# --- Analytics ---
from .analytics.metrics import sharpe_ratio, max_drawdown, win_rate
from .analytics.attribution import AttributionAnalyzer
from .analytics.benchmark import BenchmarkComparator
from .analytics.exposure import ExposureAnalyzer

# --- Factor Analysis ---
from .factor.ic_analysis import ICAnalyzer
from .research.feature_store import FeatureStore

# --- Pipeline ---
from .research.pipeline import ResearchPipeline
from .research.notebook import ResearchSession

# --- Report ---
from .research.report import Report
from .research.artifact import ArtifactStore, Artifact

# --- Validation ---
from .research.validation import ValidationRunner

__research_all__ = [
    "Experiment", "ExperimentResult", "Database",
    "Optimizer", "ParallelOptimizer", "generate_param_grid",
    "ParameterSweeper", "SweepResult", "HeatmapData",
    "WalkForward", "WalkForwardResult",
    "WalkForwardRunner", "WalkForwardResultV2",
    "sharpe_ratio", "max_drawdown", "win_rate",
    "AttributionAnalyzer", "BenchmarkComparator", "ExposureAnalyzer",
    "ICAnalyzer", "FeatureStore",
    "ResearchPipeline", "ResearchSession",
    "Report", "ArtifactStore", "Artifact",
    "ValidationRunner",
]
