"""
Alpha101 P0 因子单元测试 (批次5)
================================

覆盖: #8, #25, #26, #27, #28, #29, #30, #31, #35, #36, #37, #39, #43, #45, #47
含 adv20 解锁因子与长窗口因子。
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.alpha101 import (
    alpha_008, alpha_025, alpha_026, alpha_027, alpha_028, alpha_029,
    alpha_030, alpha_031, alpha_035, alpha_036, alpha_037, alpha_039,
    alpha_043, alpha_045, alpha_047,
    ALPHA008_DIRECTION, ALPHA025_DIRECTION, ALPHA026_DIRECTION,
    ALPHA027_DIRECTION, ALPHA028_DIRECTION, ALPHA029_DIRECTION,
    ALPHA030_DIRECTION, ALPHA031_DIRECTION, ALPHA035_DIRECTION,
    ALPHA036_DIRECTION, ALPHA037_DIRECTION, ALPHA039_DIRECTION,
    ALPHA043_DIRECTION, ALPHA045_DIRECTION, ALPHA047_DIRECTION,
)
from quantlab.factors.context import FactorContext


def _make_ctx(n=80):
    """短数据，覆盖常规因子预热期 (≤32 日)。
    使用 5 个标的避免 rank/corr 在小样本下除零 NaN。
    """
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    rng = np.random.default_rng(0)
    data = {}
    for sym in ["A", "B", "C", "D", "E"]:
        close = 100 + rng.normal(0, 1, n).cumsum()
        close = close.astype(float)
        df = pd.DataFrame(
            {
                "open": close + rng.normal(0, 0.5, n),
                "high": close + np.abs(rng.normal(0, 1, n)),
                "low": close - np.abs(rng.normal(0, 1, n)),
                "close": close,
                "volume": rng.integers(1000, 10000, n).astype(float),
                "vwap": close + rng.normal(0, 0.3, n),
                "amount": close * rng.integers(1000, 10000, n).astype(float),
            },
            index=dates,
        )
        data[sym] = df
    return FactorContext.from_dict(data)


def _make_long_ctx(n=300):
    """长数据，覆盖 200/250 日长窗口因子。"""
    dates = pd.date_range("2025-01-02", periods=n, freq="B")
    rng = np.random.default_rng(1)
    data = {}
    for sym in ["A", "B", "C", "D", "E"]:
        close = 100 + rng.normal(0, 1, n).cumsum()
        close = close.astype(float)
        df = pd.DataFrame(
            {
                "open": close + rng.normal(0, 0.5, n),
                "high": close + np.abs(rng.normal(0, 1, n)),
                "low": close - np.abs(rng.normal(0, 1, n)),
                "close": close,
                "volume": rng.integers(1000, 10000, n).astype(float),
                "vwap": close + rng.normal(0, 0.3, n),
                "amount": close * rng.integers(1000, 10000, n).astype(float),
            },
            index=dates,
        )
        data[sym] = df
    return FactorContext.from_dict(data)


# 短窗口因子: (name, func, direction, 预热期)
SHORT_FACTORS = [
    ("alpha_008", alpha_008, ALPHA008_DIRECTION, 15),
    ("alpha_026", alpha_026, ALPHA026_DIRECTION, 12),
    ("alpha_027", alpha_027, ALPHA027_DIRECTION, 7),
    ("alpha_028", alpha_028, ALPHA028_DIRECTION, 24),
    ("alpha_029", alpha_029, ALPHA029_DIRECTION, 11),
    ("alpha_030", alpha_030, ALPHA030_DIRECTION, 20),
    ("alpha_031", alpha_031, ALPHA031_DIRECTION, 31),
    ("alpha_035", alpha_035, ALPHA035_DIRECTION, 32),
    ("alpha_043", alpha_043, ALPHA043_DIRECTION, 27),
    ("alpha_045", alpha_045, ALPHA045_DIRECTION, 24),
    ("alpha_047", alpha_047, ALPHA047_DIRECTION, 24),
    ("alpha_025", alpha_025, ALPHA025_DIRECTION, 21),
]

# 长窗口因子: (name, func, direction)
LONG_FACTORS = [
    ("alpha_036", alpha_036, ALPHA036_DIRECTION),
    ("alpha_037", alpha_037, ALPHA037_DIRECTION),
    ("alpha_039", alpha_039, ALPHA039_DIRECTION),
]


@pytest.mark.parametrize("name,func,direction,warmup", SHORT_FACTORS)
def test_short_factor_basic(name, func, direction, warmup):
    ctx = _make_ctx(n=80)
    r = func(ctx)
    assert r.shape == ctx.close.shape, f"{name} 形状不一致"
    # 首期 NaN
    assert r.iloc[0].isna().all(), f"{name} 首期应为 NaN"
    # 末尾期有值
    assert not r.iloc[-1].isna().all(), f"{name} 末尾期应有值"


@pytest.mark.parametrize("name,func,direction", LONG_FACTORS)
def test_long_factor_basic(name, func, direction):
    ctx = _make_long_ctx(n=300)
    r = func(ctx)
    assert r.shape == ctx.close.shape, f"{name} 形状不一致"
    # 首期 NaN
    assert r.iloc[0].isna().all(), f"{name} 首期应为 NaN"
    # 末尾期有值
    assert not r.iloc[-1].isna().all(), f"{name} 末尾期应有值"


def test_alpha_027_binary_signal():
    """#27 是二值信号 (±1)。"""
    ctx = _make_ctx(n=80)
    r = alpha_027(ctx)
    vals = r.stack().dropna().unique()
    assert set(vals).issubset({-1.0, 1.0}), f"#27 应为二值信号，实际: {set(vals)}"


def test_alpha_030_volume_ratio():
    """#30 含 5/20 日量比。"""
    ctx = _make_ctx(n=80)
    r = alpha_030(ctx)
    assert r.iloc[0].isna().all()


def test_alpha_043_adv_ratio():
    """#43 含 volume/adv20。"""
    ctx = _make_ctx(n=80)
    r = alpha_043(ctx)
    # adv20 前 19 期 NaN
    assert r.iloc[0].isna().all()
    assert not r.iloc[-1].isna().all()


# ---------------- 方向常量 ----------------

@pytest.mark.parametrize(
    "name,func,direction,warmup",
    SHORT_FACTORS + [(n, f, d, 0) for n, f, d in LONG_FACTORS],
)
def test_direction_constant(name, func, direction, warmup):
    assert direction in (-1, 1), f"{name} 方向常量应为 ±1"


# ---------------- 完整备注字段检查 ----------------

_REQUIRED_FIELDS = [
    "公式", "公式解释", "分类", "信号方向", "数据来源与频率",
    "算子依赖", "背后逻辑", "适用场景", "变种与优化", "注意事项",
]


def _module_doc(modname):
    import sys
    mod = sys.modules.get(modname)
    return mod.__doc__ if (mod and mod.__doc__) else ""


@pytest.mark.parametrize(
    "modname",
    [
        "quantlab.factors.alpha101.alpha_008",
        "quantlab.factors.alpha101.alpha_025",
        "quantlab.factors.alpha101.alpha_026",
        "quantlab.factors.alpha101.alpha_027",
        "quantlab.factors.alpha101.alpha_028",
        "quantlab.factors.alpha101.alpha_029",
        "quantlab.factors.alpha101.alpha_030",
        "quantlab.factors.alpha101.alpha_031",
        "quantlab.factors.alpha101.alpha_035",
        "quantlab.factors.alpha101.alpha_036",
        "quantlab.factors.alpha101.alpha_037",
        "quantlab.factors.alpha101.alpha_039",
        "quantlab.factors.alpha101.alpha_043",
        "quantlab.factors.alpha101.alpha_045",
        "quantlab.factors.alpha101.alpha_047",
    ],
)
def test_docstring_has_all_10_required_fields(modname):
    doc = _module_doc(modname)
    missing = [f for f in _REQUIRED_FIELDS if f not in doc]
    assert not missing, f"{modname} 完整备注缺少字段: {missing}"
