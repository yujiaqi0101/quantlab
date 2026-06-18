"""
Explain Engine — 解释引擎

Observe Studio 的灵魂：把 RCA 的结构化结果转成人类可读的自然语言解释。

例如：
    "这笔交易亏损的主要原因：
     策略在上涨趋势末期发出买入信号
     成交滑点为 0.18%
     随后市场在 15 分钟内下跌 2.4%
     止损规则在 -2% 处触发
     根因：趋势反转 + 止损退出"

用法：
    engine = ExplainEngine()
    explanation = engine.explain(trace, causes)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .root_cause import CauseType, RootCause
from .trace import TradeTrace

logger = logging.getLogger("quantlab.execution.observe.analysis.explain")


@dataclass
class Explanation:
    """解释结果"""
    # 一句话总结
    summary: str = ""
    # 详细解释（多段）
    paragraphs: List[str] = field(default_factory=list)
    # 关键指标
    key_metrics: Dict[str, Any] = field(default_factory=dict)
    # 根因标签
    root_cause_labels: List[str] = field(default_factory=list)
    # 建议改进
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "paragraphs": self.paragraphs,
            "key_metrics": self.key_metrics,
            "root_cause_labels": self.root_cause_labels,
            "suggestions": self.suggestions,
        }

    def to_text(self) -> str:
        """转成纯文本"""
        lines = [self.summary, ""]
        lines.extend(self.paragraphs)
        if self.suggestions:
            lines.append("")
            lines.append("改进建议：")
            for s in self.suggestions:
                lines.append(f"  - {s}")
        return "\n".join(lines)


class ExplainEngine:
    """
    解释引擎

    用法：
        engine = ExplainEngine()
        explanation = engine.explain(trace, causes)
        print(explanation.to_text())
    """

    # 根因类型 → 中文标签
    CAUSE_LABELS = {
        CauseType.SIGNAL_ERROR: "信号错误",
        CauseType.EXECUTION_ERROR: "执行错误",
        CauseType.RISK_EXIT: "风控退出",
        CauseType.MARKET_SHOCK: "市场冲击",
        CauseType.OVEREXPOSURE: "仓位过大",
        CauseType.UNKNOWN: "未知",
    }

    def explain(
        self,
        trace: TradeTrace,
        causes: List[RootCause],
    ) -> Explanation:
        """生成解释"""
        exp = Explanation()

        # 1. 总结
        exp.summary = self._build_summary(trace, causes)

        # 2. 详细段落
        exp.paragraphs = self._build_paragraphs(trace, causes)

        # 3. 关键指标
        exp.key_metrics = self._build_metrics(trace)

        # 4. 根因标签
        exp.root_cause_labels = [self.CAUSE_LABELS.get(c.type, c.type.value) for c in causes]

        # 5. 建议
        exp.suggestions = self._build_suggestions(trace, causes)

        return exp

    # ------------------------------------------------------------------
    # 构建各部分
    # ------------------------------------------------------------------

    def _build_summary(self, trace: TradeTrace, causes: List[RootCause]) -> str:
        """一句话总结"""
        if not trace.is_closed:
            return f"{trace.symbol} 持仓中，未平仓"

        pnl_str = f"{trace.pnl:+.2f}" if trace.pnl is not None else "N/A"
        pnl_pct_str = f"{trace.pnl_pct:+.2f}%" if trace.pnl_pct is not None else ""

        if not causes:
            if trace.is_win:
                return f"{trace.symbol} 盈利交易 {pnl_str} ({pnl_pct_str})"
            else:
                return f"{trace.symbol} 亏损交易 {pnl_str} ({pnl_pct_str})"

        # 主要根因
        primary = causes[0]
        label = self.CAUSE_LABELS.get(primary.type, primary.type.value)

        if trace.is_loss:
            return f"{trace.symbol} 亏损 {pnl_str} ({pnl_pct_str})，根因：{label}"
        else:
            return f"{trace.symbol} 盈利 {pnl_str} ({pnl_pct_str})"

    def _build_paragraphs(self, trace: TradeTrace, causes: List[RootCause]) -> List[str]:
        """详细段落"""
        paras = []

        # 段落 1：交易概况
        paras.append(self._paragraph_trade_overview(trace))

        # 段落 2：入场分析
        if trace.entry:
            paras.append(self._paragraph_entry(trace))

        # 段落 3：持仓期间
        if trace.is_closed:
            paras.append(self._paragraph_holding(trace))

        # 段落 4：出场分析
        if trace.exit:
            paras.append(self._paragraph_exit(trace))

        # 段落 5：根因分析
        if causes:
            paras.append(self._paragraph_causes(causes))

        return paras

    def _paragraph_trade_overview(self, trace: TradeTrace) -> str:
        """交易概况"""
        parts = [f"交易标的：{trace.symbol}"]
        if trace.strategy:
            parts.append(f"策略：{trace.strategy}")
        if trace.is_closed:
            parts.append(f"持仓时间：{self._format_duration(trace.holding_ms)}")
            if trace.pnl is not None:
                parts.append(f"盈亏：{trace.pnl:+.2f} ({trace.pnl_pct:+.2f}%)")
        return "交易概况：" + "，".join(parts) + "。"

    def _paragraph_entry(self, trace: TradeTrace) -> str:
        """入场分析"""
        e = trace.entry
        parts = [f"入场方向：{e.side}", f"价格：{e.price}", f"数量：{e.qty}"]

        if e.signal_event:
            score_str = f"分数 {e.signal_score:.2f}" if e.signal_score is not None else "无分数"
            parts.append(f"信号来源：{e.signal_strategy or '未知策略'} ({score_str})")

        if e.order_price and e.slippage_bps:
            parts.append(f"订单价：{e.order_price}")
            parts.append(f"滑点：{e.slippage_bps:.1f} bps")

        return "入场：" + "，".join(parts) + "。"

    def _paragraph_holding(self, trace: TradeTrace) -> str:
        """持仓期间"""
        parts = [f"持仓时长：{self._format_duration(trace.holding_ms)}"]

        if trace.entry_price and trace.exit_price:
            change_pct = trace.market_change * 100
            direction = "上涨" if trace.market_change > 0 else "下跌"
            parts.append(f"期间市场{direction} {abs(change_pct):.2f}%")

        if trace.max_price and trace.min_price:
            parts.append(f"最高 {trace.max_price}，最低 {trace.min_price}")

        return "持仓期间：" + "，".join(parts) + "。"

    def _paragraph_exit(self, trace: TradeTrace) -> str:
        """出场分析"""
        e = trace.exit
        parts = [f"出场方向：{e.side}", f"价格：{e.price}", f"数量：{e.qty}"]

        if e.order_price and e.slippage_bps:
            parts.append(f"订单价：{e.order_price}")
            parts.append(f"滑点：{e.slippage_bps:.1f} bps")

        if trace.risk_events:
            parts.append(f"触发 {len(trace.risk_events)} 个风险事件")

        return "出场：" + "，".join(parts) + "。"

    def _paragraph_causes(self, causes: List[RootCause]) -> str:
        """根因分析"""
        lines = ["根因分析："]
        for i, c in enumerate(causes, 1):
            label = self.CAUSE_LABELS.get(c.type, c.type.value)
            lines.append(
                f"  {i}. [{label}] (置信度 {c.confidence*100:.0f}%) {c.description}"
            )
            for ev in c.evidence:
                lines.append(f"     - {ev}")
        return "\n".join(lines)

    def _build_metrics(self, trace: TradeTrace) -> Dict[str, Any]:
        """关键指标"""
        m: Dict[str, Any] = {
            "symbol": trace.symbol,
            "strategy": trace.strategy,
            "is_closed": trace.is_closed,
        }
        if trace.pnl is not None:
            m["pnl"] = round(trace.pnl, 2)
        if trace.pnl_pct is not None:
            m["pnl_pct"] = round(trace.pnl_pct, 2)
        if trace.holding_ms:
            m["holding_ms"] = trace.holding_ms
            m["holding_human"] = self._format_duration(trace.holding_ms)
        if trace.entry:
            m["entry_price"] = trace.entry.price
            m["entry_qty"] = trace.entry.qty
            if trace.entry.slippage_bps:
                m["entry_slippage_bps"] = round(trace.entry.slippage_bps, 2)
        if trace.exit:
            m["exit_price"] = trace.exit.price
            m["exit_qty"] = trace.exit.qty
            if trace.exit.slippage_bps:
                m["exit_slippage_bps"] = round(trace.exit.slippage_bps, 2)
        if trace.market_change:
            m["market_change"] = round(trace.market_change * 100, 2)
        return m

    def _build_suggestions(self, trace: TradeTrace, causes: List[RootCause]) -> List[str]:
        """改进建议"""
        suggestions = []

        for c in causes:
            if c.type == CauseType.SIGNAL_ERROR:
                suggestions.append("检查信号生成逻辑，考虑增加趋势过滤或时间过滤")
                if trace.entry and trace.entry.signal_score is not None and trace.entry.signal_score < 0.5:
                    suggestions.append("提高信号分数阈值，过滤低质量信号")
            elif c.type == CauseType.EXECUTION_ERROR:
                suggestions.append("使用限价单替代市价单，减少滑点")
                suggestions.append("检查订单路由，选择流动性更好的交易所")
            elif c.type == CauseType.RISK_EXIT:
                suggestions.append("调整止损位，避免被短期波动触发")
                suggestions.append("考虑使用追踪止损替代固定止损")
            elif c.type == CauseType.MARKET_SHOCK:
                suggestions.append("增加波动率过滤，高波动时降低仓位")
                suggestions.append("考虑添加市场状态检测，异常时暂停交易")
            elif c.type == CauseType.OVEREXPOSURE:
                suggestions.append("降低单笔仓位占比")
                suggestions.append("实施凯利公式或固定比例仓位管理")

        # 去重
        seen = set()
        unique = []
        for s in suggestions:
            if s not in seen:
                seen.add(s)
                unique.append(s)
        return unique

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------

    def _format_duration(self, ms: int) -> str:
        """格式化时长"""
        if ms < 1000:
            return f"{ms} ms"
        if ms < 60000:
            return f"{ms/1000:.1f} 秒"
        if ms < 3600000:
            return f"{ms/60000:.1f} 分钟"
        return f"{ms/3600000:.1f} 小时"
