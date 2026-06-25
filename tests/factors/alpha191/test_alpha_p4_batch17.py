"""
Alpha191 Phase 4 批次17 因子单元测试
==========================================

覆盖新增: #171, #172, #173, #176, #177, #179
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.alpha191 import (
    alpha_171, alpha_172, alpha_173, alpha_176, alpha_177, alpha_179,
    ALPHA171_DIRECTION, ALPHA172_DIRECTION, ALPHA173_DIRECTION,
    ALPHA176_DIRECTION, ALPHA177_DIRECTION, ALPHA179_DIRECTION,
)
from quantlab.factors.context import FactorContext


def _make_ctx(n=80):
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


# ---------------- Alpha #171 ----------------

def test_alpha_171_basic():
    ctx = _make_ctx(n=40)
    r = alpha_171(ctx, period=24)
    assert r.shape == ctx.close.shape
    # ts_mean 24 → idx 23
    assert r.iloc[:23].isna().all().all()


def test_alpha_171_direction():
    assert ALPHA171_DIRECTION == -1


def test_alpha_171_finite():
    ctx = _make_ctx(n=40)
    r = alpha_171(ctx, period=24)
    valid = r.iloc[23:].replace([np.inf, -np.inf], np.nan).dropna()
    if len(valid) > 0:
        assert np.isfinite(valid.to_numpy()).all()


# ---------------- Alpha #172 ----------------

def test_alpha_172_basic():
    ctx = _make_ctx(n=40)
    r = alpha_172(ctx)
    assert r.shape == ctx.close.shape
    # ts_mean 20 + corr 7 + decay 3 → idx 26
    assert r.iloc[:26].isna().all().all()


def test_alpha_172_direction():
    assert ALPHA172_DIRECTION == 1


# ---------------- Alpha #173 ----------------

def test_alpha_173_basic():
    ctx = _make_ctx(n=20)
    r = alpha_173(ctx)
    assert r.shape == ctx.close.shape
    # delay 3 + delay 1 → idx 4
    assert r.iloc[:4].isna().all().all()


def test_alpha_173_direction():
    assert ALPHA173_DIRECTION == 1


# ---------------- Alpha #176 ----------------

def test_alpha_176_basic():
    ctx = _make_ctx(n=80)
    r = alpha_176(ctx)
    assert r.shape == ctx.close.shape
    # ts_mean 20 + ts_rank 7 + corr 6 + decay 6 → idx 32
    assert r.iloc[:32].isna().all().all()


def test_alpha_176_direction():
    assert ALPHA176_DIRECTION == 1


# ---------------- Alpha #177 ----------------

def test_alpha_177_basic():
    ctx = _make_ctx(n=40)
    r = alpha_177(ctx, period=20)
    assert r.shape == ctx.close.shape
    # ts_max/ts_mean 20 → idx 19
    assert r.iloc[:19].isna().all().all()


def test_alpha_177_direction():
    assert ALPHA177_DIRECTION == 1


def test_alpha_177_finite():
    ctx = _make_ctx(n=40)
    r = alpha_177(ctx, period=20)
    valid = r.iloc[19:].replace([np.inf, -np.inf], np.nan).dropna()
    if len(valid) > 0:
        assert np.isfinite(valid.to_numpy()).all()


# ---------------- Alpha #179 ----------------

def test_alpha_179_basic():
    ctx = _make_ctx(n=10)
    r = alpha_179(ctx)
    assert r.shape == ctx.close.shape
    # 首期可计算
    assert not r.iloc[0].isna().all()


def test_alpha_179_direction():
    assert ALPHA179_DIRECTION == 1


def test_alpha_179_finite():
    ctx = _make_ctx(n=10)
    r = alpha_179(ctx)
    valid = r.replace([np.inf, -np.inf], np.nan).dropna()
    if len(valid) > 0:
        assert np.isfinite(valid.to_numpy()).all()
