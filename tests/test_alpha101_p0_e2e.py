"""
Alpha101 P0 因子批量端到端回测验证
==================================

对已实现的 38 个 Alpha101 P0 因子做历史回测，
验证因子 → 策略 → TopN → BarEngine → Report 链路跑通。
长窗口因子 (200/250 日) 使用 300 日数据覆盖。
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.engine import BarEngine
from quantlab.factors.alpha101 import (
    alpha_004, alpha_006, alpha_008, alpha_009, alpha_010, alpha_012,
    alpha_019, alpha_020, alpha_022, alpha_023, alpha_024, alpha_025,
    alpha_026, alpha_027, alpha_028, alpha_029, alpha_030, alpha_031,
    alpha_032, alpha_033, alpha_034, alpha_035, alpha_036, alpha_037,
    alpha_038, alpha_039, alpha_040, alpha_041, alpha_042, alpha_043,
    alpha_044, alpha_045, alpha_046, alpha_047, alpha_049, alpha_051,
    alpha_053, alpha_055,
)
from quantlab.factors.alpha101 import (
    ALPHA004_DIRECTION, ALPHA006_DIRECTION, ALPHA008_DIRECTION,
    ALPHA009_DIRECTION, ALPHA010_DIRECTION, ALPHA012_DIRECTION,
    ALPHA019_DIRECTION, ALPHA020_DIRECTION, ALPHA022_DIRECTION,
    ALPHA023_DIRECTION, ALPHA024_DIRECTION, ALPHA025_DIRECTION,
    ALPHA026_DIRECTION, ALPHA027_DIRECTION, ALPHA028_DIRECTION,
    ALPHA029_DIRECTION, ALPHA030_DIRECTION, ALPHA031_DIRECTION,
    ALPHA032_DIRECTION, ALPHA033_DIRECTION, ALPHA034_DIRECTION,
    ALPHA035_DIRECTION, ALPHA036_DIRECTION, ALPHA037_DIRECTION,
    ALPHA038_DIRECTION, ALPHA039_DIRECTION, ALPHA040_DIRECTION,
    ALPHA041_DIRECTION, ALPHA042_DIRECTION, ALPHA043_DIRECTION,
    ALPHA044_DIRECTION, ALPHA045_DIRECTION, ALPHA046_DIRECTION,
    ALPHA047_DIRECTION, ALPHA049_DIRECTION, ALPHA051_DIRECTION,
    ALPHA053_DIRECTION, ALPHA055_DIRECTION,
)
from quantlab.factors.context import FactorContext
from quantlab.portfolio_construction import TopN
from quantlab.research import Report
from quantlab.signals.base import SignalStrategy


def _make_ctx(n=300):
    """合成数据 (5 标的 × 300 日)，覆盖长窗口因子预热期 (≤270 日)。"""
    dates = pd.date_range("2025-01-02", periods=n, freq="B")
    t = np.arange(n)
    rng = np.random.default_rng(42)
    data = {}
    syms = ["A", "B", "C", "D", "E"]
    base = {
        "A": 100 + t * 0.3,
        "B": 100 - t * 0.2,
        "C": 100 + 4 * np.sin(t / 4),
        "D": 100 + 2 * np.cos(t / 6),
        "E": 100 + t * 0.1 + np.sin(t / 3),
    }
    for sym in syms:
        closes = (base[sym] + rng.normal(0, 1, n)).astype(float)
        vols = rng.integers(1000, 10000, n).astype(float)
        df = pd.DataFrame(
            {
                "open": closes + rng.normal(0, 0.5, n),
                "high": closes + np.abs(rng.normal(0, 1, n)),
                "low": closes - np.abs(rng.normal(0, 1, n)),
                "close": closes,
                "volume": vols,
                "amount": closes * vols,
                "vwap": closes + rng.normal(0, 0.3, n),
            },
            index=dates,
        )
        data[sym] = df
    return FactorContext.from_dict(data)


# 因子列表: (name, func, direction)
FACTORS = [
    ("alpha_004", alpha_004, ALPHA004_DIRECTION),
    ("alpha_006", alpha_006, ALPHA006_DIRECTION),
    ("alpha_008", alpha_008, ALPHA008_DIRECTION),
    ("alpha_009", alpha_009, ALPHA009_DIRECTION),
    ("alpha_010", alpha_010, ALPHA010_DIRECTION),
    ("alpha_012", alpha_012, ALPHA012_DIRECTION),
    ("alpha_019", alpha_019, ALPHA019_DIRECTION),
    ("alpha_020", alpha_020, ALPHA020_DIRECTION),
    ("alpha_022", alpha_022, ALPHA022_DIRECTION),
    ("alpha_023", alpha_023, ALPHA023_DIRECTION),
    ("alpha_024", alpha_024, ALPHA024_DIRECTION),
    ("alpha_025", alpha_025, ALPHA025_DIRECTION),
    ("alpha_026", alpha_026, ALPHA026_DIRECTION),
    ("alpha_027", alpha_027, ALPHA027_DIRECTION),
    ("alpha_028", alpha_028, ALPHA028_DIRECTION),
    ("alpha_029", alpha_029, ALPHA029_DIRECTION),
    ("alpha_030", alpha_030, ALPHA030_DIRECTION),
    ("alpha_031", alpha_031, ALPHA031_DIRECTION),
    ("alpha_032", alpha_032, ALPHA032_DIRECTION),
    ("alpha_033", alpha_033, ALPHA033_DIRECTION),
    ("alpha_034", alpha_034, ALPHA034_DIRECTION),
    ("alpha_035", alpha_035, ALPHA035_DIRECTION),
    ("alpha_036", alpha_036, ALPHA036_DIRECTION),
    ("alpha_037", alpha_037, ALPHA037_DIRECTION),
    ("alpha_038", alpha_038, ALPHA038_DIRECTION),
    ("alpha_039", alpha_039, ALPHA039_DIRECTION),
    ("alpha_040", alpha_040, ALPHA040_DIRECTION),
    ("alpha_041", alpha_041, ALPHA041_DIRECTION),
    ("alpha_042", alpha_042, ALPHA042_DIRECTION),
    ("alpha_043", alpha_043, ALPHA043_DIRECTION),
    ("alpha_044", alpha_044, ALPHA044_DIRECTION),
    ("alpha_045", alpha_045, ALPHA045_DIRECTION),
    ("alpha_046", alpha_046, ALPHA046_DIRECTION),
    ("alpha_047", alpha_047, ALPHA047_DIRECTION),
    ("alpha_049", alpha_049, ALPHA049_DIRECTION),
    ("alpha_051", alpha_051, ALPHA051_DIRECTION),
    ("alpha_053", alpha_053, ALPHA053_DIRECTION),
    ("alpha_055", alpha_055, ALPHA055_DIRECTION),
]


@pytest.mark.parametrize("name,func,direction", FACTORS)
def test_factor_e2e_backtest(name, func, direction):
    """每个因子都能跑通完整回测链路。"""
    ctx = _make_ctx(n=300)

    class _Strat(SignalStrategy):
        def signal(self, ctx):
            sig = func(ctx)
            return -sig if direction < 0 else sig

    engine = BarEngine(
        strategy=_Strat(),
        portfolio_constructor=TopN(n=1),
        initial_cash=100000.0,
    )
    result = engine.run(ctx)
    assert len(result.equity_curve) == 300
    assert (result.equity_curve > 0).all()
    m = Report(result).metrics()
    assert m["n_days"] == 300


def test_all_factors_signal_shapes_consistent():
    """所有因子输出形状与 ctx.close 一致。"""
    ctx = _make_ctx(n=300)
    for name, func, _ in FACTORS:
        sig = func(ctx)
        assert sig.shape == ctx.close.shape, f"{name} 形状不一致"
