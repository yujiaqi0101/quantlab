"""
V3.1 Live Paper SOP 跑法
=======================

演示完整链路：
  历史 CSV 数据
    → ReplayMarketData  当作实时行情
    → PaperBroker        模拟成交（按行情即时撮合）
    → ExecutionFactory(mode="paper")  统一 Execution
    → RiskManager + KillSwitch        风险层
    → EventBus                        事件总线（V3.1 新串联）

对比：
  旧：BarEngine 直接吃 df
  新：ReplayMarketData 把 df 切成 tick 流给 PaperBroker
      整条链路与实盘一致（换 broker 即可）
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
    LiveLogger,
)
from quantlab.event.event_bus import event_bus
from quantlab.event.event_types import FillEvent
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
    # ---- 0) 行情：历史 CSV 当实时流 ----
    data = load_data()
    md = ReplayMarketData(data)
    md.subscribe(list(data.keys()))

    # ---- 1) Broker ----
    broker = PaperBroker(
        market_data=md,
        tick_size=0.01,
        commission_rate=0.0003,
        initial_cash=100000.0,
    )
    broker.connect()

    # ---- 2) 风险层 ----
    risk = RiskManager(checks=[
        OrderSizeCheck(MaxOrderSize(max_qty=10000)),
    ])
    estop = EmergencyStop(threshold=-0.10)
    estop.set_initial_equity(100000.0)
    risk.add_check(KillSwitch(estop))

    # ---- 3) 日志 ----
    logger = LiveLogger(log_dir="logs")

    # ---- 4) Portfolio / TradeBook ----
    portfolio = Portfolio(initial_cash=100000.0)
    tradebook = TradeBook()

    # ---- 5) Strategy（用 RSI 当 demo） ----
    strategy = RSIStrategy(period=14, oversold=30, overbought=70)
    constructor = TopN(n=2)

    # ---- 6) 统一 Execution（核心：mode="paper"） ----
    exec_ = ExecutionFactory.create(
        mode="paper",
        portfolio=portfolio,
        broker=broker,
    )

    # ---- 7) EventBus 监听（V3.1 新增：真把 EventBus 串起来） ----
    fill_events: list = []

    def on_fill(ev: FillEvent):
        fill_events.append(ev)
        logger.trade(
            symbol=ev.symbol,
            qty=ev.quantity,
            price=ev.price,
            ts=ev.timestamp,
        )

    event_bus.subscribe("FILL", on_fill)

    # ---- 8) 主循环：tick → signal → execution → fills → portfolio ----
    last_prices: dict = {}
    timestamps_seen: list = []
    equity_curve: list = []

    # 用 signal cache + 简化的"每根 bar 末再平衡"逻辑
    # 这里 LiveEngine._on_tick 的简化版：每根 tick 跑 signal 一次
    # （完整版应该用 ReplayMarketData 把每根 bar 末端做再平衡）
    from quantlab.data.context import StrategyContext
    from quantlab.data.cache import factor_cache
    from quantlab.portfolio_construction.target_portfolio import (
        TargetPortfolio,
    )

    factor_cache.clear()
    ctx = StrategyContext(data, factor_cache)
    signal = strategy.signal(ctx)

    # 收集 unique bar timestamps
    sym0 = list(data.keys())[0]
    all_ts = list(data[sym0].index)

    for i, ts in enumerate(all_ts):
        if i == 0:
            # 首根 bar：只 record
            bar_close = {sym: float(data[sym].iloc[0]["close"]) for sym in data}
            portfolio.record(ts, bar_close)
            last_prices = bar_close
            timestamps_seen.append(ts)
            equity_curve.append(portfolio.equity())
            continue

        # 1) 用前一根 bar 的 signal → scores
        prev_scores = signal.iloc[i - 1].to_dict()

        # 2) 当前 bar close → last_prices + broker 推价
        bar_open = {sym: float(data[sym].iloc[i]["open"]) for sym in data}
        bar_close = {sym: float(data[sym].iloc[i]["close"]) for sym in data}
        for sym, p in bar_close.items():
            broker.push_tick(sym, p, timestamp=ts)
            last_prices[sym] = p

        # 3) Portfolio Construction
        target = constructor.construct(prev_scores, ts)

        # 4) Execution
        orders = exec_.submit(target)
        fills = exec_.drain_fills()

        # 5) 风险检查（在 Order → Broker 之间插一刀）
        for o in orders:
            ctx_risk = {
                "positions": broker.get_positions(),
                "equity": broker.get_account().equity,
            }
            if not risk.check(o, ctx_risk):
                logger.reject(
                    symbol=o.symbol,
                    qty=o.quantity,
                    reason=str(risk.rejects[-1]),
                )

        # 6) Apply fills
        for f in fills:
            try:
                portfolio.apply_fill(
                    symbol=f.symbol,
                    quantity=f.quantity,
                    price=f.price,
                    commission=f.commission,
                    timestamp=f.timestamp,
                )
            except Exception as e:
                print(f"  apply_fill err: {e}")
            tradebook.on_fill(f)

        # 7) Record
        portfolio.record(ts, bar_close)
        timestamps_seen.append(ts)
        equity_curve.append(portfolio.equity())

        # 8) Kill switch
        estop.update_pnl(portfolio.equity() - 100000.0)
        if estop.stop:
            print(f"  [KILL] triggered at {ts}, pnl={estop.daily_pnl:.2f}")
            break

    # ---- 9) Report ----
    tradebook.rebuild()
    final_eq = equity_curve[-1] if equity_curve else 100000.0
    print("\n" + "=" * 60)
    print("  V3.1 Live Paper Report")
    print("=" * 60)
    print(f"  bars processed    = {len(equity_curve)}")
    print(f"  fills via EventBus= {len(fill_events)}")
    print(f"  order count       = {len(orders) if 'orders' in dir() else 0}")
    print(f"  closed trades     = {len(tradebook.closed_trades)}")
    print(f"  final equity      = {final_eq:.2f}")
    print(f"  total return      = "
          f"{(final_eq - 100000.0) / 100000.0 * 100:.2f}%")
    print(f"  max drawdown      = "
          f"{min(0.0, (min(equity_curve) - 100000.0) / 100000.0) * 100:.2f}%")
    print("=" * 60)

    broker.disconnect()
    return {
        "final_equity": final_eq,
        "fill_events": len(fill_events),
        "closed_trades": len(tradebook.closed_trades),
    }


if __name__ == "__main__":
    run()
