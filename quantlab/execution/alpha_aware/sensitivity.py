"""
Execution Sensitivity Test — 执行敏感性测试

模拟不同滑点水平下的策略表现：
  - slippage × 0.5x
  - slippage × 1x
  - slippage × 2x

观察：strategy stability

如果收益崩塌 → alpha 不可执行
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence

logger = logging.getLogger("quantlab.execution.alpha_aware.sensitivity")


@dataclass
class SensitivityScenario:
    """敏感性测试场景"""
    name: str
    slippage_multiplier: float
    fee_multiplier: float = 1.0
    impact_multiplier: float = 1.0

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "slippage_multiplier": self.slippage_multiplier,
            "fee_multiplier": self.fee_multiplier,
            "impact_multiplier": self.impact_multiplier,
        }


@dataclass
class ScenarioResult:
    """场景结果"""
    scenario: SensitivityScenario
    sharpe: float = 0.0
    total_return: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    cost_ratio: float = 0.0       # 成本占收益比例
    is_profitable: bool = False

    def to_dict(self) -> Dict:
        return {
            "scenario": self.scenario.to_dict(),
            "sharpe": self.sharpe,
            "total_return": self.total_return,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "cost_ratio": self.cost_ratio,
            "is_profitable": self.is_profitable,
        }


@dataclass
class SensitivityReport:
    """敏感性报告"""
    base_sharpe: float = 0.0
    scenarios: List[ScenarioResult] = field(default_factory=list)

    # 稳定性指标
    sharpe_stability: float = 0.0       # 夏普稳定性（0~1，1=极稳定）
    return_degradation: float = 0.0     # 收益衰减率
    breakpoint_multiplier: float = 0.0  # 收益归零的滑点倍数

    # 结论
    is_robust: bool = False
    verdict: str = ""
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "base_sharpe": self.base_sharpe,
            "scenarios": [s.to_dict() for s in self.scenarios],
            "sharpe_stability": self.sharpe_stability,
            "return_degradation": self.return_degradation,
            "breakpoint_multiplier": self.breakpoint_multiplier,
            "is_robust": self.is_robust,
            "verdict": self.verdict,
            "warnings": self.warnings,
        }


class ExecutionSensitivityTest:
    """
    执行敏感性测试

    用法：
        test = ExecutionSensitivityTest()
        # backtest_fn: 接收滑点倍数，返回 {sharpe, return, drawdown, win_rate}
        report = test.run(
            base_slippage_bps=2.0,
            backtest_fn=lambda mult: {"sharpe": 2.0 - mult * 0.5, ...},
        )
    """

    def __init__(self) -> None:
        self.default_scenarios = [
            SensitivityScenario("low_slippage", 0.5),
            SensitivityScenario("base", 1.0),
            SensitivityScenario("high_slippage", 2.0),
            SensitivityScenario("extreme", 3.0),
            SensitivityScenario("crash", 5.0),
        ]

    def run(
        self,
        backtest_fn: Callable[[float], Dict],
        scenarios: Optional[List[SensitivityScenario]] = None,
    ) -> SensitivityReport:
        """
        运行敏感性测试

        Args:
            backtest_fn: 接收 slippage_multiplier，返回 dict
                         {sharpe, total_return, max_drawdown, win_rate, cost_ratio}
            scenarios: 自定义场景列表
        """
        scenarios = scenarios or self.default_scenarios
        report = SensitivityReport()

        for scenario in scenarios:
            result = backtest_fn(scenario.slippage_multiplier)

            sr = ScenarioResult(
                scenario=scenario,
                sharpe=result.get("sharpe", 0.0),
                total_return=result.get("total_return", 0.0),
                max_drawdown=result.get("max_drawdown", 0.0),
                win_rate=result.get("win_rate", 0.0),
                cost_ratio=result.get("cost_ratio", 0.0),
                is_profitable=result.get("total_return", 0.0) > 0,
            )
            report.scenarios.append(sr)

            if scenario.slippage_multiplier == 1.0:
                report.base_sharpe = sr.sharpe

        # 计算稳定性
        report.sharpe_stability = self._sharpe_stability(report.scenarios)
        report.return_degradation = self._return_degradation(report.scenarios)
        report.breakpoint_multiplier = self._find_breakpoint(report.scenarios)

        # 结论
        report.is_robust = (
            report.sharpe_stability >= 0.5
            and report.return_degradation <= 0.5
            and report.breakpoint_multiplier >= 2.0
        )
        report.verdict = self._verdict(report)
        report.warnings = self._warnings(report)

        return report

    def _sharpe_stability(self, scenarios: List[ScenarioResult]) -> float:
        """夏普稳定性"""
        sharpes = [s.sharpe for s in scenarios]
        if not sharpes or max(sharpes) == 0:
            return 0.0

        # 变异系数的倒数
        mean = sum(sharpes) / len(sharpes)
        if mean <= 0:
            return 0.0

        var = sum((s - mean) ** 2 for s in sharpes) / len(sharpes)
        std = math.sqrt(var)
        cv = std / abs(mean)

        # cv=0 → 1, cv=1 → 0
        return max(0.0, 1.0 - cv)

    def _return_degradation(self, scenarios: List[ScenarioResult]) -> float:
        """收益衰减率（0~1，1=完全衰减）"""
        if len(scenarios) < 2:
            return 0.0

        # 从最小滑点到最大滑点的收益变化
        sorted_scenarios = sorted(scenarios, key=lambda s: s.scenario.slippage_multiplier)
        low_return = sorted_scenarios[0].total_return
        high_return = sorted_scenarios[-1].total_return

        if low_return <= 0:
            return 1.0

        return max(0.0, min(1.0, 1.0 - high_return / low_return))

    def _find_breakpoint(self, scenarios: List[ScenarioResult]) -> float:
        """找到收益归零的滑点倍数"""
        sorted_scenarios = sorted(scenarios, key=lambda s: s.scenario.slippage_multiplier)

        # 找到第一个收益为负的场景
        for i, s in enumerate(sorted_scenarios):
            if s.total_return <= 0:
                if i == 0:
                    return s.scenario.slippage_multiplier
                # 线性插值
                prev = sorted_scenarios[i - 1]
                if prev.total_return > 0:
                    ratio = prev.total_return / (prev.total_return - s.total_return)
                    return prev.scenario.slippage_multiplier + ratio * (
                        s.scenario.slippage_multiplier - prev.scenario.slippage_multiplier
                    )
                return s.scenario.slippage_multiplier

        # 所有场景都盈利，返回最大倍数
        return sorted_scenarios[-1].scenario.slippage_multiplier

    def _verdict(self, report: SensitivityReport) -> str:
        if report.is_robust:
            return "ROBUST"
        elif report.breakpoint_multiplier >= 1.5:
            return "MARGINAL"
        else:
            return "FRAGILE"

    def _warnings(self, report: SensitivityReport) -> List[str]:
        warnings = []
        if report.sharpe_stability < 0.3:
            warnings.append(f"夏普极不稳定: stability={report.sharpe_stability:.2f}")
        if report.return_degradation > 0.7:
            warnings.append(f"收益严重衰减: degradation={report.return_degradation:.2f}")
        if report.breakpoint_multiplier < 2.0:
            warnings.append(
                f"滑点倍数 {report.breakpoint_multiplier:.1f}x 时收益归零 — 策略脆弱"
            )
        return warnings
