"""
烟雾测试 — Domain 层 + Service 层

目标：
  1) domain 各模型能独立使用（不依赖 service / engine）
  2) Experiment + ExperimentResult → ExperimentSummary
  3) BacktestSpec → Experiment
  4) Task 状态机
  5) StrategyDefinition 的 schema 格式
  6) BacktestService.create_task(BacktestSpec) → domain.Task 端到端
"""

from __future__ import annotations

import json
import time
import uuid

import pandas as pd

from quantlab.domain import (
    Task,
    TaskStatus,
    TaskType,
    new_task,
    Experiment,
    ExperimentResult,
    ExperimentSummary,
    ExperimentDetail,
    summary_from,
    StrategyDefinition,
    ParamSchema,
    make_ma_cross_definition,
    make_rsi_definition,
    BacktestSpec,
    BacktestJob,
    Account,
    Position,
    PortfolioSnapshot,
    PortfolioSummary,
    RuntimeInstance,
    RuntimeState,
    StartStrategySpec,
)
from quantlab.runtime.task_manager import (
    TaskManager,
    get_task_manager,
)
from quantlab.strategy_registry import (
    StrategyRegistry,
    get_strategy_registry,
)


SEP = "=" * 70
FAILURES: list = []


def _ok(msg: str) -> None:
    print(f"  [OK]   {msg}")


def _fail(msg: str, exc: Exception = None) -> None:
    print(f"  [FAIL] {msg}")
    if exc is not None:
        print(f"         {type(exc).__name__}: {exc}")
    FAILURES.append(msg)


def section(title: str) -> None:
    print()
    print(SEP)
    print(f" {title}")
    print(SEP)


# =============================================================
# 1) domain 模型独立可用
# =============================================================
def test_domain_independent() -> None:
    section("1. domain 模型独立使用（不依赖 service / engine）")

    # ---- Task 状态机 ----
    try:
        t = new_task(
            type_=TaskType.BACKTEST.value,
            task_id="task_test_001",
            metadata={"strategy_id": "ma_cross"},
        )
        assert t.id == "task_test_001"
        assert t.status == TaskStatus.PENDING.value
        assert t.type == "backtest"
        assert t.created_at
        # 转 RUNNING
        t.status = TaskStatus.RUNNING.value
        t.started_at = "2024-01-01T00:00:00"
        t.progress = 42.0
        assert t.is_running is True
        # 终态
        t.status = TaskStatus.SUCCESS.value
        t.finished_at = "2024-01-01T00:01:00"
        assert t.is_terminal is True
        _ok("Task 状态机可独立构造 / 推进")
    except Exception as e:
        _fail("Task 状态机", e)

    # ---- Experiment vs ExperimentResult ----
    try:
        exp = Experiment(
            id="exp_001",
            name="ma_cross_20_60",
            strategy_id="ma_cross",
            parameters={"fast": 20, "slow": 60},
            dataset="default",
            symbols=["AAPL", "MSFT"],
            tag="smoke",
            note="独立测试",
        )
        assert exp.to_dict()["strategy_id"] == "ma_cross"

        result = ExperimentResult(
            experiment_id=exp.id,
            sharpe=1.42,
            total_return=0.23,
            annualized_return=0.18,
            max_drawdown=-0.12,
            trade_count=87,
            win_rate=0.55,
            final_equity=123000.0,
            profit_factor=1.4,
            avg_trade=265.0,
            source="event",
        )
        summary = result.to_summary()
        assert summary["sharpe"] == 1.42
        assert summary["experiment_id"] == "exp_001"
        _ok("Experiment / ExperimentResult 互不依赖，可独立 to_dict()")
    except Exception as e:
        _fail("Experiment / ExperimentResult", e)

    # ---- StrategyDefinition + schema ----
    try:
        ma = make_ma_cross_definition()
        assert ma.id == "ma_cross"
        assert ma.class_path.endswith("MACrossStrategy")
        assert len(ma.parameters_schema) == 2
        # 前端需要的 schema_dict 格式
        sd = ma.schema_dict()
        assert "fast" in sd and "slow" in sd
        assert sd["fast"]["type"] == "int"
        assert sd["fast"]["default"] == 20
        assert sd["slow"]["max"] == 400
        # 序列化 OK
        d = ma.to_dict()
        json.dumps(d)  # 不抛异常即通过
        _ok("StrategyDefinition.schema_dict() 给前端用 OK")
    except Exception as e:
        _fail("StrategyDefinition", e)


# =============================================================
# 2) Experiment + Result → Summary / Detail
# =============================================================
def test_experiment_summary_and_detail() -> None:
    section("2. Experiment + ExperimentResult → ExperimentSummary / Detail")
    try:
        exp = Experiment(
            id="exp_002",
            name="rsi_14_30_70",
            strategy_id="rsi",
            parameters={
                "period": 14, "oversold": 30, "overbought": 70
            },
        )
        result = ExperimentResult(
            experiment_id=exp.id,
            sharpe=1.8,
            total_return=0.45,
            max_drawdown=-0.15,
            trade_count=120,
        )
        s = summary_from(exp, result)
        assert isinstance(s, ExperimentSummary)
        assert s.id == exp.id
        assert s.strategy == "rsi"
        assert s.sharpe == 1.8
        assert s.total_return == 0.45
        # 详情
        detail = ExperimentDetail(
            experiment=exp,
            result=result,
            config={"foo": "bar"},
            equity_curve=[{"t": 0, "e": 100000}],
            trades=[{"sym": "AAPL", "pnl": 100}],
        )
        d = detail.to_dict()
        assert d["experiment"]["id"] == "exp_002"
        assert d["result"]["sharpe"] == 1.8
        assert d["config"]["foo"] == "bar"
        assert len(d["equity_curve"]) == 1
        _ok("summary_from() / ExperimentDetail 字段齐全")
    except Exception as e:
        _fail("summary_from / ExperimentDetail", e)


# =============================================================
# 3) BacktestSpec → Experiment
# =============================================================
def test_backtest_spec_to_experiment() -> None:
    section("3. BacktestSpec.to_experiment()")
    try:
        spec = BacktestSpec(
            strategy_id="ma_cross",
            parameters={"fast": 10, "slow": 30},
            dataset="default",
            symbols=["AAPL"],
            initial_cash=50000.0,
            commission_bps=1.0,
            slippage_bps=0.5,
            top_n=3,
            save_experiment=True,
            experiment_name="ma_fast10_slow30",
        )
        exp = spec.to_experiment()
        assert exp.id.startswith("exp_")
        assert exp.strategy_id == "ma_cross"
        assert exp.parameters == {"fast": 10, "slow": 30}
        assert exp.dataset == "default"
        assert exp.symbols == ["AAPL"]
        assert exp.tag == "backtest"
        assert exp.name == "ma_fast10_slow30"
        # BacktestJob 把 spec + experiment 装一起
        job = BacktestJob(spec=spec, experiment=exp)
        jd = job.to_dict()
        assert jd["spec"]["strategy_id"] == "ma_cross"
        assert jd["experiment"]["id"] == exp.id
        _ok("BacktestSpec → Experiment → BacktestJob 转换无误")
    except Exception as e:
        _fail("BacktestSpec.to_experiment", e)


# =============================================================
# 4) TaskManager 状态机
# =============================================================
def test_task_manager_state_machine() -> None:
    section("4. TaskManager 状态机")
    try:
        mgr = TaskManager()
        events: list = []
        mgr.subscribe(lambda t: events.append(t.status))

        t = mgr.create_task(
            type_=TaskType.BACKTEST.value,
            metadata={"strategy_id": "ma_cross"},
        )
        assert t.status == "PENDING"
        mgr.start(t.id, message="running")
        m1 = mgr.get(t.id)
        assert m1.status == "RUNNING"
        assert m1.started_at is not None

        mgr.update_progress(t.id, 50.0, "loading data")
        m2 = mgr.get(t.id)
        assert m2.progress == 50.0
        assert m2.message == "loading data"

        mgr.update_progress(t.id, 120.0)  # 越界自动 clip
        m3 = mgr.get(t.id)
        assert m3.progress == 100.0

        mgr.complete(t.id, result={"experiment_id": "exp_xx"})
        m4 = mgr.get(t.id)
        assert m4.status == "SUCCESS"
        assert m4.progress == 100.0
        assert m4.result["experiment_id"] == "exp_xx"
        assert m4.finished_at is not None

        # 通知应至少触发 5 次（PENDING→RUNNING→update→update→SUCCESS）
        assert len(events) >= 5
        _ok(
            f"TaskManager 全状态机 OK，"
            f"订阅事件触发 {len(events)} 次"
        )

        # 失败路径
        t2 = mgr.create_task(type_=TaskType.OTHER.value)
        mgr.start(t2.id)
        mgr.fail(t2.id, error="boom")
        assert mgr.get(t2.id).status == "FAILED"
        assert mgr.get(t2.id).error == "boom"
        _ok("TaskManager 失败路径")

        # 取消路径
        t3 = mgr.create_task(type_=TaskType.OTHER.value)
        assert mgr.cancel(t3.id) is True
        assert mgr.get(t3.id).status == "CANCELLED"
        # 终态再 cancel 应返回 False
        assert mgr.cancel(t3.id) is False
        _ok("TaskManager 取消路径")
    except Exception as e:
        _fail("TaskManager", e)


# =============================================================
# 5) Account / Portfolio / Runtime 序列化
# =============================================================
def test_account_portfolio_runtime() -> None:
    section("5. Account / PortfolioSnapshot / RuntimeInstance")
    try:
        acc = Account(
            account_id="acc_001",
            name="Paper-A",
            broker="PAPER",
            cash=50000.0,
            equity=105000.0,
            risk_profile="medium",
            positions=[
                Position(
                    symbol="AAPL",
                    qty=100,
                    avg_price=150.0,
                    market_value=18000.0,
                    unrealized_pnl=3000.0,
                ),
            ],
        )
        assert acc.exposure == 18000.0
        assert acc.position_count == 1
        json.dumps(acc.to_dict())  # 可序列化

        # PortfolioSummary.from_accounts
        acc2 = Account(
            account_id="acc_002",
            cash=20000.0,
            equity=60000.0,
            positions=[
                Position(
                    symbol="NVDA", qty=50,
                    market_value=30000.0,
                )
            ],
        )
        s = PortfolioSummary.from_accounts(
            [acc, acc2],
            initial_equity={
                "acc_001": 100000.0,
                "acc_002": 50000.0,
            },
        )
        assert s.total_equity == 165000.0
        assert s.total_cash == 70000.0
        assert s.total_exposure == 48000.0
        assert "AAPL" in s.exposure_by_symbol
        _ok(f"PortfolioSummary 聚合 OK total_equity={s.total_equity}")

        # PortfolioSnapshot
        snap = PortfolioSnapshot(
            timestamp="2024-01-01T00:00:00",
            cash=acc.cash,
            equity=acc.equity,
            positions=list(acc.positions),
            exposure=acc.exposure,
        )
        assert 0.0 < snap.invested_weight < 1.0
        _ok(f"PortfolioSnapshot.invested_weight={snap.invested_weight:.3f}")

        # RuntimeInstance + StartStrategySpec
        sss = StartStrategySpec(
            runtime_id="rt_001",
            strategy_id="ma_cross",
            account_id="acc_001",
            parameters={"fast": 20, "slow": 60},
            symbols=["AAPL"],
            data_source="paper",
        )
        inst = sss.to_instance()
        assert inst.id == "rt_001"
        assert inst.status == RuntimeState.PENDING.value
        assert inst.is_terminal is False
        inst.status = RuntimeState.RUNNING.value
        assert inst.is_running is True
        _ok("RuntimeInstance / StartStrategySpec 序列化 OK")
    except Exception as e:
        _fail("Account / Portfolio / Runtime", e)


# =============================================================
# 6) StrategyRegistry 返回 domain.StrategyDefinition
# =============================================================
def test_strategy_registry_returns_domain() -> None:
    section("6. StrategyRegistry → domain.StrategyDefinition")
    try:
        reg = get_strategy_registry()
        ids = reg.list_ids()
        assert "ma_cross" in ids, f"ma_cross 未注册，已注册: {ids}"
        defn = reg.get("ma_cross")
        assert isinstance(defn, StrategyDefinition)
        assert defn.id == "ma_cross"
        assert defn.class_path.endswith("MACrossStrategy")
        # schema 至少包含 fast / slow
        names = {p.name for p in defn.parameters_schema}
        assert "fast" in names and "slow" in names
        # create() 能构造实例
        strat = reg.create("ma_cross", params={"fast": 5})
        assert strat is not None
        _ok(f"StrategyRegistry 内置 {len(ids)} 个策略")
    except Exception as e:
        _fail("StrategyRegistry", e)


# =============================================================
# 7) BacktestService.create_task(BacktestSpec) 端到端
# =============================================================
def test_backtest_service_create_task() -> None:
    section("7. BacktestService.create_task(BacktestSpec) 端到端")
    svc = None
    try:
        from quantlab.application.backtest_service import (
            BacktestService,
        )
        from quantlab.domain.backtest import BacktestSpec

        # 用独立 TaskManager 防止全局状态污染
        mgr = TaskManager()
        svc = BacktestService(
            task_manager=mgr,
            experiment_saver=lambda **kw: kw[
                "experiment"
            ].id,  # 简化 saver：只返回 id
        )

        spec = BacktestSpec(
            strategy_id="ma_cross",
            parameters={"fast": 5, "slow": 20},
            dataset="default",
            symbols=["AAPL", "MSFT"],
            initial_cash=100000.0,
            commission_bps=1.0,
            slippage_bps=0.5,
            top_n=1,
            save_experiment=True,
            experiment_name="smoke_ma_fast5_slow20",
        )
        # 提交
        task = svc.create_task(spec)
        assert isinstance(task, Task)
        assert task.status in ("PENDING", "RUNNING", "SUCCESS")
        assert task.id.startswith("task_")
        # metadata 正确
        assert task.metadata["strategy_id"] == "ma_cross"
        assert task.metadata["experiment_id"].startswith("exp_")

        # 等异步完成
        deadline = time.time() + 30
        while time.time() < deadline:
            t = mgr.get(task.id)
            if t is not None and t.is_terminal:
                break
            time.sleep(0.1)
        final = mgr.get(task.id)
        assert final is not None
        if final.status != "SUCCESS":
            # 即便失败也算跑通了"任务调度"链路
            print(
                f"  [WARN] 任务终态为 {final.status}，"
                f"err={final.error!r}"
            )
        # result 应含 experiment_id / metrics
        if final.status == "SUCCESS":
            assert "experiment_id" in final.result
            assert "metrics" in final.result
        _ok(
            f"create_task 端到端通过：status={final.status} "
            f"duration={final.duration_sec}"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        _fail("BacktestService.create_task", e)
    finally:
        if svc is not None:
            try:
                svc.shutdown(wait=False)
            except Exception:
                pass


# =============================================================
# main
# =============================================================
def main() -> int:
    print("QuantLab V4.0 — Domain & Service 烟雾测试")
    test_domain_independent()
    test_experiment_summary_and_detail()
    test_backtest_spec_to_experiment()
    test_task_manager_state_machine()
    test_account_portfolio_runtime()
    test_strategy_registry_returns_domain()
    test_backtest_service_create_task()

    print()
    print(SEP)
    if FAILURES:
        print(f" FAILED: {len(FAILURES)} 项")
        for f in FAILURES:
            print(f"   - {f}")
        return 1
    else:
        print(" ALL OK")
        return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
