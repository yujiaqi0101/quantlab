"""
QuantLab Trader V1 — 端到端验证

测试 4 个新增模块：
  1. MarketDataService: 统一行情服务
  2. BinanceBroker: 现货接口（不连真实 API，只测结构）
  3. Scheduler: 策略定时调度
  4. Notification + Journal: 通知与日志
"""

import os
import sys
import time
import logging
import tempfile
import pandas as pd
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("trader_e2e")


def test_market_data_service():
    """测试 1：MarketDataService"""
    logger.info("=" * 60)
    logger.info("Test 1: MarketDataService")
    logger.info("=" * 60)

    from quantlab.execution.market import (
        MarketDataService,
        BacktestProvider,
        Bar,
    )

    # 1) Backtest 模式
    service = MarketDataService(mode="backtest")

    # 构造测试数据
    df = pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=10, freq="1min"),
        "open": [100 + i for i in range(10)],
        "high": [101 + i for i in range(10)],
        "low": [99 + i for i in range(10)],
        "close": [100.5 + i for i in range(10)],
        "volume": [1000 + i * 100 for i in range(10)],
    })

    service.load_bars("TESTUSDT", "1m", df)

    # 2) get_bar
    bar = service.get_bar("TESTUSDT", "1m")
    assert bar is not None
    assert bar.symbol == "TESTUSDT"
    assert bar.interval == "1m"
    logger.info(f"Latest bar: {bar.to_dict()}")

    # 3) get_bars
    bars = service.get_bars("TESTUSDT", "1m", limit=5)
    assert len(bars) == 5
    logger.info(f"Got {len(bars)} bars")

    # 4) snapshot
    snap = service.snapshot("TESTUSDT")
    assert snap is not None
    assert snap.last_price > 0
    logger.info(f"Snapshot: {snap.to_dict()}")

    # 5) push_tick + subscribe
    from quantlab.core.tick import Tick
    received = []
    service.subscribe_ticks(["BTCUSDT"], lambda t: received.append(t))
    service.push_tick(Tick(timestamp=datetime.now(), symbol="BTCUSDT", price=50000))
    assert len(received) == 1
    assert received[0].price == 50000
    logger.info(f"Tick subscription OK, received {len(received)} ticks")

    # 6) stats
    stats = service.stats()
    logger.info(f"Stats: {stats}")
    assert stats["mode"] == "backtest"

    logger.info("✓ MarketDataService OK")


def test_binance_broker_structure():
    """测试 2：BinanceBroker 结构（不连真实 API）"""
    logger.info("=" * 60)
    logger.info("Test 2: BinanceBroker Structure")
    logger.info("=" * 60)

    from quantlab.live.broker.binance_broker import BinanceBroker
    from quantlab.core.order import Order

    # 1) 初始化
    broker = BinanceBroker(
        api_key="test",
        api_secret="test",
        testnet=True,
    )
    assert broker.name == "BINANCE"
    assert broker.testnet is True
    assert broker.market == "spot"
    assert broker.connected is False
    logger.info(f"Broker: {broker}")

    # 2) 未连接时 get_account 返回空
    state = broker.get_account()
    assert state.cash == 0.0
    logger.info(f"Unconnected account: {state}")

    # 3) 未连接时 get_positions 返回空
    positions = broker.get_positions()
    assert positions == {}
    logger.info(f"Unconnected positions: {positions}")

    # 4) 未连接时 submit_order 抛异常
    order = Order(symbol="BTCUSDT", quantity=1, order_type="MARKET")
    try:
        broker.submit_order(order)
        assert False, "should raise"
    except RuntimeError as e:
        assert "not connected" in str(e)
        logger.info(f"Expected error: {e}")

    # 5) 精度处理
    qty_str = broker._format_qty("BTCUSDT", 1.23456789)
    assert isinstance(qty_str, str)
    logger.info(f"Formatted qty 1.23456789 → {qty_str}")

    price_str = broker._format_price("BTCUSDT", 50000.123456)
    assert isinstance(price_str, str)
    logger.info(f"Formatted price 50000.123456 → {price_str}")

    # 6) update_last_price
    broker.update_last_price("BTCUSDT", 50000)
    assert broker._last_prices["BTCUSDT"] == 50000

    # 7) 拒绝非 spot
    try:
        BinanceBroker(api_key="x", api_secret="x", market="futures")
        assert False, "should reject futures"
    except ValueError as e:
        assert "spot" in str(e)
        logger.info(f"Expected rejection: {e}")

    logger.info("✓ BinanceBroker Structure OK")


def test_scheduler():
    """测试 3：Scheduler"""
    logger.info("=" * 60)
    logger.info("Test 3: Scheduler")
    logger.info("=" * 60)

    from quantlab.execution.scheduler import (
        Scheduler,
        ScheduleRule,
    )

    scheduler = Scheduler(tick_interval=0.1)

    # 1) ScheduleRule
    rule_1min = ScheduleRule.every_minutes(1)
    assert rule_1min.kind == "interval"
    assert rule_1min.interval_seconds == 60
    logger.info(f"Rule 1min: {rule_1min}")

    rule_1h = ScheduleRule.every_hours(1)
    assert rule_1h.interval_seconds == 3600

    rule_daily = ScheduleRule.daily_at("09:30")
    assert rule_daily.kind == "daily"
    assert rule_daily.daily_time == "09:30"
    logger.info(f"Rule daily: {rule_daily}")

    # 2) next_run_time
    now = datetime(2024, 1, 15, 10, 0, 0)
    next_run = rule_1min.next_run_time(now)
    assert next_run == datetime(2024, 1, 15, 10, 1, 0)
    logger.info(f"Next run for 1min: {next_run}")

    next_daily = rule_daily.next_run_time(now)
    # 10:00 > 09:30, 所以是明天
    assert next_daily == datetime(2024, 1, 16, 9, 30, 0)
    logger.info(f"Next run for daily 09:30 (from 10:00): {next_daily}")

    # 3) 添加任务
    triggered = []
    def callback(ts):
        triggered.append(ts)

    job = scheduler.add(
        "test_job",
        ScheduleRule.every_seconds(1),
        callback,
    )
    assert job.job_id == "test_job"
    assert job.enabled is True
    logger.info(f"Added job: {job.to_dict()}")

    # 4) 启动并等待
    scheduler.start()
    assert scheduler.running is True

    # 等待 2.5 秒，应该触发 2 次
    time.sleep(2.5)

    scheduler.stop()
    logger.info(f"Triggered {len(triggered)} times")
    assert len(triggered) >= 2

    # 5) 手动触发
    initial_count = len(triggered)
    scheduler.trigger("test_job")
    assert len(triggered) == initial_count + 1
    logger.info(f"After manual trigger: {len(triggered)}")

    # 6) enable / disable
    assert scheduler.disable("test_job") is True
    job = scheduler.get("test_job")
    assert job.enabled is False

    assert scheduler.enable("test_job") is True
    job = scheduler.get("test_job")
    assert job.enabled is True

    # 7) remove
    assert scheduler.remove("test_job") is True
    assert scheduler.get("test_job") is None

    # 8) stats
    stats = scheduler.stats()
    logger.info(f"Stats: {stats}")
    assert stats["n_jobs"] == 0

    logger.info("✓ Scheduler OK")


def test_notification_and_journal():
    """测试 4：Notification + Journal"""
    logger.info("=" * 60)
    logger.info("Test 4: Notification + Journal")
    logger.info("=" * 60)

    from quantlab.execution.notification import (
        NotificationCenter,
        NotificationLevel,
        LogChannel,
    )
    from quantlab.execution.journal import (
        TradingJournal,
        JournalCategory,
    )

    # 1) Notification
    notifier = NotificationCenter()
    notifier.add_channel(LogChannel())

    n = notifier.info(
        title="开仓通知",
        message="BUY 0.5 BTC @ 50000",
        metadata={"symbol": "BTCUSDT", "qty": 0.5},
        category="order",
    )
    assert n.level == NotificationLevel.INFO
    assert n.title == "开仓通知"
    logger.info(f"Notification: {n.to_dict()}")

    n2 = notifier.warning(
        title="风险警告",
        message="Daily loss approaching limit",
        category="risk",
    )
    assert n2.level == NotificationLevel.WARNING

    # 历史查询
    history = notifier.list_history(category="order")
    assert len(history) >= 1
    logger.info(f"Notification history: {len(history)} entries")

    stats = notifier.stats()
    assert stats["n_channels"] == 1
    logger.info(f"Notifier stats: {stats}")

    # 2) Journal
    with tempfile.TemporaryDirectory() as tmpdir:
        journal = TradingJournal(store_dir=tmpdir)

        # 开仓
        entry1 = journal.log_open(
            symbol="BTCUSDT",
            qty=0.5,
            price=50000,
            reason="RSI<30 + 趋势线支撑",
            strategy="rsi_reversal",
        )
        assert entry1.category == "open"
        assert entry1.metadata["symbol"] == "BTCUSDT"
        logger.info(f"Journal open: {entry1.to_dict()}")

        # 平仓
        entry2 = journal.log_close(
            symbol="BTCUSDT",
            qty=0.5,
            price=51000,
            pnl=500,
            reason="止盈",
            strategy="rsi_reversal",
        )
        assert entry2.category == "close"
        assert entry2.metadata["pnl"] == 500

        # 复盘
        entry3 = journal.log_reflection(
            title="2024-01-15 复盘",
            content="RSI 策略表现良好，但止损太紧",
        )
        assert entry3.category == "reflection"

        # 参数修改
        entry4 = journal.log_param(
            strategy="rsi_reversal",
            param_name="rsi_period",
            old_value=14,
            new_value=21,
            reason="降低交易频率",
        )
        assert entry4.category == "param"

        # 查询
        all_entries = journal.list_entries()
        assert len(all_entries) == 4
        logger.info(f"Total entries: {len(all_entries)}")

        open_entries = journal.list_entries(category="open")
        assert len(open_entries) == 1

        strategy_entries = journal.list_entries(strategy="rsi_reversal")
        assert len(strategy_entries) == 3  # open + close + param

        # 统计
        stats = journal.stats()
        logger.info(f"Journal stats: {stats}")
        assert stats["total"] == 4
        assert stats["by_category"]["open"] == 1
        assert stats["by_category"]["close"] == 1

        # 重新加载（验证持久化）
        journal2 = TradingJournal(store_dir=tmpdir)
        assert len(journal2.list_entries()) == 4
        logger.info(f"Reloaded {len(journal2.list_entries())} entries")

    logger.info("✓ Notification + Journal OK")


def main():
    logger.info("=" * 60)
    logger.info("QuantLab Trader V1 — End-to-End Validation")
    logger.info("=" * 60)

    tests = [
        test_market_data_service,
        test_binance_broker_structure,
        test_scheduler,
        test_notification_and_journal,
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
