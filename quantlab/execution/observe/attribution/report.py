"""
Monthly Review Engine — 月度复盘引擎

Observe Studio 最后一个重量级模块。

自动生成月度报告：
  - 总收益
  - 最大回撤
  - 胜率
  - 策略贡献
  - 风险贡献
  - 最佳交易
  - 最差交易

导出格式：
  - Markdown（默认）
  - HTML
  - PDF（预留）

用法：
    engine = MonthlyReview(store)
    report = engine.generate(year=2026, month=6)
    print(report.to_markdown())
"""

from __future__ import annotations

import calendar
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..event_store import EventStore
from .risk import RiskAttribution, RiskAttributionReport
from .strategy import StrategyAttribution, StrategyAttributionReport
from .symbol import SymbolAttribution, SymbolAttributionReport
from .time import TimeAttribution, TimeAttributionReport

logger = logging.getLogger("quantlab.execution.observe.attribution.report")


@dataclass
class TradeSummary:
    """交易摘要"""
    trace_id: str = ""
    symbol: str = ""
    strategy: str = ""
    pnl: float = 0.0
    pnl_pct: float = 0.0
    timestamp: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "symbol": self.symbol,
            "strategy": self.strategy,
            "pnl": round(self.pnl, 2),
            "pnl_pct": round(self.pnl_pct, 2),
            "timestamp": self.timestamp,
        }


@dataclass
class MonthlyReport:
    """月度报告"""
    year: int = 0
    month: int = 0
    period_label: str = ""  # "2026-06"

    # 时间范围
    start_ts: int = 0
    end_ts: int = 0

    # 核心指标
    total_pnl: float = 0.0
    total_trades: int = 0
    n_wins: int = 0
    n_losses: int = 0
    win_rate: float = 0.0
    max_drawdown: float = 0.0
    profit_factor: float = 0.0
    avg_pnl: float = 0.0

    # 归因报告
    strategy_attribution: Optional[StrategyAttributionReport] = None
    symbol_attribution: Optional[SymbolAttributionReport] = None
    time_attribution: Optional[TimeAttributionReport] = None
    risk_attribution: Optional[RiskAttributionReport] = None

    # 最佳/最差交易
    best_trade: Optional[TradeSummary] = None
    worst_trade: Optional[TradeSummary] = None

    # 评价
    summary: str = ""
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "year": self.year,
            "month": self.month,
            "period_label": self.period_label,
            "start_ts": self.start_ts,
            "end_ts": self.end_ts,
            "total_pnl": round(self.total_pnl, 2),
            "total_trades": self.total_trades,
            "n_wins": self.n_wins,
            "n_losses": self.n_losses,
            "win_rate": round(self.win_rate, 4),
            "max_drawdown": round(self.max_drawdown, 2),
            "profit_factor": round(self.profit_factor, 4),
            "avg_pnl": round(self.avg_pnl, 2),
            "strategy_attribution": self.strategy_attribution.to_dict() if self.strategy_attribution else None,
            "symbol_attribution": self.symbol_attribution.to_dict() if self.symbol_attribution else None,
            "time_attribution": self.time_attribution.to_dict() if self.time_attribution else None,
            "risk_attribution": self.risk_attribution.to_dict() if self.risk_attribution else None,
            "best_trade": self.best_trade.to_dict() if self.best_trade else None,
            "worst_trade": self.worst_trade.to_dict() if self.worst_trade else None,
            "summary": self.summary,
            "suggestions": self.suggestions,
        }

    def to_markdown(self) -> str:
        """转 Markdown"""
        lines = [
            f"# {self.period_label} Monthly Report",
            "",
            f"**期间**: {datetime.fromtimestamp(self.start_ts/1000).strftime('%Y-%m-%d')} ~ "
            f"{datetime.fromtimestamp(self.end_ts/1000).strftime('%Y-%m-%d')}",
            "",
            "## 核心指标",
            "",
            f"- 总收益: **{self.total_pnl:+.2f}**",
            f"- 交易笔数: {self.total_trades}",
            f"- 胜率: {self.win_rate*100:.1f}% ({self.n_wins}胜 / {self.n_losses}负)",
            f"- 盈亏比: {self.profit_factor:.2f}",
            f"- 最大回撤: {self.max_drawdown:.2f}",
            f"- 平均单笔: {self.avg_pnl:+.2f}",
            "",
        ]

        # 策略归因
        if self.strategy_attribution and self.strategy_attribution.strategies:
            lines.extend([
                "## 策略归因",
                "",
                "| 策略 | PnL | 占比 | 交易数 | 胜率 | 风险贡献 |",
                "|------|-----|------|--------|------|----------|",
            ])
            for s in self.strategy_attribution.strategies:
                lines.append(
                    f"| {s.strategy} | {s.pnl:+.2f} | {s.pnl_pct:.1f}% | "
                    f"{s.n_trades} | {s.win_rate*100:.1f}% | {s.risk_pct:.1f}% |"
                )
            lines.append("")

        # 品种归因
        if self.symbol_attribution and self.symbol_attribution.symbols:
            lines.extend([
                "## 品种归因",
                "",
                "| 品种 | PnL | 占比 | 交易数 | 胜率 |",
                "|------|-----|------|--------|------|",
            ])
            for s in self.symbol_attribution.symbols:
                lines.append(
                    f"| {s.symbol} | {s.pnl:+.2f} | {s.pnl_pct:.1f}% | "
                    f"{s.n_trades} | {s.win_rate*100:.1f}% |"
                )
            lines.append("")

        # 多空归因
        if self.symbol_attribution and self.symbol_attribution.long_short:
            ls = self.symbol_attribution.long_short
            lines.extend([
                "## 多空归因",
                "",
                f"- 多头 PnL: {ls.long_pnl:+.2f} ({ls.n_long} 笔)",
                f"- 空头 PnL: {ls.short_pnl:+.2f} ({ls.n_short} 笔)",
                f"- 评价: {ls.note}",
                "",
            ])

        # 时段归因
        if self.time_attribution and self.time_attribution.time_slots:
            lines.extend([
                "## 时段归因",
                "",
                "| 时段 | PnL | 交易数 | 胜率 |",
                "|------|-----|--------|------|",
            ])
            for t in self.time_attribution.time_slots:
                lines.append(
                    f"| {t.label} | {t.pnl:+.2f} | {t.n_trades} | {t.win_rate*100:.1f}% |"
                )
            lines.append("")

        # Regime 归因
        if self.time_attribution and self.time_attribution.regimes:
            lines.extend([
                "## 市场状态归因",
                "",
                "| 状态 | PnL | 交易数 | 胜率 |",
                "|------|-----|--------|------|",
            ])
            for r in self.time_attribution.regimes:
                lines.append(
                    f"| {r.label} | {r.pnl:+.2f} | {r.n_trades} | {r.win_rate*100:.1f}% |"
                )
            if self.time_attribution.regime_note:
                lines.append("")
                lines.append(f"**评价**: {self.time_attribution.regime_note}")
            lines.append("")

        # 风险归因
        if self.risk_attribution and self.risk_attribution.risk_contributions:
            lines.extend([
                "## 风险归因",
                "",
                "| 策略 | 收益贡献 | 风险贡献 | 收益质量 | Sharpe |",
                "|------|----------|----------|----------|--------|",
            ])
            for r in self.risk_attribution.risk_contributions:
                lines.append(
                    f"| {r.strategy} | {r.pnl_pct:.1f}% | {r.risk_pct:.1f}% | "
                    f"{r.quality_label} | {r.sharpe:.2f} |"
                )
            lines.append("")

        # 回撤归因
        if self.risk_attribution and self.risk_attribution.drawdown_contributions:
            lines.extend([
                "## 回撤归因",
                "",
                "| 策略 | 最大回撤 | 占比 |",
                "|------|----------|------|",
            ])
            total_dd = abs(self.risk_attribution.overall_max_drawdown)
            for d in self.risk_attribution.drawdown_contributions:
                pct = (abs(d.max_drawdown) / total_dd * 100) if total_dd > 0 else 0
                lines.append(
                    f"| {d.strategy} | {d.max_drawdown:.2f} | {pct:.1f}% |"
                )
            lines.append("")

        # 最佳/最差交易
        if self.best_trade:
            lines.extend([
                "## 最佳交易",
                "",
                f"- 标的: {self.best_trade.symbol}",
                f"- 策略: {self.best_trade.strategy}",
                f"- PnL: {self.best_trade.pnl:+.2f}",
                "",
            ])
        if self.worst_trade:
            lines.extend([
                "## 最差交易",
                "",
                f"- 标的: {self.worst_trade.symbol}",
                f"- 策略: {self.worst_trade.strategy}",
                f"- PnL: {self.worst_trade.pnl:+.2f}",
                "",
            ])

        # 总结
        if self.summary:
            lines.extend([
                "## 总结",
                "",
                self.summary,
                "",
            ])

        # 建议
        if self.suggestions:
            lines.extend([
                "## 改进建议",
                "",
            ])
            for s in self.suggestions:
                lines.append(f"- {s}")
            lines.append("")

        return "\n".join(lines)

    def to_html(self) -> str:
        """转 HTML（简单版）"""
        md = self.to_markdown()
        # 简单的 Markdown → HTML 转换
        html = ["<html><head><meta charset='utf-8'><style>",
                "body{font-family:sans-serif;margin:40px;}",
                "table{border-collapse:collapse;width:100%;}",
                "th,td{border:1px solid #ddd;padding:8px;text-align:left;}",
                "th{background:#f2f2f2;}",
                "</style></head><body>"]

        in_table = False
        for line in md.split("\n"):
            if line.startswith("# "):
                html.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith("## "):
                html.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("- "):
                html.append(f"<li>{line[2:]}</li>")
            elif line.startswith("|"):
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if cells[0] == "策略" or cells[0] == "品种" or cells[0] == "时段" or cells[0] == "状态":
                    html.append("<table><tr>" + "".join(f"<th>{c}</th>" for c in cells) + "</tr>")
                    in_table = True
                elif cells[0].startswith("---") or set(cells[0]) <= {"-", ":"}:
                    continue
                elif in_table:
                    if cells[0] == "":
                        html.append("</table>")
                        in_table = False
                    else:
                        html.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
            elif line.strip() == "":
                if in_table:
                    html.append("</table>")
                    in_table = False
                html.append("<br>")
            else:
                html.append(f"<p>{line}</p>")

        if in_table:
            html.append("</table>")
        html.append("</body></html>")
        return "\n".join(html)


class MonthlyReview:
    """
    月度复盘引擎

    用法：
        engine = MonthlyReview(store)
        report = engine.generate(year=2026, month=6)
        print(report.to_markdown())
        html = report.to_html()
    """

    def __init__(self, store: EventStore) -> None:
        self.store = store

    def generate(
        self,
        year: int,
        month: int,
        session_id: Optional[str] = None,
    ) -> MonthlyReport:
        """
        生成月度报告

        Args:
            year: 年份
            month: 月份（1-12）
            session_id: 可选，限定会话
        """
        # 计算时间范围（UTC）
        _, last_day = calendar.monthrange(year, month)
        start_dt = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_dt = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)
        start_ts = int(start_dt.timestamp() * 1000)
        end_ts = int(end_dt.timestamp() * 1000)

        report = MonthlyReport(
            year=year,
            month=month,
            period_label=f"{year}-{month:02d}",
            start_ts=start_ts,
            end_ts=end_ts,
        )

        # 生成各归因
        report.strategy_attribution = StrategyAttribution(self.store).analyze_range(
            start_ts, end_ts, session_id
        )
        report.symbol_attribution = SymbolAttribution(self.store).analyze_range(
            start_ts, end_ts, session_id
        )
        report.time_attribution = TimeAttribution(self.store).analyze_range(
            start_ts, end_ts, session_id
        )
        report.risk_attribution = RiskAttribution(self.store).analyze_range(
            start_ts, end_ts, session_id
        )

        # 核心指标（从策略归因汇总）
        sa = report.strategy_attribution
        report.total_pnl = sa.total_pnl
        report.total_trades = sa.total_trades
        report.n_wins = sum(s.n_wins for s in sa.strategies)
        report.n_losses = sum(s.n_losses for s in sa.strategies)
        report.win_rate = report.n_wins / report.total_trades if report.total_trades else 0
        gross_profit = sum(s.gross_profit for s in sa.strategies)
        gross_loss = sum(s.gross_loss for s in sa.strategies)
        report.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        report.avg_pnl = report.total_pnl / report.total_trades if report.total_trades else 0

        # 最大回撤（从风险归因）
        if report.risk_attribution.drawdown_contributions:
            report.max_drawdown = min(
                d.max_drawdown for d in report.risk_attribution.drawdown_contributions
            )

        # 最佳/最差交易
        self._find_best_worst_trades(report, start_ts, end_ts, session_id)

        # 生成总结和建议
        report.summary = self._build_summary(report)
        report.suggestions = self._build_suggestions(report)

        return report

    # ------------------------------------------------------------------

    def _find_best_worst_trades(
        self,
        report: MonthlyReport,
        start_ts: int,
        end_ts: int,
        session_id: Optional[str],
    ) -> None:
        """找最佳和最差交易"""
        from collections import defaultdict
        events = self.store.query(
            session_id=session_id,
            start_ts=start_ts,
            end_ts=end_ts,
            limit=100000,
        )

        traces = defaultdict(list)
        for e in events:
            tid = e.trace_id or e.event_id
            traces[tid].append(e)

        trades: List[TradeSummary] = []
        for tid, evs in traces.items():
            pnl = None
            symbol = ""
            strategy = ""
            ts = 0
            for e in sorted(evs, key=lambda x: x.timestamp):
                if not symbol:
                    symbol = e.payload.get("symbol", "")
                if not strategy and e.event_type.upper() == "SIGNAL":
                    strategy = e.payload.get("strategy", e.source or "")
                if not ts:
                    ts = e.timestamp
                if e.event_type.upper() == "FILL":
                    p = e.payload.get("pnl")
                    if p is not None:
                        pnl = float(p)
                        break

            if pnl is not None:
                trades.append(TradeSummary(
                    trace_id=tid,
                    symbol=symbol,
                    strategy=strategy,
                    pnl=pnl,
                    timestamp=ts,
                ))

        if trades:
            trades.sort(key=lambda t: t.pnl, reverse=True)
            report.best_trade = trades[0]
            report.worst_trade = trades[-1]

    def _build_summary(self, report: MonthlyReport) -> str:
        """生成总结"""
        parts = []
        parts.append(
            f"{report.period_label} 期间共完成 {report.total_trades} 笔交易，"
            f"总收益 {report.total_pnl:+.2f}，胜率 {report.win_rate*100:.1f}%。"
        )

        if report.strategy_attribution and report.strategy_attribution.strategies:
            best = report.strategy_attribution.best_strategy
            worst = report.strategy_attribution.worst_strategy
            parts.append(f"表现最佳的策略是 {best}，表现最差的是 {worst}。")

        if report.symbol_attribution and report.symbol_attribution.symbols:
            best_sym = report.symbol_attribution.best_symbol
            worst_sym = report.symbol_attribution.worst_symbol
            parts.append(f"赚钱最多的品种是 {best_sym}，亏钱最多的是 {worst_sym}。")

        if report.time_attribution and report.time_attribution.regime_note:
            parts.append(report.time_attribution.regime_note)

        return " ".join(parts)

    def _build_suggestions(self, report: MonthlyReport) -> List[str]:
        """生成建议"""
        suggestions = []

        # 胜率低
        if report.win_rate < 0.4:
            suggestions.append("胜率偏低，建议优化信号过滤逻辑")

        # 盈亏比低
        if report.profit_factor < 1.5:
            suggestions.append("盈亏比偏低，建议提高止盈位或缩小止损位")

        # 集中度过高
        if report.strategy_attribution and report.strategy_attribution.concentration > 0.5:
            suggestions.append("收益过度集中于单一策略，建议增加策略多样性")

        # 风险贡献失衡
        if report.risk_attribution and report.risk_attribution.risk_contributions:
            for r in report.risk_attribution.risk_contributions:
                if r.quality_label == "bad":
                    suggestions.append(
                        f"策略 {r.strategy} 收益质量差（收益贡献 {r.pnl_pct:.1f}% / "
                        f"风险贡献 {r.risk_pct:.1f}%），建议降低仓位或优化"
                    )

        # 多空失衡
        if report.symbol_attribution:
            ls = report.symbol_attribution.long_short
            if ls.bias == "long_bias" and ls.short_pnl < 0:
                suggestions.append("做空能力弱，建议暂停做空或优化做空逻辑")

        # 回撤过大
        if report.max_drawdown < -1000:
            suggestions.append("最大回撤较大，建议加强风控")

        return suggestions
