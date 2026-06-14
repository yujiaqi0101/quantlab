"""
V3.4 Multi-Strategy Multi-Account 演示
======================================

演示：
    3 个 Strategy  ×  3 个 Account  ×  3 个 Broker

策略：
    macross_low   - MACross(5, 20)     →  acc_low    (60%) + acc_mid (40%)
    rsi_high      - RSI(14)            →  acc_high   (100%)
    alpha_high    - Alpha001           →  acc_mid    (50%) + acc_high (50%)

账户：
    acc_low    100000  低风险 paper_broker
    acc_mid    150000  中等 risk paper_broker_mid
    acc_high   200000  激进 paper_broker_high

系统级 Kill Switch：任意 runtime 净值 < 80000 → 全部停
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
    PaperBroker,
    ReplayMarketData,
)
from quantlab.signals import (
    MACrossStrategy,
    RSIStrategy,
    Alpha001Strategy,
)
from quantlab.portfolio_construction import TopN
from quantlab.runtime import (
    AccountManager,
    AllocationEngine,
    FixedAllocation,
    OrderRouter,
    StrategyRegistry,
    PortfolioSupervisor,
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


def main():
    data = load_data()
    symbols = list(data.keys())

    # ---- 1) AccountManager：3 账户 ----
    am = AccountManager()
    am.create_account(
        "acc_low", cash=100000,
        broker_name="PAPER", risk_profile="low",
        name="Low Risk Account",
    )
    am.create_account(
        "acc_mid", cash=150000,
        broker_name="PAPER", risk_profile="medium",
        name="Medium Risk Account",
    )
    am.create_account(
        "acc_high", cash=200000,
        broker_name="PAPER", risk_profile="high",
        name="High Risk Account",
    )
    print("  accounts created:")
    for a in am.list_accounts():
        print(
            f"    {a.account_id:<10s} "
            f"cash={a.cash:>8.0f} "
            f"risk={a.risk_profile:<8s}"
        )

    # ---- 2) 3 个 broker（每个账户独立） ----
    md_low = ReplayMarketData(data)
    md_mid = ReplayMarketData(data)
    md_high = ReplayMarketData(data)
    md_low.subscribe(symbols)
    md_mid.subscribe(symbols)
    md_high.subscribe(symbols)

    broker_low = PaperBroker(
        market_data=md_low, tick_size=0.01,
        commission_rate=0.0003, initial_cash=100000.0,
    )
    broker_mid = PaperBroker(
        market_data=md_mid, tick_size=0.01,
        commission_rate=0.0003, initial_cash=150000.0,
    )
    broker_high = PaperBroker(
        market_data=md_high, tick_size=0.01,
        commission_rate=0.0003, initial_cash=200000.0,
    )
    broker_low.connect()
    broker_mid.connect()
    broker_high.connect()

    # ---- 3) AllocationEngine：策略×账户矩阵 ----
    allocation_map = {
        "macross_low": [
            ("acc_low", 0.6),
            ("acc_mid", 0.4),
        ],
        "rsi_high": [
            ("acc_high", 1.0),
        ],
        "alpha_high": [
            ("acc_mid", 0.5),
            ("acc_high", 0.5),
        ],
    }
    ae = AllocationEngine(
        FixedAllocation(allocation_map)
    )

    # ---- 4) StrategyRegistry + Supervisor ----
    registry = StrategyRegistry()
    registry.register("MACross", MACrossStrategy)
    registry.register("RSI", RSIStrategy)
    registry.register("Alpha001", Alpha001Strategy)

    sup = PortfolioSupervisor(
        registry=registry,
        account_manager=am,
        allocation_engine=ae,
    )

    # 注册 3 个 strategy
    rt1 = sup.register_strategy(
        strategy_id="macross_low",
        strategy_name="MACross",
        strategy_params={"fast": 5, "slow": 20},
        account_id="acc_low",       # V3.4 简化：用第一个账户作为 runtime owner
        broker=broker_low,
        constructor=TopN(n=2),
        full_data=data,
    )
    rt2 = sup.register_strategy(
        strategy_id="rsi_high",
        strategy_name="RSI",
        strategy_params={"period": 14, "oversold": 30, "overbought": 70},
        account_id="acc_high",
        broker=broker_high,
        constructor=TopN(n=2),
        full_data=data,
    )
    rt3 = sup.register_strategy(
        strategy_id="alpha_high",
        strategy_name="Alpha001",
        strategy_params={"period": 10},
        account_id="acc_mid",
        broker=broker_mid,
        constructor=TopN(n=2),
        full_data=data,
    )

    print("\n  registered 3 strategies × 3 accounts:")
    print(f"    macross_low → {rt1.runtime_id} "
          f"(broker={type(broker_low).__name__}, "
          f"alloc=acc_low 60% + acc_mid 40%)")
    print(f"    rsi_high    → {rt2.runtime_id} "
          f"(broker={type(broker_high).__name__}, "
          f"alloc=acc_high 100%)")
    print(f"    alpha_high  → {rt3.runtime_id} "
          f"(broker={type(broker_mid).__name__}, "
          f"alloc=acc_mid 50% + acc_high 50%)")

    # ---- 5) 主循环：每根 bar 广播给所有 runtime ----
    sym0 = list(data.keys())[0]
    all_ts = list(data[sym0].index)

    print(f"\n  running {len(all_ts)} bars across 3 runtimes...")
    for i, ts in enumerate(all_ts):
        if sup.global_kill_switch.is_set():
            break
        bar_data = {s: data[s].iloc[i] for s in symbols}
        sup.on_bar(bar_data, ts)

    # ---- 6) 报告 ----
    sup.print_report()

    # ---- 7) OrderRouter 演示（拆单） ----
    print("\n  OrderRouter 演示：")
    print("  输入：1 个 Order 600 股 AAPL，strategy=macross_low")
    print("  预期：acc_low 拿 360 股 + acc_mid 拿 240 股")
    from quantlab.core.order import Order
    test_order = Order(
        symbol="AAPL", quantity=600, price=150.0,
    )
    # 重用 sup 的 router
    routed = sup.router.route(test_order, "macross_low")
    for ro in routed:
        print(
            f"    → acc={ro.account_id:<10s} "
            f"qty={ro.quantity:>5d} "
            f"client_order_id={ro.client_order_id}"
        )
    print(f"  routed: {len(routed)} 子单")

    # 关 broker
    broker_low.disconnect()
    broker_mid.disconnect()
    broker_high.disconnect()


if __name__ == "__main__":
    main()
