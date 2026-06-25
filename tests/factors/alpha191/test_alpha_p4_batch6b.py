"""
Alpha191 Phase 4 批次6b 因子单元测试
==========================================

覆盖: #43, #44, #45, #60, #62, #68, #74, #83, #84, #90, #91, #99, #104, #108
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.alpha191 import (
    alpha_043, alpha_044, alpha_045, alpha_060, alpha_062, alpha_068,
    alpha_074, alpha_083, alpha_084, alpha_090, alpha_091, alpha_099,
    alpha_104, alpha_108,
    ALPHA043_DIRECTION, ALPHA044_DIRECTION, ALPHA045_DIRECTION,
    ALPHA060_DIRECTION, ALPHA062_DIRECTION, ALPHA068_DIRECTION,
    ALPHA074_DIRECTION, ALPHA083_DIRECTION, ALPHA084_DIRECTION,
    ALPHA090_DIRECTION, ALPHA091_DIRECTION, ALPHA099_DIRECTION,
    ALPHA104_DIRECTION, ALPHA108_DIRECTION,
)
from quantlab.factors.context import FactorContext


def _make_ctx(n=180):
    dates = pd.date_range("2025-06-01", periods=n, freq="B")
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
                "amount": close * rng.integers(1000, 10000, n).astype(float),
            },
            index=dates,
        )
        data[sym] = df
    return FactorContext.from_dict(data)


# ---------------- Alpha #43 ----------------

def test_alpha_043_basic():
    ctx = _make_ctx(n=60)
    r = alpha_043(ctx, period=6)
    assert r.shape == ctx.close.shape
    # ts_sum(6) 预热 5 → idx 5 首值
    assert r.iloc[:5].isna().all().all()
    assert not r.iloc[5].isna().all()


def test_alpha_043_direction():
    assert ALPHA043_DIRECTION == 1


# ---------------- Alpha #44 ----------------

def test_alpha_044_basic():
    ctx = _make_ctx(n=60)
    r = alpha_044(ctx, vol_period=10, corr_period=7, decay1=6, rank1=4,
                  delta_period=3, decay2=10, rank2=15)
    assert r.shape == ctx.close.shape
    # 第一子: corr(7) idx6 + decay(6) idx11 + ts_rank(4) idx14
    # 第二子: delta(3) idx3 + decay(10) idx12 + ts_rank(15) idx26
    # 取 max → idx 26 首值
    assert r.iloc[:26].isna().all().all()
    assert not r.iloc[26].isna().all()


def test_alpha_044_direction():
    assert ALPHA044_DIRECTION == 1


# ---------------- Alpha #45 ----------------

def test_alpha_045_basic():
    ctx = _make_ctx(n=180)
    r = alpha_045(ctx, delta_period=1, vol_period=150, corr_period=15)
    assert r.shape == ctx.close.shape
    # delta(1) idx1 + ts_mean(150) idx149 + corr(15) idx163 → idx 163 首值
    assert r.iloc[:163].isna().all().all()
    assert not r.iloc[163].isna().all()


def test_alpha_045_direction():
    assert ALPHA045_DIRECTION == -1


# ---------------- Alpha #60 ----------------

def test_alpha_060_basic():
    ctx = _make_ctx(n=60)
    r = alpha_060(ctx, period=20)
    assert r.shape == ctx.close.shape
    # ts_sum(20) 预热 19 → idx 19 首值
    assert r.iloc[:19].isna().all().all()
    assert not r.iloc[19].isna().all()


def test_alpha_060_direction():
    assert ALPHA060_DIRECTION == 1


# ---------------- Alpha #62 ----------------

def test_alpha_062_basic():
    ctx = _make_ctx(n=60)
    r = alpha_062(ctx, period=5)
    assert r.shape == ctx.close.shape
    # corr(5) 预热 4 → idx 4 首值
    assert r.iloc[:4].isna().all().all()
    assert not r.iloc[4].isna().all()


def test_alpha_062_direction():
    assert ALPHA062_DIRECTION == -1


# ---------------- Alpha #68 ----------------

def test_alpha_068_basic():
    ctx = _make_ctx(n=60)
    r = alpha_068(ctx, sma_n=15, sma_m=2)
    assert r.shape == ctx.close.shape
    # delta(1) idx1 + delta(1) idx2 (加速) + sma(15) 需 15 个非NaN (ewm 从首值开始)
    # ewm alpha=2/15 从首个非NaN(idx2)开始 → idx 2 首值
    assert r.iloc[:2].isna().all().all()
    assert not r.iloc[2].isna().all()


def test_alpha_068_direction():
    assert ALPHA068_DIRECTION == 1


# ---------------- Alpha #74 ----------------

def test_alpha_074_basic():
    ctx = _make_ctx(n=60)
    r = alpha_074(ctx, vol_period=40, corr1=7, corr2=6)
    assert r.shape == ctx.close.shape
    # 第一子: ts_mean(40) idx39 + corr(7) idx45
    # 第二子: corr(6) idx5 → 取 max → idx 45 首值
    assert r.iloc[:45].isna().all().all()
    assert not r.iloc[45].isna().all()


def test_alpha_074_direction():
    assert ALPHA074_DIRECTION == 1


# ---------------- Alpha #83 ----------------

def test_alpha_083_basic():
    ctx = _make_ctx(n=60)
    r = alpha_083(ctx, period=5)
    assert r.shape == ctx.close.shape
    # cov(5) 预热 4 → idx 4 首值
    assert r.iloc[:4].isna().all().all()
    assert not r.iloc[4].isna().all()


def test_alpha_083_direction():
    assert ALPHA083_DIRECTION == -1


# ---------------- Alpha #84 ----------------

def test_alpha_084_basic():
    ctx = _make_ctx(n=60)
    r = alpha_084(ctx, period=20)
    assert r.shape == ctx.close.shape
    # ts_sum(20) 预热 19 → idx 19 首值
    assert r.iloc[:19].isna().all().all()
    assert not r.iloc[19].isna().all()


def test_alpha_084_direction():
    assert ALPHA084_DIRECTION == 1


# ---------------- Alpha #90 ----------------

def test_alpha_090_basic():
    ctx = _make_ctx(n=60)
    r = alpha_090(ctx, period=5)
    assert r.shape == ctx.close.shape
    # corr(5) 预热 4 → idx 4 首值
    assert r.iloc[:4].isna().all().all()
    assert not r.iloc[4].isna().all()


def test_alpha_090_direction():
    assert ALPHA090_DIRECTION == -1


# ---------------- Alpha #91 ----------------

def test_alpha_091_basic():
    ctx = _make_ctx(n=60)
    r = alpha_091(ctx, max_period=5, vol_period=40, corr_period=5)
    assert r.shape == ctx.close.shape
    # ts_max(5) idx4 + ts_mean(40) idx39 + corr(5) idx43 → idx 43 首值
    assert r.iloc[:43].isna().all().all()
    assert not r.iloc[43].isna().all()


def test_alpha_091_direction():
    assert ALPHA091_DIRECTION == -1


# ---------------- Alpha #99 ----------------

def test_alpha_099_basic():
    ctx = _make_ctx(n=60)
    r = alpha_099(ctx, period=5)
    assert r.shape == ctx.close.shape
    # cov(5) 预热 4 → idx 4 首值
    assert r.iloc[:4].isna().all().all()
    assert not r.iloc[4].isna().all()


def test_alpha_099_direction():
    assert ALPHA099_DIRECTION == -1


# ---------------- Alpha #104 ----------------

def test_alpha_104_basic():
    ctx = _make_ctx(n=60)
    r = alpha_104(ctx, corr_period=5, delta_period=5, std_period=20)
    assert r.shape == ctx.close.shape
    # corr(5) idx4 + delta(5) idx8 + ts_std(20) idx19 → idx 19 首值
    assert r.iloc[:19].isna().all().all()
    assert not r.iloc[19].isna().all()


def test_alpha_104_direction():
    assert ALPHA104_DIRECTION == -1


# ---------------- Alpha #108 ----------------

def test_alpha_108_basic():
    ctx = _make_ctx(n=180)
    r = alpha_108(ctx, min_period=2, vol_period=120, corr_period=6)
    assert r.shape == ctx.close.shape
    # ts_min(2) idx1 + ts_mean(120) idx119 + corr(6) idx124 → idx 124 首值
    assert r.iloc[:124].isna().all().all()
    assert not r.iloc[124].isna().all()


def test_alpha_108_direction():
    assert ALPHA108_DIRECTION == -1


def test_alpha_108_no_inf():
    """幂次运算不应产生 inf"""
    ctx = _make_ctx(n=180)
    r = alpha_108(ctx, min_period=2, vol_period=120, corr_period=6)
    finite_part = r.iloc[124:]
    assert not np.isinf(finite_part.values).any()


# ---------------- 完整备注字段检查 ----------------

_REQUIRED_FIELDS = [
    "公式", "公式解释", "分类", "信号方向", "数据来源与频率",
    "算子依赖", "背后逻辑", "适用场景", "变种与优化", "注意事项",
]


@pytest.mark.parametrize(
    "modname",
    [
        "quantlab.factors.alpha191.alpha_043",
        "quantlab.factors.alpha191.alpha_044",
        "quantlab.factors.alpha191.alpha_045",
        "quantlab.factors.alpha191.alpha_060",
        "quantlab.factors.alpha191.alpha_062",
        "quantlab.factors.alpha191.alpha_068",
        "quantlab.factors.alpha191.alpha_074",
        "quantlab.factors.alpha191.alpha_083",
        "quantlab.factors.alpha191.alpha_084",
        "quantlab.factors.alpha191.alpha_090",
        "quantlab.factors.alpha191.alpha_091",
        "quantlab.factors.alpha191.alpha_099",
        "quantlab.factors.alpha191.alpha_104",
        "quantlab.factors.alpha191.alpha_108",
    ],
)
def test_docstring_has_all_10_required_fields(modname):
    import importlib

    mod = importlib.import_module(modname)
    doc = mod.__doc__ or ""
    missing = [f for f in _REQUIRED_FIELDS if f not in doc]
    assert not missing, f"{modname} 完整备注缺少字段: {missing}"
