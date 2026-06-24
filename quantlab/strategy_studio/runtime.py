"""
Strategy Runtime — 策略运行时解释器

职责：
  1. 加载 StrategyPackage
  2. 解析所有 ref → 加载对应 Package
  3. 按 bar 驱动执行：predict → signal → position → risk → execution → observe
  4. 输出交易记录、净值曲线、观察指标

执行流程（每个 bar）：
  1. Model.predict(features) → predictions
  2. Signal.generate(predictions) → signals
  3. Position.size(signals, capital) → target_positions
  4. Risk.apply(target_positions, portfolio_state) → adjusted_positions
  5. Execution.execute(adjusted_positions, market_data) → orders/fills
  6. Observe.update(portfolio_state, orders) → metrics

注意：
  - Runtime 是解释器，不修改 Package 内容
  - Model 的 predict() 由 ModelPackage 提供（P6 用占位接口，等 Model Package 完整实现后接入）
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..asset_package.base import PackageType
from ..asset_package.registry import PackageRegistry, get_package_registry
from ..asset_package.types import (
    StrategyPackage,
    SignalPackage, PositionPackage, RiskPackage,
    ExecutionProfile, ObserveProfile,
)
from .resolver import DependencyResolver

logger = logging.getLogger("quantlab.strategy_studio.runtime")


# ==================================================================
# 数据结构
# ==================================================================

@dataclass
class Bar:
    """单根 K 线"""
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str = ""


@dataclass
class Order:
    """订单"""
    timestamp: str
    symbol: str
    side: str          # BUY / SELL / HOLD
    quantity: float
    price: float
    order_type: str = "MARKET"


@dataclass
class BarResult:
    """单 bar 执行结果"""
    timestamp: str
    predictions: Dict[str, float] = field(default_factory=dict)
    signals: List[Dict[str, Any]] = field(default_factory=list)
    target_positions: Dict[str, float] = field(default_factory=dict)
    adjusted_positions: Dict[str, float] = field(default_factory=dict)
    orders: List[Order] = field(default_factory=list)
    portfolio_value: float = 0.0
    cash: float = 0.0


@dataclass
class RunResult:
    """运行结果"""
    strategy_id: str
    bars_processed: int = 0
    bar_results: List[BarResult] = field(default_factory=list)
    final_portfolio_value: float = 0.0
    total_return: float = 0.0
    metrics: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "bars_processed": self.bars_processed,
            "final_portfolio_value": self.final_portfolio_value,
            "total_return": self.total_return,
            "metrics": self.metrics,
            "errors": self.errors,
            "bar_results_count": len(self.bar_results),
        }


# ==================================================================
# StrategyRuntime
# ==================================================================

class StrategyRuntime:
    """
    策略运行时解释器

    用法：
        runtime = StrategyRuntime(strategy)
        result = runtime.run(bars, initial_capital=100000)
    """

    def __init__(self, strategy: StrategyPackage,
                 registry: Optional[PackageRegistry] = None) -> None:
        self.strategy = strategy
        self.registry = registry or get_package_registry()
        self.resolver = DependencyResolver(registry=self.registry)

        # 加载组件
        self.signal_pkg: Optional[SignalPackage] = None
        self.position_pkg: Optional[PositionPackage] = None
        self.risk_pkg: Optional[RiskPackage] = None
        self.execution_pkg: Optional[ExecutionProfile] = None
        self.observe_pkg: Optional[ObserveProfile] = None
        self._loaded = False

    def load_components(self) -> List[str]:
        """加载所有组件 Package，返回错误列表"""
        errors: List[str] = []

        if not self._loaded:
            # 验证依赖
            graph = self.resolver.resolve(self.strategy)
            if not graph.is_complete:
                errors.extend([f"Missing: {r}" for r in graph.missing_refs])
                return errors

            # 加载组件
            self.signal_pkg = self._load(self.strategy.signal_ref, PackageType.SIGNAL)
            self.position_pkg = self._load(self.strategy.position_ref, PackageType.POSITION)
            self.risk_pkg = self._load(self.strategy.risk_ref, PackageType.RISK)
            self.execution_pkg = self._load(self.strategy.execution_ref, PackageType.EXECUTION)
            self.observe_pkg = self._load(self.strategy.observe_ref, PackageType.OBSERVE)

            for name, pkg in [
                ("signal", self.signal_pkg),
                ("position", self.position_pkg),
                ("risk", self.risk_pkg),
                ("execution", self.execution_pkg),
                ("observe", self.observe_pkg),
            ]:
                if pkg is None:
                    errors.append(f"Failed to load {name} package")

            self._loaded = len(errors) == 0

        return errors

    def _load(self, ref_str: str, pkg_type: PackageType):
        """通过 ref 加载 Package"""
        if not ref_str:
            return None
        try:
            return self.registry.get_by_ref(pkg_type, ref_str)
        except Exception as e:
            logger.error(f"Failed to load {ref_str}: {e}")
            return None

    def run(self, bars: List[Bar], initial_capital: float = 100000.0) -> RunResult:
        """
        运行策略

        Args:
            bars: K 线列表
            initial_capital: 初始资金

        Returns:
            RunResult
        """
        result = RunResult(strategy_id=self.strategy.id)

        # 加载组件
        load_errors = self.load_components()
        if load_errors:
            result.errors.extend(load_errors)
            return result

        cash = initial_capital
        positions: Dict[str, float] = {}       # symbol → quantity
        portfolio_state: Dict[str, Any] = {"cash": cash, "positions": positions}

        logger.info(f"Running strategy {self.strategy.id} on {len(bars)} bars")

        for bar in bars:
            bar_result = self._run_bar(bar, portfolio_state)
            bar_result.cash = cash
            bar_result.portfolio_value = self._compute_portfolio_value(positions, cash, bar)

            # 更新持仓
            for order in bar_result.orders:
                if order.side == "BUY":
                    positions[order.symbol] = positions.get(order.symbol, 0) + order.quantity
                    cash -= order.quantity * order.price
                elif order.side == "SELL":
                    positions[order.symbol] = positions.get(order.symbol, 0) - order.quantity
                    cash += order.quantity * order.price

            portfolio_state["cash"] = cash
            portfolio_state["positions"] = positions
            bar_result.cash = cash

            result.bar_results.append(bar_result)
            result.bars_processed += 1

        # 计算最终结果
        if bars:
            last_bar = bars[-1]
            result.final_portfolio_value = self._compute_portfolio_value(positions, cash, last_bar)
            result.total_return = (result.final_portfolio_value - initial_capital) / initial_capital

        # 计算指标
        result.metrics = self._compute_metrics(result.bar_results, initial_capital)

        logger.info(f"Strategy run complete: {result.bars_processed} bars, "
                    f"final_value={result.final_portfolio_value:.2f}, "
                    f"return={result.total_return:.4f}")

        return result

    def _run_bar(self, bar: Bar, portfolio_state: Dict[str, Any]) -> BarResult:
        """运行单 bar"""
        result = BarResult(timestamp=bar.timestamp)

        # 1. Model.predict（P6 用占位：用 close 涨跌幅作为 prediction）
        predictions = self._mock_predict(bar)
        result.predictions = predictions

        # 2. Signal.generate
        signals = []
        if self.signal_pkg:
            try:
                pred_series = pd.Series(predictions)
                signals = self.signal_pkg.generate(pred_series, metadata={"timestamp": bar.timestamp})
                result.signals = [
                    {"symbol": s.symbol, "side": s.side.value if hasattr(s.side, 'value') else str(s.side),
                     "score": s.score}
                    for s in signals
                ]
            except Exception as e:
                logger.error(f"Signal generation failed: {e}")

        # 3. Position.size → Dict[str, float]
        target_positions: Dict[str, float] = {}
        if self.position_pkg and signals:
            try:
                target_positions = self.position_pkg.size(signals, capital=portfolio_state.get("cash", 100000))
                result.target_positions = dict(target_positions)
            except Exception as e:
                logger.error(f"Position sizing failed: {e}")

        # 4. Risk.apply → Dict[str, float]
        adjusted_positions: Dict[str, float] = dict(target_positions)
        if self.risk_pkg:
            try:
                adjusted_positions = self.risk_pkg.apply(target_positions, portfolio_state=portfolio_state)
                result.adjusted_positions = dict(adjusted_positions)
            except Exception as e:
                logger.error(f"Risk application failed: {e}")
                result.adjusted_positions = dict(target_positions)

        # 5. Execution.execute
        if self.execution_pkg:
            try:
                orders = self._generate_orders(bar, adjusted_positions, portfolio_state)
                result.orders = orders
            except Exception as e:
                logger.error(f"Execution failed: {e}")

        return result

    def _mock_predict(self, bar: Bar) -> Dict[str, float]:
        """占位 predict：用 close 涨跌幅作为 prediction"""
        # P6 阶段 Model Package 还未完整实现，用简单逻辑代替
        return {bar.symbol: 0.01}  # 默认轻微看多

    def _generate_orders(self, bar: Bar, target_positions: Dict[str, float],
                         portfolio_state: Dict[str, Any]) -> List[Order]:
        """根据目标持仓生成订单"""
        orders: List[Order] = []
        current_positions = portfolio_state.get("positions", {})
        cash = portfolio_state.get("cash", 100000)

        for symbol, target_weight in target_positions.items():
            target_value = target_weight * cash
            target_qty = target_value / bar.close if bar.close > 0 else 0
            current_qty = current_positions.get(symbol, 0)
            diff = target_qty - current_qty

            if abs(diff) < 1e-6:
                continue

            side = "BUY" if diff > 0 else "SELL"
            orders.append(Order(
                timestamp=bar.timestamp,
                symbol=symbol,
                side=side,
                quantity=abs(diff),
                price=bar.close,
                order_type="MARKET",
            ))

        return orders

    def _compute_portfolio_value(self, positions: Dict[str, float], cash: float, bar: Bar) -> float:
        """计算组合价值"""
        # 简化：只计算现金 + 当前 bar 的持仓价值
        position_value = positions.get(bar.symbol, 0) * bar.close
        return cash + position_value

    def _compute_metrics(self, bar_results: List[BarResult], initial_capital: float) -> Dict[str, Any]:
        """计算策略指标"""
        if not bar_results:
            return {}

        portfolio_values = [r.portfolio_value for r in bar_results if r.portfolio_value > 0]
        if not portfolio_values:
            return {}

        final_value = portfolio_values[-1]
        total_return = (final_value - initial_capital) / initial_capital

        # 最大回撤
        peak = portfolio_values[0]
        max_dd = 0.0
        for v in portfolio_values:
            if v > peak:
                peak = v
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd

        # 总订单数
        total_orders = sum(len(r.orders) for r in bar_results)

        return {
            "final_value": final_value,
            "total_return": total_return,
            "max_drawdown": max_dd,
            "total_orders": total_orders,
            "bars": len(bar_results),
        }
