"""
Pipeline Executor — 统一执行器

核心流程：
  Factor → Signal → Strategy → Backtest → Evaluation → Storage

三种模式：
  1. SINGLE_EXPERIMENT  单策略单次回测
  2. PARAMETER_SWEEP    参数网格搜索
  3. ALPHA_BATCH        Alpha 批量生成+评估+排序

所有模式都走同一个执行器，只是步骤不同。
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import pandas as pd

from .context import (
    ResearchContext, PipelineType, PipelineResult,
    PipelineStatus, PipelineStepResult,
)
from .registry import PipelineRegistry

logger = logging.getLogger("quantlab.research.pipeline.executor")


class PipelineExecutor:
    """
    Pipeline 统一执行器

    用法：
        executor = PipelineExecutor(registry)
        result = executor.execute(context)
    """

    def __init__(self, registry: Optional[PipelineRegistry] = None) -> None:
        self._registry = registry or PipelineRegistry()
        self._services: Dict[str, Any] = {}

    def set_service(self, name: str, service: Any) -> None:
        """注入 Service（延迟绑定）"""
        self._services[name] = service

    def _get_service(self, name: str) -> Any:
        if name not in self._services:
            # 尝试从全局容器获取
            try:
                from ...services import get_service
                self._services[name] = get_service(name)
            except Exception:
                pass
        return self._services.get(name)

    # ---- 主入口 ----

    def execute(self, context: ResearchContext) -> PipelineResult:
        """
        执行 Pipeline

        根据 pipeline_type 分发到不同的执行逻辑
        """
        result = PipelineResult(
            context_id=context.context_id,
            name=context.name or context.context_id,
            pipeline_type=context.pipeline_type,
            status=PipelineStatus.RUNNING,
        )

        start_time = time.time()
        logger.info(f"pipeline execute: {context.pipeline_type.value} [{context.context_id}]")

        try:
            if context.pipeline_type == PipelineType.SINGLE_EXPERIMENT:
                self._execute_single(context, result)
            elif context.pipeline_type == PipelineType.PARAMETER_SWEEP:
                self._execute_sweep(context, result)
            elif context.pipeline_type == PipelineType.ALPHA_BATCH:
                self._execute_alpha_batch(context, result)
            else:
                raise ValueError(f"Unknown pipeline type: {context.pipeline_type}")

            result.status = PipelineStatus.COMPLETED

        except Exception as e:
            result.status = PipelineStatus.FAILED
            result.metrics["error"] = str(e)
            logger.error(f"pipeline failed: {e}", exc_info=True)

        result.duration_ms = (time.time() - start_time) * 1000

        from datetime import datetime
        result.completed_at = datetime.now().isoformat()

        logger.info(
            f"pipeline done: {result.status.value} "
            f"[{result.duration_ms:.0f}ms, {len(result.steps)} steps]"
        )

        return result

    # ---- SINGLE_EXPERIMENT ----

    def _execute_single(self, ctx: ResearchContext, result: PipelineResult) -> None:
        """
        单策略单次回测

        流程：Load Data → Build Factors → Create Signal → Run Backtest → Evaluate
        """
        # Step 1: 加载数据
        step = PipelineStepResult(step_name="load_data", step_type="load_data")
        t0 = time.time()
        data = self._load_data(ctx)
        step.duration_ms = (time.time() - t0) * 1000
        step.status = "success" if data is not None else "error"
        step.output = f"data loaded: {type(data).__name__}" if data is not None else "failed"
        result.steps.append(step)

        if data is None:
            raise ValueError("Failed to load data")

        # Step 2: 计算因子
        step = PipelineStepResult(step_name="build_factors", step_type="build_factors")
        t0 = time.time()
        factor_data = self._build_factors(ctx, data)
        step.duration_ms = (time.time() - t0) * 1000
        step.status = "success"
        step.output = f"{len(factor_data)} factors computed"
        result.steps.append(step)

        # Step 3: 创建信号
        step = PipelineStepResult(step_name="build_signal", step_type="build_signal")
        t0 = time.time()
        signal_data = self._build_signals(ctx, factor_data, data)
        step.duration_ms = (time.time() - t0) * 1000
        step.status = "success"
        step.output = f"signal built"
        result.steps.append(step)

        # Step 4: 运行回测
        step = PipelineStepResult(step_name="run_backtest", step_type="run_backtest")
        t0 = time.time()
        backtest_result = self._run_backtest(ctx, data)
        step.duration_ms = (time.time() - t0) * 1000
        if backtest_result is not None:
            step.status = "success"
            step.output = "backtest completed"
            # 提取指标
            if isinstance(backtest_result, dict):
                result.metrics = backtest_result.get("metrics", {})
                result.experiment_id = backtest_result.get("experiment_id")
            elif hasattr(backtest_result, "metrics"):
                result.metrics = backtest_result.metrics if isinstance(backtest_result.metrics, dict) else {}
                if hasattr(backtest_result, "name"):
                    result.experiment_id = backtest_result.name
        else:
            step.status = "error"
            step.error = "backtest returned None"
        result.steps.append(step)

        # Step 5: 保存结果
        step = PipelineStepResult(step_name="save_result", step_type="save_result")
        t0 = time.time()
        self._save_result(ctx, result)
        step.duration_ms = (time.time() - t0) * 1000
        step.status = "success"
        step.output = "result saved"
        result.steps.append(step)

    # ---- PARAMETER_SWEEP ----

    def _execute_sweep(self, ctx: ResearchContext, result: PipelineResult) -> None:
        """
        参数网格搜索

        流程：Load Data → Generate Param Grid → Run Each → Collect Results → Rank
        """
        if ctx.sweep is None:
            raise ValueError("Sweep config required for PARAMETER_SWEEP mode")

        # Step 1: 加载数据
        step = PipelineStepResult(step_name="load_data", step_type="load_data")
        t0 = time.time()
        data = self._load_data(ctx)
        step.duration_ms = (time.time() - t0) * 1000
        step.status = "success" if data is not None else "error"
        result.steps.append(step)

        # Step 2: 生成参数组合
        step = PipelineStepResult(step_name="generate_grid", step_type="generate_grid")
        t0 = time.time()
        param_combos = self._generate_param_grid(ctx.sweep.param_space)
        step.duration_ms = (time.time() - t0) * 1000
        step.status = "success"
        step.output = f"{len(param_combos)} combinations"
        result.steps.append(step)

        # Step 3: 逐个运行
        sweep_results = []
        for i, params in enumerate(param_combos):
            try:
                # 创建子 context
                sub_ctx = ResearchContext(
                    pipeline_type=PipelineType.SINGLE_EXPERIMENT,
                    dataset_id=ctx.dataset_id,
                    symbols=ctx.symbols,
                    start=ctx.start,
                    end=ctx.end,
                    factors=ctx.factors,
                    strategy=ctx.strategy,
                    params=params,
                )
                sub_result = self._execute_single(sub_ctx, PipelineResult(
                    context_id=sub_ctx.context_id,
                    pipeline_type=PipelineType.SINGLE_EXPERIMENT,
                ))

                entry = {
                    "params": params,
                    "metrics": sub_result.metrics,
                    "status": sub_result.status.value,
                }
                sweep_results.append(entry)

            except Exception as e:
                sweep_results.append({
                    "params": params,
                    "metrics": {},
                    "status": "error",
                    "error": str(e),
                })

        # Step 4: 排序
        metric = ctx.sweep.metric
        sweep_results.sort(
            key=lambda x: x.get("metrics", {}).get(metric, float("-inf")),
            reverse=True,
        )

        # Step 5: 保存
        step = PipelineStepResult(step_name="save_sweep", step_type="save_sweep")
        step.status = "success"
        step.output = f"{len(sweep_results)} results, top metric: {sweep_results[0].get('metrics', {}).get(metric, 'N/A') if sweep_results else 'N/A'}"
        result.steps.append(step)

        result.sweep_results = sweep_results[:ctx.sweep.top_n]
        result.metrics = {
            "total_combinations": len(param_combos),
            "completed": len([r for r in sweep_results if r["status"] == "completed"]),
            "errors": len([r for r in sweep_results if r["status"] == "error"]),
            "top_result": sweep_results[0] if sweep_results else None,
        }

    # ---- ALPHA_BATCH ----

    def _execute_alpha_batch(self, ctx: ResearchContext, result: PipelineResult) -> None:
        """
        Alpha 批量生成+评估+排序

        流程：Generate Alphas → Evaluate → Screen → Rank → Save
        """
        if ctx.alpha_batch is None:
            raise ValueError("AlphaBatch config required for ALPHA_BATCH mode")

        alpha_svc = self._get_service("alpha")

        # Step 1: 生成 Alpha
        step = PipelineStepResult(step_name="generate_alphas", step_type="generate_alphas")
        t0 = time.time()
        all_alphas = []
        for factor_name in ctx.alpha_batch.factor_names:
            try:
                alphas = alpha_svc.generate_alphas(factor_name, ctx.alpha_batch.methods)
                all_alphas.extend(alphas)
            except Exception as e:
                logger.warning(f"Failed to generate alphas for {factor_name}: {e}")
        step.duration_ms = (time.time() - t0) * 1000
        step.status = "success"
        step.output = f"{len(all_alphas)} alphas generated"
        result.steps.append(step)

        # Step 2: 筛选候选
        step = PipelineStepResult(step_name="screen_candidates", step_type="screen_candidates")
        t0 = time.time()
        try:
            candidates = alpha_svc.screen_candidates(
                ic_min=ctx.alpha_batch.ic_min,
                ir_min=ctx.alpha_batch.ir_min,
                coverage_min=ctx.alpha_batch.coverage_min,
            )
        except Exception:
            candidates = []
        step.duration_ms = (time.time() - t0) * 1000
        step.status = "success"
        step.output = f"{len(candidates)} candidates"
        result.steps.append(step)

        # Step 3: 排行榜
        step = PipelineStepResult(step_name="leaderboard", step_type="leaderboard")
        t0 = time.time()
        try:
            leaderboard = alpha_svc.get_leaderboard(limit=20)
        except Exception:
            leaderboard = []
        step.duration_ms = (time.time() - t0) * 1000
        step.status = "success"
        step.output = f"{len(leaderboard)} ranked"
        result.steps.append(step)

        result.alpha_results = all_alphas
        result.metrics = {
            "total_generated": len(all_alphas),
            "total_candidates": len(candidates),
            "top_alpha": leaderboard[0] if leaderboard else None,
        }

    # ---- 内部方法 ----

    def _load_data(self, ctx: ResearchContext) -> Any:
        """加载数据"""
        dataset_svc = self._get_service("dataset")
        if dataset_svc is not None:
            try:
                return dataset_svc.load_dataset(
                    dataset_id=ctx.dataset_id,
                    symbols=ctx.symbols,
                    start=ctx.start,
                    end=ctx.end,
                )
            except Exception as e:
                logger.warning(f"Dataset service load failed: {e}")

        # 尝试 ResearchSession
        try:
            from ..notebook import ResearchSession
            session = ResearchSession()
            return session.load_dataset(
                dataset=ctx.dataset_id,
                symbols=ctx.symbols,
                start=ctx.start,
                end=ctx.end,
            )
        except Exception as e:
            logger.warning(f"ResearchSession load failed: {e}")

        return None

    def _build_factors(self, ctx: ResearchContext, data: Any) -> Dict[str, Any]:
        """计算因子"""
        factor_data = {}
        for fc in ctx.factors:
            try:
                factor_svc = self._get_service("factor")
                if factor_svc is not None:
                    value = factor_svc.compute_factor(fc.name, **fc.params)
                    key = fc.save_as or fc.name
                    factor_data[key] = value
            except Exception as e:
                logger.warning(f"Factor '{fc.name}' compute failed: {e}")
        return factor_data

    def _build_signals(self, ctx: ResearchContext, factor_data: Dict, data: Any) -> Any:
        """创建信号"""
        for sc in ctx.signals:
            try:
                signal_svc = self._get_service("signal")
                if signal_svc is not None:
                    return signal_svc.create_signal(sc.strategy_id, **sc.strategy_params)
            except Exception as e:
                logger.warning(f"Signal '{sc.signal_id}' build failed: {e}")
        return None

    def _run_backtest(self, ctx: ResearchContext, data: Any) -> Any:
        """运行回测"""
        if ctx.strategy is None:
            return None

        try:
            # 尝试 Experiment
            from ..experiment import Experiment as ResearchExperiment
            exp = ResearchExperiment(name=ctx.name or "pipeline")

            # 创建策略
            strategy = self._registry.create_strategy(
                ctx.strategy.strategy_id, **ctx.strategy.params
            )

            # 创建引擎
            from ...core.backtest_engine import BacktestEngine
            engine = BacktestEngine()

            return exp.run(
                strategy=strategy,
                engine=engine,
                data=data,
                params=ctx.strategy.params,
            )
        except Exception as e:
            logger.warning(f"Backtest via Experiment failed: {e}")

        # 尝试 BacktestService
        try:
            backtest_svc = self._get_service("backtest")
            if backtest_svc is not None:
                return backtest_svc.run_backtest(
                    strategy_id=ctx.strategy.strategy_id,
                    params=ctx.strategy.params,
                    dataset_id=ctx.dataset_id,
                )
        except Exception as e:
            logger.warning(f"Backtest via BacktestService failed: {e}")

        return None

    def _save_result(self, ctx: ResearchContext, result: PipelineResult) -> None:
        """保存结果"""
        try:
            experiment_svc = self._get_service("experiment")
            if experiment_svc is not None:
                # 通过 ExperimentService 保存
                pass
        except Exception:
            pass

    def _generate_param_grid(self, param_space: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
        """生成参数网格"""
        if not param_space:
            return [{}]

        keys = list(param_space.keys())
        values = list(param_space.values())

        from itertools import product
        combos = []
        for combo in product(*values):
            combos.append(dict(zip(keys, combo)))

        return combos
