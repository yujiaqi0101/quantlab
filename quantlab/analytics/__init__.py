"""
QuantLab Analytics — V4.6 分析平台

从 "赚没赚钱" 到 "为什么赚钱"
"""

from .attribution import AttributionAnalyzer
from .benchmark import BenchmarkAnalyzer
from .capacity import CapacityAnalyzer
from .exposure import ExposureAnalyzer
from .factor_exposure import FactorExposureAnalyzer
from .metrics import (
    AnalyticsEngine,
    CalmarMetric,
    KurtosisMetric,
    MaxDDMetric,
    Metric,
    MetricRegistry,
    ReturnMetric,
    AnnualizedReturnMetric,
    SharpeMetric,
    SkewnessMetric,
    SortinoMetric,
    VolatilityMetric,
    WinRateMetric,
)
from .turnover import TurnoverAnalyzer

# ── 向后兼容: 旧 analytics.py 的函数接口 ──
import numpy as np


def sharpe_ratio(equity_curve, annual_factor=252):
    """计算 Sharpe Ratio (向后兼容旧 analytics.py)"""
    equity_curve = np.array(equity_curve)
    returns = equity_curve[1:] / equity_curve[:-1] - 1
    if len(returns) == 0:
        return 0
    std = returns.std()
    if std == 0:
        return 0
    return (returns.mean() / std) * np.sqrt(annual_factor)


def max_drawdown(equity_curve):
    """计算最大回撤 (向后兼容旧 analytics.py)"""
    equity_curve = np.array(equity_curve)
    peak = np.maximum.accumulate(equity_curve)
    drawdown = (equity_curve - peak) / peak
    return drawdown.min()


def total_return(equity_curve):
    """计算总收益 (向后兼容旧 analytics.py)"""
    if len(equity_curve) == 0:
        return 0
    return equity_curve[-1] / equity_curve[0] - 1


__all__ = [
    # Analyzers
    "TurnoverAnalyzer",
    "ExposureAnalyzer",
    "BenchmarkAnalyzer",
    "AttributionAnalyzer",
    "FactorExposureAnalyzer",
    "CapacityAnalyzer",
    # Metrics
    "Metric",
    "SharpeMetric",
    "SortinoMetric",
    "MaxDDMetric",
    "ReturnMetric",
    "AnnualizedReturnMetric",
    "VolatilityMetric",
    "CalmarMetric",
    "WinRateMetric",
    "SkewnessMetric",
    "KurtosisMetric",
    "MetricRegistry",
    "AnalyticsEngine",
    # 向后兼容函数
    "sharpe_ratio",
    "max_drawdown",
    "total_return",
]
