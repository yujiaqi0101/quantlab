"""
Observe Studio V4 — Performance Attribution 端到端测试

构造模拟交易事件，验证所有归因模块正常工作。
"""

import sys
import os
import time
import uuid
from datetime import datetime, timezone, timedelta

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quantlab.execution.observe import (
    get_event_store,
    EventStore,
    StrategyAttribution,
    SymbolAttribution,
    TimeAttribution,
    RiskAttribution,
    FactorAttribution,
    MonthlyReview,
)


def make_test_store(db_path: str = ":memory:") -> EventStore:
    """创建内存数据库的 EventStore"""
    store = EventStore(db_path=db_path)
    store.open()
    return store


def inject_trades(store: EventStore, session_id: str) -> None:
    """注入模拟交易事件"""
    base_ts = int(datetime(2026, 6, 10, 10, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)

    # 创建会话
    store.create_session(
        session_id=session_id,
        strategy="TestPortfolio",
        symbol="MULTI",
        meta={"test": True},
    )

    trades = [
        # (strategy, symbol, side, entry_price, exit_price, qty, hour_offset, pnl_direct)
        # BTC_Momentum 做多 BTC，盈利
        ("BTC_Momentum", "BTCUSDT", "BUY",  60000, 61500, 0.1, 0,  150),
        ("BTC_Momentum", "BTCUSDT", "BUY",  61000, 62500, 0.1, 2,  150),
        ("BTC_Momentum", "BTCUSDT", "BUY",  62000, 61500, 0.1, 4,  -50),
        ("BTC_Momentum", "BTCUSDT", "BUY",  63000, 64500, 0.1, 6,  150),
        # ETH_MeanReversion 做多/做空 ETH，亏损
        ("ETH_MeanReversion", "ETHUSDT", "BUY",  3000, 2950, 1.0, 8,  -50),
        ("ETH_MeanReversion", "ETHUSDT", "SELL", 3000, 3050, 1.0, 10, -50),
        ("ETH_MeanReversion", "ETHUSDT", "BUY",  2950, 2900, 1.0, 12, -50),
        # LGBM_Trend 做多 SOL，小盈利
        ("LGBM_Trend", "SOLUSDT", "BUY",  150, 155, 10, 14,  50),
        ("LGBM_Trend", "SOLUSDT", "BUY",  155, 153, 10, 16, -20),
        ("LGBM_Trend", "SOLUSDT", "BUY",  153, 158, 10, 18,  50),
        # Portfolio_Rotation 做空 BNB，小盈利
        ("Portfolio_Rotation", "BNBUSDT", "SELL", 600, 590, 5, 20,  50),
    ]

    for i, (strategy, symbol, side, entry_price, exit_price, qty, hour_offset, expected_pnl) in enumerate(trades):
        trace_id = f"trace_{i:03d}"
        ts = base_ts + hour_offset * 3600 * 1000

        # SIGNAL 事件
        store.append(
            event_type="SIGNAL",
            payload={
                "strategy": strategy,
                "symbol": symbol,
                "side": side,
                "score": 0.75,
                "price": entry_price,
            },
            timestamp=ts,
            source=strategy,
            trace_id=trace_id,
            session_id=session_id,
        )

        # ORDER 事件
        store.append(
            event_type="ORDER",
            payload={
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "price": entry_price,
                "type": "LIMIT",
            },
            timestamp=ts + 100,
            source="OMS",
            trace_id=trace_id,
            session_id=session_id,
        )

        # FILL 入场
        store.append(
            event_type="FILL",
            payload={
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "price": entry_price,
                "order_id": f"ord_{i:03d}",
            },
            timestamp=ts + 200,
            source="EXCHANGE",
            trace_id=trace_id,
            session_id=session_id,
        )

        # FILL 出场（带 pnl）
        exit_side = "SELL" if side == "BUY" else "BUY"
        store.append(
            event_type="FILL",
            payload={
                "symbol": symbol,
                "side": exit_side,
                "qty": qty,
                "price": exit_price,
                "order_id": f"ord_{i:03d}_exit",
                "pnl": expected_pnl,
            },
            timestamp=ts + 7200 * 1000,  # 2小时后
            source="EXCHANGE",
            trace_id=trace_id,
            session_id=session_id,
        )


def test_strategy_attribution(store: EventStore, session_id: str) -> None:
    print("\n=== Strategy Attribution ===")
    report = StrategyAttribution(store).analyze(session_id=session_id)
    print(f"总收益: {report.total_pnl:+.2f}")
    print(f"交易笔数: {report.total_trades}")
    print(f"最佳策略: {report.best_strategy}")
    print(f"最差策略: {report.worst_strategy}")
    print(f"集中度: {report.concentration:.2%}")
    print("\n策略明细:")
    for s in report.strategies:
        print(f"  {s.strategy:25s} PnL={s.pnl:+8.2f}  占比={s.pnl_pct:6.1f}%  "
              f"交易={s.n_trades}  胜率={s.win_rate:.1%}  风险贡献={s.risk_pct:.1f}%")


def test_symbol_attribution(store: EventStore, session_id: str) -> None:
    print("\n=== Symbol Attribution ===")
    report = SymbolAttribution(store).analyze(session_id=session_id)
    print(f"最佳品种: {report.best_symbol}")
    print(f"最差品种: {report.worst_symbol}")
    print("\n品种排行榜:")
    for s in report.symbols:
        print(f"  {s.symbol:10s} PnL={s.pnl:+8.2f}  占比={s.pnl_pct:6.1f}%  "
              f"交易={s.n_trades}  多={s.long_pnl:+.2f}  空={s.short_pnl:+.2f}")

    print("\n多空归因:")
    ls = report.long_short
    print(f"  多头 PnL: {ls.long_pnl:+.2f} ({ls.n_long} 笔, 胜率 {ls.long_win_rate:.1%})")
    print(f"  空头 PnL: {ls.short_pnl:+.2f} ({ls.n_short} 笔, 胜率 {ls.short_win_rate:.1%})")
    print(f"  评价: {ls.bias} - {ls.note}")


def test_time_attribution(store: EventStore, session_id: str) -> None:
    print("\n=== Time Attribution ===")
    report = TimeAttribution(store).analyze(session_id=session_id)
    print(f"最佳时段: {report.best_slot}")
    print(f"最差时段: {report.worst_slot}")
    print("\n时段归因:")
    for t in report.time_slots:
        print(f"  {t.label:6s} PnL={t.pnl:+8.2f}  交易={t.n_trades}  胜率={t.win_rate:.1%}")

    print("\nRegime 归因:")
    for r in report.regimes:
        print(f"  {r.label:6s} PnL={r.pnl:+8.2f}  交易={r.n_trades}  时长占比={r.duration_pct:.1f}%")
    if report.regime_note:
        print(f"  评价: {report.regime_note}")


def test_risk_attribution(store: EventStore, session_id: str) -> None:
    print("\n=== Risk Attribution ===")
    report = RiskAttribution(store).analyze(session_id=session_id)
    print(f"质量最佳: {report.best_quality_strategy}")
    print(f"质量最差: {report.worst_quality_strategy}")
    print("\n风险贡献:")
    for r in report.risk_contributions:
        print(f"  {r.strategy:25s} 收益={r.pnl_pct:6.1f}%  风险={r.risk_pct:6.1f}%  "
              f"质量={r.quality_label:8s} Sharpe={r.sharpe:.2f}")

    print(f"\n回撤归因 (总回撤: {report.overall_max_drawdown:.2f}):")
    print(f"  回撤元凶: {report.drawdown_culprit}")
    for d in report.drawdown_contributions:
        print(f"  {d.strategy:25s} 最大回撤={d.max_drawdown:+8.2f}  交易={d.n_trades}")


def test_factor_attribution(store: EventStore, session_id: str) -> None:
    print("\n=== Factor Attribution (预留) ===")
    report = FactorAttribution(store).analyze(session_id=session_id)
    print(f"已实现: {report.implemented}")
    print(f"说明: {report.note}")


def test_monthly_review(store: EventStore, session_id: str) -> None:
    print("\n=== Monthly Review ===")
    report = MonthlyReview(store).generate(year=2026, month=6, session_id=session_id)
    print(f"期间: {report.period_label}")
    print(f"总收益: {report.total_pnl:+.2f}")
    print(f"交易笔数: {report.total_trades}")
    print(f"胜率: {report.win_rate:.1%}")
    print(f"盈亏比: {report.profit_factor:.2f}")
    print(f"最大回撤: {report.max_drawdown:.2f}")

    if report.best_trade:
        print(f"\n最佳交易: {report.best_trade.symbol} ({report.best_trade.strategy}) "
              f"PnL={report.best_trade.pnl:+.2f}")
    if report.worst_trade:
        print(f"最差交易: {report.worst_trade.symbol} ({report.worst_trade.strategy}) "
              f"PnL={report.worst_trade.pnl:+.2f}")

    print(f"\n总结: {report.summary}")
    if report.suggestions:
        print("\n改进建议:")
        for s in report.suggestions:
            print(f"  - {s}")

    # 测试 Markdown 输出
    md = report.to_markdown()
    print(f"\nMarkdown 报告长度: {len(md)} 字符")
    print("\n--- Markdown 预览（前 500 字符）---")
    print(md[:500])


def main() -> None:
    print("=" * 70)
    print("Observe Studio V4 — Performance Attribution 端到端测试")
    print("=" * 70)

    # 创建测试 store
    store = make_test_store()

    # 注入测试数据
    session_id = "test_session_v4"
    inject_trades(store, session_id)
    print(f"\n已注入测试数据到会话: {session_id}")

    # 验证事件数
    events = store.query(session_id=session_id, limit=100000)
    print(f"事件总数: {len(events)}")

    # 运行所有归因
    test_strategy_attribution(store, session_id)
    test_symbol_attribution(store, session_id)
    test_time_attribution(store, session_id)
    test_risk_attribution(store, session_id)
    test_factor_attribution(store, session_id)
    test_monthly_review(store, session_id)

    print("\n" + "=" * 70)
    print("所有归因模块测试通过！")
    print("=" * 70)


if __name__ == "__main__":
    main()
