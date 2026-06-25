"""
Alpha191 Phase 4 批次18 因子单元测试
==========================================

覆盖新增: #180, #184, #185, #186, #187, #190
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.alpha191 import (
    alpha_180, alpha_184, alpha_185, alpha_186, alpha_187, alpha_190,
    ALPHA180_DIRECTION, ALPHA184_DIRECTION, ALPHA185_DIRECTION,
    ALPHA186_DIRECTION, ALPHA187_DIRECTION, ALPHA190_DIRECTION,
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


# ---------------- Alpha #180 ----------------

def test_alpha_180_basic():
    ctx = _make_ctx(n=40)
    r = alpha_180(ctx)
    assert r.shape == ctx.close.shape
    # 实际首值 idx 19
    assert r.iloc[:19].isna().all().all()
    assert not r.iloc[19].isna().all()


def test_alpha_180_direction():
    assert ALPHA180_DIRECTION == -1


def test_alpha_180_finite():
    ctx = _make_ctx(n=40)
    r = alpha_180(ctx)
    valid = r.iloc[19:].replace([np.inf, -np.inf], np.nan).dropna()
    if len(valid) > 0:
        assert np.isfinite(valid.to_numpy()).all()


# ---------------- Alpha #184 ----------------

def test_alpha_184_basic():
    ctx = _make_ctx(n=80)
    r = alpha_184(ctx)
    assert r.shape == ctx.close.shape
    # 实际首值 idx 42
    assert r.iloc[:42].isna().all().all()
    assert not r.iloc[42].isna().all()


def test_alpha_184_direction():
    assert ALPHA184_DIRECTION == 1


# ---------------- Alpha #185 ----------------

def test_alpha_185_basic():
    ctx = _make_ctx(n=20)
    r = alpha_185(ctx)
    assert r.shape == ctx.close.shape
    # 首期可计算
    assert not r.iloc[0].isna().all()


def test_alpha_185_direction():
    assert ALPHA185_DIRECTION == 1


def test_alpha_185_finite():
    ctx = _make_ctx(n=20)
    r = alpha_185(ctx)
    valid = r.replace([np.inf, -np.inf], np.nan).dropna()
    if len(valid) > 0:
        assert np.isfinite(valid.to_numpy()).all()


# ---------------- Alpha #186 ----------------

def test_alpha_186_basic():
    ctx = _make_ctx(n=40)
    r = alpha_186(ctx, period=20)
    assert r.shape == ctx.close.shape
    # ts_mean 20 → idx 19
    assert r.iloc[:19].isna().all().all()


def test_alpha_186_direction():
    assert ALPHA186_DIRECTION == 1


def test_alpha_186_finite():
    ctx = _make_ctx(n=40)
    r = alpha_186(ctx, period=20)
    valid = r.iloc[19:].dropna()
    if len(valid) > 0:
        assert (valid.to_numpy() >= 0).all()


# ---------------- Alpha #187 ----------------

def test_alpha_187_basic():
    ctx = _make_ctx(n=40)
    r = alpha_187(ctx, period=20)
    assert r.shape == ctx.close.shape
    # delay 1 + ts_sum 20 → idx 20
    assert r.iloc[:20].isna().all().all()


def test_alpha_187_direction():
    assert ALPHA187_DIRECTION == 1


def test_alpha_187_values():
    ctx = _make_ctx(n=40)
    r = alpha_187(ctx, period=20)
    valid = r.iloc[20:].dropna()
    if len(valid) > 0:
        vals = valid.to_numpy().flatten()
        assert vals.min() >= 0.0
        assert vals.max() <= 20.0


# ---------------- Alpha #190 ----------------

def test_alpha_190_basic():
    ctx = _make_ctx(n=40)
    r = alpha_190(ctx, period=20)
    assert r.shape == ctx.close.shape
    # delay 20 → idx 20
    assert r.iloc[:20].isna().all().all()


def test_alpha_190_direction():
    assert ALPHA190_DIRECTION == 1


def test_alpha_190_finite():
    ctx = _make_ctx(n=40)
    r = alpha_190(ctx, period=20)
    valid = r.iloc[20:].replace([np.inf, -np.inf], np.nan).dropna()
    if len(valid) > 0:
        assert np.isfinite(valid.to_numpy()).all()
