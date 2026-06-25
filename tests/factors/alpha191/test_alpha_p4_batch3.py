"""
Alpha191 Phase 4 批次3 因子单元测试
==========================================

覆盖: #41, #48, #53, #57, #58, #67, #79
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.alpha191 import (
    alpha_041, alpha_048, alpha_053, alpha_057, alpha_058,
    alpha_067, alpha_079,
    ALPHA041_DIRECTION, ALPHA048_DIRECTION, ALPHA053_DIRECTION,
    ALPHA057_DIRECTION, ALPHA058_DIRECTION, ALPHA067_DIRECTION,
    ALPHA079_DIRECTION,
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


# ---------------- Alpha #41 ----------------

def test_alpha_041_basic():
    ctx = _make_ctx(n=60)
    r = alpha_041(ctx, delta_period=3, max_period=5)
    assert r.shape == ctx.close.shape
    # delta 预热 3 (idx3 首值) + ts_max 5 预热 4 → idx 7 首值
    assert r.iloc[:7].isna().all().all()
    assert not r.iloc[7].isna().all()


def test_alpha_041_direction():
    assert ALPHA041_DIRECTION == -1


# ---------------- Alpha #48 ----------------

def test_alpha_048_basic():
    ctx = _make_ctx(n=60)
    r = alpha_048(ctx, sign_period=3, short_vol=5, long_vol=20)
    assert r.shape == ctx.close.shape
    # delay(1) 预热 1 + sign_sum 3 预热 2 + 量比 long_vol 20 预热 19 → idx 19
    assert r.iloc[:19].isna().all().all()
    assert not r.iloc[19].isna().all()


def test_alpha_048_direction():
    assert ALPHA048_DIRECTION == -1


# ---------------- Alpha #53 ----------------

def test_alpha_053_basic():
    ctx = _make_ctx(n=60)
    r = alpha_053(ctx, period=12)
    assert r.shape == ctx.close.shape
    # delay 1 + count 12 → idx 12
    assert r.iloc[:12].isna().all().all()
    assert not r.iloc[12].isna().all()


def test_alpha_053_direction():
    assert ALPHA053_DIRECTION == 1


def test_alpha_053_range():
    """上涨频率应在 0~100 之间。"""
    ctx = _make_ctx(n=60)
    r = alpha_053(ctx).dropna()
    assert (r >= 0).all().all()
    assert (r <= 100).all().all()


# ---------------- Alpha #57 ----------------

def test_alpha_057_basic():
    ctx = _make_ctx(n=60)
    r = alpha_057(ctx, rsv_period=9, sma_n=3, sma_m=1)
    assert r.shape == ctx.close.shape
    # rsv 预热 8，ewm 从首个非 NaN → idx 8
    assert r.iloc[:8].isna().all().all()
    assert not r.iloc[8].isna().all()


def test_alpha_057_direction():
    assert ALPHA057_DIRECTION == 1


# ---------------- Alpha #58 ----------------

def test_alpha_058_basic():
    ctx = _make_ctx(n=60)
    r = alpha_058(ctx, period=20)
    assert r.shape == ctx.close.shape
    assert r.iloc[:20].isna().all().all()
    assert not r.iloc[20].isna().all()


def test_alpha_058_direction():
    assert ALPHA058_DIRECTION == 1


# ---------------- Alpha #67 ----------------

def test_alpha_067_basic():
    ctx = _make_ctx(n=60)
    r = alpha_067(ctx, period=24)
    assert r.shape == ctx.close.shape
    # diff idx0 NaN, idx1 首值 → ewm 从 idx1 开始
    assert r.iloc[:1].isna().all().all()
    assert not r.iloc[1].isna().all()


def test_alpha_067_direction():
    assert ALPHA067_DIRECTION == 1


def test_alpha_067_range():
    """RSI 应在 0~100 之间。"""
    ctx = _make_ctx(n=80)
    r = alpha_067(ctx).dropna()
    assert (r >= 0).all().all()
    assert (r <= 100).all().all()


# ---------------- Alpha #79 ----------------

def test_alpha_079_basic():
    ctx = _make_ctx(n=60)
    r = alpha_079(ctx, period=12)
    assert r.shape == ctx.close.shape
    assert r.iloc[:1].isna().all().all()
    assert not r.iloc[1].isna().all()


def test_alpha_079_direction():
    assert ALPHA079_DIRECTION == 1


def test_alpha_079_range():
    """RSI 应在 0~100 之间。"""
    ctx = _make_ctx(n=60)
    r = alpha_079(ctx).dropna()
    assert (r >= 0).all().all()
    assert (r <= 100).all().all()


# ---------------- 完整备注字段检查 ----------------

_REQUIRED_FIELDS = [
    "公式", "公式解释", "分类", "信号方向", "数据来源与频率",
    "算子依赖", "背后逻辑", "适用场景", "变种与优化", "注意事项",
]


@pytest.mark.parametrize(
    "modname",
    [
        "quantlab.factors.alpha191.alpha_041",
        "quantlab.factors.alpha191.alpha_048",
        "quantlab.factors.alpha191.alpha_053",
        "quantlab.factors.alpha191.alpha_057",
        "quantlab.factors.alpha191.alpha_058",
        "quantlab.factors.alpha191.alpha_067",
        "quantlab.factors.alpha191.alpha_079",
    ],
)
def test_docstring_has_all_10_required_fields(modname):
    import importlib

    mod = importlib.import_module(modname)
    doc = mod.__doc__ or ""
    missing = [f for f in _REQUIRED_FIELDS if f not in doc]
    assert not missing, f"{modname} 完整备注缺少字段: {missing}"
