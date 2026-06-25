"""
Alpha191 Phase 4 批次6a 因子单元测试
==========================================

覆盖: #1, #3, #5, #7, #11, #16, #32, #35, #36, #40, #42
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.alpha191 import (
    alpha_001, alpha_003, alpha_005, alpha_007, alpha_011,
    alpha_016, alpha_032, alpha_035, alpha_036, alpha_040, alpha_042,
    ALPHA001_DIRECTION, ALPHA003_DIRECTION, ALPHA005_DIRECTION,
    ALPHA007_DIRECTION, ALPHA011_DIRECTION, ALPHA016_DIRECTION,
    ALPHA032_DIRECTION, ALPHA035_DIRECTION, ALPHA036_DIRECTION,
    ALPHA040_DIRECTION, ALPHA042_DIRECTION,
)
from quantlab.factors.context import FactorContext


def _make_ctx(n=60):
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
                "amount": close * rng.integers(1000, 10000, n).astype(float),
            },
            index=dates,
        )
        data[sym] = df
    return FactorContext.from_dict(data)


# ---------------- Alpha #1 ----------------

def test_alpha_001_basic():
    ctx = _make_ctx(n=60)
    r = alpha_001(ctx, corr_period=6)
    assert r.shape == ctx.close.shape
    # delta(1) 预热 1 + corr(6) 预热 5 → idx 6 首值
    assert r.iloc[:6].isna().all().all()
    assert not r.iloc[6].isna().all()


def test_alpha_001_direction():
    assert ALPHA001_DIRECTION == -1


# ---------------- Alpha #3 ----------------

def test_alpha_003_basic():
    ctx = _make_ctx(n=60)
    r = alpha_003(ctx, period=6)
    assert r.shape == ctx.close.shape
    # delay(1) 预热 1 + ts_sum(6) 预热 5 → idx 6 首值
    assert r.iloc[:6].isna().all().all()
    assert not r.iloc[6].isna().all()


def test_alpha_003_direction():
    assert ALPHA003_DIRECTION == 1


# ---------------- Alpha #5 ----------------

def test_alpha_005_basic():
    ctx = _make_ctx(n=60)
    r = alpha_005(ctx, rank_period=5, corr_period=5, max_period=3)
    assert r.shape == ctx.close.shape
    # ts_rank(5) 预热 4 + corr(5) 预热 4 + ts_max(3) 预热 2 → idx 10 首值
    assert r.iloc[:10].isna().all().all()
    assert not r.iloc[10].isna().all()


def test_alpha_005_direction():
    assert ALPHA005_DIRECTION == -1


# ---------------- Alpha #7 ----------------

def test_alpha_007_basic():
    ctx = _make_ctx(n=60)
    r = alpha_007(ctx, period=3)
    assert r.shape == ctx.close.shape
    # ts_max/ts_min(3) 预热 2 + delta(3) 预热 3 → 取 max, idx 3 首值
    assert r.iloc[:3].isna().all().all()
    assert not r.iloc[3].isna().all()


def test_alpha_007_direction():
    assert ALPHA007_DIRECTION == 1


# ---------------- Alpha #11 ----------------

def test_alpha_011_basic():
    ctx = _make_ctx(n=60)
    r = alpha_011(ctx, period=6)
    assert r.shape == ctx.close.shape
    # ts_sum(6) 预热 5 → idx 5 首值
    assert r.iloc[:5].isna().all().all()
    assert not r.iloc[5].isna().all()


def test_alpha_011_direction():
    assert ALPHA011_DIRECTION == 1


# ---------------- Alpha #16 ----------------

def test_alpha_016_basic():
    ctx = _make_ctx(n=60)
    r = alpha_016(ctx, corr_period=5, max_period=5)
    assert r.shape == ctx.close.shape
    # corr(5) 预热 4 + ts_max(5) 预热 4 → idx 8 首值
    assert r.iloc[:8].isna().all().all()
    assert not r.iloc[8].isna().all()


def test_alpha_016_direction():
    assert ALPHA016_DIRECTION == -1


# ---------------- Alpha #32 ----------------

def test_alpha_032_basic():
    ctx = _make_ctx(n=60)
    r = alpha_032(ctx, corr_period=3, sum_period=3)
    assert r.shape == ctx.close.shape
    # corr(3) 预热 2 + ts_sum(3) 预热 2 → idx 4 首值
    assert r.iloc[:4].isna().all().all()
    assert not r.iloc[4].isna().all()


def test_alpha_032_direction():
    assert ALPHA032_DIRECTION == -1


# ---------------- Alpha #35 ----------------

def test_alpha_035_basic():
    ctx = _make_ctx(n=60)
    r = alpha_035(ctx, delta_period=1, decay_open=15, corr_period=17, decay_corr=7)
    assert r.shape == ctx.close.shape
    # delta(1) idx1 + decay_linear(15) idx15 (需15期非NaN)
    # corr(17) idx16 + decay_linear(7) idx22 (需7期非NaN)
    # 取 min → idx 22 首值
    assert r.iloc[:22].isna().all().all()
    assert not r.iloc[22].isna().all()


def test_alpha_035_direction():
    assert ALPHA035_DIRECTION == -1


# ---------------- Alpha #36 ----------------

def test_alpha_036_basic():
    ctx = _make_ctx(n=60)
    r = alpha_036(ctx, corr_period=5, sum_period=6)
    assert r.shape == ctx.close.shape
    # corr(5) 预热 4 + ts_sum(6) 预热 5 → idx 9 首值
    assert r.iloc[:9].isna().all().all()
    assert not r.iloc[9].isna().all()


def test_alpha_036_direction():
    assert ALPHA036_DIRECTION == 1


# ---------------- Alpha #40 ----------------

def test_alpha_040_basic():
    ctx = _make_ctx(n=60)
    r = alpha_040(ctx, period=26)
    assert r.shape == ctx.close.shape
    # ts_sum(26) 预热 25 → idx 25 首值
    assert r.iloc[:25].isna().all().all()
    assert not r.iloc[25].isna().all()


def test_alpha_040_direction():
    assert ALPHA040_DIRECTION == 1


# ---------------- Alpha #42 ----------------

def test_alpha_042_basic():
    ctx = _make_ctx(n=60)
    r = alpha_042(ctx, period=10)
    assert r.shape == ctx.close.shape
    # ts_std(10) 预热 9 + corr(10) 预热 9 → idx 9 首值
    assert r.iloc[:9].isna().all().all()
    assert not r.iloc[9].isna().all()


def test_alpha_042_direction():
    assert ALPHA042_DIRECTION == -1


# ---------------- 完整备注字段检查 ----------------

_REQUIRED_FIELDS = [
    "公式", "公式解释", "分类", "信号方向", "数据来源与频率",
    "算子依赖", "背后逻辑", "适用场景", "变种与优化", "注意事项",
]


@pytest.mark.parametrize(
    "modname",
    [
        "quantlab.factors.alpha191.alpha_001",
        "quantlab.factors.alpha191.alpha_003",
        "quantlab.factors.alpha191.alpha_005",
        "quantlab.factors.alpha191.alpha_007",
        "quantlab.factors.alpha191.alpha_011",
        "quantlab.factors.alpha191.alpha_016",
        "quantlab.factors.alpha191.alpha_032",
        "quantlab.factors.alpha191.alpha_035",
        "quantlab.factors.alpha191.alpha_036",
        "quantlab.factors.alpha191.alpha_040",
        "quantlab.factors.alpha191.alpha_042",
    ],
)
def test_docstring_has_all_10_required_fields(modname):
    import importlib

    mod = importlib.import_module(modname)
    doc = mod.__doc__ or ""
    missing = [f for f in _REQUIRED_FIELDS if f not in doc]
    assert not missing, f"{modname} 完整备注缺少字段: {missing}"
