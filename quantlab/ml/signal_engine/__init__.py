"""
Signal Engine — ML Lab 的信号生成引擎

把 Model Prediction 转换成 Strategy Language。
这是 ML Lab 的终点：Feature → Model → Signal。

11 个模块：
  1. Prediction Adapter   — 统一模型输出
  2. Calibrator           — 概率校准
  3. Generator            — Prediction → Signal (核心)
  4. Filter               — 流动性/停牌/黑名单过滤
  5. Ranker               — TopK / BottomK 排序
  6. Scorer               — 统一评分 [-100, 100]
  7. Position Allocator   — Kelly / VolScaling 建议权重
  8. Signal Validator     — Hit Rate / IC / Win Rate 验证
  9. Signal Registry      — SQLite 持久化 + 版本管理
  10. Signal Templates    — 预配置 pipeline (TopK/Momentum/...)
  11. Signal Explainability — 信号溯源解释
"""
from __future__ import annotations

# 核心对象
from .signal import Prediction, Signal, SignalDirection, SignalSet

# 模块 1-7
from .prediction_adapter import PredictionAdapter
from .calibrator import Calibrator, NoCalibration, TemperatureScaling, PlattScaling, IsotonicRegression, get_calibrator
from .generator import (
    Generator, ThresholdGenerator, QuantileGenerator, RankingGenerator,
    ProbabilityGenerator, ClassificationGenerator, RegressionGenerator, get_generator,
)
from .filter import (
    SignalFilter, BlacklistFilter, LiquidityFilter, SuspensionFilter,
    PriceLimitFilter, ListingAgeFilter, CompositeFilter, get_filter, build_filters,
)
from .ranker import Ranker, NoRanker, TopKRanker, BottomKRanker, TopBottomKRanker, get_ranker
from .scorer import Scorer, TanhScorer, RankScorer, ZScoreScorer, QuantileScorer, get_scorer
from .position_allocator import (
    PositionAllocator, EqualWeightAllocator, ConfidenceWeightAllocator,
    KellyAllocator, VolatilityScalingAllocator, RiskParityAllocator, get_allocator,
)

# 模块 8-11 + Pipeline
from .signal_validator import SignalValidator, ValidationReport
from .signal_registry import SignalRegistry, SignalVersion, get_signal_registry
from .templates import SignalTemplate, TEMPLATES, get_template, list_templates
from .explainability import ExplainabilityEngine, ExplainTrace, explain_signal
from .pipeline import SignalPipeline, PipelineConfig, run_pipeline

__all__ = [
    # 核心对象
    "Prediction", "Signal", "SignalDirection", "SignalSet",
    # 模块 1-7
    "PredictionAdapter",
    "Calibrator", "NoCalibration", "TemperatureScaling", "PlattScaling",
    "IsotonicRegression", "get_calibrator",
    "Generator", "ThresholdGenerator", "QuantileGenerator", "RankingGenerator",
    "ProbabilityGenerator", "ClassificationGenerator", "RegressionGenerator", "get_generator",
    "SignalFilter", "BlacklistFilter", "LiquidityFilter", "SuspensionFilter",
    "PriceLimitFilter", "ListingAgeFilter", "CompositeFilter", "get_filter", "build_filters",
    "Ranker", "NoRanker", "TopKRanker", "BottomKRanker", "TopBottomKRanker", "get_ranker",
    "Scorer", "TanhScorer", "RankScorer", "ZScoreScorer", "QuantileScorer", "get_scorer",
    "PositionAllocator", "EqualWeightAllocator", "ConfidenceWeightAllocator",
    "KellyAllocator", "VolatilityScalingAllocator", "RiskParityAllocator", "get_allocator",
    # 模块 8-11 + Pipeline
    "SignalValidator", "ValidationReport",
    "SignalRegistry", "SignalVersion", "get_signal_registry",
    "SignalTemplate", "TEMPLATES", "get_template", "list_templates",
    "ExplainabilityEngine", "ExplainTrace", "explain_signal",
    "SignalPipeline", "PipelineConfig", "run_pipeline",
]
