"""
Alpha191 P0 因子批量端到端回测验证
==================================

对已实现的 9 个 Alpha191 P0 因子逐一做短历史回测，
验证因子 → 策略 → TopN → BarEngine → Report 链路跑通。
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.engine import BarEngine
from quantlab.factors.alpha191 import (
    alpha_014, alpha_015, alpha_054, alpha_070, alpha_095,
    alpha_097, alpha_100, alpha_118, alpha_127,
)
from quantlab.factors.context import FactorContext
from quantlab.portfolio_construction import TopN
from quantlab.research import Report
from quantlab.signals.base import SignalStrategy


def _make_ctx(n=60):
    """合成趋势+震荡数据，足够长的历史覆盖所有因子预热期。"""
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    t = np.arange(n)
    rng = np.random.default_rng(42)
    data = {}
    # A: 上涨趋势 + 噪声
    a_close = 100 + t * 0.5 + rng.normal(0, 1, n)
    # B: 下跌趋势 + 噪声
    b_close = 100 - t * 0.3 + rng.normal(0, 1, n)
    # C: 震荡
    c_close = 100 + 5 * np.sin(t / 5) + rng.normal(0, 0.5, n)
    for sym, closes in [("A", a_close), ("B", b_close), ("C", c_close)]:
        closes = closes.astype(float)
        data[sym] = pd.DataFrame(
            {
                "open": closes + rng.normal(0, 0.5, n),
                "high": closes + np.abs(rng.normal(0, 1, n)),
                "low": closes - np.abs(rng.normal(0, 1, n)),
                "close": closes,
                "volume": rng.integers(1000, 10000, n).astype(float),
                "amount": closes * rng.integers(1000, 10000, n).astype(float),
            },
            index=dates,
        )
    return FactorContext.from_dict(data)


class _FactorStrategy(SignalStrategy):
    """通用因子策略封装。"""
    def __init__(self, factor_func, **kwargs):
        self.factor_func = factor_func
        self.kwargs = kwargs

    def signal(self, ctx):
        return self.factor_func(ctx, **self.kwargs)


# 因子列表: (name, func, direction, period)
# direction: +1 正向(TopN 取大), -1 反向(TopN 取小→用 -signal)
FACTORS = [
    ("alpha_014", alpha_014, +1, {"period": 5}),
    ("alpha_015", alpha_015, +1, {"period": 1}),
    ("alpha_054", alpha_054, -1, {"period": 10}),
    ("alpha_070", alpha_070, +1, {"period": 6}),
    ("alpha_095", alpha_095, +1, {"period": 20}),
    ("alpha_097", alpha_097, +1, {"period": 10}),
    ("alpha_100", alpha_100, +1, {"period": 20}),
    ("alpha_118", alpha_118, +1, {"period": 20}),
    ("alpha_127", alpha_127, +1, {"period": 12}),
]


@pytest.mark.parametrize("name,func,direction,kwargs", FACTORS)
def test_factor_e2e_backtest(name, func, direction, kwargs):
    """每个因子都能跑通完整回测链路。"""
    ctx = _make_ctx(n=60)
    # 反向因子取负号，使 TopN 取大 = 选取因子值最小(最看好)的
    class _Strat(SignalStrategy):
        def signal(self, ctx):
            sig = func(ctx, **kwargs)
            return -sig if direction < 0 else sig
    engine = BarEngine(
        strategy=_Strat(),
        portfolio_constructor=TopN(n=1),
        initial_cash=100000.0,
    )
    result = engine.run(ctx)
    # 1. 净值曲线长度正确
    assert len(result.equity_curve) == 60
    # 2. 净值始终 > 0
    assert (result.equity_curve > 0).all()
    # 3. 报告可生成
    m = Report(result).metrics()
    assert m["n_days"] == 60
    # 4. 预热期后有交易
    assert m["n_trades"] > 0


def test_all_factors_signal_shapes_consistent():
    """所有因子输出形状与 ctx.close 一致。"""
    ctx = _make_ctx(n=60)
    for name, func, _, kwargs in FACTORS:
        sig = func(ctx, **kwargs)
        assert sig.shape == ctx.close.shape, f"{name} 形状不一致"
