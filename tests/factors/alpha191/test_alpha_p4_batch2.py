"""
Alpha191 Phase 4 批次2 因子单元测试
==========================================

覆盖: #24, #27, #28, #29, #38
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.alpha191 import (
    alpha_024, alpha_027, alpha_028, alpha_029, alpha_038,
    ALPHA024_DIRECTION, ALPHA027_DIRECTION, ALPHA028_DIRECTION,
    ALPHA029_DIRECTION, ALPHA038_DIRECTION,
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


# ---------------- Alpha #24 ----------------

def test_alpha_024_basic():
    ctx = _make_ctx(n=40)
    r = alpha_024(ctx, period=5, sma_n=5, sma_m=1)
    assert r.shape == ctx.close.shape
    # delay 预热 4，ewm 无严格预热但首值从有动量处开始
    assert r.iloc[:5].isna().all().all()
    assert not r.iloc[5].isna().all()


def test_alpha_024_direction():
    assert ALPHA024_DIRECTION == 1


# ---------------- Alpha #27 ----------------

def test_alpha_027_basic():
    ctx = _make_ctx(n=40)
    r = alpha_027(ctx, short_period=3, long_period=6, wma_period=12)
    assert r.shape == ctx.close.shape
    # delay(6) 预热 5 (idx6 首值) + wma(12) 需 12 个非 NaN → idx 17 首值
    assert r.iloc[:17].isna().all().all()
    assert not r.iloc[17].isna().all()


def test_alpha_027_direction():
    assert ALPHA027_DIRECTION == 1


# ---------------- Alpha #28 ----------------

def test_alpha_028_basic():
    ctx = _make_ctx(n=40)
    r = alpha_028(ctx, rsv_period=9, sma_n=3, sma_m=1)
    assert r.shape == ctx.close.shape
    # rsv (ts_min/ts_max 9) 预热 8，ewm 从首个非 NaN 开始 → idx 8 首值
    assert r.iloc[:8].isna().all().all()
    assert not r.iloc[8].isna().all()


def test_alpha_028_direction():
    assert ALPHA028_DIRECTION == 1


def test_alpha_028_k_range():
    """K 值通常落在 0~100 附近。"""
    ctx = _make_ctx(n=40)
    r = alpha_028(ctx)
    valid = r.dropna()
    assert (valid >= -50).all().all()
    assert (valid <= 150).all().all()


# ---------------- Alpha #29 ----------------

def test_alpha_029_basic():
    ctx = _make_ctx(n=40)
    r = alpha_029(ctx, period=6)
    assert r.shape == ctx.close.shape
    assert r.iloc[:6].isna().all().all()
    assert not r.iloc[6].isna().all()


def test_alpha_029_direction():
    assert ALPHA029_DIRECTION == 1


# ---------------- Alpha #38 ----------------

def test_alpha_038_basic():
    ctx = _make_ctx(n=40)
    r = alpha_038(ctx, ma_period=20, delta_period=2)
    assert r.shape == ctx.close.shape
    # ts_sum(20) 预热 19 → idx 19 首值
    assert r.iloc[:19].isna().all().all()
    assert not r.iloc[19].isna().all()


def test_alpha_038_direction():
    assert ALPHA038_DIRECTION == -1


# ---------------- 完整备注字段检查 ----------------

_REQUIRED_FIELDS = [
    "公式", "公式解释", "分类", "信号方向", "数据来源与频率",
    "算子依赖", "背后逻辑", "适用场景", "变种与优化", "注意事项",
]


@pytest.mark.parametrize(
    "modname",
    [
        "quantlab.factors.alpha191.alpha_024",
        "quantlab.factors.alpha191.alpha_027",
        "quantlab.factors.alpha191.alpha_028",
        "quantlab.factors.alpha191.alpha_029",
        "quantlab.factors.alpha191.alpha_038",
    ],
)
def test_docstring_has_all_10_required_fields(modname):
    import importlib

    mod = importlib.import_module(modname)
    doc = mod.__doc__ or ""
    missing = [f for f in _REQUIRED_FIELDS if f not in doc]
    assert not missing, f"{modname} 完整备注缺少字段: {missing}"
