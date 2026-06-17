"""
Latency Fragility Test — 延迟脆弱性测试

测试不同延迟水平下的策略表现：
  - signal delay 10ms
  - signal delay 100ms
  - signal delay 1000ms

如果策略依赖极低延迟 → 不可扩展 alpha
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

logger = logging.getLogger("quantlab.execution.alpha_aware.latency_fragility")


@dataclass
class LatencyScenario:
    """延迟场景"""
    name: str
    delay_ms: float

    def to_dict(self) -> Dict:
        return {"name": self.name, "delay_ms": self.delay_ms}


@dataclass
class LatencyTestResult:
    """延迟测试结果"""
    scenario: LatencyScenario
    sharpe: float = 0.0
    total_return: float = 0.0
    alpha_decay: float = 0.0       # alpha 衰减
    fill_rate: float = 0.0         # 成交率
    slippage_increase_bps: float = 0.0  # 滑点增加

    def to_dict(self) -> Dict:
        return {
            "scenario": self.scenario.to_dict(),
            "sharpe": self.sharpe,
            "total_return": self.total_return,
            "alpha_decay": self.alpha_decay,
            "fill_rate": self.fill_rate,
            "slippage_increase_bps": self.slippage_increase_bps,
        }


@dataclass
class LatencyFragilityReport:
    """延迟脆弱性报告"""
    base_sharpe: float = 0.0
    results: List[LatencyTestResult] = field(default_factory=list)

    # 脆弱性指标
    alpha_half_life_ms: float = 0.0    # alpha 半衰期（ms）
    sharpe_decay_rate: float = 0.0     # 夏普衰减率
    critical_latency_ms: float = 0.0   # 临界延迟（夏普归零）

    # 结论
    is_scalable: bool = False
    latency_class: str = ""            # HFT / MEDIUM / LOW_FREQ
    verdict: str = ""
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "base_sharpe": self.base_sharpe,
            "results": [r.to_dict() for r in self.results],
            "alpha_half_life_ms": self.alpha_half_life_ms,
            "sharpe_decay_rate": self.sharpe_decay_rate,
            "critical_latency_ms": self.critical_latency_ms,
            "is_scalable": self.is_scalable,
            "latency_class": self.latency_class,
            "verdict": self.verdict,
            "warnings": self.warnings,
        }


class LatencyFragilityTest:
    """
    延迟脆弱性测试

    用法：
        test = LatencyFragilityTest()
        # backtest_fn: 接收 delay_ms，返回 {sharpe, return, alpha_decay, fill_rate}
        report = test.run(
            backtest_fn=lambda delay: {"sharpe": 2.0 * math.exp(-delay/200), ...},
        )
    """

    def __init__(self) -> None:
        self.default_scenarios = [
            LatencyScenario("ultra_low", 1),
            LatencyScenario("low", 10),
            LatencyScenario("medium", 100),
            LatencyScenario("high", 500),
            LatencyScenario("very_high", 1000),
            LatencyScenario("extreme", 5000),
        ]

    def run(
        self,
        backtest_fn: Callable[[float], Dict],
        scenarios: Optional[List[LatencyScenario]] = None,
    ) -> LatencyFragilityReport:
        """运行延迟脆弱性测试"""
        scenarios = scenarios or self.default_scenarios
        report = LatencyFragilityReport()

        for scenario in scenarios:
            result = backtest_fn(scenario.delay_ms)

            tr = LatencyTestResult(
                scenario=scenario,
                sharpe=result.get("sharpe", 0.0),
                total_return=result.get("total_return", 0.0),
                alpha_decay=result.get("alpha_decay", 0.0),
                fill_rate=result.get("fill_rate", 1.0),
                slippage_increase_bps=result.get("slippage_increase_bps", 0.0),
            )
            report.results.append(tr)

            if scenario.delay_ms <= 1:
                report.base_sharpe = tr.sharpe

        # 计算脆弱性指标
        report.alpha_half_life_ms = self._alpha_half_life(report.results)
        report.sharpe_decay_rate = self._sharpe_decay_rate(report.results)
        report.critical_latency_ms = self._critical_latency(report.results)

        # 分类
        report.latency_class = self._classify(report)
        report.is_scalable = report.critical_latency_ms >= 100

        # 结论
        report.verdict = self._verdict(report)
        report.warnings = self._warnings(report)

        return report

    def _alpha_half_life(self, results: List[LatencyTestResult]) -> float:
        """计算 alpha 半衰期（夏普减半的延迟）"""
        if not results:
            return 0.0

        base = results[0].sharpe
        if base <= 0:
            return 0.0

        half_sharpe = base / 2

        for i in range(1, len(results)):
            if results[i].sharpe <= half_sharpe:
                # 线性插值
                prev = results[i - 1]
                curr = results[i]
                if prev.sharpe > half_sharpe:
                    ratio = (prev.sharpe - half_sharpe) / (prev.sharpe - curr.sharpe)
                    return prev.scenario.delay_ms + ratio * (
                        curr.scenario.delay_ms - prev.scenario.delay_ms
                    )
                return prev.scenario.delay_ms

        return results[-1].scenario.delay_ms

    def _sharpe_decay_rate(self, results: List[LatencyTestResult]) -> float:
        """夏普衰减率（每 100ms 衰减比例）"""
        if len(results) < 2:
            return 0.0

        # 拟合指数衰减
        import math
        sorted_results = sorted(results, key=lambda r: r.scenario.delay_ms)

        # 简化：用首尾计算
        first = sorted_results[0]
        last = sorted_results[-1]

        if first.sharpe <= 0 or last.scenario.delay_ms <= 0:
            return 0.0

        # 衰减率 = -ln(sharpe_last / sharpe_first) / delay
        if last.sharpe <= 0:
            return 1.0

        decay = -math.log(last.sharpe / first.sharpe) / (last.scenario.delay_ms / 100)
        return max(0.0, min(1.0, decay))

    def _critical_latency(self, results: List[LatencyTestResult]) -> float:
        """临界延迟（夏普归零）"""
        sorted_results = sorted(results, key=lambda r: r.scenario.delay_ms)

        for i, r in enumerate(sorted_results):
            if r.sharpe <= 0:
                if i == 0:
                    return r.scenario.delay_ms
                prev = sorted_results[i - 1]
                if prev.sharpe > 0:
                    ratio = prev.sharpe / (prev.sharpe - r.sharpe)
                    return prev.scenario.delay_ms + ratio * (
                        r.scenario.delay_ms - prev.scenario.delay_ms
                    )
                return r.scenario.delay_ms

        return sorted_results[-1].scenario.delay_ms

    def _classify(self, report: LatencyFragilityReport) -> str:
        """延迟分类"""
        if report.alpha_half_life_ms < 10:
            return "HFT"          # 高频
        elif report.alpha_half_life_ms < 100:
            return "MEDIUM"       # 中频
        else:
            return "LOW_FREQ"     # 低频

    def _verdict(self, report: LatencyFragilityReport) -> str:
        if report.critical_latency_ms >= 1000:
            return "SCALABLE"
        elif report.critical_latency_ms >= 100:
            return "MARGINAL"
        else:
            return "FRAGILE"

    def _warnings(self, report: LatencyFragilityReport) -> List[str]:
        warnings = []
        if report.alpha_half_life_ms < 10:
            warnings.append(f"Alpha 半衰期极短: {report.alpha_half_life_ms:.0f}ms — 依赖 HFT 基础设施")
        if report.critical_latency_ms < 100:
            warnings.append(f"临界延迟 {report.critical_latency_ms:.0f}ms — 策略不可扩展")
        if report.sharpe_decay_rate > 0.5:
            warnings.append(f"夏普衰减过快: {report.sharpe_decay_rate:.2f}/100ms")
        return warnings
