"""
Turnover Pressure Model — 换手压力模型

核心问题：这个策略"想交易多少"

计算：
  turnover = Σ |position_t - position_{t-1}|

然后惩罚：
  high turnover → cost explosion
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

logger = logging.getLogger("quantlab.execution.alpha_aware.turnover")


@dataclass
class TurnoverAnalysis:
    """换手分析结果"""
    total_turnover: float = 0.0        # 总换手
    avg_daily_turnover: float = 0.0    # 日均换手
    max_daily_turnover: float = 0.0    # 最大日换手
    turnover_volatility: float = 0.0   # 换手波动率
    annual_turnover: float = 0.0       # 年化换手

    # 成本估算
    cost_per_trade: float = 0.0        # 单次交易成本
    total_cost: float = 0.0            # 总成本
    annual_cost: float = 0.0           # 年化成本
    cost_drag_bps: float = 0.0         # 成本拖累（bps）

    # 压力评分
    pressure_score: float = 0.0        # 压力评分（0~1，1=极高压力）
    is_sustainable: bool = False       # 是否可持续

    def to_dict(self) -> Dict:
        return {
            "total_turnover": self.total_turnover,
            "avg_daily_turnover": self.avg_daily_turnover,
            "max_daily_turnover": self.max_daily_turnover,
            "turnover_volatility": self.turnover_volatility,
            "annual_turnover": self.annual_turnover,
            "cost_per_trade": self.cost_per_trade,
            "total_cost": self.total_cost,
            "annual_cost": self.annual_cost,
            "cost_drag_bps": self.cost_drag_bps,
            "pressure_score": self.pressure_score,
            "is_sustainable": self.is_sustainable,
        }


class TurnoverPressureModel:
    """
    换手压力模型

    用法：
        model = TurnoverPressureModel(
            fee_rate=0.0004,
            slippage_bps=2.0,
        )
        positions = [0.1, 0.2, 0.15, 0.3, 0.1]  # 每日持仓
        analysis = model.analyze(positions, capital=1_000_000)
    """

    def __init__(
        self,
        fee_rate: float = 0.0004,
        slippage_bps: float = 2.0,
        max_sustainable_turnover: float = 5.0,
        trading_days_per_year: int = 252,
    ) -> None:
        self.fee_rate = fee_rate
        self.slippage_bps = slippage_bps
        self.max_sustainable_turnover = max_sustainable_turnover
        self.trading_days = trading_days_per_year

    def analyze(
        self,
        positions: Sequence[float],
        capital: float = 1_000_000,
        prices: Optional[Sequence[float]] = None,
    ) -> TurnoverAnalysis:
        """分析换手压力"""
        if len(positions) < 2:
            return TurnoverAnalysis()

        # 1. 计算每日换手
        daily_turnovers: List[float] = []
        for i in range(1, len(positions)):
            delta = abs(positions[i] - positions[i - 1])
            daily_turnovers.append(delta)

        total_turnover = sum(daily_turnovers)
        avg_daily = total_turnover / len(daily_turnovers)
        max_daily = max(daily_turnovers) if daily_turnovers else 0

        # 换手波动率
        if len(daily_turnovers) > 1:
            mean = avg_daily
            var = sum((t - mean) ** 2 for t in daily_turnovers) / len(daily_turnovers)
            turnover_vol = math.sqrt(var)
        else:
            turnover_vol = 0.0

        annual_turnover = avg_daily * self.trading_days

        # 2. 成本估算
        cost_per_trade = self.fee_rate + self.slippage_bps / 10000
        total_cost = total_turnover * cost_per_trade * capital
        annual_cost = avg_daily * cost_per_trade * capital * self.trading_days

        # 成本拖累（bps）
        cost_drag_bps = avg_daily * cost_per_trade * 10000

        # 3. 压力评分
        pressure_score = self._pressure_score(avg_daily, turnover_vol, max_daily)

        # 4. 可持续性
        is_sustainable = avg_daily <= self.max_sustainable_turnover

        return TurnoverAnalysis(
            total_turnover=total_turnover,
            avg_daily_turnover=avg_daily,
            max_daily_turnover=max_daily,
            turnover_volatility=turnover_vol,
            annual_turnover=annual_turnover,
            cost_per_trade=cost_per_trade,
            total_cost=total_cost,
            annual_cost=annual_cost,
            cost_drag_bps=cost_drag_bps,
            pressure_score=pressure_score,
            is_sustainable=is_sustainable,
        )

    def _pressure_score(
        self,
        avg_turnover: float,
        turnover_vol: float,
        max_turnover: float,
    ) -> float:
        """
        压力评分（0~1，1=极高压力）

        综合考虑：
          - 平均换手
          - 换手波动
          - 峰值换手
        """
        # 平均换手贡献
        avg_component = min(1.0, avg_turnover / 10.0)

        # 波动贡献
        vol_component = min(1.0, turnover_vol / 5.0)

        # 峰值贡献
        max_component = min(1.0, max_turnover / 20.0)

        return avg_component * 0.5 + vol_component * 0.2 + max_component * 0.3

    def suggest_optimization(
        self,
        analysis: TurnoverAnalysis,
        target_pressure: float = 0.3,
    ) -> Dict:
        """建议优化方案"""
        suggestions = []

        if analysis.pressure_score > target_pressure:
            # 需要降低换手
            reduction_needed = analysis.avg_daily_turnover * (1 - target_pressure / analysis.pressure_score)
            suggestions.append({
                "action": "reduce_turnover",
                "target_reduction": reduction_needed,
                "methods": [
                    "增加信号阈值（减少交易次数）",
                    "引入持仓平滑（降低换手波动）",
                    "延长持仓周期",
                ],
            })

        if analysis.cost_drag_bps > 50:
            suggestions.append({
                "action": "reduce_cost",
                "current_drag_bps": analysis.cost_drag_bps,
                "methods": [
                    "使用 maker 单降低手续费",
                    "拆单减少滑点",
                    "选择流动性更好的标的",
                ],
            })

        if not analysis.is_sustainable:
            suggestions.append({
                "action": "warning",
                "message": f"换手 {analysis.avg_daily_turnover:.2f} 超过可持续阈值 {self.max_sustainable_turnover}",
            })

        return {
            "suggestions": suggestions,
            "current_pressure": analysis.pressure_score,
            "target_pressure": target_pressure,
            "needs_optimization": len(suggestions) > 0,
        }
