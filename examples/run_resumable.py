"""
V3.3 Resumable SOP 跑法
======================

演示完整 9 件：
    1) StateSnapshot         — 状态快照
    2) CheckpointManager     — 每 50 根 bar 落盘
    3) RecoveryManager       — 启动恢复
    4) Order Idempotency     — 同一 client_order_id 多次提交只成交一次
    5) ConsistencyChecker    — 对账（portfolio vs broker）
    6) ReplayEngine          — 用 checkpoint 重放
    7) ShutdownManager       — Ctrl+C 优雅停机
    8) TradeLock             — 锁临界区
    9) EventLog              — 所有事件落盘

流程：
    A) Phase 1: 跑 100 bars
    B) Phase 2: 模拟"崩溃" → 重启
    C) Phase 3: 恢复 + 接着跑 200 bars
    D) Phase 4: ReplayEngine 复盘
    E) Phase 5: ConsistencyChecker 报警
"""
import os
import sys

_PKG_PARENT = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)
if _PKG_PARENT not in sys.path:
    sys.path.insert(0, _PKG_PARENT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd

from quantlab.live import (
    ExecutionFactory,
    PaperBroker,
    ReplayMarketData,
)
from quantlab.portfolio_construction import TopN
from quantlab.core.portfolio import Portfolio
from quantlab.core.tradebook import TradeBook
from quantlab.core.order import Order
from quantlab.signals.rsi import RSIStrategy
from quantlab.monitoring import SystemContext
from quantlab.runtime import (
    StateSnapshot,
    CheckpointManager,
    RecoveryManager,
    ConsistencyChecker,
    ReplayEngine,
    ShutdownManager,
    TradeLock,
    EventLog,
)


def load_data(data_dir: str = "data"):
    out = {}
    for sym in ["AAPL", "MSFT", "NVDA"]:
        df = pd.read_csv(
            f"{data_dir}/{sym}.csv",
            parse_dates=True, index_col=0,
        )
        df = df[["open", "high", "low", "close", "volume"]].astype(float)
        out[sym] = df
    return out


# ============================================================ #
# 主循环（一个 phase）
# ============================================================ #
def run_phase(
    phase_name: str,
    data: dict,
    start_bar: int,
    end_bar: int,
    portfolio: Portfolio,
    broker: PaperBroker,
    exec_,
    strategy,
    constructor,
    signal,
    checkpoint: CheckpointManager,
    event_log: EventLog,
    shutdown: ShutdownManager,
    consistency: ConsistencyChecker,
    ctx: SystemContext,
):
    sym0 = list(data.keys())[0]
    all_ts = list(data[sym0].index)
    end_bar = min(end_bar, len(all_ts))
    print(f"\n--- {phase_name}: bars {start_bar}..{end_bar} ---")
    fills_count = 0

    for i in range(start_bar, end_bar):
        if shutdown.is_set():
            print(f"  [shutdown] requested at bar {i}")
            break

        ts = all_ts[i]

        if i == 0:
            bar_close = {
                s: float(data[s].iloc[0]["close"]) for s in data
            }
            portfolio.record(ts, bar_close)
            for s, p in bar_close.items():
                with TradeLock.section("broker"):
                    broker.push_tick(s, p, timestamp=ts)
            continue

        prev_scores = signal.iloc[i - 1].to_dict()
        bar_close = {
            s: float(data[s].iloc[i]["close"]) for s in data
        }

        # V3.3: 事件落盘
        event_log.append("MARKET", timestamp=str(ts), **bar_close)

        with TradeLock.section("broker"):
            for s, p in bar_close.items():
                broker.push_tick(s, p, timestamp=ts)

        target = constructor.construct(prev_scores, ts)

        orders = exec_.submit(target)
        for o in orders:
            event_log.append(
                "ORDER",
                symbol=o.symbol, qty=o.quantity, price=o.price,
                client_order_id=o.client_order_id,
            )

        # V3.3: 幂等性演示
        # 把上一根 bar 重新提交一次同一 Order 对象（不会重复成交）
        if i > start_bar + 5 and i % 20 == 0:
            # 模拟网络重试
            retry_order = Order(
                symbol=orders[0].symbol if orders else "AAPL",
                quantity=orders[0].quantity if orders else 100,
                client_order_id=orders[0].client_order_id if orders else "",
            )
            with TradeLock.section("broker"):
                broker.submit_order(retry_order)

        fills = exec_.drain_fills()
        for f in fills:
            with TradeLock.section("portfolio"):
                portfolio.apply_fill(
                    symbol=f.symbol,
                    quantity=f.quantity,
                    price=f.price,
                    commission=f.commission,
                    timestamp=f.timestamp,
                )
            fills_count += 1
            event_log.append(
                "FILL",
                symbol=f.symbol, qty=f.quantity, price=f.price,
            )

        portfolio.record(ts, bar_close)

        # V3.3: CheckpointManager（每 50 bar）
        if checkpoint.should_save(tick=i, trade_count=fills_count):
            with TradeLock.section("checkpoint"):
                snap = StateSnapshot.capture(
                    timestamp=ts,
                    portfolio=portfolio,
                    broker=broker,
                    tradebook=None,
                    open_orders=[
                        {
                            "id": o.id,
                            "symbol": o.symbol,
                            "qty": o.quantity,
                            "price": o.price,
                            "client_order_id": o.client_order_id,
                        }
                        for o in orders
                    ],
                    metrics_snap=ctx.metrics.snapshot(),
                    source="paper",
                )
                path = checkpoint.save(snap)
                print(
                    f"  [checkpoint v{snap.version}] → {path} "
                    f"equity={snap.equity:.2f}"
                )

        # V3.3: ConsistencyChecker（每 30 bar）
        if i % 30 == 0:
            with TradeLock.section("consistency"):
                issues = consistency.check(
                    portfolio=portfolio, broker=broker,
                )
            if issues:
                for iss in issues:
                    print(
                        f"  [CONSISTENCY {iss.severity}] "
                        f"{iss.message}"
                    )

    return fills_count


def main():
    # ---- 0) 准备 ----
    data = load_data()
    md = ReplayMarketData(data)
    md.subscribe(list(data.keys()))

    # ---- 1) V3.3: 9 大件 ----
    checkpoint = CheckpointManager(
        strategy="by_ticks", interval=50, base_dir="checkpoints",
    )
    recovery = RecoveryManager(checkpoint)
    consistency = ConsistencyChecker(tolerance=0.01)
    shutdown = ShutdownManager()
    shutdown.install_signal_handlers()
    event_log = EventLog(source="paper", base_dir="logs/events")

    # ---- 2) 启动恢复（fresh / from checkpoint）----
    snap = recovery.boot()
    if snap is not None:
        # 恢复 portfolio / broker
        portfolio = Portfolio(initial_cash=100000.0)
        recovery.restore_portfolio(snap, portfolio)
        broker = PaperBroker(
            market_data=md,
            tick_size=0.01,
            commission_rate=0.0003,
            initial_cash=100000.0,
        )
        broker.connect()
        recovery.restore_broker(snap, broker)
        resume_bar = checkpoint._counter * 50
        print(
            f"  resumed from checkpoint v{snap.version}, "
            f"equity={snap.equity:.2f}, "
            f"start_bar={resume_bar}"
        )
    else:
        portfolio = Portfolio(initial_cash=100000.0)
        broker = PaperBroker(
            market_data=md,
            tick_size=0.01,
            commission_rate=0.0003,
            initial_cash=100000.0,
        )
        broker.connect()
        resume_bar = 0
        print("  fresh start, no checkpoint")

    broker.trade_log.clear()   # 清空 paper broker 内部 fill log
    exec_ = ExecutionFactory.create(
        mode="paper", portfolio=portfolio, broker=broker,
    )

    # ---- 3) Strategy / Construction ----
    strategy = RSIStrategy(period=14, oversold=30, overbought=70)
    constructor = TopN(n=2)

    # ---- 4) SystemContext (V3.2) ----
    ctx = SystemContext(
        source="paper",
        strategy=strategy,
        portfolio=portfolio,
        execution=exec_,
        broker=broker,
        risk_manager=None,
        log_dir="logs",
        initial_equity=100000.0,
    )

    # 算 signal
    from quantlab.data.context import StrategyContext
    from quantlab.data.cache import factor_cache
    factor_cache.clear()
    str_ctx = StrategyContext(data, factor_cache)
    signal = strategy.signal(str_ctx)

    # ---- 5) Phase 1: 跑 100 bars ----
    fills1 = run_phase(
        "Phase 1",
        data=data,
        start_bar=resume_bar,
        end_bar=min(100, len(list(data[list(data.keys())[0]].index))),
        portfolio=portfolio,
        broker=broker,
        exec_=exec_,
        strategy=strategy,
        constructor=constructor,
        signal=signal,
        checkpoint=checkpoint,
        event_log=event_log,
        shutdown=shutdown,
        consistency=consistency,
        ctx=ctx,
    )
    print(f"  Phase 1 done: {fills1} fills")

    # ---- 6) Phase 2: 模拟"崩溃" → 保存 final snapshot ----
    final_snap = StateSnapshot.capture(
        timestamp=pd.Timestamp.now(),
        portfolio=portfolio,
        broker=broker,
        tradebook=None,
        open_orders=[],
        metrics_snap=ctx.metrics.snapshot(),
        source="paper",
    )
    shutdown.set_final_snapshot(final_snap)
    final_path = shutdown.save_final_snapshot()
    print(f"  Phase 2: final snapshot saved → {final_path}")

    # 模拟崩溃：丢掉 portfolio / broker
    # ---- 7) Phase 3: 重新启动 + 恢复 ----
    print("\n--- Phase 3: Restart + Recovery ---")
    snap2 = recovery.boot()
    portfolio2 = Portfolio(initial_cash=100000.0)
    recovery.restore_portfolio(snap2, portfolio2)
    broker2 = PaperBroker(
        market_data=md, tick_size=0.01,
        commission_rate=0.0003, initial_cash=100000.0,
    )
    broker2.connect()
    recovery.restore_broker(snap2, broker2)
    print(
        f"  restored equity={portfolio2.equity():.2f}, "
        f"positions={ {s: p.qty for s, p in portfolio2.positions.items()} }"
    )

    # ---- 8) Phase 4: ReplayEngine 复盘 ----
    print("\n--- Phase 4: ReplayEngine ---")
    re = ReplayEngine(
        data=data,
        snapshot=snap2,
        strategy=strategy,
        constructor=constructor,
        execution=exec_,
        event_log_path="logs/events/paper/2026-06-14.jsonl"
            if os.path.exists("logs/events/paper/2026-06-14.jsonl")
            else None,
        start_bar=0,
    )
    results = re.run()
    summary = re.diff_summary(results)
    print(f"  replay: {summary}")

    # ---- 9) Phase 5: 优雅停机 ----
    print("\n--- Phase 5: Graceful Shutdown ---")
    shutdown.request_shutdown(reason="end of demo")
    final_path = shutdown.save_final_snapshot("checkpoints/000FINAL.json")
    broker.disconnect()
    broker2.disconnect()
    event_log.close()
    print(f"  final snapshot → {final_path}")

    # ---- 10) Report ----
    print("\n" + "=" * 60)
    print("  V3.3 Resumable Report")
    print("=" * 60)
    print(f"  checkpoints dir:")
    for f in sorted(os.listdir("checkpoints")):
        p = os.path.join("checkpoints", f)
        if os.path.isfile(p):
            print(
                f"    {f:<20s} "
                f"{os.path.getsize(p):>8d} bytes"
            )
    print(f"  event_log lines today: "
          f"{len(event_log.read_today())}")
    print(f"  consistency issues:    "
          f"{len(consistency.issues_history)}")
    print(f"  shutdown reason:       "
          f"{shutdown.reason or '(none)'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
