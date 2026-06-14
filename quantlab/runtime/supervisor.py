"""
StrategyRegistry + PortfolioSupervisor（V3.4 核心）

设计原则：
    1) Supervisor 是观察者 + 调度器，不直接改 runtime 状态
    2) 每个 runtime 独立 portfolio + broker + account
    3) Supervisor 维护全局视图（账户、风险、监控）
    4) 主循环：广播行情给所有 runtime → 收集 stats

核心能力：
    多策略并行（MACross + Momentum + ...）
    多账户矩阵（A 账户低风险 + B 账户激进）
    资金隔离（runtime 之间互不污染）
    统一风控（总 exposure / 总 pnl / 系统级 Kill Switch）
"""

from __future__ import annotations

import logging
import os
import signal
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type

from .account_manager import AccountManager, Account
from .allocation import (
    AllocationEngine,
    FixedAllocation,
    AllocationRule,
)
from .router import OrderRouter
from .strategy_runtime import StrategyRuntime
from ..portfolio_construction import TopN


logger = logging.getLogger("quantlab.supervisor")


# ================================================================
# StrategyRegistry：策略类注册器
# ================================================================ #
class StrategyRegistry:
    """
    V3.4 策略注册器

    用法：
        registry = StrategyRegistry()
        registry.register("MACross", MACrossStrategy)
        registry.register("RSI", RSIStrategy)
        instance = registry.create(
            "MACross", params={"fast": 5, "slow": 20},
        )
    """

    def __init__(self):
        self._registry: Dict[str, Type] = {}

    def register(
        self,
        name: str,
        strategy_cls: Type,
    ) -> None:
        if name in self._registry:
            raise ValueError(f"strategy {name!r} already registered")
        self._registry[name] = strategy_cls
        logger.info(f"registered strategy: {name} → {strategy_cls.__name__}")

    def create(
        self,
        name: str,
        params: Optional[Dict] = None,
    ):
        if name not in self._registry:
            raise KeyError(f"strategy {name!r} not registered")
        cls = self._registry[name]
        return cls(**(params or {}))

    def list_strategies(self) -> List[str]:
        return list(self._registry.keys())


# ================================================================
# PortfolioSupervisor：总调度器
# ================================================================ #
class PortfolioSupervisor:
    """
    V3.4 PortfolioSupervisor

    用法：
        registry = StrategyRegistry()
        registry.register("MACross", MACrossStrategy)
        registry.register("RSI", RSIStrategy)

        sup = PortfolioSupervisor(registry=registry)

        # 创建账户
        am = sup.account_manager
        am.create_account("acc_low",  cash=100000, risk_profile="low")
        am.create_account("acc_high", cash=200000, risk_profile="high")

        # 注册策略（strategy_id → strategy + account + broker）
        sup.register_strategy(
            strategy_id="macross_low",
            strategy_name="MACross",
            strategy_params={"fast": 5, "slow": 20},
            account_id="acc_low",
            broker=paper_broker_a,
        )
        sup.register_strategy(
            strategy_id="rsi_high",
            strategy_name="RSI",
            strategy_params={"period": 14},
            account_id="acc_high",
            broker=paper_broker_b,
        )

        # 主循环
        for i, ts in enumerate(bar_iter):
            sup.on_bar(data_dict, ts)
            if sup.global_kill_switch.is_set():
                break

        # 报告
        sup.report()
    """

    def __init__(
        self,
        registry: StrategyRegistry,
        account_manager: Optional[AccountManager] = None,
        allocation_engine: Optional[AllocationEngine] = None,
    ):
        self.registry = registry
        self.account_manager = (
            account_manager or AccountManager()
        )
        self.allocation_engine = (
            allocation_engine or AllocationEngine(
                FixedAllocation({})
            )
        )
        self.router = OrderRouter(
            self.account_manager,
            self.allocation_engine,
        )

        # runtime_id → StrategyRuntime
        self.runtimes: Dict[str, StrategyRuntime] = {}

        # strategy_id → runtime_id
        self.strategy_to_runtime: Dict[str, str] = {}

        # V3.4 系统级 Kill Switch（任一 runtime 爆仓触发）
        self.global_kill_switch = threading.Event()
        self.kill_reason: str = ""

        # 总监控
        self._global_stats: Dict[str, Any] = {
            "bars_processed": 0,
            "total_orders": 0,
            "total_fills": 0,
        }

    # ---- 策略注册 ----
    def register_strategy(
        self,
        strategy_id: str,
        strategy_name: str,
        strategy_params: Optional[Dict],
        account_id: str,
        broker,
        constructor=None,
        data_symbols: Optional[List[str]] = None,
        full_data: Optional[Dict] = None,    # V3.4: 首次算 signal
    ) -> StrategyRuntime:
        """
        V3.4 一站式注册一个 runtime

        内部：
            1) 拿 account
            2) 实例化 strategy
            3) 建 portfolio（账户隔离）
            4) 建 execution（用该 account 的 broker）
            5) 建 StrategyRuntime
            6) 注册到 router
        """
        if strategy_id in self.strategy_to_runtime:
            raise ValueError(
                f"strategy_id {strategy_id!r} already registered"
            )
        account = self.account_manager.get_account(account_id)

        # 1) strategy
        strategy = self.registry.create(
            strategy_name, strategy_params
        )

        # 2) portfolio（用 account 的初始 cash 隔离）
        from ..core.portfolio import Portfolio
        portfolio = Portfolio(initial_cash=account.cash)

        # 3) execution：这里直接走 broker（不区分 backtest/paper/live）
        #    V3.4 简化：execution 内部用 broker
        from ..live.execution import ExecutionFactory
        execution = ExecutionFactory.create(
            mode="paper",         # V3.4 演示默认 paper
            portfolio=portfolio,
            broker=broker,
        )

        # 4) constructor
        if constructor is None:
            constructor = TopN(n=2)

        # 5) runtime
        runtime = StrategyRuntime(
            runtime_id=f"rt_{strategy_id}",
            strategy=strategy,
            portfolio=portfolio,
            execution=execution,
            broker=broker,
            constructor=constructor,
            account_id=account_id,
            data_symbols=data_symbols,
            full_data=full_data,
        )

        self.runtimes[runtime.runtime_id] = runtime
        self.strategy_to_runtime[strategy_id] = runtime.runtime_id
        self.router.register_runtime(strategy_id, broker)

        logger.info(
            f"registered strategy: id={strategy_id} "
            f"name={strategy_name} "
            f"account={account_id} "
            f"broker={type(broker).__name__}"
        )
        return runtime

    # ---- 主循环 ----
    def on_bar(
        self,
        data: Dict[str, Any],
        timestamp: Any,
    ) -> None:
        """
        V3.4 广播：每根 bar 推给所有 runtime
        """
        if self.global_kill_switch.is_set():
            return
        self._global_stats["bars_processed"] += 1

        for rt in self.runtimes.values():
            try:
                stats = rt.on_bar(data, timestamp)
            except Exception as e:
                logger.warning(
                    f"[{rt.runtime_id}] on_bar fail: {e}"
                )
                continue

            self._global_stats["total_orders"] += (
                stats.orders_submitted
            )
            self._global_stats["total_fills"] += (
                stats.fills_received
            )

            # V3.4 系统级 Kill Switch
            # 任意 runtime 净值跌穿 -20% → 全部停
            if (
                stats.last_equity > 0
                and stats.last_equity < 80000
            ):
                self._request_global_kill(
                    f"{rt.runtime_id} equity={stats.last_equity:.2f}"
                )
                break

    def _request_global_kill(self, reason: str) -> None:
        if not self.global_kill_switch.is_set():
            self.global_kill_switch.set()
            self.kill_reason = reason
            for rt in self.runtimes.values():
                rt.stop(reason=f"global kill: {reason}")
            logger.error(
                f"GLOBAL KILL SWITCH: {reason}"
            )

    # ---- 报告 ----
    def report(self) -> Dict[str, Any]:
        out = {
            "global_stats": self._global_stats,
            "kill_switch": self.global_kill_switch.is_set(),
            "kill_reason": self.kill_reason,
            "runtimes": [
                rt.snapshot()
                for rt in self.runtimes.values()
            ],
            "accounts": self.account_manager.snapshot(),
        }
        return out

    def print_report(self) -> None:
        rep = self.report()
        print("\n" + "=" * 60)
        print("  V3.4 PortfolioSupervisor Report")
        print("=" * 60)
        print(f"  bars processed     = "
              f"{rep['global_stats']['bars_processed']}")
        print(f"  total orders       = "
              f"{rep['global_stats']['total_orders']}")
        print(f"  total fills        = "
              f"{rep['global_stats']['total_fills']}")
        print(f"  kill switch        = {rep['kill_switch']}")
        if rep['kill_reason']:
            print(f"  kill reason        = "
                  f"{rep['kill_reason']}")
        print()
        print("  Runtimes:")
        for rt in rep['runtimes']:
            s = rt['stats']
            print(
                f"    {rt['runtime_id']:<25s} "
                f"strat={rt['strategy']:<15s} "
                f"acc={rt['account_id']:<10s} "
                f"broker={rt['broker']:<12s} "
                f"orders={s['orders_submitted']:>3d} "
                f"fills={s['fills_received']:>3d} "
                f"equity={s['last_equity']:>10.2f}"
            )
        print()
        print("  Accounts:")
        for acc_id, info in rep['accounts'].items():
            print(
                f"    {acc_id:<10s} "
                f"cash={info['cash']:>10.2f} "
                f"broker={info['broker_name']:<10s} "
                f"risk={info['risk_profile']:<8s}"
            )
        print("=" * 60)
