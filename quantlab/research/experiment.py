"""
实验与报告 (research)
======================

Experiment: 封装一次回测运行，记录策略、参数、数据、结果
Report:     根据回测结果生成指标报告 (净值、收益、夏普、回撤等)

最小可用版本:
    - 年化收益率
    - 最大回撤
    - 夏普比率 (无风险利率默认 0)
    - 波动率
    - 日均收益率
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from quantlab.engine import BarEngine, BacktestResult
from quantlab.factors.context import FactorContext
from quantlab.portfolio_construction import PortfolioConstructor
from quantlab.signals.base import SignalStrategy

__all__ = ["Experiment", "Report", "ExperimentResult"]


@dataclass
class ExperimentResult:
    """实验结果。"""
    name: str
    params: Dict[str, Any]
    result: BacktestResult
    metrics: Dict[str, float] = field(default_factory=dict)


class Experiment:
    """回测实验封装。

    Args:
        name: 实验名称
    """

    def __init__(self, name: str = "experiment"):
        self.name = name

    def run(
        self,
        strategy: SignalStrategy,
        ctx: FactorContext,
        portfolio_constructor: PortfolioConstructor,
        engine: Optional[BarEngine] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> ExperimentResult:
        """执行回测。

        Args:
            strategy: 信号策略
            ctx: 因子数据上下文
            portfolio_constructor: 组合构造器
            engine: 回测引擎 (None 则新建默认 BarEngine)
            params: 参数记录 (用于追踪)

        Returns:
            ExperimentResult
        """
        if engine is None:
            engine = BarEngine(
                strategy=strategy,
                portfolio_constructor=portfolio_constructor,
            )
        result = engine.run(ctx)
        metrics = Report(result).metrics()
        return ExperimentResult(
            name=self.name,
            params=params or {},
            result=result,
            metrics=metrics,
        )


class Report:
    """回测报告生成器。

    Args:
        result: 回测结果
    """

    def __init__(self, result: BacktestResult):
        self.result = result

    def metrics(self) -> Dict[str, float]:
        """计算核心回测指标。"""
        eq = self.result.equity_curve
        if len(eq) < 2:
            return {}

        returns = eq.pct_change().dropna()
        n_days = len(eq)
        total_return = eq.iloc[-1] / eq.iloc[0] - 1.0

        # 年化 (按 252 交易日)
        ann_factor = 252.0 / n_days if n_days > 0 else 0
        ann_return = (1 + total_return) ** ann_factor - 1.0

        # 波动率 (日波动率年化)
        ann_vol = returns.std() * np.sqrt(252) if len(returns) > 0 else 0.0

        # 夏普比率 (无风险利率 0)
        sharpe = ann_return / ann_vol if ann_vol > 0 else 0.0

        # 最大回撤
        cummax = eq.cummax()
        drawdown = (eq - cummax) / cummax
        max_drawdown = float(drawdown.min())

        return {
            "total_return": float(total_return),
            "annual_return": float(ann_return),
            "annual_volatility": float(ann_vol),
            "sharpe": float(sharpe),
            "max_drawdown": max_drawdown,
            "n_days": int(n_days),
            "final_equity": float(eq.iloc[-1]),
            "n_trades": len(self.result.trades),
        }

    def generate(self) -> str:
        """生成文本报告。"""
        m = self.metrics()
        if not m:
            return f"[{self.result.equity_curve.name or 'equity'}] 数据不足"
        lines = [
            f"=== 回测报告 ===",
            f"交易日数:     {m['n_days']}",
            f"最终权益:     {m['final_equity']:.2f}",
            f"总收益率:     {m['total_return']:.2%}",
            f"年化收益率:   {m['annual_return']:.2%}",
            f"年化波动率:   {m['annual_volatility']:.2%}",
            f"夏普比率:     {m['sharpe']:.3f}",
            f"最大回撤:     {m['max_drawdown']:.2%}",
            f"成交笔数:     {m['n_trades']}",
        ]
        return "\n".join(lines)
