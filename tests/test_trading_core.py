"""
统一 Trading Core 测试套件
==========================

覆盖范围：
    1. interfaces — Bar/OrderIntent/Position/TradingContext/EventStrategy
    2. core — TradingCore 部署/数据流/订单/查询
    3. modes — BacktestMode/PaperMode/LiveMode
    4. adapters — SignalStrategyAdapter
    5. 集成测试 — 端到端回测流程
    6. Bug 修复验证 — SlippageModel

运行命令：
    python -X utf8 -m pytest tests/test_trading_core.py -v
"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timedelta
from typing import List

import pandas as pd
import pytest

# 确保 quantlab 包可导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from quantlab.trading_core import (
    Bar,
    EventStrategy,
    OrderIntent,
    Position,
    TradingContext,
    TradingCore,
)
from quantlab.trading_core.modes import BacktestMode, LiveMode, PaperMode
from quantlab.trading_core.modes.base import TradingMode


# ======================================================================
# 测试辅助：策略实现
# ======================================================================


class BuyOnceStrategy(EventStrategy):
    """测试策略：第一次收到 bar 时全仓买入100股，之后持有。"""

    name = "buy_once"
    version = "1.0"

    def __init__(self):
        self._bought = False
        self.bar_count = 0

    def on_init(self) -> None:
        self._bought = False

    def on_exit(self, ctx: TradingContext) -> List[OrderIntent]:
        return []

    def on_bar(self, bar: Bar, ctx: TradingContext) -> List[OrderIntent]:
        self.bar_count += 1
        if not self._bought and ctx.cash > bar.close * 100:
            self._bought = True
            return [
                OrderIntent(
                    symbol=bar.symbol,
                    side="buy",
                    quantity=100,
                    order_type="market",
                    reason="首次买入",
                )
            ]
        return []


class SellAllStrategy(EventStrategy):
    """测试策略：如果有持仓则全部卖出。"""

    name = "sell_all"
    version = "1.0"

    def on_exit(self, ctx: TradingContext) -> List[OrderIntent]:
        orders = []
        for symbol, pos in ctx.positions.items():
            if pos.quantity > 0:
                orders.append(
                    OrderIntent(
                        symbol=symbol,
                        side="sell",
                        quantity=pos.quantity,
                        order_type="market",
                        reason="清仓",
                    )
                )
        return orders

    def on_bar(self, bar: Bar, ctx: TradingContext) -> List[OrderIntent]:
        return []


class NoTradeStrategy(EventStrategy):
    """测试策略：永不交易。"""

    name = "no_trade"
    version = "1.0"

    def on_exit(self, ctx: TradingContext) -> List[OrderIntent]:
        return []

    def on_bar(self, bar: Bar, ctx: TradingContext) -> List[OrderIntent]:
        return []


def make_bar(symbol: str, day_offset: int = 0, price: float = 10.0) -> Bar:
    """构造测试用 Bar。"""
    base = datetime(2024, 1, 1, 15, 0, 0)
    return Bar(
        timestamp=base + timedelta(days=day_offset),
        symbol=symbol,
        open=price,
        high=price * 1.02,
        low=price * 0.98,
        close=price,
        volume=1000000,
    )


# ======================================================================
# 1. interfaces 测试
# ======================================================================


class TestInterfaces:
    """测试核心数据结构。"""

    def test_bar_creation(self):
        """Bar 基本创建。"""
        bar = make_bar("000001.SZ", price=10.5)
        assert bar.symbol == "000001.SZ"
        assert bar.close == 10.5
        assert bar.open == 10.5
        assert bar.high == 10.5 * 1.02
        assert bar.low == 10.5 * 0.98
        assert bar.volume == 1000000

    def test_order_intent_defaults(self):
        """OrderIntent 默认值。"""
        intent = OrderIntent(symbol="000001.SZ", side="buy", quantity=100)
        assert intent.order_type == "market"
        assert intent.price is None
        assert intent.reason == ""

    def test_order_intent_limit(self):
        """OrderIntent 限价单。"""
        intent = OrderIntent(
            symbol="000001.SZ",
            side="sell",
            quantity=200,
            order_type="limit",
            price=11.0,
            reason="止盈",
        )
        assert intent.order_type == "limit"
        assert intent.price == 11.0
        assert intent.reason == "止盈"

    def test_position_value(self):
        """Position 市值计算。"""
        pos = Position(
            symbol="000001.SZ",
            quantity=100,
            entry_price=10.0,
            entry_date="2024-01-01",
            current_price=11.0,
        )
        assert pos.value == 1100.0
        assert pos.cost == 1000.0
        assert pos.unrealized_pnl == 100.0

    def test_position_short(self):
        """Position 空头方向。"""
        pos = Position(
            symbol="000001.SZ",
            quantity=-100,
            entry_price=10.0,
            entry_date="2024-01-01",
            current_price=9.0,
            direction="short",
        )
        assert pos.value == -900.0
        assert pos.cost == -1000.0
        assert pos.unrealized_pnl == 100.0  # 空头跌了赚钱

    def test_trading_context_total_value(self):
        """TradingContext 总资产计算。"""
        positions = {
            "000001.SZ": Position(
                symbol="000001.SZ",
                quantity=100,
                entry_price=10.0,
                entry_date="2024-01-01",
                current_price=11.0,
            ),
            "000002.SZ": Position(
                symbol="000002.SZ",
                quantity=200,
                entry_price=5.0,
                entry_date="2024-01-01",
                current_price=6.0,
            ),
        }
        ctx = TradingContext(
            timestamp=datetime(2024, 1, 1),
            cash=500000,
            frozen_cash=0.0,
            positions=positions,
            bar_data={},
            universe=["000001.SZ", "000002.SZ"],
        )
        # 500000 + 0 + 1100 + 1200 = 502300
        assert ctx.total_value == 502300.0

    def test_event_strategy_is_abstract(self):
        """EventStrategy 是抽象类，不能直接实例化。"""
        with pytest.raises(TypeError):
            EventStrategy()  # type: ignore


# ======================================================================
# 2. TradingCore 核心测试
# ======================================================================


class TestTradingCore:
    """测试 TradingCore 主类。"""

    def test_init_backtest_mode(self):
        """BacktestMode 初始化。"""
        core = TradingCore(BacktestMode(), initial_capital=1_000_000)
        assert core.mode.name == "backtest"
        assert core.initial_capital == 1_000_000
        assert core.broker is not None
        assert core.oms is not None
        assert core.portfolio_book is not None
        assert core.position_book is not None

    def test_init_paper_mode(self):
        """PaperMode 初始化。"""
        core = TradingCore(PaperMode(), initial_capital=500_000)
        assert core.mode.name == "paper"
        assert core.initial_capital == 500_000

    def test_init_live_mode(self):
        """LiveMode 初始化。"""
        core = TradingCore(LiveMode(), initial_capital=100_000)
        assert core.mode.name == "live"

    def test_deploy_strategy(self):
        """策略部署。"""
        core = TradingCore(BacktestMode())
        strategy = NoTradeStrategy()
        core.deploy_strategy("test", strategy, ["000001.SZ"])
        assert "test" in core._strategies
        assert core._strategies["test"][0] is strategy

    def test_undeploy_strategy(self):
        """策略卸载。"""
        core = TradingCore(BacktestMode())
        core.deploy_strategy("test", NoTradeStrategy(), ["000001.SZ"])
        assert core.undeploy_strategy("test") is True
        assert "test" not in core._strategies
        assert core.undeploy_strategy("test") is False

    def test_on_bar_no_strategy(self):
        """无策略时 on_bar 不报错。"""
        core = TradingCore(BacktestMode())
        bar = make_bar("000001.SZ", price=10.0)
        core.on_bar(bar)  # 不应抛异常
        assert core._latest_prices["000001.SZ"] == 10.0

    def test_on_bar_with_no_trade_strategy(self):
        """NoTradeStrategy 不产生订单。"""
        core = TradingCore(BacktestMode())
        core.deploy_strategy("nt", NoTradeStrategy(), ["000001.SZ"])
        bar = make_bar("000001.SZ", price=10.0)
        core.on_bar(bar)
        assert len(core.oms.get_all_orders()) == 0
        assert len(core.get_positions()) == 0

    def test_buy_flow(self):
        """买入流程：on_bar → 订单 → 成交 → 持仓。"""
        core = TradingCore(BacktestMode(), initial_capital=1_000_000)
        strategy = BuyOnceStrategy()
        core.deploy_strategy("buy", strategy, ["000001.SZ"])

        bar = make_bar("000001.SZ", price=10.0)
        core.on_bar(bar)

        # 验证订单
        orders = core.oms.get_all_orders()
        assert len(orders) == 1
        assert orders[0].state.value == "FILLED"

        # 验证持仓
        positions = core.get_positions()
        assert len(positions) == 1
        assert positions[0]["symbol"] == "000001.SZ"
        assert positions[0]["qty"] == 100

        # 验证现金减少（买入100股@10+滑点+手续费）
        account = core.get_account()
        assert account["cash"] < 1_000_000
        assert account["cash"] > 1_000_000 - 1200  # 不超过 100*10*1.2

    def test_sell_flow(self):
        """卖出流程：先买入再卖出。"""
        core = TradingCore(BacktestMode(), initial_capital=1_000_000)

        # 先用 BuyOnceStrategy 买入
        buy_strategy = BuyOnceStrategy()
        core.deploy_strategy("buy", buy_strategy, ["000001.SZ"])
        bar1 = make_bar("000001.SZ", day_offset=0, price=10.0)
        core.on_bar(bar1)

        # 确认有持仓
        assert len(core.get_positions()) == 1

        # 卸载买入策略，部署卖出策略
        core.undeploy_strategy("buy")
        sell_strategy = SellAllStrategy()
        core.deploy_strategy("sell", sell_strategy, ["000001.SZ"])
        bar2 = make_bar("000001.SZ", day_offset=1, price=11.0)
        core.on_bar(bar2)

        # 验证卖单成交
        all_orders = core.oms.get_all_orders()
        filled_orders = [o for o in all_orders if o.state.value == "FILLED"]
        assert len(filled_orders) == 2  # 1买 + 1卖

        # 验证持仓清零（SellAll 卖出全部）
        open_positions = [p for p in core.get_positions() if p["qty"] != 0]
        assert len(open_positions) == 0

    def test_get_account(self):
        """账户查询。"""
        core = TradingCore(BacktestMode(), initial_capital=1_000_000)
        account = core.get_account()
        assert account["initial_capital"] == 1_000_000
        assert account["cash"] == 1_000_000
        assert account["equity"] == 1_000_000

    def test_get_status(self):
        """综合状态查询。"""
        core = TradingCore(PaperMode())
        core.deploy_strategy("s1", NoTradeStrategy(), ["000001.SZ"])
        status = core.get_status()
        assert status["mode"] == "paper"
        assert "s1" in status["strategies"]
        assert status["strategies"]["s1"]["name"] == "no_trade"

    def test_get_orders_active_only(self):
        """订单查询：active_only 过滤。"""
        core = TradingCore(BacktestMode())
        core.deploy_strategy("buy", BuyOnceStrategy(), ["000001.SZ"])
        core.on_bar(make_bar("000001.SZ", price=10.0))

        all_orders = core.get_orders(active_only=False)
        active_orders = core.get_orders(active_only=True)
        assert len(all_orders) == 1
        assert len(active_orders) == 0  # 已成交，无活动订单

    def test_bar_history_buffer(self):
        """K线历史缓冲。"""
        core = TradingCore(BacktestMode(), max_bar_history=5)
        core.deploy_strategy("nt", NoTradeStrategy(), ["000001.SZ"])
        for i in range(10):
            core.on_bar(make_bar("000001.SZ", day_offset=i, price=10.0 + i))
        # 缓冲被限制为5
        assert len(core._bar_history["000001.SZ"]) == 5

    def test_context_has_bar_data(self):
        """策略上下文包含 bar_data。"""
        core = TradingCore(BacktestMode())
        strategy = NoTradeStrategy()
        core.deploy_strategy("nt", strategy, ["000001.SZ"])
        core.on_bar(make_bar("000001.SZ", price=10.0))

        # 获取上下文（通过 _build_context）
        bar = make_bar("000001.SZ", day_offset=1, price=11.0)
        ctx = core._build_context(bar)
        assert "000001.SZ" in ctx.bar_data
        assert isinstance(ctx.bar_data["000001.SZ"], pd.DataFrame)
        assert len(ctx.bar_data["000001.SZ"]) >= 1


# ======================================================================
# 3. Modes 测试
# ======================================================================


class TestModes:
    """测试三种交易模式。"""

    def test_backtest_mode_name(self):
        assert BacktestMode().name == "backtest"

    def test_paper_mode_name(self):
        assert PaperMode().name == "paper"

    def test_live_mode_name(self):
        assert LiveMode().name == "live"

    def test_backtest_create_broker(self):
        """BacktestMode 创建 PaperBroker。"""
        mode = BacktestMode()
        broker = mode.create_broker(1_000_000)
        assert broker is not None
        assert broker.broker_type.value == "PAPER"

    def test_paper_create_broker(self):
        """PaperMode 创建 PaperBroker。"""
        mode = PaperMode()
        broker = mode.create_broker(500_000)
        assert broker is not None
        assert broker.broker_type.value == "PAPER"

    def test_backtest_run_history(self):
        """BacktestMode.run_history 端到端回测。"""
        mode = BacktestMode()
        core = TradingCore(mode, initial_capital=1_000_000)
        core.deploy_strategy("buy", BuyOnceStrategy(), ["000001.SZ"])

        bars = [make_bar("000001.SZ", day_offset=i, price=10.0 + i * 0.5) for i in range(5)]
        mode.run_history(core, bars)

        # 第1根bar买入，之后持有
        assert core.get_positions()[0]["qty"] == 100
        account = core.get_account()
        assert account["n_open_positions"] == 1

    def test_trading_mode_is_abstract(self):
        """TradingMode 是抽象类。"""
        with pytest.raises(TypeError):
            TradingMode()  # type: ignore


# ======================================================================
# 4. Adapter 测试
# ======================================================================


class TestSignalAdapter:
    """测试 SignalStrategyAdapter。"""

    def test_adapter_import(self):
        """适配器可导入。"""
        from quantlab.trading_core.adapters import SignalStrategyAdapter

        assert SignalStrategyAdapter is not None

    def test_adapter_with_no_signal_strategy(self):
        """适配器空策略不报错。"""
        from quantlab.trading_core.adapters import SignalStrategyAdapter

        # 构造一个最小的 mock signal strategy
        class MockSignalStrategy:
            name = "mock"
            def signal(self, ctx=None):
                return pd.DataFrame()

        adapter = SignalStrategyAdapter(MockSignalStrategy())
        assert adapter.name == "mock"

        # on_bar 不应抛异常
        bar = make_bar("000001.SZ", price=10.0)
        ctx = TradingContext(
            timestamp=datetime(2024, 1, 1),
            cash=1_000_000,
            frozen_cash=0.0,
            positions={},
            bar_data={},
            universe=["000001.SZ"],
        )
        orders = adapter.on_bar(bar, ctx)
        assert isinstance(orders, list)


# ======================================================================
# 5. 集成测试：端到端回测
# ======================================================================


class TestIntegration:
    """端到端集成测试。"""

    def test_full_backtest_cycle(self):
        """完整回测周期：部署→买入→持有→卖出→结算。"""
        core = TradingCore(BacktestMode(), initial_capital=1_000_000)

        # 阶段1：买入
        buy_strategy = BuyOnceStrategy()
        core.deploy_strategy("phase1", buy_strategy, ["000001.SZ"])

        for i in range(3):
            core.on_bar(make_bar("000001.SZ", day_offset=i, price=10.0 + i))

        # 验证买入成功
        assert len(core.get_positions()) == 1
        assert buy_strategy.bar_count == 3

        # 阶段2：切换为卖出策略
        core.undeploy_strategy("phase1")
        sell_strategy = SellAllStrategy()
        core.deploy_strategy("phase2", sell_strategy, ["000001.SZ"])

        core.on_bar(make_bar("000001.SZ", day_offset=3, price=13.0))

        # 验证卖出成功
        all_orders = core.oms.get_all_orders()
        filled = [o for o in all_orders if o.state.value == "FILLED"]
        assert len(filled) == 2  # 1买 + 1卖

        # 验证账户有盈亏（买@10.x 卖@13.x）
        account = core.get_account()
        assert account["realized_pnl"] != 0 or account["cash"] != 1_000_000

    def test_multi_day_price_update(self):
        """多日价格更新，equity 跟踪正确。"""
        core = TradingCore(BacktestMode(), initial_capital=1_000_000)
        core.deploy_strategy("buy", BuyOnceStrategy(), ["000001.SZ"])

        prices = [10.0, 10.5, 11.0, 10.8, 11.2]
        equities = []

        for i, price in enumerate(prices):
            core.on_bar(make_bar("000001.SZ", day_offset=i, price=price))
            equities.append(core.get_account()["equity"])

        # 第1天买入后，equity 应随价格波动
        # 第1天：买入@10+滑点，equity 略低于初始
        # 之后随价格上涨 equity 增加
        assert equities[0] < 1_000_000  # 买入后有手续费+滑点
        assert equities[2] > equities[1]  # 价格上涨 equity 增加
        assert equities[4] > equities[3]  # 同上

    def test_csv_backtest_via_cli(self):
        """通过 CLI 运行 CSV 回测（端到端）。"""
        import csv

        # 创建临时 CSV
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8"
        ) as f:
            writer = csv.writer(f)
            writer.writerow(["date", "open", "high", "low", "close", "volume"])
            for i in range(5):
                price = 10.0 + i * 0.5
                writer.writerow(
                    [f"2024-01-0{i+1}", price, price * 1.02, price * 0.98, price, 1000000]
                )
            csv_path = f.name

        try:
            from quantlab.cli.trading_cli import handle_trading

            class Args:
                mode = "backtest"
                capital = 1000000
                status = False
                positions = False
                orders = False
                run_backtest = csv_path
                strategy = "demo"
                symbols = ["000001.SZ"]
                bar_csv = None

            # 不应抛异常
            handle_trading(Args())
        finally:
            os.unlink(csv_path)


# ======================================================================
# 6. Bug 修复验证
# ======================================================================


class TestBugFixes:
    """验证已知 Bug 修复。"""

    def test_slippage_model_bug_fixed(self):
        """UpgradedPaperBroker 的 SlippageModel.calculate Bug 已修复。"""
        from quantlab.execution.core.fills.slippage_model import FixedSlippage
        from quantlab.execution.core.oms.order import OMSOrder, OrderSide, OrderType, OrderState
        from quantlab.execution.paper.upgraded_broker import UpgradedPaperBroker

        # 构造 broker
        slippage = FixedSlippage(slippage=0.01)
        broker = UpgradedPaperBroker(slippage_model=slippage)

        # 构造订单
        order = OMSOrder(
            symbol="000001.SZ",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET,
        )
        order.transition_to(OrderState.PENDING_SUBMIT, "test")
        order.transition_to(OrderState.SUBMITTED, "test")

        # 调用 submit_order — 不应抛 AttributeError
        result = broker.submit_order(
            order=order,
            market_price=10.0,
            volume=1000000,
            bid=9.99,
            ask=10.01,
        )
        assert result is not None
        assert result.fill_qty > 0
        # BUY 成交价应 > 市场价（滑点加价）
        assert result.fill_price >= 10.0


# ======================================================================
# 运行入口
# ======================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
