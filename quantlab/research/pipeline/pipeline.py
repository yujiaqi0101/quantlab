"""
Research Pipeline — V2 主控调度器

统一入口，所有研究 = Pipeline 执行

用法：
    # 单实验
    pipeline = ResearchPipeline()
    result = pipeline.run(ResearchContext(
        pipeline_type=PipelineType.SINGLE_EXPERIMENT,
        dataset_id="default",
        factors=[FactorConfig(name="RSI", params={"period": 14})],
        strategy=StrategyConfig(strategy_id="ma_cross", params={"fast": 5, "slow": 20}),
    ))

    # 参数扫描
    result = pipeline.run(ResearchContext(
        pipeline_type=PipelineType.PARAMETER_SWEEP,
        sweep=SweepConfig(param_space={"fast": [5,10,20], "slow": [60,120]}),
    ))

    # Alpha 批处理
    result = pipeline.run(ResearchContext(
        pipeline_type=PipelineType.ALPHA_BATCH,
        alpha_batch=AlphaBatchConfig(factor_names=["RSI", "MA"]),
    ))
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .context import (
    ResearchContext, PipelineType, PipelineResult,
    PipelineStatus, FactorConfig, SignalConfig, StrategyConfig,
    SweepConfig, AlphaBatchConfig,
)
from .registry import PipelineRegistry
from .executor import PipelineExecutor

logger = logging.getLogger("quantlab.research.pipeline")


class ResearchPipeline:
    """
    研究流水线 — V2 主控

    统一调度所有研究任务：
      - SINGLE_EXPERIMENT  单策略单次回测
      - PARAMETER_SWEEP    参数网格搜索
      - ALPHA_BATCH        Alpha 批量生成+评估+排序
    """

    def __init__(
        self,
        registry: Optional[PipelineRegistry] = None,
        executor: Optional[PipelineExecutor] = None,
    ) -> None:
        self._registry = registry or PipelineRegistry()
        self._executor = executor or PipelineExecutor(self._registry)
        self._history: List[PipelineResult] = []

    # ---- 便捷构建 ----

    def single(
        self,
        name: str = "",
        dataset_id: str = "default",
        symbols: Optional[List[str]] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        factors: Optional[List[FactorConfig]] = None,
        strategy: Optional[StrategyConfig] = None,
    ) -> "ResearchPipeline":
        """
        配置单实验 Pipeline

        用法：
            pipeline = ResearchPipeline().single(
                name="rsi_test",
                factors=[FactorConfig(name="RSI", params={"period": 14})],
                strategy=StrategyConfig(strategy_id="ma_cross"),
            )
            result = pipeline.execute()
        """
        self._context = ResearchContext(
            name=name,
            pipeline_type=PipelineType.SINGLE_EXPERIMENT,
            dataset_id=dataset_id,
            symbols=symbols,
            start=start,
            end=end,
            factors=factors or [],
            strategy=strategy,
        )
        return self

    def sweep(
        self,
        name: str = "",
        dataset_id: str = "default",
        param_space: Optional[Dict[str, List[Any]]] = None,
        metric: str = "sharpe",
        top_n: int = 10,
        strategy: Optional[StrategyConfig] = None,
    ) -> "ResearchPipeline":
        """
        配置参数扫描 Pipeline

        用法：
            pipeline = ResearchPipeline().sweep(
                param_space={"fast": [5,10,20], "slow": [60,120]},
                metric="sharpe",
            )
            result = pipeline.execute()
        """
        self._context = ResearchContext(
            name=name,
            pipeline_type=PipelineType.PARAMETER_SWEEP,
            dataset_id=dataset_id,
            strategy=strategy,
            sweep=SweepConfig(
                param_space=param_space or {},
                metric=metric,
                top_n=top_n,
            ),
        )
        return self

    def alpha_batch(
        self,
        name: str = "",
        factor_names: Optional[List[str]] = None,
        methods: Optional[List[str]] = None,
        ic_min: float = 0.03,
        ir_min: float = 0.5,
    ) -> "ResearchPipeline":
        """
        配置 Alpha 批处理 Pipeline

        用法：
            pipeline = ResearchPipeline().alpha_batch(
                factor_names=["RSI", "MA"],
                methods=["threshold", "cross"],
            )
            result = pipeline.execute()
        """
        self._context = ResearchContext(
            name=name,
            pipeline_type=PipelineType.ALPHA_BATCH,
            alpha_batch=AlphaBatchConfig(
                factor_names=factor_names or [],
                methods=methods or ["threshold"],
                ic_min=ic_min,
                ir_min=ir_min,
            ),
        )
        return self

    # ---- 执行 ----

    def run(self, context: Optional[ResearchContext] = None) -> PipelineResult:
        """
        执行 Pipeline

        可以传入自定义 context，也可以用 .single()/.sweep()/.alpha_batch() 预配置
        """
        ctx = context or getattr(self, "_context", None)
        if ctx is None:
            raise ValueError("No context configured. Use .single()/.sweep()/.alpha_batch() or pass context.")

        result = self._executor.execute(ctx)
        self._history.append(result)
        return result

    # 别名
    execute = run

    # ---- 查询 ----

    @property
    def registry(self) -> PipelineRegistry:
        return self._registry

    @property
    def executor(self) -> PipelineExecutor:
        return self._executor

    def history(self, limit: int = 20) -> List[PipelineResult]:
        """查询执行历史"""
        return self._history[-limit:]

    def last_result(self) -> Optional[PipelineResult]:
        """最近一次执行结果"""
        return self._history[-1] if self._history else None

    def stats(self) -> Dict[str, Any]:
        """统计信息"""
        total = len(self._history)
        completed = sum(1 for r in self._history if r.status == PipelineStatus.COMPLETED)
        failed = sum(1 for r in self._history if r.status == PipelineStatus.FAILED)
        by_type = {}
        for r in self._history:
            key = r.pipeline_type.value
            by_type[key] = by_type.get(key, 0) + 1
        return {
            "total_runs": total,
            "completed": completed,
            "failed": failed,
            "by_type": by_type,
            "registry": self._registry.stats(),
        }

    # ---- 服务注入 ----

    def inject_service(self, name: str, service: Any) -> "ResearchPipeline":
        """注入 Service"""
        self._executor.set_service(name, service)
        return self

    def inject_services(self, **services: Any) -> "ResearchPipeline":
        """批量注入 Service"""
        for name, svc in services.items():
            self._executor.set_service(name, svc)
        return self
