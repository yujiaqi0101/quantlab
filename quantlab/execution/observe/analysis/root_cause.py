"""
Root Cause Analyzer — 根因分析器

自动判断亏损原因类型：
  - SIGNAL_ERROR      信号反转过慢 / 信号方向错误
  - EXECUTION_ERROR   滑点过大 / 执行延迟
  - RISK_EXIT         止损触发 / 风控平仓
  - MARKET_SHOCK      异常波动 / 市场急变
  - OVEREXPOSURE      仓位过大 / 杠杆过高

用法：
    analyzer = RootCauseAnalyzer()
    causes = analyzer.analyze(trace)
    # causes: List[RootCause]，按 confidence 排序
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .trace import TradeTrace

logger = logging.getLogger("quantlab.execution.observe.analysis.root_cause")


class CauseType(str, Enum):
    """根因类型"""
    SIGNAL_ERROR = "SIGNAL_ERROR"          # 信号反转过慢 / 信号方向错误
    EXECUTION_ERROR = "EXECUTION_ERROR"    # 滑点过大 / 执行延迟
    RISK_EXIT = "RISK_EXIT"                # 止损触发 / 风控平仓
    MARKET_SHOCK = "MARKET_SHOCK"          # 异常波动 / 市场急变
    OVEREXPOSURE = "OVEREXPOSURE"          # 仓位过大 / 杠杆过高
    UNKNOWN = "UNKNOWN"


class CauseSeverity(str, Enum):
    """严重程度"""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass
class RootCause:
    """根因"""
    type: CauseType = CauseType.UNKNOWN
    severity: CauseSeverity = CauseSeverity.INFO
    confidence: float = 0.0  # 0.0 ~ 1.0
    title: str = ""
    description: str = ""
    # 支撑证据
    evidence: List[str] = field(default_factory=list)
    # 相关指标
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "severity": self.severity.value,
            "confidence": round(self.confidence, 3),
            "title": self.title,
            "description": self.description,
            "evidence": self.evidence,
            "metrics": self.metrics,
        }


class RootCauseAnalyzer:
    """
    根因分析器

    用法：
        analyzer = RootCauseAnalyzer()
        causes = analyzer.analyze(trace)
        primary = analyzer.primary_cause(trace)
    """

    # 阈值配置
    SLIPPAGE_WARN_BPS = 10.0       # 滑点警告（10 bps = 0.1%）
    SLIPPAGE_CRITICAL_BPS = 50.0   # 滑点严重（50 bps = 0.5%）
    MARKET_SHOCK_PCT = 0.02        # 市场急变 2%
    SIGNAL_DELAY_MS = 5000         # 信号延迟 5 秒
    HOLDING_TOO_LONG_HOURS = 24.0  # 持仓过长 24 小时
    LOSS_PCT_THRESHOLD = -2.0      # 亏损 2% 触发分析

    def analyze(self, trace: TradeTrace) -> List[RootCause]:
        """分析交易根因，返回所有可能的原因（按 confidence 排序）"""
        causes: List[RootCause] = []

        if not trace.is_closed:
            return causes

        # 只分析亏损交易
        if not trace.is_loss:
            return causes

        # 逐一检测
        causes.append(self._check_signal_error(trace))
        causes.append(self._check_execution_error(trace))
        causes.append(self._check_risk_exit(trace))
        causes.append(self._check_market_shock(trace))
        causes.append(self._check_overexposure(trace))

        # 过滤掉 confidence=0 的
        causes = [c for c in causes if c.confidence > 0]

        # 按 confidence 降序
        causes.sort(key=lambda c: c.confidence, reverse=True)

        return causes

    def primary_cause(self, trace: TradeTrace) -> Optional[RootCause]:
        """主要根因（confidence 最高的）"""
        causes = self.analyze(trace)
        return causes[0] if causes else None

    # ------------------------------------------------------------------
    # 检测器
    # ------------------------------------------------------------------

    def _check_signal_error(self, trace: TradeTrace) -> RootCause:
        """信号错误：信号反转过慢 / 信号方向错误"""
        cause = RootCause(type=CauseType.SIGNAL_ERROR)

        if not trace.entry or not trace.entry.signal_event:
            return cause

        evidence = []
        metrics: Dict[str, Any] = {}
        confidence = 0.0

        # 1. 信号分数低
        score = trace.entry.signal_score
        if score is not None and score < 0.5:
            confidence += 0.3
            evidence.append(f"信号分数偏低: {score:.2f}")
            metrics["signal_score"] = score

        # 2. 市场反向变动（信号方向错误）
        if trace.entry_price and trace.exit_price and trace.entry.side.upper() == "BUY":
            market_drop = (trace.exit_price - trace.entry_price) / trace.entry_price
            if market_drop < -0.01:  # 下跌超过 1%
                confidence += 0.4
                evidence.append(f"买入后市场下跌 {market_drop*100:.2f}%，信号方向错误")
                metrics["market_drop"] = market_drop

        # 3. 持仓时间短但亏损（可能是信号时机错误）
        if trace.holding_minutes < 30 and trace.is_loss:
            confidence += 0.2
            evidence.append(f"持仓仅 {trace.holding_minutes:.1f} 分钟即亏损，信号时机错误")
            metrics["holding_minutes"] = trace.holding_minutes

        # 4. 持仓时间过长（信号反转过慢）
        if trace.holding_hours > self.HOLDING_TOO_LONG_HOURS:
            confidence += 0.3
            evidence.append(f"持仓 {trace.holding_hours:.1f} 小时，信号反转过慢")
            metrics["holding_hours"] = trace.holding_hours

        if confidence > 0:
            cause.confidence = min(confidence, 1.0)
            cause.title = "信号错误"
            cause.description = "策略信号方向错误或时机不佳"
            cause.evidence = evidence
            cause.metrics = metrics
            cause.severity = CauseSeverity.WARNING if confidence < 0.6 else CauseSeverity.CRITICAL

        return cause

    def _check_execution_error(self, trace: TradeTrace) -> RootCause:
        """执行错误：滑点过大 / 执行延迟"""
        cause = RootCause(type=CauseType.EXECUTION_ERROR)

        evidence = []
        metrics: Dict[str, Any] = {}
        confidence = 0.0

        # 检查入场滑点
        if trace.entry and trace.entry.slippage_bps:
            slippage = trace.entry.slippage_bps
            metrics["entry_slippage_bps"] = slippage
            if slippage > self.SLIPPAGE_CRITICAL_BPS:
                confidence += 0.5
                evidence.append(f"入场滑点 {slippage:.1f} bps，严重偏高")
            elif slippage > self.SLIPPAGE_WARN_BPS:
                confidence += 0.3
                evidence.append(f"入场滑点 {slippage:.1f} bps，偏高")

        # 检查出出场滑点
        if trace.exit and trace.exit.slippage_bps:
            slippage = trace.exit.slippage_bps
            metrics["exit_slippage_bps"] = slippage
            if slippage > self.SLIPPAGE_CRITICAL_BPS:
                confidence += 0.4
                evidence.append(f"出场滑点 {slippage:.1f} bps，严重偏高")
            elif slippage > self.SLIPPAGE_WARN_BPS:
                confidence += 0.2
                evidence.append(f"出场滑点 {slippage:.1f} bps，偏高")

        # 检查订单到成交的延迟
        if trace.entry and trace.entry.order_event and trace.entry.fill_event:
            delay_ms = trace.entry.fill_event.timestamp - trace.entry.order_event.timestamp
            metrics["entry_delay_ms"] = delay_ms
            if delay_ms > self.SIGNAL_DELAY_MS:
                confidence += 0.2
                evidence.append(f"订单到成交延迟 {delay_ms} ms")

        if confidence > 0:
            cause.confidence = min(confidence, 1.0)
            cause.title = "执行错误"
            cause.description = "滑点过大或执行延迟导致成本增加"
            cause.evidence = evidence
            cause.metrics = metrics
            cause.severity = CauseSeverity.WARNING if confidence < 0.6 else CauseSeverity.CRITICAL

        return cause

    def _check_risk_exit(self, trace: TradeTrace) -> RootCause:
        """风控退出：止损触发 / 风控平仓"""
        cause = RootCause(type=CauseType.RISK_EXIT)

        evidence = []
        metrics: Dict[str, Any] = {}
        confidence = 0.0

        # 检查是否有风险事件
        if trace.risk_events:
            confidence += 0.6
            for re in trace.risk_events:
                msg = re.payload.get("message", re.payload.get("reason", re.event_type))
                evidence.append(f"风险事件: {msg}")
            metrics["n_risk_events"] = len(trace.risk_events)

        # 检查是否在止损位附近平仓
        if trace.pnl_pct is not None and trace.pnl_pct <= self.LOSS_PCT_THRESHOLD:
            confidence += 0.3
            evidence.append(f"亏损 {trace.pnl_pct:.2f}%，接近止损位")
            metrics["pnl_pct"] = trace.pnl_pct

        # 检查 KILL_SWITCH
        for re in trace.risk_events:
            if re.event_type.upper() == "KILL_SWITCH":
                confidence = 1.0
                cause.severity = CauseSeverity.CRITICAL
                evidence.append("触发 KILL SWITCH，强制平仓")
                break

        if confidence > 0:
            cause.confidence = min(confidence, 1.0)
            cause.title = "风控退出"
            cause.description = "止损规则或风控系统触发平仓"
            cause.evidence = evidence
            cause.metrics = metrics
            if cause.severity != CauseSeverity.CRITICAL:
                cause.severity = CauseSeverity.WARNING if confidence < 0.7 else CauseSeverity.CRITICAL

        return cause

    def _check_market_shock(self, trace: TradeTrace) -> RootCause:
        """市场冲击：异常波动 / 市场急变"""
        cause = RootCause(type=CauseType.MARKET_SHOCK)

        evidence = []
        metrics: Dict[str, Any] = {}
        confidence = 0.0

        # 检查市场变动幅度
        if trace.market_change:
            change = abs(trace.market_change)
            metrics["market_change"] = trace.market_change
            if change > self.MARKET_SHOCK_PCT:
                confidence += 0.5
                direction = "下跌" if trace.market_change < 0 else "上涨"
                evidence.append(f"持仓期间市场{direction} {change*100:.2f}%，异常波动")

                # 如果是多头且市场下跌，或空头且市场上涨
                if trace.entry:
                    is_long = trace.entry.side.upper() == "BUY"
                    adverse = (is_long and trace.market_change < 0) or (not is_long and trace.market_change > 0)
                    if adverse:
                        confidence += 0.2
                        evidence.append("市场变动方向不利于持仓")

        # 检查最大回撤（max_price - exit_price）
        if trace.max_price and trace.exit_price and trace.entry and trace.entry.side.upper() == "BUY":
            drawdown = (trace.max_price - trace.exit_price) / trace.max_price
            if drawdown > self.MARKET_SHOCK_PCT:
                confidence += 0.2
                evidence.append(f"从最高点回撤 {drawdown*100:.2f}%")
                metrics["max_drawdown"] = drawdown

        if confidence > 0:
            cause.confidence = min(confidence, 1.0)
            cause.title = "市场冲击"
            cause.description = "市场异常波动导致亏损"
            cause.evidence = evidence
            cause.metrics = metrics
            cause.severity = CauseSeverity.WARNING if confidence < 0.6 else CauseSeverity.CRITICAL

        return cause

    def _check_overexposure(self, trace: TradeTrace) -> RootCause:
        """仓位过大：仓位占比过高 / 杠杆过高"""
        cause = RootCause(type=CauseType.OVEREXPOSURE)

        evidence = []
        metrics: Dict[str, Any] = {}
        confidence = 0.0

        # 检查仓位大小（相对于价格的绝对值）
        if trace.entry and trace.entry.qty and trace.entry.price:
            notional = trace.entry.qty * trace.entry.price
            metrics["notional"] = notional

            # 这里没有账户规模信息，用启发式判断
            # 如果亏损金额较大，可能是仓位过大
            if trace.pnl is not None and trace.pnl < -100:
                confidence += 0.2
                evidence.append(f"亏损金额 ${trace.pnl:.2f}，绝对值较大")

            # 如果 pnl_pct 不大但 pnl 绝对值大，说明仓位大
            if trace.pnl_pct is not None and abs(trace.pnl_pct) < 2 and trace.pnl is not None and trace.pnl < -50:
                confidence += 0.3
                evidence.append(f"亏损率仅 {trace.pnl_pct:.2f}% 但亏损 ${trace.pnl:.2f}，仓位过大")

        if confidence > 0:
            cause.confidence = min(confidence, 1.0)
            cause.title = "仓位过大"
            cause.description = "仓位占比过高，放大了亏损"
            cause.evidence = evidence
            cause.metrics = metrics
            cause.severity = CauseSeverity.WARNING

        return cause
