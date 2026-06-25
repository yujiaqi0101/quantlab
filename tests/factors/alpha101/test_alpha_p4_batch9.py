"""
Alpha101 P0 因子单元测试 (批次9)
================================

覆盖: #1, #2, #3, #5, #7, #11, #13, #14, #15, #16, #17, #18, #21, #50, #52, #54, #57
动量 + K线 + 量价相关 + 波动率类因子。
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.alpha101 import (
    alpha_001, alpha_002, alpha_003, alpha_005, alpha_007, alpha_011,
    alpha_013, alpha_014, alpha_015, alpha_016, alpha_017, alpha_018,
    alpha_021, alpha_050, alpha_052, alpha_054, alpha_057,
    ALPHA001_DIRECTION, ALPHA002_DIRECTION, ALPHA003_DIRECTION,
    ALPHA005_DIRECTION, ALPHA007_DIRECTION, ALPHA011_DIRECTION,
    ALPHA013_DIRECTION, ALPHA014_DIRECTION, ALPHA015_DIRECTION,
    ALPHA016_DIRECTION, ALPHA017_DIRECTION, ALPHA018_DIRECTION,
    ALPHA021_DIRECTION, ALPHA050_DIRECTION, ALPHA052_DIRECTION,
    ALPHA054_DIRECTION, ALPHA057_DIRECTION,
)
from quantlab.factors.context import FactorContext


def _make_ctx(n=80):
    """短数据，覆盖常规因子预热期 (≤32 日)。"""
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


def _make_long_ctx(n=120):
    """长数据，覆盖 #7 (ts_rank 60) 长窗口因子。"""
    dates = pd.date_range("2025-09-01", periods=n, freq="B")
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


# 短窗口因子: (name, func, direction)
SHORT_FACTORS = [
    ("alpha_001", alpha_001, ALPHA001_DIRECTION),
    ("alpha_002", alpha_002, ALPHA002_DIRECTION),
    ("alpha_003", alpha_003, ALPHA003_DIRECTION),
    ("alpha_005", alpha_005, ALPHA005_DIRECTION),
    ("alpha_011", alpha_011, ALPHA011_DIRECTION),
    ("alpha_013", alpha_013, ALPHA013_DIRECTION),
    ("alpha_014", alpha_014, ALPHA014_DIRECTION),
    ("alpha_015", alpha_015, ALPHA015_DIRECTION),
    ("alpha_016", alpha_016, ALPHA016_DIRECTION),
    ("alpha_017", alpha_017, ALPHA017_DIRECTION),
    ("alpha_018", alpha_018, ALPHA018_DIRECTION),
    ("alpha_021", alpha_021, ALPHA021_DIRECTION),
    ("alpha_050", alpha_050, ALPHA050_DIRECTION),
    ("alpha_052", alpha_052, ALPHA052_DIRECTION),
    ("alpha_054", alpha_054, ALPHA054_DIRECTION),
    ("alpha_057", alpha_057, ALPHA057_DIRECTION),
]

# 长窗口因子 (ts_rank 60): #7
LONG_FACTORS = [
    ("alpha_007", alpha_007, ALPHA007_DIRECTION),
]


@pytest.mark.parametrize("name,func,direction", SHORT_FACTORS)
def test_short_factor_basic(name, func, direction):
    ctx = _make_ctx(n=80)
    r = func(ctx)
    assert r.shape == ctx.close.shape, f"{name} 形状不一致"
    # 首期 NaN (除 #54 外都有预热期)
    if name != "alpha_054":
        assert r.iloc[0].isna().all(), f"{name} 首期应为 NaN"
    # 末尾期有值
    assert not r.iloc[-1].isna().all(), f"{name} 末尾期应有值"


@pytest.mark.parametrize("name,func,direction", LONG_FACTORS)
def test_long_factor_basic(name, func, direction):
    ctx = _make_long_ctx(n=120)
    r = func(ctx)
    assert r.shape == ctx.close.shape, f"{name} 形状不一致"
    # 首期 NaN
    assert r.iloc[0].isna().all(), f"{name} 首期应为 NaN"
    # 末尾期有值
    assert not r.iloc[-1].isna().all(), f"{name} 末尾期应有值"


# ---------------- 方向常量 ----------------

@pytest.mark.parametrize(
    "name,func,direction",
    SHORT_FACTORS + LONG_FACTORS,
)
def test_direction_constant(name, func, direction):
    assert direction in (-1, 1), f"{name} 方向常量应为 ±1"


# ---------------- 特殊场景测试 ----------------

def test_alpha_021_binary_signal():
    """#21 是布林带策略，返回二值信号 {-1, 1}。"""
    ctx = _make_ctx(n=80)
    r = alpha_021(ctx)
    valid = r.stack().dropna().unique()
    assert set(valid).issubset({-1.0, 1.0}), f"#21 应为二值信号，实际: {set(valid)}"


def test_alpha_054_no_nan_inf():
    """#54 应处理除零，无 inf 值。"""
    ctx = _make_ctx(n=80)
    r = alpha_054(ctx)
    assert not np.isinf(r.to_numpy()).any(), "#54 不应包含 inf"


def test_alpha_057_trend_consistency():
    """#57 趋势一致时顺势，不一致时反转。"""
    ctx = _make_ctx(n=80)
    r = alpha_057(ctx)
    assert r.shape == ctx.close.shape


def test_alpha_007_volume_breakout():
    """#7 放量时返回动量信号，缩量时返回 -1。"""
    ctx = _make_long_ctx(n=120)
    r = alpha_007(ctx)
    assert r.shape == ctx.close.shape


def test_alpha_001_rank_range():
    """#1 排名中心化后范围约 [-0.5, 0.5]。"""
    ctx = _make_ctx(n=80)
    r = alpha_001(ctx)
    valid = r.stack().dropna()
    if len(valid) > 0:
        assert valid.min() >= -0.5 - 1e-6
        assert valid.max() <= 0.5 + 1e-6


def test_alpha_005_vwap_deviation():
    """#5 VWAP 偏离因子。"""
    ctx = _make_ctx(n=80)
    r = alpha_005(ctx)
    assert r.iloc[0].isna().all()
    assert not r.iloc[-1].isna().all()


# ---------------- 完整备注字段检查 ----------------

_REQUIRED_FIELDS = [
    "公式", "公式解释", "分类", "信号方向", "数据来源与频率",
    "算子依赖", "背后逻辑", "适用场景", "变种与优化", "注意事项",
]


def _module_doc(modname):
    import sys
    mod = sys.modules.get(modname)
    return mod.__doc__ if (mod and mod.__doc__) else ""


_ALPHA101_BATCH9_MODULES = [
    "quantlab.factors.alpha101.alpha_001",
    "quantlab.factors.alpha101.alpha_002",
    "quantlab.factors.alpha101.alpha_003",
    "quantlab.factors.alpha101.alpha_005",
    "quantlab.factors.alpha101.alpha_007",
    "quantlab.factors.alpha101.alpha_011",
    "quantlab.factors.alpha101.alpha_013",
    "quantlab.factors.alpha101.alpha_014",
    "quantlab.factors.alpha101.alpha_015",
    "quantlab.factors.alpha101.alpha_016",
    "quantlab.factors.alpha101.alpha_017",
    "quantlab.factors.alpha101.alpha_018",
    "quantlab.factors.alpha101.alpha_021",
    "quantlab.factors.alpha101.alpha_050",
    "quantlab.factors.alpha101.alpha_052",
    "quantlab.factors.alpha101.alpha_054",
    "quantlab.factors.alpha101.alpha_057",
]


@pytest.mark.parametrize("modname", _ALPHA101_BATCH9_MODULES)
def test_docstring_has_all_10_required_fields(modname):
    import importlib

    importlib.import_module(modname)
    doc = _module_doc(modname)
    missing = [f for f in _REQUIRED_FIELDS if f not in doc]
    assert not missing, f"{modname} 完整备注缺少字段: {missing}"
