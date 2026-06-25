"""
Alpha191 Phase 4 批次1 动量类因子单元测试
==========================================

覆盖: #6, #8, #17, #18, #20, #21
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.alpha191 import (
    alpha_006, alpha_008, alpha_017, alpha_018, alpha_020, alpha_021,
    ALPHA006_DIRECTION, ALPHA008_DIRECTION, ALPHA017_DIRECTION,
    ALPHA018_DIRECTION, ALPHA020_DIRECTION, ALPHA021_DIRECTION,
)
from quantlab.factors.context import FactorContext


def _make_ctx(n=40):
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


# ---------------- Alpha #6 ----------------

def test_alpha_006_basic():
    ctx = _make_ctx(n=40)
    r = alpha_006(ctx, period=4)
    assert r.shape == ctx.close.shape
    # 前 4 期 NaN (delta 预热)
    assert r.iloc[:4].isna().all().all()
    assert not r.iloc[4].isna().all()


def test_alpha_006_direction():
    assert ALPHA006_DIRECTION == -1


# ---------------- Alpha #8 ----------------

def test_alpha_008_basic():
    ctx = _make_ctx(n=40)
    r = alpha_008(ctx, period=4)
    assert r.shape == ctx.close.shape
    assert r.iloc[:4].isna().all().all()
    assert not r.iloc[4].isna().all()


def test_alpha_008_direction():
    assert ALPHA008_DIRECTION == -1


# ---------------- Alpha #17 ----------------

def test_alpha_017_basic():
    ctx = _make_ctx(n=40)
    r = alpha_017(ctx, vwap_period=15, momentum_period=5)
    assert r.shape == ctx.close.shape
    # ts_max 预热 14 + delta 5，取 max(14,4)=14
    assert r.iloc[:14].isna().all().all()
    assert not r.iloc[14].isna().all()


def test_alpha_017_direction():
    assert ALPHA017_DIRECTION == -1


def test_alpha_017_no_inf():
    """幂运算不应产生 inf。"""
    ctx = _make_ctx(n=40)
    r = alpha_017(ctx)
    assert not np.isinf(r.values).any()


# ---------------- Alpha #18 ----------------

def test_alpha_018_basic():
    ctx = _make_ctx(n=40)
    r = alpha_018(ctx, period=5)
    assert r.shape == ctx.close.shape
    assert r.iloc[:5].isna().all().all()
    assert not r.iloc[5].isna().all()


def test_alpha_018_direction():
    assert ALPHA018_DIRECTION == 1


# ---------------- Alpha #20 ----------------

def test_alpha_020_basic():
    ctx = _make_ctx(n=40)
    r = alpha_020(ctx, period=6)
    assert r.shape == ctx.close.shape
    assert r.iloc[:6].isna().all().all()
    assert not r.iloc[6].isna().all()


def test_alpha_020_direction():
    assert ALPHA020_DIRECTION == 1


# ---------------- Alpha #21 ----------------

def test_alpha_021_basic():
    ctx = _make_ctx(n=40)
    r = alpha_021(ctx, period=6)
    assert r.shape == ctx.close.shape
    # ts_mean 预热 5 (idx0-4 NaN) + 回归窗口 6 → idx 10 首值
    assert r.iloc[:10].isna().all().all()
    assert not r.iloc[10].isna().all()


def test_alpha_021_direction():
    assert ALPHA021_DIRECTION == -1


def test_alpha_021_trend_consistency():
    """纯上涨序列斜率应为正。"""
    n = 20
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    data = {
        "A": pd.DataFrame(
            {
                "open": np.arange(100, 100 + n, dtype=float),
                "high": np.arange(101, 101 + n, dtype=float),
                "low": np.arange(99, 99 + n, dtype=float),
                "close": np.arange(100, 100 + n, dtype=float),
                "volume": np.full(n, 5000.0),
                "amount": np.arange(100, 100 + n, dtype=float) * 5000,
            },
            index=dates,
        ),
    }
    ctx = FactorContext.from_dict(data)
    r = alpha_021(ctx, period=6)
    # 上涨序列斜率 > 0
    assert (r.iloc[-1] > 0).all()


# ---------------- 完整备注字段检查 ----------------

_REQUIRED_FIELDS = [
    "公式", "公式解释", "分类", "信号方向", "数据来源与频率",
    "算子依赖", "背后逻辑", "适用场景", "变种与优化", "注意事项",
]


@pytest.mark.parametrize(
    "modname",
    [
        "quantlab.factors.alpha191.alpha_006",
        "quantlab.factors.alpha191.alpha_008",
        "quantlab.factors.alpha191.alpha_017",
        "quantlab.factors.alpha191.alpha_018",
        "quantlab.factors.alpha191.alpha_020",
        "quantlab.factors.alpha191.alpha_021",
    ],
)
def test_docstring_has_all_10_required_fields(modname):
    import importlib

    mod = importlib.import_module(modname)
    doc = mod.__doc__ or ""
    missing = [f for f in _REQUIRED_FIELDS if f not in doc]
    assert not missing, f"{modname} 完整备注缺少字段: {missing}"
