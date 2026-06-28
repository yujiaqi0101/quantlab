"""
StrategyRuntime — 策略运行时（支持单标的时间序列和多标的截面回测）

P6 阶段 MVP，支持：
  1. 单标的时间序列回测（List[Bar] 或 DataFrame 单 symbol）
  2. 多标的截面回测（DataFrame with symbol column，按日期横截面处理）
  3. 调用 Signal Package 生成信号
  4. 调用 Position Package 计算仓位
  5. 简化模拟执行（收盘价成交 / 次日开盘成交）
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd

from ..asset_package.base import PackageType
from ..asset_package.registry import PackageRegistry
from ..asset_package.types import (
    SignalPackage, PositionPackage, RiskPackage,
    ExecutionProfile, ObserveProfile, ModelPackage, StrategyPackage,
    ThresholdSignal, RankingSignal,
    FixedSizing, KellySizing,
)

logger = logging.getLogger("quantlab.strategy_studio.runtime")


@dataclass
class Bar:
    """K线数据"""
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str = ""


@dataclass
class Signal:
    """交易信号"""
    symbol: str
    direction: int      # 1=多, -1=空, 0=平仓
    strength: float     # 信号强度 0-1
    price: float
    timestamp: str


@dataclass
class Order:
    """订单"""
    timestamp: str
    symbol: str
    side: str           # BUY / SELL
    quantity: float
    price: float


@dataclass
class BarResult:
    """单时间点结果"""
    timestamp: str
    signals: List[Signal] = field(default_factory=list)
    orders: List[Order] = field(default_factory=list)
    cash: float = 0.0
    portfolio_value: float = 0.0
    positions: Dict[str, float] = field(default_factory=dict)


@dataclass
class Position:
    """持仓信息"""
    symbol: str
    quantity: float
    avg_cost: float
    market_value: float
    unrealized_pnl: float


@dataclass
class RunResult:
    """运行结果"""
    strategy_id: str
    bars_processed: int = 0
    symbols_traded: int = 0
    bar_results: List[BarResult] = field(default_factory=list)
    final_portfolio_value: float = 0.0
    total_return: float = 0.0
    metrics: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)
    orders: List[Dict[str, Any]] = field(default_factory=list)
    positions_history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "bars_processed": self.bars_processed,
            "symbols_traded": self.symbols_traded,
            "final_portfolio_value": self.final_portfolio_value,
            "total_return": self.total_return,
            "metrics": self.metrics,
            "errors": self.errors,
            "equity_curve": self.equity_curve,
            "orders": self.orders[-100:] if len(self.orders) > 100 else self.orders,
            "total_orders": len(self.orders),
            "positions_history": self.positions_history[-50:] if len(self.positions_history) > 50 else self.positions_history,
        }


class StrategyRuntime:
    """策略运行时

    支持两种模式：
    1. 单标的模式：传入 List[Bar]
    2. 多标的截面模式：传入 pd.DataFrame（含 symbol 列，DatetimeIndex）
    """

    def __init__(self, strategy: StrategyPackage, registry: Optional[PackageRegistry] = None):
        self.strategy = strategy
        self.registry = registry or PackageRegistry()
        self.cash = 0.0
        self.positions: Dict[str, Dict[str, float]] = {}  # symbol -> {qty, avg_cost}

    def run(self, data: Union[List[Bar], pd.DataFrame],
            initial_capital: float = 100000.0) -> RunResult:
        strategy_id = f"{self.strategy.name}@{self.strategy.version}"
        result = RunResult(strategy_id=strategy_id)
        self.cash = initial_capital
        self.positions = {}

        # 收集策略配置引用
        self._sig_ref = self.strategy.signal_ref
        self._pos_ref = self.strategy.position_ref
        self._risk_ref = self.strategy.risk_ref

        try:
            if isinstance(data, pd.DataFrame):
                self._run_dataframe(data, initial_capital, result)
            else:
                self._run_bars(data, initial_capital, result)
        except Exception as e:
            logger.exception(f"Strategy runtime error: {e}")
            result.errors.append(str(e))

        if result.bar_results:
            result.final_portfolio_value = result.bar_results[-1].portfolio_value
            result.total_return = (result.final_portfolio_value - initial_capital) / initial_capital
            result.metrics = self._compute_metrics(result.bar_results, initial_capital)

        return result

    # ------------------------------------------------------------------
    # 单标的模式
    # ------------------------------------------------------------------

    def _run_bars(self, bars: List[Bar], initial_capital: float, result: RunResult):
        signal_pkg = self._resolve_package(SignalPackage, self._sig_ref)
        position_pkg = self._resolve_package(PositionPackage, self._pos_ref)
        risk_pkg = self._resolve_package(RiskPackage, self._risk_ref)
        symbols_seen = set()

        for bar in bars:
            if not bar.symbol:
                bar.symbol = "UNKNOWN"
            symbols_seen.add(bar.symbol)
            prediction = self._predict(bar)
            signals = self._generate_signals_single(
                signal_pkg, bar.symbol, prediction.get(bar.symbol, 0.0), bar.close, bar.timestamp
            )
            orders = self._generate_orders(position_pkg, signals, {bar.symbol: bar.close}, bar.timestamp)
            self._execute_orders(orders, {bar.symbol: bar.close})

            pv = self._portfolio_value({bar.symbol: bar.close})
            br = BarResult(
                timestamp=bar.timestamp, signals=signals, orders=orders,
                cash=self.cash, portfolio_value=pv,
                positions={s: p["qty"] for s, p in self.positions.items()},
            )
            result.bar_results.append(br)
            result.bars_processed += 1
            self._record_curve(br, result, orders)

        result.symbols_traded = len(symbols_seen)

    # ------------------------------------------------------------------
    # 多标的截面模式
    # ------------------------------------------------------------------

    def _run_dataframe(self, df: pd.DataFrame, initial_capital: float, result: RunResult):
        signal_pkg = self._resolve_package(SignalPackage, self._sig_ref)
        position_pkg = self._resolve_package(PositionPackage, self._pos_ref)
        risk_pkg = self._resolve_package(RiskPackage, self._risk_ref)

        required_cols = {"open", "high", "low", "close", "volume"}
        if not required_cols.issubset(set(df.columns)):
            raise ValueError(f"DataFrame missing required columns: {required_cols - set(df.columns)}")

        has_symbol = "symbol" in df.columns
        if not has_symbol:
            raise ValueError("Multi-symbol DataFrame must have a 'symbol' column")

        # 计算每只股票的历史价格用于预测
        price_history: Dict[str, List[float]] = {}
        prev_close: Dict[str, float] = {}

        # 按日期分组
        dates = sorted(df.index.unique())
        all_symbols = set(df["symbol"].unique())
        symbols_traded = set()

        for date in dates:
            day_data = df.loc[date]
            if isinstance(day_data, pd.Series):
                day_data = day_data.to_frame().T

            prices: Dict[str, float] = {}
            bar_signals: List[Signal] = []
            predictions: Dict[str, float] = {}

            # 1. 对每个标的计算预测分数
            for _, row in day_data.iterrows():
                sym = row["symbol"]
                close = float(row["close"])
                prices[sym] = close
                symbols_traded.add(sym)

                # 更新价格历史
                if sym not in price_history:
                    price_history[sym] = []
                price_history[sym].append(close)
                if len(price_history[sym]) > 60:
                    price_history[sym] = price_history[sym][-60:]

                # 计算动量预测分数
                score = self._compute_score(sym, close, price_history.get(sym, []), prev_close.get(sym))
                predictions[sym] = score
                prev_close[sym] = close

            # 2. 生成信号（支持截面排序）
            bar_signals = self._generate_signals_cross_section(
                signal_pkg, predictions, prices, str(date)[:10]
            )

            # 3. 计算仓位
            orders = self._generate_orders(position_pkg, bar_signals, prices, str(date)[:10])

            # 4. 执行订单（用当日收盘价成交，简化模型）
            self._execute_orders(orders, prices)

            # 5. 风控检查
            self._apply_risk_checks(risk_pkg, prices, str(date)[:10])

            pv = self._portfolio_value(prices)
            br = BarResult(
                timestamp=str(date)[:10], signals=bar_signals, orders=orders,
                cash=self.cash, portfolio_value=pv,
                positions={s: p["qty"] for s, p in self.positions.items()},
            )
            result.bar_results.append(br)
            result.bars_processed += 1
            self._record_curve(br, result, orders)

            if len(result.bar_results) % 50 == 0:
                result.positions_history.append({
                    "timestamp": str(date)[:10],
                    "cash": round(self.cash, 2),
                    "total_value": round(pv, 2),
                    "n_positions": len(self.positions),
                    "top_positions": sorted(
                        [{"symbol": s, "qty": p["qty"], "value": p["qty"] * prices.get(s, 0)}
                         for s, p in self.positions.items()],
                        key=lambda x: abs(x["value"]), reverse=True
                    )[:10],
                })

        result.symbols_traded = len(symbols_traded)

    # ------------------------------------------------------------------
    # 信号生成
    # ------------------------------------------------------------------

    def _generate_signals_single(self, signal_pkg, symbol: str, pred: float,
                                  price: float, ts: str) -> List[Signal]:
        signals = []
        if signal_pkg is None or not isinstance(signal_pkg, ThresholdSignal):
            direction = 1 if pred > 0 else (-1 if pred < 0 else 0)
            strength = min(abs(pred) / 0.05, 1.0)
            signals.append(Signal(symbol, direction, strength, price, ts))
            return signals

        # ThresholdSignal
        if isinstance(signal_pkg, ThresholdSignal):
            if pred > signal_pkg.long_threshold:
                signals.append(Signal(symbol, 1, min(pred / 0.05, 1.0), price, ts))
            elif pred < signal_pkg.short_threshold and signal_pkg.use_short:
                signals.append(Signal(symbol, -1, min(abs(pred) / 0.05, 1.0), price, ts))
            else:
                # 平仓信号
                if symbol in self.positions:
                    signals.append(Signal(symbol, 0, 0, price, ts))

        return signals

    def _generate_signals_cross_section(self, signal_pkg, predictions: Dict[str, float],
                                         prices: Dict[str, float], ts: str) -> List[Signal]:
        signals: List[Signal] = []
        if not predictions:
            return signals

        # 截面排序信号（RankingSignal）
        if isinstance(signal_pkg, RankingSignal):
            sorted_syms = sorted(predictions.keys(), key=lambda s: predictions[s], reverse=True)
            n = len(sorted_syms)
            top_n = max(1, int(n * signal_pkg.top_pct))
            bottom_n = max(1, int(n * signal_pkg.bottom_pct)) if signal_pkg.use_short else 0

            top_set = set(sorted_syms[:top_n])
            bottom_set = set(sorted_syms[-bottom_n:]) if bottom_n > 0 else set()

            for sym, score in predictions.items():
                if sym in top_set:
                    rank = sorted_syms.index(sym)
                    strength = 1.0 - (rank / max(top_n, 1)) * 0.3
                    signals.append(Signal(sym, 1, strength, prices[sym], ts))
                elif sym in bottom_set:
                    rank = sorted_syms.index(sym)
                    strength = 1.0 - ((n - 1 - rank) / max(bottom_n, 1)) * 0.3
                    signals.append(Signal(sym, -1, strength, prices[sym], ts))
                elif sym in self.positions:
                    signals.append(Signal(sym, 0, 0, prices[sym], ts))

        # 阈值信号（ThresholdSignal）—— 逐个标的独立判断
        elif isinstance(signal_pkg, ThresholdSignal):
            for sym, score in predictions.items():
                if score > signal_pkg.long_threshold:
                    signals.append(Signal(sym, 1, min(score / 0.05, 1.0), prices[sym], ts))
                elif score < signal_pkg.short_threshold and signal_pkg.use_short:
                    signals.append(Signal(sym, -1, min(abs(score) / 0.05, 1.0), prices[sym], ts))
                elif sym in self.positions:
                    signals.append(Signal(sym, 0, 0, prices[sym], ts))

        # 默认：用分数做简单阈值
        else:
            for sym, score in predictions.items():
                if score > 0.01:
                    signals.append(Signal(sym, 1, min(abs(score) / 0.05, 1.0), prices[sym], ts))
                elif score < -0.01:
                    signals.append(Signal(sym, -1, min(abs(score) / 0.05, 1.0), prices[sym], ts))
                elif sym in self.positions:
                    signals.append(Signal(sym, 0, 0, prices[sym], ts))

        return signals

    # ------------------------------------------------------------------
    # 订单生成 + 执行
    # ------------------------------------------------------------------

    def _generate_orders(self, position_pkg, signals: List[Signal],
                          prices: Dict[str, float], ts: str) -> List[Order]:
        orders: List[Order] = []
        if not signals:
            return orders

        active_signals = [s for s in signals if s.direction != 0]
        if not active_signals:
            # 全平
            for sym in list(self.positions.keys()):
                if sym in prices:
                    pos = self.positions[sym]
                    qty = pos["qty"]
                    if qty > 0:
                        orders.append(Order(ts, sym, "SELL", qty, prices[sym]))
                    elif qty < 0:
                        orders.append(Order(ts, sym, "BUY", abs(qty), prices[sym]))
            return orders

        total_equity = self._portfolio_value(prices)
        n_active = len(active_signals)

        # 计算目标仓位
        if isinstance(position_pkg, FixedSizing):
            weight_per_signal = min(position_pkg.base_size, 1.0 / max(n_active, 1))
            target_weights: Dict[str, float] = {}
            for sig in active_signals:
                w = weight_per_signal * sig.strength
                target_weights[sig.symbol] = w * sig.direction  # 正数做多，负数做空
        elif isinstance(position_pkg, KellySizing):
            kelly_f = position_pkg.kelly_fraction
            f_star = (position_pkg.win_rate * position_pkg.win_loss_ratio -
                      (1 - position_pkg.win_rate)) / position_pkg.win_loss_ratio
            f = max(0, f_star * kelly_f)
            weight_per_signal = min(f, position_pkg.max_size / max(n_active, 1))
            target_weights = {}
            for sig in active_signals:
                target_weights[sig.symbol] = weight_per_signal * sig.strength * sig.direction
        else:
            weight_per_signal = 0.95 / max(n_active, 1)
            target_weights = {}
            for sig in active_signals:
                target_weights[sig.symbol] = weight_per_signal * sig.strength * sig.direction

        # 归一化权重（总绝对值不超过1）
        total_abs = sum(abs(w) for w in target_weights.values())
        if total_abs > 0.95:
            scale = 0.95 / total_abs
            target_weights = {s: w * scale for s, w in target_weights.items()}

        # 生成再平衡订单
        current_symbols = set(self.positions.keys())
        target_symbols = set(target_weights.keys())

        # 平仓不再持有的
        for sym in current_symbols - target_symbols:
            if sym in prices:
                pos = self.positions[sym]
                qty = pos["qty"]
                if qty > 0:
                    orders.append(Order(ts, sym, "SELL", qty, prices[sym]))
                elif qty < 0:
                    orders.append(Order(ts, sym, "BUY", abs(qty), prices[sym]))

        # 开仓/调仓
        for sym, target_w in target_weights.items():
            if sym not in prices:
                continue
            target_value = total_equity * target_w
            target_qty = target_value / prices[sym] if prices[sym] > 0 else 0
            current_qty = self.positions.get(sym, {}).get("qty", 0.0)
            diff_qty = target_qty - current_qty

            if abs(diff_qty * prices[sym]) < total_equity * 0.001:
                continue  # 差异太小，不交易

            if diff_qty > 0:
                orders.append(Order(ts, sym, "BUY", diff_qty, prices[sym]))
            elif diff_qty < 0:
                orders.append(Order(ts, sym, "SELL", abs(diff_qty), prices[sym]))

        return orders

    def _execute_orders(self, orders: List[Order], prices: Dict[str, float]):
        for order in orders:
            if order.side == "BUY":
                cost = order.quantity * order.price
                if cost <= self.cash + 1e-6:
                    self.cash -= cost
                    if order.symbol in self.positions:
                        pos = self.positions[order.symbol]
                        total_qty = pos["qty"] + order.quantity
                        if abs(total_qty) < 1e-8:
                            pos["avg_cost"] = 0
                        else:
                            pos["avg_cost"] = (pos["qty"] * pos["avg_cost"] + cost) / total_qty
                        pos["qty"] = total_qty
                    else:
                        self.positions[order.symbol] = {
                            "qty": order.quantity,
                            "avg_cost": order.price,
                        }
                else:
                    affordable_qty = self.cash / order.price if order.price > 0 else 0
                    if affordable_qty > 0:
                        self.cash -= affordable_qty * order.price
                        self.positions[order.symbol] = {
                            "qty": affordable_qty,
                            "avg_cost": order.price,
                        }
            elif order.side == "SELL":
                if order.symbol in self.positions:
                    pos = self.positions[order.symbol]
                    sell_qty = min(order.quantity, abs(pos["qty"]))
                    if pos["qty"] > 0:
                        self.cash += sell_qty * order.price
                        pos["qty"] -= sell_qty
                    elif pos["qty"] < 0:
                        self.cash -= sell_qty * order.price
                        pos["qty"] += sell_qty
                    if abs(pos["qty"]) < 1e-8:
                        del self.positions[order.symbol]

    def _apply_risk_checks(self, risk_pkg, prices: Dict[str, float], ts: str):
        if risk_pkg is None:
            return
        pv = self._portfolio_value(prices)
        if pv <= 0:
            return
        for sym in list(self.positions.keys()):
            if sym not in prices:
                continue
            pos = self.positions[sym]
            if abs(pos["qty"] * prices[sym]) > pv * 0.25:
                pass  # TODO: 单标的集中度风控

    # ------------------------------------------------------------------
    # 预测与评分
    # ------------------------------------------------------------------

    def _predict(self, bar: Bar) -> Dict[str, float]:
        if not hasattr(self, '_price_history'):
            self._price_history: Dict[str, List[float]] = {}
            self._prev_close: Dict[str, float] = {}
        sym = bar.symbol
        if sym not in self._price_history:
            self._price_history[sym] = []
        self._price_history[sym].append(bar.close)
        if len(self._price_history[sym]) > 60:
            self._price_history[sym] = self._price_history[sym][-60:]
        score = self._compute_score(sym, bar.close, self._price_history[sym], self._prev_close.get(sym))
        self._prev_close[sym] = bar.close
        return {sym: score}

    def _compute_score(self, symbol: str, close: float, history: List[float],
                        prev_close: Optional[float]) -> float:
        if prev_close is None or len(history) < 5:
            return 0.0
        ret_1 = (close - prev_close) / prev_close if prev_close > 0 else 0
        ma5 = sum(history[-5:]) / 5
        ma_lookback = min(20, len(history))
        ma20 = sum(history[-ma_lookback:]) / ma_lookback
        mom = (close - history[-5]) / history[-5] if len(history) >= 5 and history[-5] > 0 else 0
        # 简单波动率：用最近10天日收益率标准差
        recent = history[-min(20, len(history)):]
        if len(recent) > 2:
            rets = [(recent[i] - recent[i-1]) / recent[i-1] for i in range(1, len(recent)) if recent[i-1] > 0]
            vol = float(np.std(rets)) if rets else 0.02
        else:
            vol = 0.02
        vol = max(vol, 0.005)
        score = (0.3 * ret_1 + 0.4 * (close - ma20) / ma20 + 0.3 * mom) / (vol * 5)
        return max(min(score, 0.05), -0.05)

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------

    def _portfolio_value(self, prices: Dict[str, float]) -> float:
        value = self.cash
        for sym, pos in self.positions.items():
            if sym in prices:
                value += pos["qty"] * prices[sym]
        return value

    def _resolve_package(self, pkg_cls, ref: Optional[str]):
        if not ref or not self.registry:
            return None
        try:
            if ref.startswith("ref://"):
                ref = ref[6:]
            name, version = ref.split("@")
            pkg_type = pkg_cls.package_type
            return self.registry.get(pkg_type, name, version)
        except Exception:
            return None

    def _record_curve(self, br: BarResult, result: RunResult, orders: List[Order]):
        result.equity_curve.append({
            "timestamp": br.timestamp,
            "value": br.portfolio_value,
            "cash": br.cash,
            "n_positions": len(self.positions),
        })
        for order in orders:
            result.orders.append({
                "timestamp": order.timestamp,
                "symbol": order.symbol,
                "side": order.side,
                "quantity": round(order.quantity, 4),
                "price": round(order.price, 4),
            })

    def _compute_metrics(self, bar_results: List[BarResult], initial_capital: float) -> Dict[str, Any]:
        if not bar_results:
            return {}
        portfolio_values = [r.portfolio_value for r in bar_results if r.portfolio_value > 0]
        if not portfolio_values:
            return {}
        final_value = portfolio_values[-1]
        total_return = (final_value - initial_capital) / initial_capital
        peak = portfolio_values[0]
        max_dd = 0.0
        for v in portfolio_values:
            if v > peak:
                peak = v
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd
        returns = []
        for i in range(1, len(portfolio_values)):
            if portfolio_values[i - 1] > 0:
                returns.append((portfolio_values[i] - portfolio_values[i - 1]) / portfolio_values[i - 1])
        sharpe = 0.0
        if returns and np.std(returns) > 0:
            sharpe = float(np.mean(returns) / np.std(returns) * np.sqrt(252))
        vol = float(np.std(returns) * np.sqrt(252)) if returns else 0.0
        total_orders = sum(len(r.orders) for r in bar_results)
        buy_orders = sum(1 for r in bar_results for o in r.orders if o.side == "BUY")
        sell_orders = sum(1 for r in bar_results for o in r.orders if o.side == "SELL")
        max_positions = max((len(r.positions) for r in bar_results), default=0)
        n_bars = len(portfolio_values)
        return {
            "total_return": float(total_return),
            "annual_return": float(total_return * (252 / max(n_bars, 1))),
            "max_drawdown": float(max_dd),
            "sharpe_ratio": float(sharpe),
            "volatility": float(vol),
            "total_orders": int(total_orders),
            "buy_orders": int(buy_orders),
            "sell_orders": int(sell_orders),
            "bars": int(n_bars),
            "final_value": float(final_value),
            "max_positions": int(max_positions),
            "avg_positions": float(np.mean([len(r.positions) for r in bar_results])) if bar_results else 0.0,
        }
