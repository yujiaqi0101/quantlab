"""
BacktestService — 异步回测服务

入口模型（domain 视角）：
    task = service.create_task(BacktestSpec(
        strategy_id="ma_cross",
        parameters={"fast": 20, "slow": 60},
        dataset="default",
        symbols=["AAPL", "MSFT", "NVDA"],
    ))
    # task 是 domain.Task
    # 真正的工作在 worker 线程里跑

便捷入口（API 视角）：
    resp = service.run_backtest(BacktestRequest(...))
    → BacktestResponse(task_id=..., status="PENDING")

为什么两种入口并存：
  - create_task(spec)        → Service 的"标准入口"，返回 domain.Task
  - run_backtest(req)        → 便捷包装，自动从 BacktestRequest → BacktestSpec
                              → 调 create_task

后续 Optimizer / Runtime / Validation 服务遵循同一模式：
    service.create_task(experiment_or_spec) -> Task

内部流程：
    1) TaskManager 创建 PENDING 任务
    2) 线程池异步执行
    3) 进度回调更新 task
    4) 完成后落库 Experiment
    5) task.result 填 experiment_id / metrics
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import (
    Future,
    ThreadPoolExecutor,
)
from typing import Any, Callable, Dict, List, Optional

from ..dto.backtest import (
    BacktestRequest,
    BacktestResponse,
    BacktestMetrics,
)
from ..dto.task import TaskType
from ..domain.task import Task
from ..domain.experiment import (
    Experiment,
    ExperimentResult,
)
from ..domain.backtest import (
    BacktestSpec,
    BacktestJob,
)
from ..runtime.task_manager import (
    TaskManager,
    get_task_manager,
)
from ..strategy_registry import (
    StrategyRegistry,
    get_strategy_registry,
)
from ..data.dataset_loader import (
    DataLoader,
    get_data_loader,
)


logger = logging.getLogger("quantlab.backtest_service")


class BacktestService:
    """
    回测服务

    可注入依赖：
      task_manager     任务管理器（默认全局单例）
      registry         策略注册表（默认全局单例）
      data_loader      数据加载器（默认全局单例）
      max_workers      工作线程数
      experiment_saver 把 (BacktestResult, BacktestRequest) 落库的回调
                        默认使用 ExperimentTracker
    """

    def __init__(
        self,
        task_manager: Optional[TaskManager] = None,
        registry: Optional[StrategyRegistry] = None,
        data_loader: Optional[DataLoader] = None,
        max_workers: int = 4,
        experiment_saver: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.task_manager: TaskManager = (
            task_manager or get_task_manager()
        )
        self.registry: StrategyRegistry = (
            registry or get_strategy_registry()
        )
        self.data_loader: DataLoader = (
            data_loader or get_data_loader()
        )
        self.max_workers = max_workers
        self.experiment_saver = experiment_saver

        # 进程内线程池
        # 任务可能跑很久，但比 ProcessPool 简单，跨平台稳定
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="bt-svc",
        )
        self._lock = threading.Lock()
        self._futures: Dict[str, Future] = {}

    # ---------------------------------------------------------
    # 对外 API
    # ---------------------------------------------------------
    def create_task(self, spec: BacktestSpec) -> Task:
        """
        Service 标准入口：提交一次回测，返回 domain.Task

        推荐所有调用方（Optimizer / API / CLI）走这里。
        内部：
          1) 构造 BacktestJob = (BacktestSpec, Experiment)
          2) TaskManager 创建 PENDING 任务
          3) 线程池执行
          4) 完成后把 experiment_id / metrics 写回 task.result
        """
        # 1) 注册表预检
        if not self.registry.has(spec.strategy_id):
            raise KeyError(
                f"strategy_id {spec.strategy_id!r} not registered. "
                f"known: {self.registry.list_ids()}"
            )

        # 2) 构造 Experiment（落库用）
        experiment = spec.to_experiment()

        # 3) 创建任务
        task = self.task_manager.create_task(
            type_=TaskType.BACKTEST.value,
            metadata={
                "strategy_id": spec.strategy_id,
                "parameters": dict(spec.parameters),
                "dataset": spec.dataset,
                "symbols": list(spec.symbols),
                "experiment_id": experiment.id,
            },
        )

        # 4) 提交线程池
        fut = self._executor.submit(
            self._execute, task.id, spec, experiment
        )
        with self._lock:
            self._futures[task.id] = fut

        def _done_callback(
            f: Future, tid: str = task.id
        ) -> None:
            with self._lock:
                self._futures.pop(tid, None)

        fut.add_done_callback(_done_callback)
        return task

    def run_backtest(
        self,
        request: BacktestRequest,
    ) -> BacktestResponse:
        """
        API 便捷入口：从 BacktestRequest 构造 BacktestSpec
        然后调 create_task，返回 BacktestResponse

        BacktestRequest 与 BacktestSpec 字段基本对齐，
        但 BacktestSpec 才是真正的"领域参数"。
        """
        spec = _request_to_spec(request)
        task = self.create_task(spec)
        return BacktestResponse(
            task_id=task.id,
            status=task.status,
            message="submitted",
        )

    def cancel(self, task_id: str) -> bool:
        """取消一个未完成的任务"""
        ok = self.task_manager.cancel(task_id)
        if ok:
            fut = self._futures.get(task_id)
            if fut is not None and not fut.done():
                # Python 没有强制 kill 线程的能力
                # 任务会在自己检查 cancel 标记后停止
                # 这里仅尝试 cancel Future
                fut.cancel()
        return ok

    def shutdown(self, wait: bool = True) -> None:
        """关闭线程池（应用退出时）"""
        self._executor.shutdown(wait=wait)

    # ---------------------------------------------------------
    # 内部执行
    # ---------------------------------------------------------
    def _execute(
        self,
        task_id: str,
        spec: BacktestSpec,
        experiment: Experiment,
    ) -> None:
        """
        在 worker 线程里跑回测

        阶段：
          10% 创建 strategy / engine
          30% 加载数据
          50% 跑回测
          80% 算指标
          95% 落库 Experiment
         100% 完成
        """
        try:
            self.task_manager.start(
                task_id, message="starting backtest"
            )

            # ---- 0) 检查取消 ----
            if self._is_cancelled(task_id):
                return

            # ---- 1) 创建 strategy + engine ----
            self.task_manager.update_progress(
                task_id, 10, "creating strategy & engine"
            )
            strategy = self.registry.create(
                spec.strategy_id,
                params=spec.parameters,
            )
            engine = self._build_engine(
                strategy,
                spec,
            )

            # ---- 2) 加载数据 ----
            self.task_manager.update_progress(
                task_id, 30, "loading data"
            )
            data = self.data_loader.load(
                dataset=spec.dataset,
                symbols=spec.symbols,
            )

            # ---- 2.5) 自动获取 dataset_version（如果未指定）----
            if not spec.dataset_version:
                try:
                    from ..dataset.registry import get_dataset_registry
                    ds_registry = get_dataset_registry()
                    ds_meta = ds_registry.get(spec.dataset)
                    if ds_meta is not None:
                        spec.dataset_version = ds_meta.version.version
                        experiment.dataset_version = spec.dataset_version
                except Exception:
                    pass

            # ---- 3) 跑回测 ----
            self.task_manager.update_progress(
                task_id, 50, "running backtest"
            )
            result = engine.run(
                strategy=strategy,
                data=data,
            )

            if self._is_cancelled(task_id):
                return

            # ---- 4) 算指标 ----
            self.task_manager.update_progress(
                task_id, 80, "computing metrics"
            )
            metrics_dto = _build_metrics(result)
            exp_result = _to_experiment_result(
                experiment.id, result, metrics_dto
            )

            # ---- 5) 落库 ----
            exp_id: Optional[str] = None
            if spec.save_experiment:
                self.task_manager.update_progress(
                    task_id, 95,
                    "saving experiment",
                )
                exp_id = self._save_experiment(
                    experiment=experiment,
                    exp_result=exp_result,
                    result=result,
                )
            else:
                exp_id = experiment.id  # 不入库时仍返回 ID

            # ---- 5.5) 缓存 BacktestResult（供 Experiment API 查 equity/trades）----
            from ..api.experiments import cache_backtest_result
            cache_backtest_result(exp_id, result)

            # ---- 6) 完成 ----
            self.task_manager.complete(
                task_id,
                result={
                    "experiment_id": exp_id,
                    "metrics": metrics_dto.to_dict(),
                    "status_detail": "ok",
                },
                message="backtest completed",
            )

        except Exception as exc:
            logger.exception(
                "backtest task %s failed", task_id
            )
            self.task_manager.fail(
                task_id,
                error=str(exc),
            )

    # ---------------------------------------------------------
    # 工具
    # ---------------------------------------------------------
    def _is_cancelled(self, task_id: str) -> bool:
        t = self.task_manager.get(task_id)
        return (
            t is not None
            and t.status == "CANCELLED"
        )

    def _build_engine(
        self,
        strategy: Any,
        spec: BacktestSpec,
    ) -> Any:
        """
        构造 BarEngine
        - 优先 backend=spec.engine（目前只支持 "bar"）
        - 其它走 bar
        """
        from ..engine import BarEngine
        from ..execution import (
            PercentageCommission,
            PercentageSlippage,
            TargetWeightExecution,
        )
        from ..portfolio_construction import TopN

        commission_bps = float(
            spec.commission_bps
        ) / 10000.0
        slippage_bps = float(
            spec.slippage_bps
        ) / 10000.0

        return BarEngine(
            strategy=strategy,
            portfolio_constructor=TopN(
                n=max(1, int(spec.top_n))
            ),
            execution_model=TargetWeightExecution(),
            commission_model=PercentageCommission(
                rate=commission_bps
            ),
            slippage_model=PercentageSlippage(
                rate=slippage_bps
            ),
            initial_cash=float(spec.initial_cash),
        )

    def _save_experiment(
        self,
        experiment: Experiment,
        exp_result: ExperimentResult,
        result: Any,
    ) -> Optional[str]:
        """
        把回测结果落库到 ExperimentTracker

        允许外部注入 saver；默认使用 ExperimentTracker。
        返回 experiment_id（失败返回 None）
        """
        if self.experiment_saver is not None:
            try:
                return self.experiment_saver(
                    experiment=experiment,
                    exp_result=exp_result,
                    result=result,
                )
            except Exception as exc:
                logger.warning(
                    "custom experiment_saver failed: %s",
                    exc,
                )
                return None

        try:
            from ..research import (
                ExperimentRecord,
                ExperimentTracker,
            )
            from ..research.tracker import (
                ExperimentResultV2,
            )

            tracker = ExperimentTracker(
                strategy_registry={
                    experiment.strategy_id:
                        self.registry.get_class(
                            experiment.strategy_id
                        ),
                }
            )
            record = ExperimentRecord(
                name=experiment.name,
                strategy_name=experiment.strategy_id,
                params=dict(experiment.parameters),
                tag=experiment.tag or "backtest_service",
                note=experiment.note,
            )
            # 落库后用真实 ID 覆盖
            experiment_id = record.id
            result_v2 = ExperimentResultV2(
                experiment=record,
                backtest_result=result,
            )
            tracker.repo.save(result_v2)
            return experiment_id
        except Exception as exc:
            logger.warning(
                "default experiment save failed: %s",
                exc,
            )
            return None


# -------------------------------------------------------------
# 内部辅助
# -------------------------------------------------------------
def _request_to_spec(req: BacktestRequest) -> BacktestSpec:
    """BacktestRequest（API 输入）→ BacktestSpec（领域参数）"""
    return BacktestSpec(
        strategy_id=req.strategy_id,
        parameters=dict(req.parameters),
        dataset=req.dataset,
        symbols=list(req.symbols),
        start=req.start,
        end=req.end,
        initial_cash=float(req.initial_cash),
        commission_bps=float(req.commission_bps),
        slippage_bps=float(req.slippage_bps),
        engine=req.engine,
        top_n=int(req.top_n),
        save_experiment=bool(req.save_experiment),
        experiment_name=req.experiment_name,
        dataset_version=req.dataset_version,
    )


def _to_experiment_result(
    experiment_id: str,
    result: Any,
    metrics_dto: BacktestMetrics,
) -> ExperimentResult:
    """从 BacktestResult 构造 domain.ExperimentResult"""
    return ExperimentResult(
        experiment_id=experiment_id,
        sharpe=metrics_dto.sharpe,
        total_return=metrics_dto.total_return,
        annualized_return=(
            metrics_dto.annualized_return
        ),
        max_drawdown=metrics_dto.max_drawdown,
        trade_count=metrics_dto.n_trades,
        win_rate=metrics_dto.win_rate,
        final_equity=metrics_dto.final_equity,
        profit_factor=metrics_dto.profit_factor,
        avg_trade=metrics_dto.avg_trade,
        source=_safe_get(result, "source", "event"),
        extra={
            "raw_metrics": metrics_dto.to_dict(),
        },
    )


def _build_metrics(result: Any) -> BacktestMetrics:
    """从 BacktestResult 抽 DTO 用指标（统一为 Python float）"""
    return BacktestMetrics(
        total_return=_to_float(
            _safe_get(result, "total_return", 0.0)
        ),
        annualized_return=_to_float(
            _safe_get(result, "annualized_return", 0.0)
        ),
        sharpe=_to_float(
            _safe_get(result, "sharpe", 0.0)
        ),
        max_drawdown=_to_float(
            _safe_get(result, "max_drawdown", 0.0)
        ),
        win_rate=_to_float(
            _safe_get(result, "win_rate", 0.0)
        ),
        profit_factor=_to_float(
            _safe_get(result, "profit_factor", 0.0)
        ),
        n_trades=int(
            _safe_get(result, "trade_count", 0) or 0
        ),
        avg_trade=_to_float(
            _safe_get(result, "avg_trade", 0.0)
        ),
        final_equity=_to_float(
            _safe_get(result, "final_equity", 0.0)
        ),
    )


def _safe_get(obj: Any, key: str, default: Any) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _to_float(v: Any) -> float:
    """numpy / pandas / 其它 → Python float"""
    if v is None:
        return 0.0
    try:
        # numpy scalar
        if hasattr(v, "item") and callable(v.item):
            try:
                return float(v.item())
            except Exception:
                pass
        return float(v)
    except (TypeError, ValueError):
        return 0.0
