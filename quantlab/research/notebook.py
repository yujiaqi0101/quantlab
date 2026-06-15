"""
ResearchSession / Cell — V4.5 研究 Notebook 后端

职责：
  - ResearchSession: 一次研究会话（类似 Jupyter Kernel）
  - Cell: 代码/标记单元（执行 + 输出）
  - 统一管理 dataset / cache / artifacts / features
  - 与 ExperimentTracker 集成：run_backtest → 自动入库

用法：
    session = ResearchSession(name="alpha_research")
    session.load_dataset("default")

    # 执行 cell
    cell = session.add_code("rsi14 = rsi(ctx, 14)")
    session.execute(cell)

    # 保存特征
    session.save_feature("rsi14", rsi14_df)

    # 快速回测 → 自动生成 Experiment
    result = session.run_backtest(strategy=MACrossStrategy(fast=5, slow=20))
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd

from .cache import ResearchCache
from .feature_store import FeatureStore, FeatureMetadata
from .factor import FactorRegistry
from .artifact import ArtifactStore, Artifact

logger = logging.getLogger("quantlab.research.notebook")


# ------------------------------------------------------------------
# Cell
# ------------------------------------------------------------------
@dataclass(slots=True)
class Cell:
    """研究单元"""
    cell_id: str
    cell_type: str          # "code" / "markdown"
    source: str
    output: Any = None
    status: str = "idle"    # "idle" / "running" / "success" / "error"
    error: str = ""
    execution_count: int = 0


# ------------------------------------------------------------------
# ResearchSession
# ------------------------------------------------------------------
class ResearchSession:
    """
    研究会话

    不是 Jupyter Notebook，而是 Research Session：
      - 统一管理 dataset / cache / features / artifacts
      - Cell 执行模型
      - 快速验证 → 生成 Experiment
    """

    def __init__(
        self,
        name: str = "research",
        cache: Optional[ResearchCache] = None,
        feature_store: Optional[FeatureStore] = None,
        factor_registry: Optional[FactorRegistry] = None,
        artifact_store: Optional[ArtifactStore] = None,
        data_dir: str = "data",
    ) -> None:
        self.session_id = f"rs_{uuid.uuid4().hex[:8]}"
        self.name = name
        self.created_at = _now_iso()

        # 核心组件
        self.cache = cache or ResearchCache()
        self.feature_store = feature_store or FeatureStore(cache=self.cache)
        self.factor_registry = factor_registry or FactorRegistry()
        self.artifact_store = artifact_store or ArtifactStore()

        # 数据
        self._data: Dict[str, pd.DataFrame] = {}
        self._data_dir = data_dir
        self._current_dataset: str = ""

        # Cell 列表
        self._cells: List[Cell] = []
        self._execution_count: int = 0

        # 命名空间（cell 执行的 locals）
        self._namespace: Dict[str, Any] = {}

        # 自动注册默认因子
        self.factor_registry.register_defaults()

    # ------------------------------------------------------------------
    # Dataset API
    # ------------------------------------------------------------------
    def load_dataset(
        self,
        dataset: str = "default",
        symbols: Optional[List[str]] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        加载数据集

        内部用 DataLoader
        """
        from quantlab.data import DataLoader
        loader = DataLoader(data_dir=self._data_dir)
        self._data = loader.load(dataset=dataset, symbols=symbols,
                                 start=start, end=end)
        self._current_dataset = dataset
        # 注入 namespace
        self._namespace["data"] = self._data
        self._namespace["dataset"] = dataset
        logger.info(f"dataset loaded: {dataset} ({len(self._data)} symbols)")
        return self._data

    @property
    def data(self) -> Dict[str, pd.DataFrame]:
        return self._data

    def head(self, symbol: Optional[str] = None, n: int = 5) -> pd.DataFrame:
        """预览数据"""
        if not self._data:
            return pd.DataFrame()
        sym = symbol or list(self._data.keys())[0]
        return self._data[sym].head(n)

    def tail(self, symbol: Optional[str] = None, n: int = 5) -> pd.DataFrame:
        if not self._data:
            return pd.DataFrame()
        sym = symbol or list(self._data.keys())[0]
        return self._data[sym].tail(n)

    def sample(self, symbol: Optional[str] = None, n: int = 5) -> pd.DataFrame:
        if not self._data:
            return pd.DataFrame()
        sym = symbol or list(self._data.keys())[0]
        return self._data[sym].sample(n=min(n, len(self._data[sym])))

    def symbols(self) -> List[str]:
        return list(self._data.keys())

    def dataset_info(self) -> Dict[str, Any]:
        info = {}
        for sym, df in self._data.items():
            info[sym] = {
                "rows": len(df),
                "columns": list(df.columns),
                "start": str(df.index[0]) if len(df) > 0 else "",
                "end": str(df.index[-1]) if len(df) > 0 else "",
            }
        return info

    # ------------------------------------------------------------------
    # Cell API
    # ------------------------------------------------------------------
    def add_code(self, source: str) -> Cell:
        """添加代码 Cell"""
        cell = Cell(
            cell_id=f"cell_{uuid.uuid4().hex[:6]}",
            cell_type="code",
            source=source,
        )
        self._cells.append(cell)
        return cell

    def add_markdown(self, source: str) -> Cell:
        cell = Cell(
            cell_id=f"cell_{uuid.uuid4().hex[:6]}",
            cell_type="markdown",
            source=source,
        )
        self._cells.append(cell)
        return cell

    def execute(self, cell: Cell) -> Cell:
        """
        执行 Cell

        code cell: exec() 在 _namespace 里
        markdown cell: 不执行
        """
        if cell.cell_type == "markdown":
            cell.status = "success"
            return cell

        cell.status = "running"
        self._execution_count += 1
        cell.execution_count = self._execution_count

        # 注入常用对象
        self._namespace.update({
            "pd": pd,
            "data": self._data,
            "cache": self.cache,
            "feature_store": self.feature_store,
            "factor_registry": self.factor_registry,
            "artifact_store": self.artifact_store,
            "session": self,
        })

        try:
            # exec → 输出最后一个表达式
            import io
            import contextlib

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                exec(compile(cell.source, f"<{cell.cell_id}>", "exec"),
                     self._namespace)
            output = buf.getvalue().strip()
            cell.output = output if output else self._namespace.get("_", None)
            cell.status = "success"
        except Exception as e:
            cell.error = f"{type(e).__name__}: {e}"
            cell.output = None
            cell.status = "error"
            logger.warning(f"cell execute error [{cell.cell_id}]: {e}")

        return cell

    def execute_all(self) -> List[Cell]:
        """执行所有 Cell"""
        for cell in self._cells:
            self.execute(cell)
        return self._cells

    @property
    def cells(self) -> List[Cell]:
        return list(self._cells)

    # ------------------------------------------------------------------
    # Factor API
    # ------------------------------------------------------------------
    def compute_factor(self, name: str, **params) -> Any:
        """
        计算因子（全 symbol）

        自动构建 StrategyContext，返回 DataFrame(columns=symbols)
        """
        from quantlab.data import StrategyContext, factor_cache
        factor_cache.clear()
        ctx = StrategyContext(self._data, factor_cache)
        return self.factor_registry.compute_all(name, ctx, **params)

    # ------------------------------------------------------------------
    # Feature API
    # ------------------------------------------------------------------
    def save_feature(
        self,
        name: str,
        value: Any,
        **kwargs,
    ) -> FeatureMetadata:
        # 过滤掉 FeatureMetadata 不认识的字段
        valid_keys = {"dataset", "formula", "creator", "version",
                      "description", "tags", "dependencies"}
        filtered = {k: v for k, v in kwargs.items() if k in valid_keys}
        return self.feature_store.save(
            name, value,
            dataset=self._current_dataset,
            creator=f"session:{self.session_id}",
            **filtered,
        )

    def load_feature(self, name: str) -> Optional[Any]:
        return self.feature_store.load(name)

    # ------------------------------------------------------------------
    # Artifact API
    # ------------------------------------------------------------------
    def save_artifact(
        self,
        name: str,
        data: Any,
        kind: str = "custom",
        **kwargs,
    ) -> Artifact:
        return self.artifact_store.save(
            name, data, kind=kind,
            session_id=self.session_id,
            **kwargs,
        )

    # ------------------------------------------------------------------
    # Backtest API（关键：研究 → 实验 闭环）
    # ------------------------------------------------------------------
    def run_backtest(
        self,
        strategy: Any,
        engine: Optional[Any] = None,
        params: Optional[Dict] = None,
        tag: str = "",
        note: str = "",
    ) -> Any:
        """
        快速回测 → 自动生成 Experiment 入库

        这是 Research → Experiment 的关键接口：
          Notebook 中 run_backtest(...)
          → 不是直接回测
          → 生成 Experiment
          → 自动进入 ExperimentRegistry
        """
        from quantlab.engine import BarEngine
        from quantlab.portfolio_construction import EqualWeight
        from quantlab.execution import (
            TargetWeightExecution, PercentageCommission, PercentageSlippage,
        )
        from quantlab.research.tracker import ExperimentRecord, ExperimentTracker
        from quantlab.research.database import Database
        from quantlab.research.repository import ExperimentRepository

        if engine is None:
            engine = BarEngine(
                strategy=strategy,
                portfolio_constructor=EqualWeight(),
                execution_model=TargetWeightExecution(),
                commission_model=PercentageCommission(),
                slippage_model=PercentageSlippage(),
            )

        # 构建 ExperimentRecord
        strategy_name = type(strategy).__name__
        record = ExperimentRecord(
            name=f"research_{self.session_id}",
            strategy_name=strategy_name,
            params=params or {},
            tag=tag or "research",
            note=note or f"from session {self.name}",
        )

        # 用 ExperimentTracker 跑 + 入库
        db = Database()
        try:
            db._init_schema()
        except Exception:
            # schema 不兼容时重建
            db.reset()
        repo = ExperimentRepository(db)
        tracker = ExperimentTracker(
            strategy_registry={strategy_name: type(strategy)},
            repository=repo,
        )
        result = tracker.run(record, engine, self._data)

        logger.info(
            f"backtest done: {strategy_name} "
            f"return={result.metrics().get('total_return', 'N/A'):.2%} "
            f"sharpe={result.metrics().get('sharpe', 'N/A'):.2f}"
        )
        return result

    # ------------------------------------------------------------------
    # 状态
    # ------------------------------------------------------------------
    def stats(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "name": self.name,
            "cells": len(self._cells),
            "symbols": len(self._data),
            "dataset": self._current_dataset,
            "features": len(self.feature_store.list_features()),
            "artifacts": len(self.artifact_store.list_artifacts()),
            "factors": len(self.factor_registry.list_factors()),
            "cache": self.cache.stats(),
        }

    def __repr__(self) -> str:
        return (
            f"ResearchSession(id={self.session_id}, name={self.name}, "
            f"symbols={len(self._data)}, cells={len(self._cells)})"
        )


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------
def _now_iso() -> str:
    import datetime
    return datetime.datetime.now().isoformat(timespec="seconds")
