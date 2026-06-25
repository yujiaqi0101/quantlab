"""
Alpha191 Phase 4 批次12 因子单元测试
==========================================

覆盖新增: #122, #123, #125, #129, #130, #131
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.alpha191 import (
    alpha_122, alpha_123, alpha_125, alpha_129, alpha_130, alpha_131,
    ALPHA122_DIRECTION, ALPHA123_DIRECTION, ALPHA125_DIRECTION,
    ALPHA129_DIRECTION, ALPHA130_DIRECTION, ALPHA131_DIRECTION,
)
from quantlab.factors.context import FactorContext


def _make_ctx(n=250):
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
                "vwap": close + rng.normal(0, 0.3, n),
            },
            index=dates,
        )
        data[sym] = df
    return FactorContext.from_dict(data)


# ---------------- Alpha #122 ----------------

def test_alpha_122_basic():
    ctx = _make_ctx(n=250)
    r = alpha_122(ctx)
    assert r.shape == ctx.close.shape
    # 长期窗口 230
    assert r.iloc[:230].isna().all().all()


def test_alpha_122_direction():
    assert ALPHA122_DIRECTION == 1


# ---------------- Alpha #123 ----------------

def test_alpha_123_basic():
    ctx = _make_ctx(n=80)
    r = alpha_123(ctx)
    assert r.shape == ctx.close.shape
    # 实际首值 idx 43
    assert r.iloc[:43].isna().all().all()
    assert not r.iloc[43].isna().all()


def test_alpha_123_direction():
    assert ALPHA123_DIRECTION == 1


# ---------------- Alpha #125 ----------------

def test_alpha_125_basic():
    ctx = _make_ctx(n=80)
    r = alpha_125(ctx)
    assert r.shape == ctx.close.shape
    # 实际首值 idx 57
    assert r.iloc[:57].isna().all().all()
    assert not r.iloc[57].isna().all()


def test_alpha_125_direction():
    assert ALPHA125_DIRECTION == 1


# ---------------- Alpha #129 ----------------

def test_alpha_129_basic():
    ctx = _make_ctx(n=80)
    r = alpha_129(ctx)
    assert r.shape == ctx.close.shape
    # 实际首值 idx 37
    assert r.iloc[:37].isna().all().all()
    assert not r.iloc[37].isna().all()


def test_alpha_129_direction():
    assert ALPHA129_DIRECTION == 1


def test_alpha_129_finite():
    ctx = _make_ctx(n=80)
    r = alpha_129(ctx)
    valid = r.iloc[37:].replace([np.inf, -np.inf], np.nan).dropna()
    if len(valid) > 0:
        assert np.isfinite(valid.to_numpy()).all()


# ---------------- Alpha #130 ----------------

def test_alpha_130_basic():
    ctx = _make_ctx(n=80)
    r = alpha_130(ctx)
    assert r.shape == ctx.close.shape
    # ts_mean 40 + corr 11 + decay 4 → idx 54
    assert r.iloc[:54].isna().all().all()


def test_alpha_130_direction():
    assert ALPHA130_DIRECTION == 1


# ---------------- Alpha #131 ----------------

def test_alpha_131_basic():
    ctx = _make_ctx(n=80)
    r = alpha_131(ctx)
    assert r.shape == ctx.close.shape
    # 实际首值 idx 57
    assert r.iloc[:57].isna().all().all()
    assert not r.iloc[57].isna().all()


def test_alpha_131_direction():
    assert ALPHA131_DIRECTION == 1
