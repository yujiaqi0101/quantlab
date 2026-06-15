"""
Capacity Analyzer — V4.6 容量分析

Volume / Turnover / Trade Size → 最大可承载资金估算

策略容量 500万 or 5亿 — 实盘极有价值
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


class CapacityAnalyzer:
    """
    容量分析器

    用法：
        analyzer = CapacityAnalyzer()
        result = analyzer.analyze(trades, volume_data)
    """

    def analyze(
        self,
        trades: List[Dict],
        volume_data: Optional[Dict[str, pd.Series]] = None,
        max_participation_rate: float = 0.1,
        max_daily_volume_pct: float = 0.05,
    ) -> Dict[str, Any]:
        """
        分析策略容量

        trades: [{"symbol": ..., "qty": ..., "price": ..., "timestamp": ...}]
        volume_data: {symbol: Series of daily volumes}
        max_participation_rate: 单笔最大参与率 (默认10%)
        max_daily_volume_pct: 日最大成交量占比 (默认5%)
        """
        if not trades:
            return self._empty_result()

        # 1) 按 symbol 统计交易量
        by_symbol: Dict[str, List[Dict]] = {}
        for t in trades:
            sym = t.get("symbol", "UNKNOWN")
            by_symbol.setdefault(sym, []).append(t)

        symbol_capacity = {}
        for sym, sym_trades in by_symbol.items():
            trade_sizes = [t.get("qty", 0) * t.get("price", 1) for t in sym_trades]
            avg_trade = np.mean(trade_sizes) if trade_sizes else 0
            max_trade = max(trade_sizes) if trade_sizes else 0

            # 基于交易频率估算
            n_trades = len(sym_trades)
            total_notional = sum(trade_sizes)

            # 如果有 volume 数据，基于成交量估算
            if volume_data and sym in volume_data:
                vol = volume_data[sym]
                avg_daily_vol = float(vol.mean())
                max_daily_vol = float(vol.max())

                # 容量 = 日均成交量 * 最大日占比 / 单笔参与率
                vol_based_capacity = avg_daily_vol * max_daily_volume_pct
                trade_based_capacity = avg_trade / max_participation_rate if max_participation_rate > 0 else 0

                capacity = min(vol_based_capacity, trade_based_capacity) * avg_trade / max_trade if max_trade > 0 else 0
            else:
                # 无 volume 数据，用交易自身估算
                # 简单假设：单笔不超过市场 10%
                capacity = avg_trade / max_participation_rate if max_participation_rate > 0 else 0

            symbol_capacity[sym] = {
                "avg_trade_size": round(float(avg_trade), 2),
                "max_trade_size": round(float(max_trade), 2),
                "n_trades": n_trades,
                "total_notional": round(float(total_notional), 2),
                "estimated_capacity": round(float(capacity), 2),
            }

        # 2) 整体策略容量 = 所有 symbol 容量之和
        total_capacity = sum(sc["estimated_capacity"] for sc in symbol_capacity.values())

        # 3) 容量等级
        capacity_tier = self._classify_capacity(total_capacity)

        return {
            "total_capacity": round(float(total_capacity), 2),
            "capacity_tier": capacity_tier,
            "symbol_capacity": symbol_capacity,
            "max_participation_rate": max_participation_rate,
            "max_daily_volume_pct": max_daily_volume_pct,
        }

    def analyze_from_weights(
        self,
        weights_history: Any,
        equity_curve: Any,
        volume_data: Optional[Dict[str, pd.Series]] = None,
        max_participation_rate: float = 0.1,
    ) -> Dict[str, Any]:
        """
        从权重历史和净值曲线估算容量

        weights_history: DataFrame(index=时间, columns=symbols)
        equity_curve: list / pd.Series
        volume_data: {symbol: Series of daily volumes}
        """
        if isinstance(weights_history, list):
            weights_history = pd.DataFrame(weights_history).fillna(0)

        if not isinstance(weights_history, pd.DataFrame):
            raise TypeError("weights_history must be DataFrame or list")

        equity = np.array(equity_curve, dtype=float)
        if len(equity) < 2:
            return self._empty_result()

        # 估算每 bar 的交易量
        total_turnover_notional = 0
        max_single_trade = 0

        for i in range(1, len(weights_history)):
            prev = weights_history.iloc[i - 1].fillna(0)
            curr = weights_history.iloc[i].fillna(0)
            delta = (curr - prev).abs() / 2  # 单边换手

            # 用当前净值估算名义金额
            eq_val = equity[min(i, len(equity) - 1)]
            bar_notional = float(delta.sum() * eq_val)
            total_turnover_notional += bar_notional

            # 单 symbol 最大变动
            max_delta = float(delta.max() * eq_val)
            max_single_trade = max(max_single_trade, max_delta)

        n_bars = len(weights_history) - 1
        avg_trade_size = total_turnover_notional / n_bars if n_bars > 0 else 0

        # 容量估算
        capacity = avg_trade_size / max_participation_rate if max_participation_rate > 0 else 0
        capacity_tier = self._classify_capacity(capacity)

        return {
            "total_capacity": round(float(capacity), 2),
            "capacity_tier": capacity_tier,
            "avg_trade_size": round(float(avg_trade_size), 2),
            "max_single_trade": round(float(max_single_trade), 2),
            "total_turnover_notional": round(float(total_turnover_notional), 2),
            "max_participation_rate": max_participation_rate,
        }

    def _classify_capacity(self, capacity: float) -> str:
        """容量等级分类"""
        if capacity <= 0:
            return "N/A"
        elif capacity < 500_000:
            return "micro (< 50万)"
        elif capacity < 5_000_000:
            return "small (50万-500万)"
        elif capacity < 50_000_000:
            return "medium (500万-5000万)"
        elif capacity < 500_000_000:
            return "large (5000万-5亿)"
        else:
            return "institutional (> 5亿)"

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "total_capacity": 0.0,
            "capacity_tier": "N/A",
            "symbol_capacity": {},
            "max_participation_rate": 0.1,
            "max_daily_volume_pct": 0.05,
        }
