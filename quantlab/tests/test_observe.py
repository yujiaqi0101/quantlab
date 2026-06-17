"""
Observe 模块端到端测试

验证：
  1. Trade Analytics        — profit_factor / expectancy / long_short_win_rate
  2. Execution Analytics    — signal/order/fill latency
  3. Event Timeline         — 基于 EventTracer 聚合
  4. Strategy Health        — 24h 信号/成交/收益监控
  5. Drift Detection        — PSI / KS / mean_std
  6. Observe API            — FastAPI 路由可用

运行：
  python -m quantlab.tests.test_observe
"""

from __future__ import annotations

import logging
import sys
import tempfile
from datetime import datetime, timedelta

import numpy as np

logger = logging.getLogger("trader_e2e")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def banner(title: str) -> None:
    logger.info("=" * 60)
    logger.info(title)
    logger.info("=" * 60)


# ------------------------------------------------------------------
# Test 1: Trade Analytics
# ------------------------------------------------------------------

def test_trade_analytics() -> None:
    banner("Test 1: Trade Analytics")
    from quantlab.observe import TradeAnalytics

    analytics = TradeAnalytics()

    trades = [
        {"pnl": 100, "side": "LONG", "symbol": "AAPL"},
        {"pnl": -50, "side": "LONG", "symbol": "AAPL"},
        {"pnl": 200, "side": "LONG", "symbol": "BTCUSDT"},
        {"pnl": -80, "side": "SHORT", "symbol": "AAPL"},
        {"pnl": 150, "side": "SHORT", "symbol": "BTCUSDT"},
        {"pnl": -30, "side": "LONG", "symbol": "AAPL"},
    ]
    report = analytics.analyze(trades)

    logger.info(f"n_trades: {report.n_trades}")
    logger.info(f"win_rate: {report.win_rate:.2%}")
    logger.info(f"profit_factor: {report.profit_factor:.2f}")
    logger.info(f"expectancy: {report.expectancy:.2f}")
    logger.info(f"avg_win: {report.avg_win:.2f}")
    logger.info(f"avg_loss: {report.avg_loss:.2f}")
    logger.info(f"long_win_rate: {report.long_win_rate:.2%}")
    logger.info(f"short_win_rate: {report.short_win_rate:.2%}")
    logger.info(f"max_consecutive_win: {report.max_consecutive_win}")
    logger.info(f"max_consecutive_loss: {report.max_consecutive_loss}")
    logger.info(f"largest_win: {report.largest_win}")
    logger.info(f"largest_loss: {report.largest_loss}")

    assert report.n_trades == 6
    assert report.n_wins == 3
    assert report.n_losses == 3
    assert abs(report.total_pnl - 290) < 1e-6
    assert abs(report.win_rate - 0.5) < 1e-6
    assert abs(report.profit_factor - (450 / 160)) < 1e-6
    assert abs(report.expectancy - 290 / 6) < 1e-6
    assert abs(report.avg_win - 150) < 1e-6
    assert abs(report.avg_loss - 80 / 3 * 2) < 1e-6  # (50+80+30)/3 = 53.33
    assert report.long_win_rate == 2 / 4
    assert report.short_win_rate == 1 / 2

    # 按 symbol 分组
    by_symbol = analytics.analyze_by_symbol(trades)
    assert "AAPL" in by_symbol
    assert "BTCUSDT" in by_symbol
    logger.info(f"by_symbol: {list(by_symbol.keys())}")

    # 按 side 分组
    by_side = analytics.analyze_by_side(trades)
    assert "LONG" in by_side
    assert "SHORT" in by_side
    logger.info(f"by_side: {list(by_side.keys())}")

    logger.info("✓ Trade Analytics OK")


# ------------------------------------------------------------------
# Test 2: Execution Analytics
# ------------------------------------------------------------------

def test_execution_analytics() -> None:
    banner("Test 2: Execution Analytics")
    from quantlab.observe import ExecutionAnalytics

    analytics = ExecutionAnalytics()

    # 完整流程
    analytics.record(
        trace_id="t001",
        signal_time="2024-01-15T10:00:00",
        order_time="2024-01-15T10:00:02",
        fill_time="2024-01-15T10:00:05",
    )
    # 只有 signal
    analytics.record(
        trace_id="t002",
        signal_time="2024-01-15T10:01:00",
    )
    # signal + order 没 fill
    analytics.record(
        trace_id="t003",
        signal_time="2024-01-15T10:02:00",
        order_time="2024-01-15T10:02:03",
    )

    report = analytics.report()
    logger.info(f"n_records: {report.n_records}")
    logger.info(f"n_complete: {report.n_complete}")
    logger.info(f"n_signal_only: {report.n_signal_only}")
    logger.info(f"n_order_no_fill: {report.n_order_no_fill}")
    logger.info(f"signal_latency_mean: {report.signal_latency_mean:.2f}s")
    logger.info(f"order_latency_mean: {report.order_latency_mean:.2f}s")
    logger.info(f"fill_latency_mean: {report.fill_latency_mean:.2f}s")

    assert report.n_records == 3
    assert report.n_complete == 1
    assert report.n_signal_only == 1
    assert report.n_order_no_fill == 1
    # signal_latency: t001=2s, t003=3s → mean=2.5s
    assert abs(report.signal_latency_mean - 2.5) < 1e-6
    assert abs(report.order_latency_mean - 3.0) < 1e-6
    assert abs(report.fill_latency_mean - 5.0) < 1e-6

    # 查询
    rec = analytics.get("t001")
    assert rec is not None
    assert rec.signal_latency == 2.0
    assert rec.order_latency == 3.0
    assert rec.fill_latency == 5.0

    logger.info("✓ Execution Analytics OK")


# ------------------------------------------------------------------
# Test 3: Event Timeline
# ------------------------------------------------------------------

def test_timeline() -> None:
    banner("Test 3: Event Timeline")
    from quantlab.monitoring import EventTracer
    from quantlab.observe import TimelineView

    tracer = EventTracer(log_to_file=False)

    # 模拟一笔交易
    tid1 = tracer.begin(label="BTC_BUY")
    tracer.span(tid1, "MARKET", symbol="BTCUSDT", price=50000)
    tracer.span(tid1, "SIGNAL", side="BUY", symbol="BTCUSDT", strength=0.85)
    tracer.span(tid1, "ORDER", symbol="BTCUSDT", qty=0.5)
    tracer.span(tid1, "FILL", symbol="BTCUSDT", price=50001, qty=0.5)
    tracer.end(tid1)

    # 模拟另一笔（未成交）
    tid2 = tracer.begin(label="ETH_SELL")
    tracer.span(tid2, "MARKET", symbol="ETHUSDT", price=3000)
    tracer.span(tid2, "SIGNAL", side="SELL", symbol="ETHUSDT", strength=0.6)
    tracer.span(tid2, "ORDER", symbol="ETHUSDT", qty=2.0)
    tracer.end(tid2)

    view = TimelineView(tracer)

    # 全部时间线
    timeline = view.get_timeline(limit=100)
    logger.info(f"timeline entries: {len(timeline)}")
    assert len(timeline) >= 10  # 2 begin + 8 span

    # 按分类过滤
    fills = view.get_timeline(category="fill")
    logger.info(f"fill entries: {len(fills)}")
    assert len(fills) == 1

    signals = view.get_timeline(category="signal")
    logger.info(f"signal entries: {len(signals)}")
    assert len(signals) == 2

    # 按 trace 过滤
    t1_entries = view.get_timeline(trace_id=tid1)
    logger.info(f"trace {tid1} entries: {len(t1_entries)}")
    assert len(t1_entries) >= 5

    # trace 列表
    traces = view.list_traces()
    logger.info(f"traces: {len(traces)}")
    assert len(traces) == 2

    # 单个 trace 详情
    summary = view.get_by_trace(tid1)
    assert summary is not None
    logger.info(f"trace1 status: {summary.status}")
    logger.info(f"trace1 summary: {summary.summary}")
    assert summary.status == "complete"

    summary2 = view.get_by_trace(tid2)
    assert summary2 is not None
    assert summary2.status == "partial"  # 下了单没成交

    # 统计
    stats = view.stats()
    logger.info(f"stats: {stats}")
    assert stats["n_traces"] == 2

    logger.info("✓ Event Timeline OK")


# ------------------------------------------------------------------
# Test 4: Strategy Health
# ------------------------------------------------------------------

def test_health() -> None:
    banner("Test 4: Strategy Health")
    from quantlab.observe import (
        StrategyHealthMonitor,
        HealthConfig,
        HealthStatus,
    )

    config = HealthConfig(
        window_hours=24,
        min_signals_24h=1,
        max_loss_24h=-1000.0,
        stalled_hours=6.0,
        min_fill_rate=0.1,
    )
    monitor = StrategyHealthMonitor(config=config)

    # 健康策略
    now = datetime.now()
    for i in range(5):
        monitor.record_signal(
            "rsi_strategy",
            timestamp=now - timedelta(hours=2, minutes=i),
        )
    for i in range(4):
        monitor.record_fill(
            "rsi_strategy",
            pnl=100 if i % 2 == 0 else -50,
            timestamp=now - timedelta(hours=2, minutes=i),
        )

    # 停摆策略（长时间无信号）
    monitor.record_signal(
        "stalled_strategy",
        timestamp=now - timedelta(hours=10),
    )

    # 有信号无成交
    for i in range(3):
        monitor.record_signal(
            "no_fill_strategy",
            timestamp=now - timedelta(minutes=30 + i * 10),
        )

    # 亏损策略
    monitor.record_signal("losing_strategy", timestamp=now - timedelta(minutes=30))
    monitor.record_fill("losing_strategy", pnl=-1500, timestamp=now - timedelta(minutes=25))

    # 查询
    health_rsi = monitor.get_health("rsi_strategy")
    logger.info(f"rsi_strategy: status={health_rsi.status.value}, "
                f"signals={health_rsi.signals_24h}, fills={health_rsi.fills_24h}, "
                f"pnl={health_rsi.pnl_24h}")
    assert health_rsi.status == HealthStatus.HEALTHY
    assert health_rsi.signals_24h == 5
    assert health_rsi.fills_24h == 4
    assert abs(health_rsi.pnl_24h - (100 * 2 - 50 * 2)) < 1e-6

    health_stalled = monitor.get_health("stalled_strategy")
    logger.info(f"stalled_strategy: status={health_stalled.status.value}")
    assert health_stalled.status == HealthStatus.STALLED

    health_no_fill = monitor.get_health("no_fill_strategy")
    logger.info(f"no_fill_strategy: status={health_no_fill.status.value}")
    assert health_no_fill.status == HealthStatus.NO_FILLS

    health_losing = monitor.get_health("losing_strategy")
    logger.info(f"losing_strategy: status={health_losing.status.value}, pnl={health_losing.pnl_24h}")
    assert health_losing.status == HealthStatus.LOSING

    # 全局统计
    stats = monitor.stats()
    logger.info(f"stats: {stats}")
    assert stats["n_strategies"] == 4

    # 停止策略
    monitor.record_stop("rsi_strategy", reason="manual stop")
    health_stopped = monitor.get_health("rsi_strategy")
    assert health_stopped.status == HealthStatus.STOPPED

    logger.info("✓ Strategy Health OK")


# ------------------------------------------------------------------
# Test 5: Drift Detection
# ------------------------------------------------------------------

def test_drift() -> None:
    banner("Test 5: Drift Detection")
    from quantlab.observe import DriftDetector, DriftConfig

    detector = DriftDetector(DriftConfig(method="psi"))

    # 基线：正态分布
    np.random.seed(42)
    baseline = np.random.normal(50, 10, 1000)
    detector.set_baseline("rsi_14", baseline)

    # 当前数据 1：相同分布 → 不应漂移
    current_no_drift = np.random.normal(50, 10, 1000)
    result1 = detector.detect("rsi_14", current_no_drift)
    logger.info(f"no drift: score={result1.score:.4f}, drifted={result1.drifted}")
    assert not result1.drifted

    # 当前数据 2：均值偏移 → 应漂移
    current_drifted = np.random.normal(70, 10, 1000)  # 均值从 50 → 70
    result2 = detector.detect("rsi_14", current_drifted)
    logger.info(f"drifted: score={result2.score:.4f}, drifted={result2.drifted}")
    assert result2.drifted

    # mean_std 方法
    result3 = detector.detect("rsi_14", current_drifted, method="mean_std")
    logger.info(f"mean_std: score={result3.score:.4f}, drifted={result3.drifted}")
    assert result3.drifted

    # KS 方法（需要 scipy）
    try:
        result4 = detector.detect("rsi_14", current_drifted, method="ks")
        logger.info(f"ks: score={result4.score:.4f}, pvalue={result4.details.get('pvalue')}, drifted={result4.drifted}")
        assert result4.drifted
    except ImportError:
        logger.info("scipy not available, skipping KS test")

    # 批量检测
    results = detector.detect_all({
        "rsi_14": current_drifted,
        "unknown_feature": current_drifted,  # 没基线
    })
    logger.info(f"batch detect: {len(results)} results")
    assert len(results) == 1  # 只有 rsi_14 有基线

    # 统计
    stats = detector.stats()
    logger.info(f"stats: {stats}")
    assert stats["n_baselines"] == 1

    # 删除基线
    ok = detector.remove_baseline("rsi_14")
    assert ok
    assert len(detector.list_baselines()) == 0

    logger.info("✓ Drift Detection OK")


# ------------------------------------------------------------------
# Test 6: Observe API
# ------------------------------------------------------------------

def test_observe_api() -> None:
    banner("Test 6: Observe API")
    try:
        from fastapi.testclient import TestClient
        from quantlab.api.app import app
    except ImportError as e:
        logger.warning(f"fastapi/httpx not available, skipping API test: {e}")
        return

    client = TestClient(app)

    # 1. Trade Analytics
    resp = client.post("/api/v1/observe/trade-analytics", json=[
        {"pnl": 100, "side": "LONG", "symbol": "AAPL"},
        {"pnl": -50, "side": "LONG", "symbol": "AAPL"},
        {"pnl": 200, "side": "SHORT", "symbol": "BTCUSDT"},
    ])
    logger.info(f"POST /trade-analytics: {resp.status_code}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["n_trades"] == 3
    assert data["n_wins"] == 2
    logger.info(f"  profit_factor: {data['profit_factor']}")

    # 2. Execution Analytics
    resp = client.post("/api/v1/observe/execution-analytics", json={
        "trace_id": "api_t001",
        "signal_time": "2024-01-15T10:00:00",
        "order_time": "2024-01-15T10:00:02",
        "fill_time": "2024-01-15T10:00:05",
    })
    assert resp.status_code == 200
    logger.info(f"POST /execution-analytics: {resp.status_code}")

    resp = client.get("/api/v1/observe/execution-analytics")
    assert resp.status_code == 200
    data = resp.json()
    logger.info(f"GET /execution-analytics: n_records={data['n_records']}")
    assert data["n_records"] == 1
    assert data["n_complete"] == 1

    # 3. Timeline stats
    resp = client.get("/api/v1/observe/timeline/stats")
    assert resp.status_code == 200
    logger.info(f"GET /timeline/stats: {resp.json()}")

    # 4. Health
    resp = client.post("/api/v1/observe/health/rsi_strategy/signal", json={})
    assert resp.status_code == 200
    logger.info(f"POST /health/rsi_strategy/signal: {resp.status_code}")

    resp = client.post("/api/v1/observe/health/rsi_strategy/fill", json={"pnl": 100})
    assert resp.status_code == 200

    resp = client.get("/api/v1/observe/health/rsi_strategy")
    assert resp.status_code == 200
    data = resp.json()
    logger.info(f"GET /health/rsi_strategy: status={data['status']}, signals={data['signals_24h']}")
    assert data["signals_24h"] == 1
    assert data["fills_24h"] == 1

    resp = client.get("/api/v1/observe/health")
    assert resp.status_code == 200
    data = resp.json()
    logger.info(f"GET /health: {len(data)} strategies")
    assert len(data) >= 1

    # 5. Drift
    np.random.seed(42)
    baseline = np.random.normal(50, 10, 500).tolist()
    resp = client.post("/api/v1/observe/drift/baselines/rsi_14", json={"values": baseline})
    assert resp.status_code == 200
    logger.info(f"POST /drift/baselines/rsi_14: {resp.status_code}")

    resp = client.get("/api/v1/observe/drift/baselines")
    assert resp.status_code == 200
    data = resp.json()
    logger.info(f"GET /drift/baselines: {data}")
    assert data["n_baselines"] == 1

    # 检测漂移
    drifted = np.random.normal(70, 10, 500).tolist()
    resp = client.post("/api/v1/observe/drift/detect/rsi_14", json={"values": drifted})
    assert resp.status_code == 200
    data = resp.json()
    logger.info(f"POST /drift/detect/rsi_14: score={data['score']:.4f}, drifted={data['drifted']}")
    assert data["drifted"]

    # 6. Global stats
    resp = client.get("/api/v1/observe/stats")
    assert resp.status_code == 200
    data = resp.json()
    logger.info(f"GET /stats: keys={list(data.keys())}")
    assert "execution_analytics" in data
    assert "health" in data
    assert "drift" in data

    logger.info("✓ Observe API OK")


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main() -> int:
    tests = [
        ("Trade Analytics", test_trade_analytics),
        ("Execution Analytics", test_execution_analytics),
        ("Event Timeline", test_timeline),
        ("Strategy Health", test_health),
        ("Drift Detection", test_drift),
        ("Observe API", test_observe_api),
    ]

    passed = 0
    failed = 0

    for name, fn in tests:
        try:
            fn()
            passed += 1
        except Exception as e:
            failed += 1
            logger.error(f"✗ {name} FAILED: {e}", exc_info=True)

    logger.info("=" * 60)
    logger.info(f"Results: {passed} passed, {failed} failed")
    logger.info("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
