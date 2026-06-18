"""
Observe Studio V4 — Attribution 模块（绩效归因）

回答：这 12% 是谁赚出来的？

包含：
  1. StrategyAttribution — 策略归因（收益/风险贡献）
  2. SymbolAttribution   — 品种归因 + Long/Short 归因
  3. TimeAttribution     — 时段归因 + Regime 归因
  4. RiskAttribution     — 风险归因 + Drawdown 归因
  5. FactorAttribution   — 因子归因（接口预留）
  6. MonthlyReview       — 月度复盘引擎

用法：
    from quantlab.execution.observe.attribution import (
        StrategyAttribution,
        SymbolAttribution,
        TimeAttribution,
        RiskAttribution,
        MonthlyReview,
    )

    # 策略归因
    report = StrategyAttribution(store).analyze(session_id="s1")

    # 月度报告
    report = MonthlyReview(store).generate(year=2026, month=6)
    print(report.to_markdown())
"""

from .factor import FactorAttribution, FactorAttributionReport, FactorContribution
from .report import MonthlyReport, MonthlyReview, TradeSummary
from .risk import (
    DrawdownContribution,
    RiskAttribution,
    RiskAttributionReport,
    RiskContribution,
)
from .strategy import (
    StrategyAttribution,
    StrategyAttributionReport,
    StrategyMetric,
)
from .symbol import (
    LongShortMetric,
    SymbolAttribution,
    SymbolAttributionReport,
    SymbolMetric,
)
from .time import (
    RegimeMetric,
    TimeAttribution,
    TimeAttributionReport,
    TimeSlotMetric,
)

__all__ = [
    # strategy
    "StrategyAttribution",
    "StrategyAttributionReport",
    "StrategyMetric",
    # symbol
    "SymbolAttribution",
    "SymbolAttributionReport",
    "SymbolMetric",
    "LongShortMetric",
    # time
    "TimeAttribution",
    "TimeAttributionReport",
    "TimeSlotMetric",
    "RegimeMetric",
    # risk
    "RiskAttribution",
    "RiskAttributionReport",
    "RiskContribution",
    "DrawdownContribution",
    # factor
    "FactorAttribution",
    "FactorAttributionReport",
    "FactorContribution",
    # monthly review
    "MonthlyReview",
    "MonthlyReport",
    "TradeSummary",
]
