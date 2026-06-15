"""
ResearchPipeline — V4.5 研究流水线

职责：
  - 链式调用：数据 → 因子 → 信号 → 回测
  - 每一步自动缓存
  - 最终产出 Experiment

用法：
    pipeline = (
        ResearchPipeline(session)
        .load_dataset("default")
        .add_factor("MA", period=20)
        .add_factor("RSI", period=14)
        .create_signal(MACrossStrategy, fast=5, slow=20)
        .run_backtest(tag="pipeline_test")
    )
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type

import pandas as pd

from .notebook import ResearchSession
from .cache import ResearchCache
from .feature_store import FeatureStore
from .factor import FactorRegistry
from .artifact import ArtifactStore

logger = logging.getLogger("quantlab.research.pipeline")


# ------------------------------------------------------------------
# PipelineStep
# ------------------------------------------------------------------
@dataclass(slots=True)
class PipelineStep:
    """流水线步骤"""
    step_id: str
    step_type: str      # "load_dataset" / "add_factor" / "create_signal" / "run_backtest" / "custom"
    name: str
    params: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"   # "pending" / "running" / "success" / "error"
    output: Any = None
    error: str = ""


# ------------------------------------------------------------------
# ResearchPipeline
# ------------------------------------------------------------------
class ResearchPipeline:
    """
    研究流水线

    链式调用，每一步：
      1. 检查缓存
      2. 执行
      3. 保存结果
      4. 传递给下一步
    """

    def __init__(self, session: Optional[ResearchSession] = None) -> None:
        self.session = session or ResearchSession()
        self._steps: List[PipelineStep] = []
        self._results: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # 链式 API
    # ------------------------------------------------------------------
    def load_dataset(
        self,
        dataset: str = "default",
        symbols: Optional[List[str]] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> "ResearchPipeline":
        step = PipelineStep(
            step_id=f"step_{len(self._steps)}",
            step_type="load_dataset",
            name=f"load:{dataset}",
            params={"dataset": dataset, "symbols": symbols,
                    "start": start, "end": end},
        )
        self._steps.append(step)
        return self

    def add_factor(
        self,
        name: str,
        save_as: Optional[str] = None,
        **params,
    ) -> "ResearchPipeline":
        """
        添加因子计算步骤

        name: 因子注册名（如 "MA", "RSI"）
        save_as: 保存到 FeatureStore 的名称（默认 "factor_{name}"）
        params: 因子参数
        """
        step = PipelineStep(
            step_id=f"step_{len(self._steps)}",
            step_type="add_factor",
            name=f"factor:{name}",
            params={"factor_name": name, "save_as": save_as, **params},
        )
        self._steps.append(step)
        return self

    def create_signal(
        self,
        strategy_cls: Type,
        save_as: Optional[str] = None,
        **strategy_params,
    ) -> "ResearchPipeline":
        """
        创建信号步骤

        strategy_cls: 策略类（如 MACrossStrategy）
        strategy_params: 策略参数
        """
        step = PipelineStep(
            step_id=f"step_{len(self._steps)}",
            step_type="create_signal",
            name=f"signal:{strategy_cls.__name__}",
            params={"strategy_cls": strategy_cls,
                    "save_as": save_as, **strategy_params},
        )
        self._steps.append(step)
        return self

    def run_backtest(
        self,
        tag: str = "",
        note: str = "",
        engine: Optional[Any] = None,
    ) -> "ResearchPipeline":
        step = PipelineStep(
            step_id=f"step_{len(self._steps)}",
            step_type="run_backtest",
            name="backtest",
            params={"tag": tag, "note": note, "engine": engine},
        )
        self._steps.append(step)
        return self

    def custom(
        self,
        name: str,
        fn: Callable,
        **params,
    ) -> "ResearchPipeline":
        """
        自定义步骤

        fn 签名：fn(session, **params) -> Any
        """
        step = PipelineStep(
            step_id=f"step_{len(self._steps)}",
            step_type="custom",
            name=f"custom:{name}",
            params={"fn": fn, **params},
        )
        self._steps.append(step)
        return self

    # ------------------------------------------------------------------
    # 执行
    # ------------------------------------------------------------------
    def execute(self) -> Dict[str, Any]:
        """
        执行整个流水线

        返回每步的结果
        """
        results: Dict[str, Any] = {}

        for step in self._steps:
            step.status = "running"
            logger.info(f"pipeline step: {step.name}")

            try:
                output = self._execute_step(step, results)
                step.output = output
                step.status = "success"
                results[step.step_id] = output
                logger.info(f"pipeline step done: {step.name}")
            except Exception as e:
                step.error = f"{type(e).__name__}: {e}"
                step.status = "error"
                logger.error(f"pipeline step failed: {step.name} → {e}")
                break

        self._results = results
        return results

    def _execute_step(
        self,
        step: PipelineStep,
        results: Dict[str, Any],
    ) -> Any:
        if step.step_type == "load_dataset":
            return self.session.load_dataset(
                dataset=step.params.get("dataset", "default"),
                symbols=step.params.get("symbols"),
                start=step.params.get("start"),
                end=step.params.get("end"),
            )

        elif step.step_type == "add_factor":
            factor_name = step.params["factor_name"]
            save_as = step.params.get("save_as") or f"factor_{factor_name}"
            # 提取因子参数（去掉 factor_name / save_as）
            factor_params = {
                k: v for k, v in step.params.items()
                if k not in ("factor_name", "save_as")
            }
            # 计算
            value = self.session.compute_factor(factor_name, **factor_params)
            # 保存到 FeatureStore
            self.session.save_feature(
                save_as, value,
                formula=f"{factor_name}({factor_params})",
            )
            return value

        elif step.step_type == "create_signal":
            strategy_cls = step.params["strategy_cls"]
            save_as = step.params.get("save_as") or f"signal_{strategy_cls.__name__}"
            strategy_params = {
                k: v for k, v in step.params.items()
                if k not in ("strategy_cls", "save_as")
            }
            strategy = strategy_cls(**strategy_params)
            from quantlab.data import StrategyContext, factor_cache
            factor_cache.clear()
            ctx = StrategyContext(self.session.data, factor_cache)
            signal_df = strategy.signal(ctx)
            self.session.save_feature(
                save_as, signal_df,
                formula=f"{strategy_cls.__name__}({strategy_params})",
            )
            return signal_df

        elif step.step_type == "run_backtest":
            # 找最近一个 signal 步骤
            signal_step = None
            for s in self._steps:
                if s.step_type == "create_signal" and s.status == "success":
                    signal_step = s
            if signal_step is None:
                raise ValueError("no signal step found before backtest")

            # 找 strategy
            strategy_cls = signal_step.params["strategy_cls"]
            strategy_params = {
                k: v for k, v in signal_step.params.items()
                if k not in ("strategy_cls", "save_as")
            }
            strategy = strategy_cls(**strategy_params)

            return self.session.run_backtest(
                strategy=strategy,
                engine=step.params.get("engine"),
                tag=step.params.get("tag", ""),
                note=step.params.get("note", ""),
            )

        elif step.step_type == "custom":
            fn = step.params["fn"]
            custom_params = {
                k: v for k, v in step.params.items()
                if k != "fn"
            }
            return fn(self.session, **custom_params)

        else:
            raise ValueError(f"unknown step type: {step.step_type}")

    # ------------------------------------------------------------------
    # 状态
    # ------------------------------------------------------------------
    @property
    def steps(self) -> List[PipelineStep]:
        return list(self._steps)

    def stats(self) -> Dict[str, Any]:
        return {
            "total_steps": len(self._steps),
            "completed": sum(1 for s in self._steps if s.status == "success"),
            "failed": sum(1 for s in self._steps if s.status == "error"),
            "pending": sum(1 for s in self._steps if s.status == "pending"),
        }

    def describe(self) -> str:
        """打印流水线描述"""
        lines = [f"ResearchPipeline ({len(self._steps)} steps):"]
        for i, step in enumerate(self._steps):
            status_icon = {
                "pending": "[ ]", "running": "[>]",
                "success": "[OK]", "error": "[!!]",
            }.get(step.status, "[?]")
            lines.append(f"  {i+1}. {status_icon} {step.name} [{step.step_type}]")
        return "\n".join(lines)
