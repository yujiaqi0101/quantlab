"""
Adaptive Execution Engine — 自适应执行引擎

根据市场状态调整执行策略：
  1. 波动高 → 减仓 / 拆单
  2. 流动性低 → 拆单 / 等待
  3. 趋势强 → 加速执行
  4. TWAP / VWAP / Implementation Shortfall

模型：execution policy learning
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("quantlab.execution.fidelity.adaptive")


class MarketRegime(str, Enum):
    """市场状态"""
    CALM = "CALM"                # 平静
    VOLATILE = "VOLATILE"        # 高波动
    LOW_LIQUIDITY = "LOW_LIQ"    # 低流动性
    TRENDING = "TRENDING"        # 趋势
    REVERSAL = "REVERSAL"        # 反转


class ExecutionStyle(str, Enum):
    """执行风格"""
    AGGRESSIVE = "AGGRESSIVE"    # 激进（市价单）
    NEUTRAL = "NEUTRAL"          # 中性
    PASSIVE = "PASSIVE"          # 被动（限价单）
    TWAP = "TWAP"                # 时间加权
    VWAP = "VWAP"                # 成交量加权
    ICEBERG = "ICEBERG"          # 冰山单


@dataclass
class MarketState:
    """市场状态"""
    volatility: float = 0.01
    volume: float = 1000000
    spread_bps: float = 2.0
    trend_strength: float = 0.0   # -1~1
    liquidity_score: float = 1.0  # 0~1

    def regime(self) -> MarketRegime:
        """判断市场状态"""
        if self.volatility > 0.05:
            return MarketRegime.VOLATILE
        if self.liquidity_score < 0.3:
            return MarketRegime.LOW_LIQUIDITY
        if abs(self.trend_strength) > 0.6:
            return MarketRegime.TRENDING if self.trend_strength > 0 else MarketRegime.REVERSAL
        return MarketRegime.CALM

    def to_dict(self) -> Dict:
        return {
            "volatility": self.volatility,
            "volume": self.volume,
            "spread_bps": self.spread_bps,
            "trend_strength": self.trend_strength,
            "liquidity_score": self.liquidity_score,
            "regime": self.regime().value,
        }


@dataclass
class ExecutionPlan:
    """执行计划"""
    order_id: str
    symbol: str
    side: str
    total_qty: float
    style: ExecutionStyle
    slices: List[Dict] = field(default_factory=list)    # [{qty, delay_ms, order_type}]
    rationale: str = ""
    regime: str = ""

    def to_dict(self) -> Dict:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "total_qty": self.total_qty,
            "style": self.style.value,
            "slices": self.slices,
            "rationale": self.rationale,
            "regime": self.regime,
        }


class AdaptiveExecutionEngine:
    """
    自适应执行引擎

    用法：
        engine = AdaptiveExecutionEngine()
        plan = engine.plan(
            order_id="o1",
            symbol="BTCUSDT",
            side="BUY",
            total_qty=100,
            market=MarketState(volatility=0.03, liquidity_score=0.5),
        )
    """

    def __init__(
        self,
        max_participation_rate: float = 0.1,   # 最大参与率
        min_slice_qty: float = 0.01,
        max_slices: int = 20,
    ) -> None:
        self.max_participation_rate = max_participation_rate
        self.min_slice_qty = min_slice_qty
        self.max_slices = max_slices
        self._plans: List[ExecutionPlan] = []
        self._policy_history: List[Dict] = []

    def plan(
        self,
        order_id: str,
        symbol: str,
        side: str,
        total_qty: float,
        market: MarketState,
        urgency: float = 0.5,    # 0~1, 1=最紧急
    ) -> ExecutionPlan:
        """生成执行计划"""
        regime = market.regime()
        style, rationale = self._select_style(regime, urgency, market)

        # 根据风格生成切片
        slices = self._generate_slices(
            total_qty=total_qty,
            style=style,
            market=market,
            urgency=urgency,
        )

        plan = ExecutionPlan(
            order_id=order_id,
            symbol=symbol,
            side=side,
            total_qty=total_qty,
            style=style,
            slices=slices,
            rationale=rationale,
            regime=regime.value,
        )

        self._plans.append(plan)
        self._policy_history.append({
            "timestamp": int(time.time() * 1000),
            "regime": regime.value,
            "style": style.value,
            "urgency": urgency,
            "market": market.to_dict(),
        })

        logger.info(
            f"AdaptiveExecution: {order_id} {side} {total_qty} "
            f"regime={regime.value} style={style.value} slices={len(slices)}"
        )

        return plan

    def _select_style(
        self,
        regime: MarketRegime,
        urgency: float,
        market: MarketState,
    ) -> tuple:
        """选择执行风格"""
        if regime == MarketRegime.VOLATILE:
            if urgency > 0.7:
                return ExecutionStyle.AGGRESSIVE, "高波动+高紧急 → 激进执行"
            return ExecutionStyle.TWAP, "高波动 → TWAP 拆单减少冲击"

        if regime == MarketRegime.LOW_LIQUIDITY:
            return ExecutionStyle.ICEBERG, "低流动性 → 冰山单隐藏真实量"

        if regime == MarketRegime.TRENDING:
            if urgency > 0.5:
                return ExecutionStyle.AGGRESSIVE, "趋势+紧急 → 加速执行"
            return ExecutionStyle.VWAP, "趋势 → VWAP 跟随成交量"

        if regime == MarketRegime.REVERSAL:
            return ExecutionStyle.PASSIVE, "反转 → 被动限价等待"

        # CALM
        if urgency > 0.7:
            return ExecutionStyle.AGGRESSIVE, "平静+紧急 → 直接市价"
        return ExecutionStyle.NEUTRAL, "平静 → 中性执行"

    def _generate_slices(
        self,
        total_qty: float,
        style: ExecutionStyle,
        market: MarketState,
        urgency: float,
    ) -> List[Dict]:
        """生成切片"""
        slices: List[Dict] = []

        if style == ExecutionStyle.AGGRESSIVE:
            # 激进：1-2 笔
            slices.append({
                "qty": total_qty,
                "delay_ms": 0,
                "order_type": "MARKET",
            })

        elif style == ExecutionStyle.NEUTRAL:
            # 中性：2-3 笔
            n = min(3, self.max_slices)
            per_slice = total_qty / n
            for i in range(n):
                slices.append({
                    "qty": per_slice,
                    "delay_ms": i * 500,
                    "order_type": "MARKET",
                })

        elif style == ExecutionStyle.PASSIVE:
            # 被动：限价单
            slices.append({
                "qty": total_qty,
                "delay_ms": 0,
                "order_type": "LIMIT",
            })

        elif style == ExecutionStyle.TWAP:
            # TWAP：均匀拆分
            n = min(self.max_slices, max(3, int(total_qty / max(self.min_slice_qty, total_qty / 20))))
            n = max(2, n)
            per_slice = total_qty / n
            interval = max(1000, int(60000 / n))   # 1分钟内分完
            for i in range(n):
                slices.append({
                    "qty": per_slice,
                    "delay_ms": i * interval,
                    "order_type": "LIMIT",
                })

        elif style == ExecutionStyle.VWAP:
            # VWAP：按成交量分布（简化为 U 型）
            n = min(self.max_slices, max(3, int(total_qty / max(self.min_slice_qty, total_qty / 15))))
            n = max(2, n)
            # U 型分布：开头和结尾量大
            weights = [1 + abs(i - n / 2) * 0.5 for i in range(n)]
            total_weight = sum(weights)
            for i in range(n):
                slices.append({
                    "qty": total_qty * weights[i] / total_weight,
                    "delay_ms": i * 2000,
                    "order_type": "LIMIT",
                })

        elif style == ExecutionStyle.ICEBERG:
            # 冰山单：小切片
            visible_qty = max(self.min_slice_qty, total_qty * 0.1)
            remaining = total_qty
            i = 0
            while remaining > 0 and i < self.max_slices:
                q = min(visible_qty, remaining)
                slices.append({
                    "qty": q,
                    "delay_ms": i * 3000,
                    "order_type": "LIMIT",
                })
                remaining -= q
                i += 1

        return slices

    def get_plans(self, limit: int = 100) -> List[Dict]:
        return [p.to_dict() for p in self._plans[-limit:]]

    def get_policy_stats(self) -> Dict:
        """策略统计"""
        if not self._policy_history:
            return {"count": 0}

        regime_counts: Dict[str, int] = {}
        style_counts: Dict[str, int] = {}
        for p in self._policy_history:
            regime_counts[p["regime"]] = regime_counts.get(p["regime"], 0) + 1
            style_counts[p["style"]] = style_counts.get(p["style"], 0) + 1

        return {
            "count": len(self._policy_history),
            "regimes": regime_counts,
            "styles": style_counts,
        }
