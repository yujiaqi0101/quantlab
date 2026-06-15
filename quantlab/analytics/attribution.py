"""
Attribution Analyzer — V4.6 归因分析

哪些交易赚钱 / 哪些亏钱 / 利润来源
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


class AttributionAnalyzer:
    """
    归因分析器

    用法：
        analyzer = AttributionAnalyzer()
        result = analyzer.analyze(fills)
        result = analyzer.analyze_trades(trade_list)
    """

    def analyze(
        self,
        fills: List[Dict],
    ) -> Dict[str, Any]:
        """
        从 Fill 列表分析归因

        fills: [{"symbol": "AAPL", "side": "BUY"/"SELL", "price": ..., "qty": ..., "pnl": ...}]
        """
        if not fills:
            return self._empty_result()

        # 按 symbol 分组
        by_symbol: Dict[str, List[Dict]] = {}
        for f in fills:
            sym = f.get("symbol", "UNKNOWN")
            by_symbol.setdefault(sym, []).append(f)

        # 逐 symbol 统计
        symbol_pnl = {}
        symbol_trades = {}
        for sym, sym_fills in by_symbol.items():
            pnls = [f.get("pnl", 0) for f in sym_fills if f.get("pnl") is not None]
            symbol_pnl[sym] = sum(pnls) if pnls else 0
            symbol_trades[sym] = len(sym_fills)

        # 盈亏交易
        winning = [p for p in symbol_pnl.values() if p > 0]
        losing = [p for p in symbol_pnl.values() if p < 0]

        total_pnl = sum(symbol_pnl.values())

        # Top contributors / Top detractors
        sorted_by_pnl = sorted(symbol_pnl.items(), key=lambda x: x[1], reverse=True)
        top_contributors = sorted_by_pnl[:5]
        top_detractors = sorted_by_pnl[-5:] if len(sorted_by_pnl) > 5 else []

        return {
            "total_pnl": round(float(total_pnl), 2),
            "winning_symbols": len(winning),
            "losing_symbols": len(losing),
            "avg_win": round(float(np.mean(winning)), 2) if winning else 0,
            "avg_loss": round(float(np.mean(losing)), 2) if losing else 0,
            "win_loss_ratio": round(abs(np.mean(winning) / np.mean(losing)), 2) if winning and losing else 0,
            "symbol_pnl": {s: round(v, 2) for s, v in symbol_pnl.items()},
            "symbol_trades": symbol_trades,
            "top_contributors": [(s, round(v, 2)) for s, v in top_contributors],
            "top_detractors": [(s, round(v, 2)) for s, v in top_detractors],
        }

    def analyze_trades(
        self,
        trades: List[Dict],
    ) -> Dict[str, Any]:
        """
        从交易列表分析归因

        trades: [{"symbol": ..., "entry_price": ..., "exit_price": ..., "pnl": ..., ...}]
        """
        if not trades:
            return self._empty_result()

        by_symbol: Dict[str, List[Dict]] = {}
        for t in trades:
            sym = t.get("symbol", "UNKNOWN")
            by_symbol.setdefault(sym, []).append(t)

        symbol_pnl = {}
        symbol_count = {}
        for sym, sym_trades in by_symbol.items():
            pnls = [t.get("pnl", 0) for t in sym_trades]
            symbol_pnl[sym] = sum(pnls)
            symbol_count[sym] = len(sym_trades)

        winning = [t for t in trades if t.get("pnl", 0) > 0]
        losing = [t for t in trades if t.get("pnl", 0) < 0]

        win_pnls = [t["pnl"] for t in winning]
        lose_pnls = [t["pnl"] for t in losing]

        return {
            "total_pnl": round(float(sum(t.get("pnl", 0) for t in trades)), 2),
            "total_trades": len(trades),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": round(len(winning) / len(trades), 4) if trades else 0,
            "avg_win": round(float(np.mean(win_pnls)), 2) if win_pnls else 0,
            "avg_loss": round(float(np.mean(lose_pnls)), 2) if lose_pnls else 0,
            "profit_factor": round(
                abs(sum(win_pnls) / sum(lose_pnls)), 2
            ) if lose_pnls and sum(lose_pnls) != 0 else float("inf"),
            "symbol_pnl": {s: round(v, 2) for s, v in symbol_pnl.items()},
            "symbol_count": symbol_count,
            "top_contributors": sorted(
                symbol_pnl.items(), key=lambda x: x[1], reverse=True
            )[:5],
            "top_detractors": sorted(
                symbol_pnl.items(), key=lambda x: x[1]
            )[:5],
        }

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "total_pnl": 0.0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "symbol_pnl": {},
            "top_contributors": [],
            "top_detractors": [],
        }
