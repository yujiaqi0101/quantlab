"""
Research Pipeline — V2 统一研究调度器

所有研究 = Pipeline 执行

PipelineType:
  - SINGLE_EXPERIMENT  单策略单次回测
  - PARAMETER_SWEEP    参数网格搜索
  - ALPHA_BATCH        Alpha 批量生成+评估+排序

核心流程：
  ResearchContext → PipelineExecutor → PipelineResult

模块：
  context.py    ResearchContext / PipelineType / PipelineResult
  registry.py   PipelineRegistry — 统一注册 Factor/Signal/Strategy
  executor.py   PipelineExecutor — 统一执行器
  pipeline.py   ResearchPipeline — 主控调度器
"""

from .context import (
    ResearchContext, PipelineType, PipelineResult, PipelineStepResult,
    PipelineStatus, FactorConfig, SignalConfig, StrategyConfig,
    SweepConfig, AlphaBatchConfig,
)
from .registry import PipelineRegistry
from .executor import PipelineExecutor
from .pipeline import ResearchPipeline

__all__ = [
    "ResearchContext",
    "PipelineType",
    "PipelineResult",
    "PipelineStepResult",
    "PipelineStatus",
    "FactorConfig",
    "SignalConfig",
    "StrategyConfig",
    "SweepConfig",
    "AlphaBatchConfig",
    "PipelineRegistry",
    "PipelineExecutor",
    "ResearchPipeline",
]
