"""
Experiment + Report 单元测试
============================
"""
import numpy as np
import pandas as pd

from quantlab.engine import BarEngine, BacktestResult
from quantlab.factors.context import FactorContext
from quantlab.portfolio_construction import TopN
from quantlab.research import Experiment, Report, ExperimentResult
from quantlab.signals.base import SignalStrategy


def _make_ctx(n=10):
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    rng = np.random.default_rng(0)
    data = {}
    for sym in ["A", "B", "C"]:
        data[sym] = pd.DataFrame(
            {
                "open": rng.uniform(90, 110, n),
                "high": rng.uniform(100, 120, n),
                "low": rng.uniform(80, 100, n),
                "close": rng.uniform(95, 115, n),
                "volume": rng.integers(1000, 10000, n).astype(float),
            },
            index=dates,
        )
    return FactorContext.from_dict(data)


class _ConstSig(SignalStrategy):
    def signal(self, ctx):
        return pd.DataFrame(
            {"A": 1.0, "B": 0.5, "C": 0.1}, index=ctx.dates,
        )


def test_experiment_run_returns_metrics():
    ctx = _make_ctx(10)
    exp = Experiment(name="t")
    res = exp.run(
        strategy=_ConstSig(),
        ctx=ctx,
        portfolio_constructor=TopN(n=1),
        params={"k": 1},
    )
    assert isinstance(res, ExperimentResult)
    assert res.name == "t"
    assert res.params == {"k": 1}
    m = res.metrics
    assert "sharpe" in m
    assert "max_drawdown" in m
    assert m["n_days"] == 10


def test_report_metrics_keys():
    ctx = _make_ctx(8)
    engine = BarEngine(_ConstSig(), TopN(n=1))
    bt = engine.run(ctx)
    m = Report(bt).metrics()
    expected = {
        "total_return", "annual_return", "annual_volatility",
        "sharpe", "max_drawdown", "n_days", "final_equity", "n_trades",
    }
    assert expected.issubset(m.keys())


def test_report_generate_has_content():
    ctx = _make_ctx(8)
    engine = BarEngine(_ConstSig(), TopN(n=1))
    bt = engine.run(ctx)
    txt = Report(bt).generate()
    assert "夏普比率" in txt
    assert "最大回撤" in txt


def test_report_empty_data():
    eq = pd.Series([], name="equity")
    bt = BacktestResult(
        equity_curve=eq,
        positions_history=pd.DataFrame(),
        target_weights=pd.DataFrame(),
    )
    m = Report(bt).metrics()
    assert m == {}
