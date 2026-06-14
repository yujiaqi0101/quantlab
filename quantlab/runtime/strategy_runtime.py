"""
StrategyRuntime：独立运行单元（V3.4）

V3.4 核心抽象：
    一个 StrategyRuntime = 完整小交易系统
        strategy  +  portfolio  +  execution  +  broker
    状态完全独立，不与其他 runtime 共享

API:
    rt = StrategyRuntime(
        runtime_id="rt_A",
        strategy=strat_a,
        portfolio=portfolio_a,
        execution=exec_a,
        broker=broker_a,
        account_id="acc1",
    )
    rt.on_bar(bar_close, timestamp)    # 主循环钩子

每个 runtime 内部：
    - 自己的 factor_cache
    - 自己的 signal cache
    - 自己的 tradebook
    - 自己的 last_target（与 portfolio 对账）
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..core.portfolio import Portfolio
from ..core.tradebook import TradeBook
from ..data.cache import factor_cache
from ..data.context import StrategyContext


logger = logging.getLogger("quantlab.strategy_runtime")


@dataclass
class RuntimeStats:
    """运行时统计"""
    bars_processed: int = 0
    signals_generated: int = 0
    orders_submitted: int = 0
    fills_received: int = 0
    last_pnl: float = 0.0
    last_equity: float = 0.0
    stopped: bool = False
    stop_reason: str = ""


class StrategyRuntime:
    """
    V3.4 StrategyRuntime

    一个 runtime 跑一个 strategy 在一个 account 上
    多个 runtime = 多策略多账户矩阵

    用法（supervisor 内部）：
        rt = StrategyRuntime(...)
        rt.on_bar(bar_close, timestamp)
    """

    def __init__(
        self,
        runtime_id: str,
        strategy,
        portfolio: Portfolio,
        execution,
        broker,
        constructor=None,                    # PortfolioConstruction
        account_id: str = "",
        data_symbols: Optional[List[str]] = None,
        full_data: Optional[Dict] = None,    # V3.4: 首次算 signal 的全 data
    ):
        self.runtime_id = runtime_id
        self.strategy = strategy
        self.portfolio = portfolio
        self.execution = execution
        self.broker = broker
        self.constructor = constructor
        self.account_id = account_id

        # V3.4 状态完全独立
        self.factor_cache = factor_cache
        self.tradebook = TradeBook()
        self.stats = RuntimeStats()
        self._signal_cache = None
        self._data_symbols = data_symbols or []
        self._bar_count = 0
        self._full_data = full_data or {}

    # ---- 主循环 ----
    def on_bar(
        self,
        data: Dict[str, Any],
        timestamp: Any,
    ) -> RuntimeStats:
        """
        一根 bar 进入所有 runtime
            1) 行情推送 → 推 broker 拿价
            2) signal 算（首次） + target 算（每根）
            3) execution submit
            4) apply fills
            5) record portfolio
        """
        if self.stats.stopped:
            return self.stats

        self._bar_count += 1
        self.stats.bars_processed += 1
        symbols = self._data_symbols or list(data.keys())

        # 1) 推价
        for sym in symbols:
            if sym not in data:
                continue
            row = data[sym]
            if hasattr(row, "__getitem__") and "close" in row:
                close = float(row["close"])
            else:
                close = float(row)
            if hasattr(self.broker, "push_tick"):
                self.broker.push_tick(sym, close, timestamp=timestamp)
            if hasattr(self.portfolio, "last_prices"):
                self.portfolio.last_prices[sym] = close

        # 2) signal 缓存（首次用全 data 算）
        #    V3.4 简化：信号在 bar 0 算一次（基于 full_data 全量），
        #    之后每根 bar 用 signal.iloc[bar_count-1] 当作"当前决策"
        if self._signal_cache is None:
            # 优先用 full_data（注册时传入的全量 DataFrame）
            # 退化：再尝试从 data 拿
            full_data = self._full_data
            if not full_data:
                full_data = {}
                for sym in symbols:
                    if sym not in data:
                        continue
                    obj = data[sym]
                    if hasattr(obj, "columns"):
                        full_data[sym] = obj
                    else:
                        # 单行 Series：合成个单行 DataFrame
                        import pandas as pd
                        full_data[sym] = pd.DataFrame([obj])
            if not full_data:
                return self.stats

            str_ctx = StrategyContext(
                full_data, self.factor_cache
            )
            try:
                self._signal_cache = self.strategy.signal(str_ctx)
            except Exception as e:
                logger.warning(
                    f"[{self.runtime_id}] signal fail: {e}"
                )
                return self.stats
            self.stats.signals_generated = 1

        # 防御：单行 DataFrame 没有 iloc[N]，但我们已经在用 full_data 算了
        # iloc[bar_count-1] 在 bar_count<=len(_signal_cache) 时合法
        sig_len = len(self._signal_cache)
        if self._bar_count < 2 or sig_len == 0:
            # 第一根 bar 拿不到"前一根"，不交易
            return self.stats
        idx = min(self._bar_count - 1, sig_len - 1)
        try:
            prev_scores = self._signal_cache.iloc[idx].to_dict()
        except Exception as e:
            logger.warning(
                f"[{self.runtime_id}] signal read fail: {e}"
            )
            return self.stats

        if self.constructor is not None:
            target = self.constructor.construct(
                prev_scores, timestamp
            )
        else:
            target = None

        # 4) execution
        try:
            orders = self.execution.submit(target) \
                if target is not None else []
            self.stats.orders_submitted += len(orders)
        except Exception as e:
            logger.warning(
                f"[{self.runtime_id}] execution fail: {e}"
            )
            orders = []

        # 5) drain fills
        try:
            fills = self.execution.drain_fills() \
                if hasattr(self.execution, "drain_fills") else []
        except Exception:
            fills = []
        self.stats.fills_received += len(fills)

        # 6) apply
        for f in fills:
            try:
                self.portfolio.apply_fill(
                    symbol=f.symbol,
                    quantity=f.quantity,
                    price=f.price,
                    commission=f.commission,
                    timestamp=f.timestamp,
                )
                self.tradebook.on_fill(f)
            except Exception as e:
                logger.warning(
                    f"[{self.runtime_id}] apply_fill fail: {e}"
                )

        # 7) record
        bar_close: Dict[str, float] = {}
        for s in symbols:
            if s in data:
                row = data[s]
                if hasattr(row, "__getitem__") and "close" in row:
                    bar_close[s] = float(row["close"])
                else:
                    bar_close[s] = float(row)
        self.portfolio.record(timestamp, bar_close)

        # 8) stats
        self.stats.last_equity = self.portfolio.equity()
        self.stats.last_pnl = (
            self.stats.last_equity - 100000.0
        )
        return self.stats

    # ---- 控制 ----
    def stop(self, reason: str = "") -> None:
        self.stats.stopped = True
        self.stats.stop_reason = reason

    def resume(self) -> None:
        self.stats.stopped = False
        self.stats.stop_reason = ""

    def snapshot(self) -> Dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "account_id": self.account_id,
            "strategy": type(self.strategy).__name__,
            "broker": type(self.broker).__name__,
            "stats": {
                "bars_processed": self.stats.bars_processed,
                "signals_generated": self.stats.signals_generated,
                "orders_submitted": self.stats.orders_submitted,
                "fills_received": self.stats.fills_received,
                "last_pnl": self.stats.last_pnl,
                "last_equity": self.stats.last_equity,
                "stopped": self.stats.stopped,
            },
        }
