"""
SignalStrategy 基类单元测试
=========================

验证:
    - 必须实现 signal() 才能实例化
    - params() 序列化
    - 子类正常工作
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.context import FactorContext
from quantlab.signals.base import SignalStrategy


def _make_ctx(n=5, symbols=None):
    symbols = symbols or ["A", "B"]
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    rng = np.random.default_rng(1)
    data = {}
    for sym in symbols:
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


def test_cannot_instantiate_abstract():
    with pytest.raises(TypeError):
        SignalStrategy()  # type: ignore[abstract]


class _Dummy(SignalStrategy):
    def __init__(self, period: int = 5, name: str = "dummy"):
        self.period = period
        self.name = name

    def signal(self, ctx):
        return ctx.close


def test_subclass_works():
    s = _Dummy(period=3)
    ctx = _make_ctx()
    df = s.signal(ctx)
    assert df.shape == (5, 2)


def test_params_serializable():
    s = _Dummy(period=10, name="x")
    p = s.params()
    assert p == {"period": 10, "name": "x"}


def test_params_excludes_non_serializable():
    class _WithDF(SignalStrategy):
        def __init__(self):
            self.n = 5
            self.df = pd.DataFrame({"a": [1, 2]})  # 不可序列化

        def signal(self, ctx):
            return ctx.close

    s = _WithDF()
    p = s.params()
    assert p == {"n": 5}  # df 被过滤


def test_repr():
    s = _Dummy(period=7, name="abc")
    assert "_Dummy" in repr(s)
    assert "7" in repr(s)
