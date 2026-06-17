"""
Execution Platform — 端到端验证

测试三个补齐模块：
  1. SignalExecutor: Signal → TargetPortfolio → Order
  2. PromotionWorkflow: Research → Candidate → Paper → Approved → Live
  3. Live Studio API: accounts/portfolio/orders/positions/risk/monitoring
"""

import sys
import os
import logging
import numpy as np
import pandas as pd
import tempfile

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("execution_e2e")


def test_signal_executor():
    """测试 1：SignalExecutor"""
    logger.info("=" * 60)
    logger.info("Test 1: SignalExecutor")
    logger.info("=" * 60)

    from quantlab.execution import Signal, SignalSide, SignalExecutor
    from quantlab.core.portfolio import Portfolio

    # 初始组合（用股票价格，避免加密货币数量取整为 0）
    portfolio = Portfolio(initial_cash=100000)
    prices = {"AAPL": 150, "MSFT": 300}

    executor = SignalExecutor(
        portfolio=portfolio,
        prices=prices,
        max_weight=0.5,
    )

    # 信号：买 AAPL（强度 0.6），卖 MSFT（清仓）
    signals = {
        "AAPL": Signal(symbol="AAPL", side=SignalSide.BUY, strength=0.6),
        "MSFT": Signal(symbol="MSFT", side=SignalSide.SELL, strength=0.0),
    }

    orders = executor.execute(signals, timestamp="2024-01-01")
    logger.info(f"Generated {len(orders)} orders")
    for o in orders:
        logger.info(f"  Order: {o.symbol} qty={o.quantity} side={o.side}")

    assert len(orders) > 0
    # AAPL 应该是买单
    aapl_orders = [o for o in orders if o.symbol == "AAPL"]
    assert any(o.quantity > 0 for o in aapl_orders)
    logger.info("✓ SignalExecutor OK")


def test_promotion_workflow():
    """测试 2：PromotionWorkflow"""
    logger.info("=" * 60)
    logger.info("Test 2: PromotionWorkflow")
    logger.info("=" * 60)

    from quantlab.research.projects import (
        CandidateManager,
        PromotionWorkflow,
        PromotionConfig,
        PaperTradingResult,
    )

    # 用临时目录
    with tempfile.TemporaryDirectory() as tmpdir:
        cm = CandidateManager(store_dir=tmpdir)
        config = PromotionConfig(
            paper_min_sharpe=0.3,
            paper_min_duration_days=1,
            paper_min_trades=1,
            research_min_sharpe=0.8,
        )
        workflow = PromotionWorkflow(
            candidate_manager=cm,
            config=config,
        )

        # 1. Research → Candidate
        cand = workflow.submit_from_research(
            alpha_id="alpha_001",
            project_id="proj_test",
            metrics={"sharpe": 1.5, "max_drawdown": 0.1},
        )
        logger.info(f"Step 1: candidate status = {cand.status.value}")
        assert cand.status.value == "candidate"

        # 2. Candidate → Paper Trading
        paper_result = workflow.start_paper_trading(
            candidate_id=cand.candidate_id,
            duration_days=1,
        )
        logger.info(f"Step 2: paper started, duration={paper_result.duration_days}d")
        assert cand.candidate_id in workflow.active_paper

        # 3. 报告 Paper 结果（通过）
        good_result = PaperTradingResult(
            candidate_id=cand.candidate_id,
            duration_days=1,
            sharpe=0.8,
            max_drawdown=0.05,
            n_trades=10,
        )
        cand = workflow.report_paper_result(cand.candidate_id, good_result)
        logger.info(f"Step 3: after paper, status = {cand.status.value}")
        assert cand.status.value == "approved"

        # 4. Approved → Live
        cand = workflow.deploy_to_live(
            candidate_id=cand.candidate_id,
            account_id="acc_001",
        )
        logger.info(f"Step 4: deployed, status = {cand.status.value}, portfolio = {cand.portfolio_id}")
        assert cand.status.value == "portfolio"

        # 5. 流水线状态
        status = workflow.get_pipeline_status()
        logger.info(f"Pipeline status: {status}")
        assert status["completed_paper_trading"] == 1

        # 6. 测试不达标的候选
        bad_cand = workflow.submit_from_research(
            alpha_id="alpha_002",
            project_id="proj_test",
            metrics={"sharpe": 0.3, "max_drawdown": 0.1},  # sharpe 不够
        )
        logger.info(f"Bad candidate status: {bad_cand.status.value}")
        assert bad_cand.status.value == "evaluated"  # 没 promote

    logger.info("✓ PromotionWorkflow OK")


def test_execution_api():
    """测试 3：Live Studio API"""
    logger.info("=" * 60)
    logger.info("Test 3: Live Studio API")
    logger.info("=" * 60)

    from fastapi.testclient import TestClient
    from quantlab.api.app import app
    from quantlab.api.execution import get_execution_registry
    from quantlab.live.broker.paper_broker import PaperBroker
    from quantlab.live.market_data import MarketDataAdapter
    from quantlab.live.order_manager import OrderManager
    from quantlab.live.risk import RiskManager
    from quantlab.core.order import Order

    # 1. 注册一个 Paper 账户
    registry = get_execution_registry()

    class MockMarketData:
        def subscribe(self, *args, **kwargs): pass
        def stream(self): return iter([])

    broker = PaperBroker(
        market_data=MockMarketData(),
        tick_size=0.01,
        commission_rate=0.0003,
        initial_cash=100000.0,
    )
    broker.connect()
    broker.push_tick("BTCUSDT", 50000)

    # 简单 engine mock
    class MockEngine:
        def __init__(self, broker):
            self.broker = broker
            self.order_manager = OrderManager(broker)
            self.risk_manager = RiskManager()
            self.initial_cash = 100000.0
            self.equity_curve = [100000.0]
            self.equity_ts = []
            class EmergencyStop:
                stop = False
            self.emergency_stop = EmergencyStop()

    engine = MockEngine(broker)
    registry.register_account("paper_001", broker, engine)

    client = TestClient(app)

    # 2. 测试 accounts
    resp = client.get("/api/v1/execution/accounts")
    assert resp.status_code == 200
    data = resp.json()
    logger.info(f"Accounts: {data}")
    assert data["total"] >= 1

    # 3. 测试 account 详情
    resp = client.get("/api/v1/execution/accounts/paper_001")
    assert resp.status_code == 200
    logger.info(f"Account detail: {resp.json()}")

    # 4. 测试 portfolio
    resp = client.get("/api/v1/execution/portfolio?account_id=paper_001")
    assert resp.status_code == 200
    logger.info(f"Portfolio: {resp.json()}")

    # 5. 测试 positions
    resp = client.get("/api/v1/execution/positions?account_id=paper_001")
    assert resp.status_code == 200
    logger.info(f"Positions: {resp.json()}")

    # 6. 测试下单
    resp = client.post("/api/v1/execution/orders", json={
        "account_id": "paper_001",
        "symbol": "BTCUSDT",
        "quantity": 1,
        "order_type": "MARKET",
    })
    assert resp.status_code == 200
    order_data = resp.json()
    logger.info(f"Order submitted: {order_data}")
    assert order_data["status"] == "submitted"

    # 7. 测试 orders 列表
    resp = client.get("/api/v1/execution/orders?account_id=paper_001")
    assert resp.status_code == 200
    logger.info(f"Orders: {resp.json()}")

    # 8. 测试 risk status
    resp = client.get("/api/v1/execution/risk/status?account_id=paper_001")
    assert resp.status_code == 200
    logger.info(f"Risk status: {resp.json()}")

    # 9. 测试 monitoring dashboard
    resp = client.get("/api/v1/execution/monitoring/dashboard?account_id=paper_001")
    assert resp.status_code == 200
    logger.info(f"Dashboard: {resp.json()}")

    # 10. 测试 pipeline
    resp = client.get("/api/v1/execution/pipeline")
    assert resp.status_code == 200
    logger.info(f"Pipeline: {resp.json()}")

    logger.info("✓ Live Studio API OK")


def main():
    logger.info("=" * 60)
    logger.info("Execution Platform — End-to-End Validation")
    logger.info("=" * 60)

    tests = [
        test_signal_executor,
        test_promotion_workflow,
        test_execution_api,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            logger.error(f"FAILED: {test.__name__}: {e}", exc_info=True)
            failed += 1

    logger.info("=" * 60)
    logger.info(f"Results: {passed} passed, {failed} failed")
    logger.info("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
