"""
V3.2 Observability SOP 跑法
==========================

演示 SystemContext 完整接入：
  数据
    → ReplayMarketData
    → PaperBroker
    → ExecutionFactory("paper")
    → RiskManager + KillSwitch
    ↓
  SystemContext
    ├─ TradeLogger        统一日志（JSON Lines）
    ├─ MetricsCollector   实时指标
    ├─ EventTracer        事件链路（trace_id）
    ├─ AlertManager       告警引擎
    └─ Dashboard          matplotlib 4 子图
    ↓
  主循环：
    每根 bar:
      trace_id = ctx.tracer.begin(...)
      ctx.tracer.span(tid, "MARKET", ...)
      ctx.tracer.span(tid, "SIGNAL", score=...)
      ctx.tracer.span(tid, "ORDER", qty=...)
      ctx.tracer.span(tid, "FILL", price=...)
      ctx.tracer.end(tid)
      ctx.tick(pnl=..., equity=..., drawdown=..., last_pnl=...)
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
    RiskManager,
    OrderSizeCheck,
    MaxOrderSize,
    EmergencyStop,
    KillSwitch,
    # V3.2
    TradeLogger,
    MetricsCollector,
    EventTracer,
    AlertManager,
    Dashboard,
    SystemContext,
)
from quantlab.event.event_bus import event_bus
from quantlab.portfolio_construction import TopN
from quantlab.core.portfolio import Portfolio
from quantlab.core.tradebook import TradeBook
from quantlab.signals.rsi import RSIStrategy


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


def run():
    # ---- 1) 准备数据 / 行情 / Broker / Execution ----
    data = load_data()
    md = ReplayMarketData(data)
    md.subscribe(list(data.keys()))

    broker = PaperBroker(
        market_data=md,
        tick_size=0.01,
        commission_rate=0.0003,
        initial_cash=100000.0,
    )
    broker.connect()

    portfolio = Portfolio(initial_cash=100000.0)
    tradebook = TradeBook()

    exec_ = ExecutionFactory.create(
        mode="paper",
        portfolio=portfolio,
        broker=broker,
    )

    risk = RiskManager(checks=[
        OrderSizeCheck(MaxOrderSize(max_qty=10000)),
    ])
    estop = EmergencyStop(threshold=-0.10)
    estop.set_initial_equity(100000.0)
    risk.add_check(KillSwitch(estop))

    # ---- 2) Strategy ----
    strategy = RSIStrategy(period=14, oversold=30, overbought=70)
    constructor = TopN(n=2)

    # ---- 3) SystemContext 统一入口 ----
    ctx = SystemContext(
        source="paper",
        strategy=strategy,
        portfolio=portfolio,
        execution=exec_,
        broker=broker,
        risk_manager=risk,
        market_data=md,
        tradebook=tradebook,
        log_dir="logs",
        initial_equity=100000.0,
    )

    # 加告警规则
    ctx.alerts.add_rule(
        AlertManager.__class__,  # 仅为类型避免 lint，无关
    ) if False else None
    from quantlab.monitoring import (
        PnLThresholdRule,
        DrawdownBreachRule,
        ConsecutiveLossRule,
        FillFailureRule,
    )
    ctx.alerts.add_rule(PnLThresholdRule(max_loss_pnl=-5000))
    ctx.alerts.add_rule(DrawdownBreachRule(max_dd=-0.08))
    ctx.alerts.add_rule(ConsecutiveLossRule(n=4))
    ctx.alerts.add_rule(FillFailureRule(max_failure_rate=0.40))

    # EventBus → 自动转 logger
    ctx.attach_event_bus(event_bus)

    # ---- 4) 主循环 ----
    from quantlab.data.context import StrategyContext
    from quantlab.data.cache import factor_cache

    factor_cache.clear()
    str_ctx = StrategyContext(data, factor_cache)
    signal = strategy.signal(str_ctx)

    sym0 = list(data.keys())[0]
    all_ts = list(data[sym0].index)
    last_pnl = 0.0

    ctx.logger.info("=== V3.2 Observability run started ===")

    for i, ts in enumerate(all_ts):
        if i == 0:
            bar_close = {
                sym: float(data[sym].iloc[0]["close"])
                for sym in data
            }
            portfolio.record(ts, bar_close)
            for sym, p in bar_close.items():
                broker.push_tick(sym, p, timestamp=ts)
            ctx.metrics.update(
                equity=portfolio.equity(),
                pnl=0.0,
            )
            continue

        # 1) 链路起点
        tid = ctx.tracer.begin(label=f"BAR_{i}")

        # 2) Market span
        prev_scores = signal.iloc[i - 1].to_dict()
        ctx.tracer.span(
            tid, "MARKET", scores=prev_scores,
        )

        # 3) 推价
        bar_close = {
            sym: float(data[sym].iloc[i]["close"])
            for sym in data
        }
        for sym, p in bar_close.items():
            broker.push_tick(sym, p, timestamp=ts)

        # 4) Signal
        ctx.tracer.span(tid, "SIGNAL", **prev_scores)

        # 5) Target
        target = constructor.construct(prev_scores, ts)
        ctx.tracer.span(
            tid, "TARGET",
            weights=str(target.weights),
        )

        # 6) Execution
        orders = exec_.submit(target)
        for o in orders:
            ctx.tracer.span(
                tid, "ORDER",
                symbol=o.symbol, qty=o.quantity, price=o.price,
            )
        fills = exec_.drain_fills()

        # 7) Risk check
        for o in orders:
            risk_ctx = {
                "positions": broker.get_positions(),
                "equity": broker.get_account().equity,
            }
            if not risk.check(o, risk_ctx):
                ctx.logger.reject(
                    symbol=o.symbol, qty=o.quantity,
                    reason=str(risk.rejects[-1]),
                )

        # 8) Apply fills + 串 FILL span
        pnl_change = 0.0
        for f in fills:
            ctx.tracer.span(
                tid, "FILL",
                symbol=f.symbol, qty=f.quantity, price=f.price,
            )
            portfolio.apply_fill(
                symbol=f.symbol,
                quantity=f.quantity,
                price=f.price,
                commission=f.commission,
                timestamp=f.timestamp,
            )
            tradebook.on_fill(f)
            ctx.metrics.record_trade(
                pnl=0.0,   # PnL 真实计算要等 portfolio.update
                symbol=f.symbol,
                timestamp=f.timestamp,
            )

        # 9) Record + 指标
        portfolio.record(ts, bar_close)
        eq = portfolio.equity()
        new_pnl = eq - 100000.0
        pnl_change = new_pnl - last_pnl
        last_pnl = new_pnl
        ctx.metrics.update(
            equity=eq,
            pnl=new_pnl,
            exposure=sum(
                abs(portfolio.positions.get(s).qty
                    if hasattr(portfolio.positions.get(s, 0), "qty")
                    else 0)
                * bar_close.get(s, 0)
                for s in data
            ) / max(eq, 1.0),
        )
        ctx.metrics.record(timestamp=ts)

        # 10) Alert check
        ctx.alerts.check_and_dispatch(
            ctx.metrics.snapshot() | {"last_pnl": pnl_change}
        )

        # 11) End trace
        ctx.tracer.end(tid, "END", equity=eq, pnl=new_pnl)

        # 12) Kill switch
        estop.update_pnl(new_pnl)
        if estop.stop:
            ctx.logger.kill(
                reason="drawdown threshold breach",
                pnl=new_pnl,
            )
            break

    # ---- 5) Report ----
    tradebook.rebuild()
    snap = ctx.metrics.snapshot()
    print("\n" + "=" * 60)
    print("  V3.2 Observability Report")
    print("=" * 60)
    print(f"  bars processed    = {len(all_ts)}")
    print(f"  total traces      = "
          f"{len(ctx.tracer._traces)}")
    print(f"  total fills       = {snap['trade_count']}")
    print(f"  win rate          = {snap['win_rate']*100:.1f}%")
    print(f"  drawdown (latest) = "
          f"{snap['drawdown']*100:.2f}%")
    print(f"  pnl               = {snap['pnl']:.2f}")
    print(f"  equity            = {snap['equity']:.2f}")
    print(f"  alerts fired      = {len(ctx.alerts.alerts)}")
    for a in ctx.alerts.alerts[:10]:
        print(f"    [{a.level:>8}] {a.rule_name}: "
              f"{a.message}")
    print("=" * 60)
    print(f"  logs/traces.jsonl = "
          f"{os.path.getsize('logs/traces.jsonl') if os.path.exists('logs/traces.jsonl') else 0} bytes")
    print(f"  logs/events_paper.log = "
          f"{os.path.getsize('logs/events_paper.log') if os.path.exists('logs/events_paper.log') else 0} bytes")
    print(f"  logs/alerts.log = "
          f"{os.path.getsize('logs/alerts.log') if os.path.exists('logs/alerts.log') else 0} bytes")
    print("=" * 60)

    # ---- 6) Dashboard save (不 show 避免阻塞) ----
    try:
        ctx.dashboard.save("logs/dashboard.png")
        print("  dashboard saved → logs/dashboard.png")
    except Exception as e:
        print(f"  dashboard skipped: {e}")

    broker.disconnect()
    return snap


if __name__ == "__main__":
    run()
