"""
Alpha191 Phase 4 批次5 因子单元测试
==========================================

覆盖: #31, #34, #46, #47, #65, #66, #71, #72, #78, #82
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.alpha191 import (
    alpha_031, alpha_034, alpha_046, alpha_047, alpha_065,
    alpha_066, alpha_071, alpha_072, alpha_078, alpha_082,
    ALPHA031_DIRECTION, ALPHA034_DIRECTION, ALPHA046_DIRECTION,
    ALPHA047_DIRECTION, ALPHA065_DIRECTION, ALPHA066_DIRECTION,
    ALPHA071_DIRECTION, ALPHA072_DIRECTION, ALPHA078_DIRECTION,
    ALPHA082_DIRECTION,
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


# ---------------- Alpha #31 ----------------

def test_alpha_031_basic():
    ctx = _make_ctx(n=60)
    r = alpha_031(ctx, period=12)
    assert r.shape == ctx.close.shape
    # ts_mean(12) 预热 11 → idx 11 首值
    assert r.iloc[:11].isna().all().all()
    assert not r.iloc[11].isna().all()


def test_alpha_031_direction():
    assert ALPHA031_DIRECTION == -1


# ---------------- Alpha #34 ----------------

def test_alpha_034_basic():
    ctx = _make_ctx(n=60)
    r = alpha_034(ctx, period=12)
    assert r.shape == ctx.close.shape
    assert r.iloc[:11].isna().all().all()
    assert not r.iloc[11].isna().all()


def test_alpha_034_direction():
    assert ALPHA034_DIRECTION == -1


# ---------------- Alpha #46 ----------------

def test_alpha_046_basic():
    ctx = _make_ctx(n=60)
    r = alpha_046(ctx)
    assert r.shape == ctx.close.shape
    # 24日均线预热 23
    assert r.iloc[:23].isna().all().all()
    assert not r.iloc[23].isna().all()


def test_alpha_046_direction():
    assert ALPHA046_DIRECTION == -1


# ---------------- Alpha #47 ----------------

def test_alpha_047_basic():
    ctx = _make_ctx(n=60)
    r = alpha_047(ctx, range_period=6, sma_n=9, sma_m=1)
    assert r.shape == ctx.close.shape
    # ts_max/ts_min(6) 预热 5，ewm 从首个非 NaN → idx 5
    assert r.iloc[:5].isna().all().all()
    assert not r.iloc[5].isna().all()


def test_alpha_047_direction():
    assert ALPHA047_DIRECTION == -1


# ---------------- Alpha #65 ----------------

def test_alpha_065_basic():
    ctx = _make_ctx(n=60)
    r = alpha_065(ctx, period=6)
    assert r.shape == ctx.close.shape
    assert r.iloc[:5].isna().all().all()
    assert not r.iloc[5].isna().all()


def test_alpha_065_direction():
    assert ALPHA065_DIRECTION == -1


# ---------------- Alpha #66 ----------------

def test_alpha_066_basic():
    ctx = _make_ctx(n=60)
    r = alpha_066(ctx, period=6)
    assert r.shape == ctx.close.shape
    assert r.iloc[:5].isna().all().all()
    assert not r.iloc[5].isna().all()


def test_alpha_066_direction():
    assert ALPHA066_DIRECTION == -1


# ---------------- Alpha #71 ----------------

def test_alpha_071_basic():
    ctx = _make_ctx(n=60)
    r = alpha_071(ctx, period=24)
    assert r.shape == ctx.close.shape
    assert r.iloc[:23].isna().all().all()
    assert not r.iloc[23].isna().all()


def test_alpha_071_direction():
    assert ALPHA071_DIRECTION == -1


# ---------------- Alpha #72 ----------------

def test_alpha_072_basic():
    ctx = _make_ctx(n=60)
    r = alpha_072(ctx, rsv_period=9, sma_n=15, sma_m=1)
    assert r.shape == ctx.close.shape
    # rsv 预热 8，ewm 从首个非 NaN → idx 8
    assert r.iloc[:8].isna().all().all()
    assert not r.iloc[8].isna().all()


def test_alpha_072_direction():
    assert ALPHA072_DIRECTION == -1


# ---------------- Alpha #78 ----------------

def test_alpha_078_basic():
    ctx = _make_ctx(n=60)
    r = alpha_078(ctx, period=12)
    assert r.shape == ctx.close.shape
    # ma(12) 预热 11 (dev 首值 idx 11) + mad(12) 需 12 个非 NaN dev → idx 22
    assert r.iloc[:22].isna().all().all()
    assert not r.iloc[22].isna().all()


def test_alpha_078_direction():
    assert ALPHA078_DIRECTION == 1


# ---------------- Alpha #82 ----------------

def test_alpha_082_basic():
    ctx = _make_ctx(n=60)
    r = alpha_082(ctx, rsv_period=9, sma_n=20, sma_m=1)
    assert r.shape == ctx.close.shape
    assert r.iloc[:8].isna().all().all()
    assert not r.iloc[8].isna().all()


def test_alpha_082_direction():
    assert ALPHA082_DIRECTION == -1


# ---------------- 完整备注字段检查 ----------------

_REQUIRED_FIELDS = [
    "公式", "公式解释", "分类", "信号方向", "数据来源与频率",
    "算子依赖", "背后逻辑", "适用场景", "变种与优化", "注意事项",
]


@pytest.mark.parametrize(
    "modname",
    [
        "quantlab.factors.alpha191.alpha_031",
        "quantlab.factors.alpha191.alpha_034",
        "quantlab.factors.alpha191.alpha_046",
        "quantlab.factors.alpha191.alpha_047",
        "quantlab.factors.alpha191.alpha_065",
        "quantlab.factors.alpha191.alpha_066",
        "quantlab.factors.alpha191.alpha_071",
        "quantlab.factors.alpha191.alpha_072",
        "quantlab.factors.alpha191.alpha_078",
        "quantlab.factors.alpha191.alpha_082",
    ],
)
def test_docstring_has_all_10_required_fields(modname):
    import importlib

    mod = importlib.import_module(modname)
    doc = mod.__doc__ or ""
    missing = [f for f in _REQUIRED_FIELDS if f not in doc]
    assert not missing, f"{modname} 完整备注缺少字段: {missing}"
