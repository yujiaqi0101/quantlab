"""
Benchmark Analyzer — V4.6 基准对比分析

Alpha / Beta / Information Ratio / Tracking Error
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


class BenchmarkAnalyzer:
    """
    基准对比分析器

    用法：
        analyzer = BenchmarkAnalyzer()
        result = analyzer.analyze(strategy_equity, benchmark_equity)
    """

    def analyze(
        self,
        strategy_equity: Any,
        benchmark_equity: Any,
        risk_free_rate: float = 0.0,
        annual_factor: int = 252,
    ) -> Dict[str, Any]:
        """
        分析策略 vs 基准

        strategy_equity: list / pd.Series of equity values
        benchmark_equity: list / pd.Series of equity values
        """
        strat = np.array(strategy_equity, dtype=float)
        bench = np.array(benchmark_equity, dtype=float)

        if len(strat) < 2 or len(bench) < 2:
            return self._empty_result()

        # 对齐长度
        min_len = min(len(strat), len(bench))
        strat = strat[:min_len]
        bench = bench[:min_len]

        # 日收益率
        strat_ret = strat[1:] / strat[:-1] - 1
        bench_ret = bench[1:] / bench[:-1] - 1

        # Alpha: 策略收益 - 基准收益
        alpha = strat_ret - bench_ret

        # Beta: cov(strategy, benchmark) / var(benchmark)
        cov_matrix = np.cov(strat_ret, bench_ret)
        bench_var = np.var(bench_ret, ddof=1)
        beta = cov_matrix[0, 1] / bench_var if bench_var > 0 else 0

        # Tracking Error
        tracking_error = np.std(alpha, ddof=1) * np.sqrt(annual_factor)

        # Information Ratio
        ir = (np.mean(alpha) * annual_factor) / tracking_error if tracking_error > 0 else 0

        # Correlation
        corr = np.corrcoef(strat_ret, bench_ret)[0, 1] if len(strat_ret) > 1 else 0

        # Cumulative alpha
        cum_alpha = float((1 + pd.Series(alpha)).prod() - 1)

        return {
            "alpha_annualized": round(float(np.mean(alpha) * annual_factor), 4),
            "beta": round(float(beta), 4),
            "tracking_error": round(float(tracking_error), 4),
            "information_ratio": round(float(ir), 4),
            "correlation": round(float(corr), 4),
            "cumulative_alpha": round(cum_alpha, 4),
            "strategy_total_return": round(float(strat[-1] / strat[0] - 1), 4),
            "benchmark_total_return": round(float(bench[-1] / bench[0] - 1), 4),
            "outperformance": round(float(strat[-1] / strat[0] - bench[-1] / bench[0]), 4),
        }

    def analyze_buy_hold(
        self,
        strategy_equity: Any,
        data: Dict[str, pd.DataFrame],
        symbol: str = "",
        annual_factor: int = 252,
    ) -> Dict[str, Any]:
        """
        策略 vs Buy & Hold 基准

        如果 symbol 为空，取所有 symbol 的等权均值
        """
        if symbol and symbol in data:
            bench = data[symbol]["close"].values
        else:
            # 等权均值
            closes = pd.DataFrame({s: df["close"] for s, df in data.items()})
            bench = closes.mean(axis=1).values

        return self.analyze(strategy_equity, bench, annual_factor=annual_factor)

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "alpha_annualized": 0.0,
            "beta": 0.0,
            "tracking_error": 0.0,
            "information_ratio": 0.0,
            "correlation": 0.0,
            "cumulative_alpha": 0.0,
            "strategy_total_return": 0.0,
            "benchmark_total_return": 0.0,
            "outperformance": 0.0,
        }
