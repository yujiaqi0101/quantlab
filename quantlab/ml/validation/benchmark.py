"""
Benchmark Engine — 基准对比引擎

ML Lab M3 第七部分：任何模型都必须有基准

  比较：
    Buy & Hold    买入持有
    Momentum      动量策略
    Random Signal 随机信号
    ML Model      机器学习模型

  输出：ML 是否真的更好

  否则：复杂模型不如买 BTC
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("quantlab.ml.validation.benchmark")


@dataclass
class BenchmarkResult:
    """单一基准结果"""
    name: str = ""
    sharpe: float = 0.0
    annual_return: float = 0.0
    max_drawdown: float = 0.0
    ic: float = 0.0
    win_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "sharpe": round(self.sharpe, 6),
            "annual_return": round(self.annual_return, 6),
            "max_drawdown": round(self.max_drawdown, 6),
            "ic": round(self.ic, 6),
            "win_rate": round(self.win_rate, 6),
        }


@dataclass
class BenchmarkReport:
    """基准对比报告"""
    benchmarks: List[BenchmarkResult] = field(default_factory=list)
    ml_result: Optional[BenchmarkResult] = None
    # ML 是否优于所有基准
    ml_beats_all: bool = False
    ml_beats_buy_hold: bool = False
    ml_beats_random: bool = False
    # 评分
    benchmark_score: float = 0.0
    grade: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmarks": [b.to_dict() for b in self.benchmarks],
            "ml_result": self.ml_result.to_dict() if self.ml_result else None,
            "ml_beats_all": self.ml_beats_all,
            "ml_beats_buy_hold": self.ml_beats_buy_hold,
            "ml_beats_random": self.ml_beats_random,
            "benchmark_score": round(self.benchmark_score, 2),
            "grade": self.grade,
        }


class BenchmarkEngine:
    """
    基准对比引擎

    用法：
        engine = BenchmarkEngine()
        report = engine.compare(
            predictions=preds,
            label=returns,
            price=price_series,
        )
        print(f"ML beats Buy&Hold: {report.ml_beats_buy_hold}")
    """

    def __init__(self, annualization: int = 252) -> None:
        self.annualization = annualization

    def compare(
        self,
        predictions: pd.Series,
        label: pd.Series,
        price: Optional[pd.Series] = None,
        momentum_window: int = 20,
        n_random_trials: int = 10,
        seed: int = 42,
    ) -> BenchmarkReport:
        """
        对比 ML 模型与基准策略

        Args:
            predictions: ML 预测信号
            label: 真实收益
            price: 价格序列（用于 Buy&Hold）
            momentum_window: 动量窗口
            n_random_trials: 随机信号试验次数
            seed: 随机种子
        """
        report = BenchmarkReport()
        rng = np.random.RandomState(seed)

        common_idx = predictions.index.intersection(label.index)
        if len(common_idx) == 0:
            return report
        preds = predictions.loc[common_idx]
        y = label.loc[common_idx]

        # 1. Buy & Hold
        if price is not None:
            common_p = common_idx.intersection(price.index)
            if len(common_p) > 1:
                p = price.loc[common_p]
                bh_returns = p.pct_change().dropna()
                report.benchmarks.append(self._compute_benchmark(
                    "Buy & Hold", bh_returns, y.loc[bh_returns.index] if bh_returns.index.isin(y.index).any() else None
                ))
        else:
            # 用 label 作为收益
            report.benchmarks.append(self._compute_benchmark(
                "Buy & Hold", y, y
            ))

        # 2. Momentum（过去 N 日收益正负作为信号）
        if price is not None:
            common_p = common_idx.intersection(price.index)
            if len(common_p) > momentum_window:
                p = price.loc[common_p]
                mom_signal = (p / p.shift(momentum_window) - 1)
                mom_signal = np.sign(mom_signal)
                mom_returns = mom_signal.shift(1) * p.pct_change()
                mom_returns = mom_returns.dropna()
                report.benchmarks.append(self._compute_benchmark(
                    "Momentum", mom_returns, y
                ))
        else:
            # 用 label 滚动动量
            mom_signal = np.sign(y.shift(momentum_window))
            mom_returns = mom_signal * y
            mom_returns = mom_returns.dropna()
            report.benchmarks.append(self._compute_benchmark(
                "Momentum", mom_returns, y
            ))

        # 3. Random Signal（多次平均）
        random_sharpes = []
        for _ in range(n_random_trials):
            random_signal = pd.Series(
                rng.choice([-1, 1], size=len(preds)),
                index=preds.index,
            )
            random_returns = random_signal * y
            random_metrics = self._compute_benchmark("Random", random_returns, y)
            random_sharpes.append(random_metrics.sharpe)
        avg_random_sharpe = float(np.mean(random_sharpes)) if random_sharpes else 0.0
        # 替换为平均值
        for b in report.benchmarks:
            if b.name == "Random":
                b.sharpe = avg_random_sharpe
                break
        else:
            report.benchmarks.append(BenchmarkResult(
                name="Random",
                sharpe=avg_random_sharpe,
            ))

        # 4. ML Model
        ml_returns = preds * y
        report.ml_result = self._compute_benchmark("ML Model", ml_returns, y)

        # 对比
        ml_sharpe = report.ml_result.sharpe
        for b in report.benchmarks:
            if b.name == "Buy & Hold":
                report.ml_beats_buy_hold = ml_sharpe > b.sharpe
            elif b.name == "Random":
                report.ml_beats_random = ml_sharpe > b.sharpe
        report.ml_beats_all = all(
            ml_sharpe > b.sharpe for b in report.benchmarks
        )

        # 评分
        report.benchmark_score = self._compute_score(report)
        report.grade = self._score_to_grade(report.benchmark_score)
        return report

    def _compute_benchmark(
        self,
        name: str,
        returns: pd.Series,
        label: Optional[pd.Series] = None,
    ) -> BenchmarkResult:
        """计算单一基准指标"""
        returns = returns.dropna()
        if len(returns) == 0:
            return BenchmarkResult(name=name)

        sharpe = 0.0
        if returns.std() > 0:
            sharpe = float(
                returns.mean() / returns.std() * np.sqrt(self.annualization)
            )

        annual_return = float(returns.mean() * self.annualization)

        # 最大回撤
        cum = (1 + returns).cumprod()
        running_max = cum.cummax()
        drawdown = (cum - running_max) / running_max
        max_dd = float(drawdown.min()) if len(drawdown) > 0 else 0.0

        # IC（如果提供 label）
        ic = 0.0
        if label is not None:
            common = returns.index.intersection(label.index)
            if len(common) > 5:
                try:
                    ic = float(returns.loc[common].corr(label.loc[common]))
                except Exception:
                    pass

        # 胜率
        win_rate = float((returns > 0).mean()) if len(returns) > 0 else 0.0

        return BenchmarkResult(
            name=name,
            sharpe=sharpe,
            annual_return=annual_return,
            max_drawdown=max_dd,
            ic=ic,
            win_rate=win_rate,
        )

    def _compute_score(self, report: BenchmarkReport) -> float:
        """评分：ML 是否优于基准"""
        if not report.ml_result:
            return 0.0
        score = 0.0
        if report.ml_beats_random:
            score += 30
        if report.ml_beats_buy_hold:
            score += 35
        if report.ml_beats_all:
            score += 35
        return float(score)

    @staticmethod
    def _score_to_grade(score: float) -> str:
        if score >= 80:
            return "A"
        elif score >= 65:
            return "B"
        elif score >= 50:
            return "C"
        elif score >= 35:
            return "D"
        else:
            return "F"
