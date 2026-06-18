"""
Phase T1 Trading Core — 端到端测试

验证 10 个模块的完整集成：
  1. Broker Abstraction
  2. OMS
  3. Fill Engine
  4. Position Book
  5. Portfolio Book
  6. Paper Exchange
  7. Runtime Engine
  8. Deployment Manager
  9. Strategy Registry
 10. Live Studio API

运行：
    pytest tests/test_trading_core_t1.py -v
"""

import pytest

from quantlab.execution.broker import (
    Broker, PaperBroker, BinanceBroker,
    AccountInfo, PositionInfo, OrderRequest, OrderResponse, BrokerType,
)
from quantlab.execution.core.oms import (
    OrderManager, OMSOrder, OrderSide, OrderType, OrderState,
)
from quantlab.execution.core.fills import Fill, FillEngine
from quantlab.execution.position_book import PositionBook, Position
from quantlab.execution.portfolio_book import PortfolioBook
from quantlab.execution.paper_exchange import PaperExchange, ExchangeConfig
from quantlab.execution.runtime import Runtime, start, stop, get_runtime
from quantlab.execution.deployment import (
    DeploymentManager, DeployRequest, DeployResult, DeployStatus,
)
from quantlab.execution.strategy_registry import (
    StrategyRegistry, StrategyInfo, StrategyParameter, get_registry,
)


# ==================================================================
# Module 1: Broker Abstraction
# ==================================================================

class TestModule1BrokerAbstraction:
    """模块 1: Broker 抽象"""

    def test_paper_broker_creation(self):
        broker = PaperBroker(initial_capital=100000)
        assert broker.name.upper() == "PAPER"
        assert broker.broker_type == BrokerType.PAPER

    def test_get_account(self):
        broker = PaperBroker(initial_capital=100000)
        account = broker.get_account()
        assert account.cash == 100000
        assert account.equity == 100000

    def test_get_positions_empty(self):
        broker = PaperBroker(initial_capital=100000)
        positions = broker.get_positions()
        assert isinstance(positions, list)

    def test_submit_market_order(self):
        broker = PaperBroker(initial_capital=100000)
        broker.update_market_prices({"BTCUSDT": 50000})
        req = OrderRequest(
            symbol="BTCUSDT",
            side="BUY",
            qty=0.1,
            order_type="MARKET",
        )
        resp = broker.submit_order(req)
        assert resp.status in ["FILLED", "SUBMITTED"]

    def test_cancel_order(self):
        broker = PaperBroker(initial_capital=100000)
        broker.update_market_prices({"BTCUSDT": 50000})
        req = OrderRequest(
            symbol="BTCUSDT",
            side="BUY",
            qty=0.1,
            order_type="LIMIT",
            price=40000,
        )
        resp = broker.submit_order(req)
        if resp.broker_order_id:
            result = broker.cancel_order(resp.broker_order_id)
            assert isinstance(result, bool)

    def test_get_open_orders(self):
        broker = PaperBroker(initial_capital=100000)
        orders = broker.get_open_orders()
        assert isinstance(orders, list)

    def test_binance_broker_placeholder(self):
        broker = BinanceBroker()
        assert broker.name.upper() == "BINANCE"
        assert broker.broker_type == BrokerType.BINANCE


# ==================================================================
# Module 2: OMS
# ==================================================================

class TestModule2OMS:
    """模块 2: 订单管理系统"""

    def test_create_order(self):
        oms = OrderManager()
        order = oms.create_order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.1,
            order_type=OrderType.MARKET,
            strategy_id="test",
        )
        assert order is not None
        assert order.state == OrderState.NEW
        assert order.symbol == "BTCUSDT"

    def test_order_state_machine(self):
        oms = OrderManager()
        order = oms.create_order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.1,
            order_type=OrderType.MARKET,
        )
        # NEW → PENDING_SUBMIT → SUBMITTED
        order.transition_to(OrderState.PENDING_SUBMIT, "USER_SUBMIT")
        oms.submit(order.id, broker_order_id="BROKER-001")
        updated = oms.get_order(order.id)
        assert updated.state == OrderState.SUBMITTED

        # SUBMITTED → FILLED
        oms.apply_fill(order.id, fill_qty=0.1, fill_price=50000)
        filled = oms.get_order(order.id)
        assert filled.state == OrderState.FILLED
        assert filled.filled_qty == pytest.approx(0.1)

    def test_cancel_order(self):
        oms = OrderManager()
        order = oms.create_order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.1,
            order_type=OrderType.LIMIT,
            price=40000,
        )
        oms.submit(order.id, broker_order_id="BROKER-002")
        success = oms.cancel(order.id)
        assert success
        cancelled = oms.get_order(order.id)
        assert cancelled.state == OrderState.CANCELLED

    def test_get_active_orders(self):
        oms = OrderManager()
        order = oms.create_order(
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            quantity=0.1,
            order_type=OrderType.LIMIT,
            price=40000,
        )
        oms.submit(order.id, broker_order_id="BROKER-003")
        active = oms.get_active_orders()
        assert len(active) >= 1


# ==================================================================
# Module 3: Fill Engine
# ==================================================================

class TestModule3FillEngine:
    """模块 3: 成交引擎"""

    def test_fill_creation(self):
        fill = Fill(
            order_id="ORDER-001",
            symbol="BTCUSDT",
            side="BUY",
            fill_qty=0.1,
            fill_price=50000,
            commission=5.0,
            timestamp=1234567890,
        )
        assert fill.order_id == "ORDER-001"
        assert fill.fill_qty == pytest.approx(0.1)
        assert fill.fill_price == 50000
        assert fill.commission == 5.0

    def test_fill_engine(self):
        engine = FillEngine()
        fill = engine.process_fill(
            order_id="ORDER-001",
            symbol="BTCUSDT",
            side="BUY",
            fill_qty=0.1,
            fill_price=50000,
        )
        assert fill is not None
        assert fill.symbol == "BTCUSDT"


# ==================================================================
# Module 4: Position Book
# ==================================================================

class TestModule4PositionBook:
    """模块 4: 持仓簿"""

    def test_apply_buy_fill(self):
        book = PositionBook()
        pos = book.apply_fill(
            symbol="BTCUSDT",
            side="BUY",
            qty=0.1,
            price=50000,
            commission=5.0,
            strategy_id="test",
        )
        assert pos.qty == pytest.approx(0.1)
        assert pos.avg_price == pytest.approx(50000)
        assert pos.side == "LONG"

    def test_position_pnl_update(self):
        book = PositionBook()
        book.apply_fill(
            symbol="BTCUSDT",
            side="BUY",
            qty=0.1,
            price=50000,
        )
        book.update_prices({"BTCUSDT": 55000})
        pos = book.get_position("BTCUSDT")
        assert pos.market_price == 55000
        assert pos.unrealized_pnl == pytest.approx(500, rel=0.01)

    def test_realized_pnl_on_close(self):
        book = PositionBook()
        # 开仓
        book.apply_fill("BTCUSDT", "BUY", 0.1, 50000)
        # 平仓
        pos = book.apply_fill("BTCUSDT", "SELL", 0.1, 55000)
        assert pos.qty == pytest.approx(0)
        assert pos.realized_pnl == pytest.approx(500, rel=0.01)


# ==================================================================
# Module 5: Portfolio Book
# ==================================================================

class TestModule5PortfolioBook:
    """模块 5: 组合簿"""

    def test_initial_state(self):
        book = PortfolioBook(initial_capital=100000)
        assert book.cash == 100000
        assert book.equity() == 100000
        assert book.exposure() == 0

    def test_apply_buy(self):
        book = PortfolioBook(initial_capital=100000)
        book.apply_fill(
            symbol="BTCUSDT",
            side="BUY",
            qty=0.1,
            price=50000,
            commission=5.0,
        )
        assert book.cash < 100000
        assert book.n_open_positions() == 1

    def test_equity_calculation(self):
        book = PortfolioBook(initial_capital=100000)
        book.apply_fill("BTCUSDT", "BUY", 0.1, 50000)
        book.update_prices({"BTCUSDT": 55000})
        # equity = cash + market_value
        assert book.equity() > 100000

    def test_exposure_calculation(self):
        book = PortfolioBook(initial_capital=100000)
        book.apply_fill("BTCUSDT", "BUY", 0.1, 50000)
        book.update_prices({"BTCUSDT": 50000})
        assert book.exposure() > 0
        assert book.long_exposure() > 0


# ==================================================================
# Module 6: Paper Exchange
# ==================================================================

class TestModule6PaperExchange:
    """模块 6: 模拟交易所"""

    def test_default_config(self):
        ex = PaperExchange()
        assert ex.config.fee_rate == pytest.approx(0.001)
        assert ex.config.slippage_rate == pytest.approx(0.0005)

    def test_match_market_order(self):
        ex = PaperExchange()
        ex.update_price("BTCUSDT", 50000)
        req = OrderRequest(
            symbol="BTCUSDT",
            side="BUY",
            qty=0.1,
            order_type="MARKET",
        )
        fill = ex.match_order(req)
        assert fill is not None
        assert fill.qty == pytest.approx(0.1)
        # 价格应包含滑点
        assert fill.price >= 50000

    def test_fee_calculation(self):
        ex = PaperExchange()
        ex.update_price("BTCUSDT", 50000)
        req = OrderRequest(
            symbol="BTCUSDT",
            side="BUY",
            qty=0.1,
            order_type="MARKET",
        )
        fill = ex.match_order(req)
        expected_fee = fill.price * 0.1 * 0.001
        assert fill.commission == pytest.approx(expected_fee, rel=0.01)


# ==================================================================
# Module 7: Runtime Engine
# ==================================================================

class TestModule7RuntimeEngine:
    """模块 7: 运行时引擎"""

    def test_runtime_creation(self):
        runtime = Runtime(initial_capital=100000)
        assert runtime.portfolio_book.cash == 100000
        assert runtime.broker is not None

    def test_runtime_start_stop(self):
        runtime = Runtime(initial_capital=100000)
        runtime.start()
        assert runtime.is_running
        runtime.stop()
        assert not runtime.is_running

    def test_submit_order_via_runtime(self):
        runtime = Runtime(initial_capital=100000)
        runtime.start()
        runtime.update_prices({"BTCUSDT": 50000})
        order = runtime.submit_order(
            symbol="BTCUSDT",
            side="BUY",
            qty=0.1,
            strategy_id="test",
        )
        assert order is not None
        runtime.stop()

    def test_module_level_start(self):
        runtime = start(initial_capital=50000)
        assert runtime.is_running
        assert runtime.portfolio_book.cash == 50000
        stop()
        assert not runtime.is_running


# ==================================================================
# Module 8: Deployment Manager
# ==================================================================

class TestModule8DeploymentManager:
    """模块 8: 部署管理器"""

    def test_deploy_strategy(self):
        mgr = DeploymentManager()
        req = DeployRequest(
            strategy_id="rsi",
            symbols=["BTCUSDT"],
            initial_capital=10000,
        )
        result = mgr.deploy(req)
        assert result.status == DeployStatus.RUNNING
        assert result.deploy_id.startswith("DEPLOY-")

        # 清理
        mgr.undeploy(result.deploy_id)

    def test_list_deployments(self):
        mgr = DeploymentManager()
        req = DeployRequest(
            strategy_id="rsi",
            symbols=["BTCUSDT"],
            initial_capital=10000,
        )
        result = mgr.deploy(req)
        records = mgr.list_deployments()
        assert len(records) >= 1

        mgr.undeploy(result.deploy_id)

    def test_undeploy(self):
        mgr = DeploymentManager()
        req = DeployRequest(
            strategy_id="rsi",
            symbols=["BTCUSDT"],
            initial_capital=10000,
        )
        result = mgr.deploy(req)
        success = mgr.undeploy(result.deploy_id)
        assert success

    def test_get_status(self):
        mgr = DeploymentManager()
        status = mgr.get_status()
        assert "total" in status
        assert "running" in status


# ==================================================================
# Module 9: Strategy Registry
# ==================================================================

class TestModule9StrategyRegistry:
    """模块 9: 策略注册表"""

    def test_registry_creation(self):
        reg = StrategyRegistry()
        assert len(reg.list_strategies()) == 0

    def test_register_strategy(self):
        reg = StrategyRegistry()
        info = StrategyInfo(
            strategy_id="test",
            name="Test Strategy",
            description="Test",
        )
        reg.register(info)
        assert reg.has("test")
        assert len(reg.list_strategies()) == 1

    def test_builtin_strategies(self):
        reg = get_registry()
        strategies = reg.list_strategies()
        ids = [s.strategy_id for s in strategies]
        assert "rsi" in ids
        assert "momentum" in ids
        assert "lgbm_trend" in ids

    def test_get_strategy(self):
        reg = get_registry()
        info = reg.get_strategy("rsi")
        assert info is not None
        assert info.name == "RSI Strategy"
        assert len(info.parameters) > 0

    def test_list_by_category(self):
        reg = get_registry()
        ml_strategies = reg.list_strategies(category="ml")
        assert len(ml_strategies) >= 1
        assert all(s.category == "ml" for s in ml_strategies)


# ==================================================================
# Module 10: Live Studio API
# ==================================================================

class TestModule10LiveStudioAPI:
    """模块 10: Live Studio API"""

    def test_router_import(self):
        from quantlab.api.live import router
        assert router is not None
        paths = [r.path for r in router.routes]
        assert "/api/v1/live/status" in paths
        assert "/api/v1/live/strategies" in paths
        assert "/api/v1/live/deploy" in paths

    def test_app_includes_live_router(self):
        from quantlab.api.app import app
        # 检查 live 路由已注册
        live_paths = [
            r.path for r in app.routes
            if hasattr(r, 'path') and '/live' in r.path
        ]
        # app.routes 包含子路由（APIRouter 的路由会展开）
        # 如果直接看不到，检查 router 是否已 include
        from quantlab.api.app import app as _app
        # 通过 OpenAPI schema 验证
        schema = _app.openapi()
        paths = schema.get("paths", {})
        live_endpoints = [p for p in paths if "/live" in p]
        assert len(live_endpoints) >= 10


# ==================================================================
# 集成测试: 完整交易流程
# ==================================================================

class TestIntegrationFullFlow:
    """端到端集成测试：完整交易流程"""

    def test_full_trading_flow(self):
        """完整流程：注册 → 部署 → 下单 → 持仓 → 组合 → 卸载"""
        # 1. 策略注册表
        reg = get_registry()
        assert reg.has("rsi")

        # 2. 部署管理器
        mgr = DeploymentManager()
        req = DeployRequest(
            strategy_id="rsi",
            symbols=["BTCUSDT"],
            initial_capital=10000,
        )
        result = mgr.deploy(req)
        assert result.status == DeployStatus.RUNNING

        # 3. 获取 Runtime
        runtime = mgr.get_runtime(result.deploy_id)
        assert runtime is not None

        # 4. 更新价格
        runtime.update_prices({"BTCUSDT": 50000})

        # 5. 下单
        order = runtime.submit_order(
            symbol="BTCUSDT",
            side="BUY",
            qty=0.05,
            strategy_id="rsi",
        )
        assert order is not None

        # 6. 检查持仓
        positions = runtime.get_positions()
        assert len(positions) >= 1

        # 7. 检查组合
        portfolio = runtime.portfolio_book
        assert portfolio.n_open_positions() >= 1

        # 8. 卸载
        success = mgr.undeploy(result.deploy_id)
        assert success

    def test_research_to_deploy_closed_loop(self):
        """Research → Deploy 闭环"""
        # 1. 从策略库选择策略
        reg = get_registry()
        info = reg.get_strategy("momentum")
        assert info is not None

        # 2. 部署
        mgr = DeploymentManager()
        result = mgr.deploy(DeployRequest(
            strategy_id=info.strategy_id,
            symbols=info.symbols,
            initial_capital=50000,
        ))
        assert result.status == DeployStatus.RUNNING

        # 3. 验证运行时
        runtime = mgr.get_runtime(result.deploy_id)
        assert runtime.is_running

        # 4. 清理
        mgr.undeploy(result.deploy_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
