"""
ML Backtest Adapter — ML 策略回测适配器

ML Lab M5 第八部分：ML Strategy 必须接入 Research Studio

  支持：
    backtest(strategy="LGBM_Momentum")

  直接输出：
    Sharpe
    Return
    MaxDD

  这样：
    传统策略 和 ML 策略 统一比较。
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from .ml_strategy import MLStrategyV2
from .strategy_builder import StrategyBuilder, get_strategy_builder

logger = logging.getLogger("quantlab.ml.strategy.backtest_adapter")


# ------------------------------------------------------------------
# Backtest Result
# ------------------------------------------------------------------

@dataclass
class BacktestResult:
    """回测结果"""
    backtest_id: str = field(default_factory=lambda: f"BT-{uuid.uuid4().hex[:8]}")
    strategy_id: str = ""
    strategy_name: str = ""
    symbol: str = ""

    # 指标
    total_return: float = 0.0
    annual_return: float = 0.0
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    n_trades: int = 0
    n_bars: int = 0

    # 曲线
    equity_curve: Optional[pd.Series] = None
    positions: Optional[pd.Series] = None
    signals: Optional[pd.Series] = None
    predictions: Optional[pd.Series] = None

    # 元信息
    initial_capital: float = 100000.0
    final_equity: float = 100000.0
    duration_days: int = 0
    created_at: str = ""

    # 风控状态
    risk_status: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self, include_series: bool = False) -> Dict[str, Any]:
        d = {
            "backtest_id": self.backtest_id,
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "symbol": self.symbol,
            "total_return": self.total_return,
            "annual_return": self.annual_return,
            "sharpe": self.sharpe,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "n_trades": self.n_trades,
            "n_bars": self.n_bars,
            "initial_capital": self.initial_capital,
            "final_equity": self.final_equity,
            "duration_days": self.duration_days,
            "created_at": self.created_at,
            "risk_status": self.risk_status,
        }
        if include_series:
            d["equity_curve"] = self.equity_curve.to_dict() if self.equity_curve is not None else {}
            d["positions"] = self.positions.to_dict() if self.positions is not None else {}
        return d

    def summary(self) -> str:
        """生成摘要字符串"""
        return (
            f"Backtest {self.backtest_id}\n"
            f"  Strategy:    {self.strategy_name}\n"
            f"  Symbol:      {self.symbol}\n"
            f"  Total Ret:   {self.total_return:.2%}\n"
            f"  Annual Ret:  {self.annual_return:.2%}\n"
            f"  Sharpe:      {self.sharpe:.4f}\n"
            f"  Max DD:      {self.max_drawdown:.2%}\n"
            f"  Win Rate:    {self.win_rate:.2%}\n"
            f"  Trades:      {self.n_trades}\n"
            f"  Bars:        {self.n_bars}\n"
            f"  Final Eq:    {self.final_equity:.2f}\n"
        )


# ------------------------------------------------------------------
# ML Backtest Adapter
# ------------------------------------------------------------------

class MLBacktestAdapter:
    """
    ML 策略回测适配器

    用法：
        adapter = MLBacktestAdapter()
        result = adapter.run(
            strategy_id="MLS-xxx",
            df=ohlc_data,
            initial_capital=100000,
        )
        print(result.summary())

        # 便捷：直接用 strategy_name
        result = adapter.run_by_name(
            strategy_name="LGBM_Momentum_Strategy",
            df=ohlc_data,
        )
    """

    def __init__(self, builder: Optional[StrategyBuilder] = None) -> None:
        self.builder = builder or get_strategy_builder()
        # 历史结果
        self._results: Dict[str, BacktestResult] = {}

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    def run(
        self,
        strategy_id: str,
        df: pd.DataFrame,
        initial_capital: float = 100000.0,
    ) -> BacktestResult:
        """
        运行回测

        Args:
            strategy_id: 策略 ID
            df: OHLCV 数据
            initial_capital: 初始资金

        Returns:
            BacktestResult
        """
        strategy = self.builder.get_strategy(strategy_id)
        if strategy is None:
            raise ValueError(f"Strategy not found: {strategy_id}")

        return self._run_strategy(strategy, df, initial_capital)

    def run_strategy(
        self,
        strategy: MLStrategyV2,
        df: pd.DataFrame,
        initial_capital: float = 100000.0,
    ) -> BacktestResult:
        """直接对策略对象运行回测"""
        return self._run_strategy(strategy, df, initial_capital)

    def run_by_name(
        self,
        strategy_name: str,
        df: pd.DataFrame,
        initial_capital: float = 100000.0,
    ) -> BacktestResult:
        """按策略名运行回测"""
        for s in self.builder.list_strategies():
            if s.config.name == strategy_name:
                return self._run_strategy(s, df, initial_capital)
        raise ValueError(f"Strategy not found by name: {strategy_name}")

    # ------------------------------------------------------------------
    # 内部：执行回测
    # ------------------------------------------------------------------

    def _run_strategy(
        self,
        strategy: MLStrategyV2,
        df: pd.DataFrame,
        initial_capital: float,
    ) -> BacktestResult:
        """执行策略回测"""
        import pandas as pd
        logger.info(
            f"Backtest start: {strategy.config.strategy_id} "
            f"({strategy.config.name}) bars={len(df)}"
        )

        # 调用策略的 backtest
        raw = strategy.backtest(df, initial_capital=initial_capital)

        # 提取指标
        metrics = raw.get("metrics", {})
        equity = raw.get("equity_curve")
        positions = raw.get("positions")
        signals = raw.get("signals")
        predictions = raw.get("predictions")

        # 计算年化收益
        annual_return = 0.0
        if equity is not None and len(equity) > 1:
            initial = float(equity.iloc[0])
            if initial > 0:
                total_return = float(equity.iloc[-1] / initial - 1.0)
                n_days = len(equity)
                if n_days > 1:
                    annual_return = (1.0 + total_return) ** (252.0 / n_days) - 1.0

        # 持续天数
        duration_days = len(df) if df is not None else 0

        result = BacktestResult(
            strategy_id=strategy.config.strategy_id,
            strategy_name=strategy.config.name,
            symbol=strategy.config.symbol,
            total_return=metrics.get("total_return", 0.0),
            annual_return=annual_return,
            sharpe=metrics.get("sharpe", 0.0),
            max_drawdown=metrics.get("max_drawdown", 0.0),
            win_rate=metrics.get("win_rate", 0.0),
            n_trades=metrics.get("n_trades", 0),
            n_bars=metrics.get("n_bars", 0),
            equity_curve=equity,
            positions=positions,
            signals=signals,
            predictions=predictions,
            initial_capital=initial_capital,
            final_equity=float(equity.iloc[-1]) if equity is not None and len(equity) > 0 else initial_capital,
            duration_days=duration_days,
            created_at=pd.Timestamp.now().isoformat(),
            risk_status=raw.get("risk_status", {}),
        )

        self._results[result.backtest_id] = result
        logger.info(
            f"Backtest done: {result.backtest_id} "
            f"return={result.total_return:.2%} sharpe={result.sharpe:.4f} "
            f"maxdd={result.max_drawdown:.2%}"
        )
        return result

    # ------------------------------------------------------------------
    # 对比
    # ------------------------------------------------------------------

    def compare(
        self,
        backtest_ids: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """
        对比多个回测结果

        Args:
            backtest_ids: 指定 ID 列表（None=全部）

        Returns:
            DataFrame:
                strategy_name  total_return  sharpe  max_drawdown  ...
        """
        if backtest_ids:
            results = [self._results[bid] for bid in backtest_ids if bid in self._results]
        else:
            results = list(self._results.values())

        if not results:
            return pd.DataFrame()

        rows = []
        for r in results:
            rows.append({
                "backtest_id": r.backtest_id,
                "strategy_name": r.strategy_name,
                "symbol": r.symbol,
                "total_return": r.total_return,
                "annual_return": r.annual_return,
                "sharpe": r.sharpe,
                "max_drawdown": r.max_drawdown,
                "win_rate": r.win_rate,
                "n_trades": r.n_trades,
                "n_bars": r.n_bars,
                "final_equity": r.final_equity,
            })
        df = pd.DataFrame(rows)
        # 按 sharpe 降序
        df = df.sort_values("sharpe", ascending=False).reset_index(drop=True)
        return df

    def get_leaderboard(self, top_n: int = 10) -> pd.DataFrame:
        """获取排行榜"""
        df = self.compare()
        if df.empty:
            return df
        return df.head(top_n)

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def get_result(self, backtest_id: str) -> Optional[BacktestResult]:
        return self._results.get(backtest_id)

    def list_results(self) -> List[BacktestResult]:
        return list(self._results.values())

    def clear_results(self) -> None:
        self._results.clear()


# ------------------------------------------------------------------
# 模块级单例
# ------------------------------------------------------------------

_adapter: Optional[MLBacktestAdapter] = None


def get_backtest_adapter() -> MLBacktestAdapter:
    """获取全局 MLBacktestAdapter 单例"""
    global _adapter
    if _adapter is None:
        _adapter = MLBacktestAdapter()
    return _adapter
