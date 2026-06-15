"""
Metrics Registry & Analytics Engine — V4.6

MetricRegistry: 注册 SharpeMetric / SortinoMetric / MaxDDMetric 等，统一 compute()
AnalyticsEngine: run(experiment) → 自动生成 metrics.json / attribution.json / exposure.json / turnover.json
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Type

import numpy as np
import pandas as pd

from .attribution import AttributionAnalyzer
from .benchmark import BenchmarkAnalyzer
from .capacity import CapacityAnalyzer
from .exposure import ExposureAnalyzer
from .factor_exposure import FactorExposureAnalyzer
from .turnover import TurnoverAnalyzer


# ──────────────────────────────────────────────
# Metric ABC + 内置指标
# ──────────────────────────────────────────────

class Metric(ABC):
    """指标基类，所有指标统一 compute() 接口"""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    def category(self) -> str:
        return "general"

    @abstractmethod
    def compute(self, equity_curve: np.ndarray, **kwargs) -> float:
        pass


class SharpeMetric(Metric):
    name = "sharpe"
    category = "risk_adjusted"

    def compute(self, equity_curve: np.ndarray, **kwargs) -> float:
        annual_factor = kwargs.get("annual_factor", 252)
        risk_free_rate = kwargs.get("risk_free_rate", 0.0)
        if len(equity_curve) < 2:
            return 0.0
        returns = equity_curve[1:] / equity_curve[:-1] - 1
        if len(returns) == 0 or returns.std() == 0:
            return 0.0
        excess = returns - risk_free_rate / annual_factor
        return float(excess.mean() / returns.std() * np.sqrt(annual_factor))


class SortinoMetric(Metric):
    name = "sortino"
    category = "risk_adjusted"

    def compute(self, equity_curve: np.ndarray, **kwargs) -> float:
        annual_factor = kwargs.get("annual_factor", 252)
        risk_free_rate = kwargs.get("risk_free_rate", 0.0)
        if len(equity_curve) < 2:
            return 0.0
        returns = equity_curve[1:] / equity_curve[:-1] - 1
        if len(returns) == 0:
            return 0.0
        excess = returns - risk_free_rate / annual_factor
        downside = returns[returns < 0]
        if len(downside) == 0 or downside.std() == 0:
            return float("inf") if excess.mean() > 0 else 0.0
        return float(excess.mean() / downside.std() * np.sqrt(annual_factor))


class MaxDDMetric(Metric):
    name = "max_drawdown"
    category = "risk"

    def compute(self, equity_curve: np.ndarray, **kwargs) -> float:
        if len(equity_curve) < 2:
            return 0.0
        peak = np.maximum.accumulate(equity_curve)
        drawdown = (equity_curve - peak) / peak
        return float(drawdown.min())


class ReturnMetric(Metric):
    name = "total_return"
    category = "return"

    def compute(self, equity_curve: np.ndarray, **kwargs) -> float:
        if len(equity_curve) < 2:
            return 0.0
        return float(equity_curve[-1] / equity_curve[0] - 1)


class AnnualizedReturnMetric(Metric):
    name = "annualized_return"
    category = "return"

    def compute(self, equity_curve: np.ndarray, **kwargs) -> float:
        annual_factor = kwargs.get("annual_factor", 252)
        if len(equity_curve) < 2:
            return 0.0
        total = equity_curve[-1] / equity_curve[0]
        n_periods = len(equity_curve) - 1
        return float(total ** (annual_factor / n_periods) - 1) if n_periods > 0 else 0.0


class VolatilityMetric(Metric):
    name = "volatility"
    category = "risk"

    def compute(self, equity_curve: np.ndarray, **kwargs) -> float:
        annual_factor = kwargs.get("annual_factor", 252)
        if len(equity_curve) < 2:
            return 0.0
        returns = equity_curve[1:] / equity_curve[:-1] - 1
        return float(returns.std() * np.sqrt(annual_factor))


class CalmarMetric(Metric):
    name = "calmar"
    category = "risk_adjusted"

    def compute(self, equity_curve: np.ndarray, **kwargs) -> float:
        annual_factor = kwargs.get("annual_factor", 252)
        if len(equity_curve) < 2:
            return 0.0
        total = equity_curve[-1] / equity_curve[0]
        n_periods = len(equity_curve) - 1
        ann_ret = total ** (annual_factor / n_periods) - 1 if n_periods > 0 else 0.0
        peak = np.maximum.accumulate(equity_curve)
        mdd = ((equity_curve - peak) / peak).min()
        return float(ann_ret / abs(mdd)) if mdd != 0 else 0.0


class WinRateMetric(Metric):
    name = "win_rate"
    category = "trade"

    def compute(self, equity_curve: np.ndarray, **kwargs) -> float:
        returns = kwargs.get("returns")
        if returns is None and len(equity_curve) >= 2:
            returns = equity_curve[1:] / equity_curve[:-1] - 1
        if returns is None or len(returns) == 0:
            return 0.0
        return float(np.sum(returns > 0) / len(returns))


class SkewnessMetric(Metric):
    name = "skewness"
    category = "distribution"

    def compute(self, equity_curve: np.ndarray, **kwargs) -> float:
        if len(equity_curve) < 3:
            return 0.0
        returns = equity_curve[1:] / equity_curve[:-1] - 1
        return float(pd.Series(returns).skew())


class KurtosisMetric(Metric):
    name = "kurtosis"
    category = "distribution"

    def compute(self, equity_curve: np.ndarray, **kwargs) -> float:
        if len(equity_curve) < 4:
            return 0.0
        returns = equity_curve[1:] / equity_curve[:-1] - 1
        return float(pd.Series(returns).kurtosis())


# ──────────────────────────────────────────────
# MetricRegistry
# ──────────────────────────────────────────────

class MetricRegistry:
    """
    指标注册中心

    用法：
        registry = MetricRegistry()
        registry.register(SharpeMetric)
        result = registry.compute_all(equity_curve)
    """

    def __init__(self):
        self._metrics: Dict[str, Metric] = {}

    def register(self, metric_cls: Type[Metric]) -> None:
        """注册指标类"""
        instance = metric_cls()
        self._metrics[instance.name] = instance

    def register_function(self, name: str, fn: Callable, category: str = "custom") -> None:
        """注册自定义函数指标"""
        self._metrics[name] = _FunctionMetric(name, fn, category)

    def unregister(self, name: str) -> None:
        """移除指标"""
        self._metrics.pop(name, None)

    def get(self, name: str) -> Optional[Metric]:
        """获取指标实例"""
        return self._metrics.get(name)

    def list(self) -> List[str]:
        """列出所有指标名"""
        return list(self._metrics.keys())

    def list_by_category(self) -> Dict[str, List[str]]:
        """按类别列出指标"""
        result: Dict[str, List[str]] = {}
        for name, m in self._metrics.items():
            result.setdefault(m.category, []).append(name)
        return result

    def compute(self, name: str, equity_curve: np.ndarray, **kwargs) -> float:
        """计算单个指标"""
        m = self._metrics.get(name)
        if m is None:
            raise KeyError(f"Metric '{name}' not registered")
        return m.compute(np.array(equity_curve, dtype=float), **kwargs)

    def compute_all(self, equity_curve: Any, **kwargs) -> Dict[str, float]:
        """计算所有指标"""
        ec = np.array(equity_curve, dtype=float)
        results = {}
        for name, m in self._metrics.items():
            try:
                results[name] = round(m.compute(ec, **kwargs), 6)
            except Exception as e:
                results[name] = None
        return results

    def stats(self) -> Dict[str, Any]:
        """注册统计"""
        return {
            "total_metrics": len(self._metrics),
            "categories": self.list_by_category(),
        }


class _FunctionMetric(Metric):
    """函数式指标包装"""

    def __init__(self, metric_name: str, fn: Callable, category: str):
        self._name = metric_name
        self._fn = fn
        self._category = category

    @property
    def name(self) -> str:
        return self._name

    @property
    def category(self) -> str:
        return self._category

    def compute(self, equity_curve: np.ndarray, **kwargs) -> float:
        return float(self._fn(equity_curve, **kwargs))


# ──────────────────────────────────────────────
# AnalyticsEngine
# ──────────────────────────────────────────────

class AnalyticsEngine:
    """
    统一分析引擎

    用法：
        engine = AnalyticsEngine()
        result = engine.run(
            equity_curve=...,
            weights_history=...,
            fills=...,
            benchmark_equity=...,
        )

    集成到 ExperimentRepository.save() 之后自动执行
    """

    def __init__(self, metric_registry: Optional[MetricRegistry] = None):
        self._registry = metric_registry or self._default_registry()
        self._turnover = TurnoverAnalyzer()
        self._exposure = ExposureAnalyzer()
        self._benchmark = BenchmarkAnalyzer()
        self._attribution = AttributionAnalyzer()
        self._factor_exposure = FactorExposureAnalyzer()
        self._capacity = CapacityAnalyzer()

    @staticmethod
    def _default_registry() -> MetricRegistry:
        """默认注册所有内置指标"""
        reg = MetricRegistry()
        reg.register(SharpeMetric)
        reg.register(SortinoMetric)
        reg.register(MaxDDMetric)
        reg.register(ReturnMetric)
        reg.register(AnnualizedReturnMetric)
        reg.register(VolatilityMetric)
        reg.register(CalmarMetric)
        reg.register(WinRateMetric)
        reg.register(SkewnessMetric)
        reg.register(KurtosisMetric)
        return reg

    @property
    def registry(self) -> MetricRegistry:
        return self._registry

    def run(
        self,
        equity_curve: Any,
        weights_history: Any = None,
        fills: Optional[List[Dict]] = None,
        trades: Optional[List[Dict]] = None,
        benchmark_equity: Any = None,
        factor_values: Optional[Dict[str, Dict[str, float]]] = None,
        volume_data: Optional[Dict[str, pd.Series]] = None,
        risk_free_rate: float = 0.0,
        annual_factor: int = 252,
    ) -> Dict[str, Any]:
        """
        运行全部分析

        返回：{
            "metrics": {...},
            "turnover": {...},
            "exposure": {...},
            "attribution": {...},
            "benchmark": {...},
            "factor_exposure": {...},
            "capacity": {...},
        }
        """
        result: Dict[str, Any] = {}

        # 1) Metrics
        result["metrics"] = self._registry.compute_all(
            equity_curve,
            risk_free_rate=risk_free_rate,
            annual_factor=annual_factor,
        )

        # 2) Turnover
        if weights_history is not None:
            result["turnover"] = self._turnover.analyze(weights_history)
        else:
            result["turnover"] = {}

        # 3) Exposure
        if weights_history is not None:
            result["exposure"] = self._exposure.analyze(weights_history)
        else:
            result["exposure"] = {}

        # 4) Attribution
        if fills:
            result["attribution"] = self._attribution.analyze(fills)
        elif trades:
            result["attribution"] = self._attribution.analyze_trades(trades)
        else:
            result["attribution"] = {}

        # 5) Benchmark
        if benchmark_equity is not None:
            result["benchmark"] = self._benchmark.analyze(
                equity_curve, benchmark_equity,
                risk_free_rate=risk_free_rate,
                annual_factor=annual_factor,
            )
        else:
            result["benchmark"] = {}

        # 6) Factor Exposure
        if factor_values is not None and weights_history is not None:
            if isinstance(weights_history, pd.DataFrame):
                weights = weights_history.iloc[-1].to_dict() if len(weights_history) > 0 else {}
            elif isinstance(weights_history, list) and len(weights_history) > 0:
                weights = weights_history[-1]
            else:
                weights = {}
            result["factor_exposure"] = self._factor_exposure.analyze(weights, factor_values)
        else:
            result["factor_exposure"] = {}

        # 7) Capacity
        if trades:
            result["capacity"] = self._capacity.analyze(trades, volume_data)
        elif weights_history is not None:
            result["capacity"] = self._capacity.analyze_from_weights(
                weights_history, equity_curve, volume_data,
            )
        else:
            result["capacity"] = {}

        return result

    def run_and_save(
        self,
        output_dir: str,
        equity_curve: Any,
        weights_history: Any = None,
        fills: Optional[List[Dict]] = None,
        trades: Optional[List[Dict]] = None,
        benchmark_equity: Any = None,
        factor_values: Optional[Dict[str, Dict[str, float]]] = None,
        volume_data: Optional[Dict[str, pd.Series]] = None,
        risk_free_rate: float = 0.0,
        annual_factor: int = 252,
    ) -> Dict[str, str]:
        """
        运行全部分析并保存为 JSON

        output_dir: 输出目录 (如 experiments/exp_001/)
        返回：{文件名: 文件路径}
        """
        result = self.run(
            equity_curve=equity_curve,
            weights_history=weights_history,
            fills=fills,
            trades=trades,
            benchmark_equity=benchmark_equity,
            factor_values=factor_values,
            volume_data=volume_data,
            risk_free_rate=risk_free_rate,
            annual_factor=annual_factor,
        )

        os.makedirs(output_dir, exist_ok=True)

        saved = {}
        for key, data in result.items():
            if not data:
                continue
            filepath = os.path.join(output_dir, f"{key}.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            saved[key] = filepath

        return saved
