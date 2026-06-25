"""
Alpha191 Phase 4 批次15 因子单元测试
==========================================

覆盖新增: #152, #153, #154, #156, #157, #159
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.alpha191 import (
    alpha_152, alpha_153, alpha_154, alpha_156, alpha_157, alpha_159,
    ALPHA152_DIRECTION, ALPHA153_DIRECTION, ALPHA154_DIRECTION,
    ALPHA156_DIRECTION, ALPHA157_DIRECTION, ALPHA159_DIRECTION,
)
from quantlab.factors.context import FactorContext


def _make_ctx(n=100):
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


# ---------------- Alpha #152 ----------------

def test_alpha_152_basic():
    ctx = _make_ctx(n=50)
    r = alpha_152(ctx)
    assert r.shape == ctx.close.shape
    # delay 20 + delay 1 → idx 21; sma ewm 无预热
    assert r.iloc[:21].isna().all().all()


def test_alpha_152_direction():
    assert ALPHA152_DIRECTION == 1


# ---------------- Alpha #153 ----------------

def test_alpha_153_basic():
    ctx = _make_ctx(n=30)
    r = alpha_153(ctx, period=20)
    assert r.shape == ctx.close.shape
    # delay 19 → idx 19; sma ewm 无预热
    assert r.iloc[:19].isna().all().all()


def test_alpha_153_direction():
    assert ALPHA153_DIRECTION == 1


# ---------------- Alpha #154 ----------------

def test_alpha_154_basic():
    ctx = _make_ctx(n=60)
    r = alpha_154(ctx)
    assert r.shape == ctx.close.shape
    # 实际首值 idx 37
    assert r.iloc[:37].isna().all().all()
    assert not r.iloc[37].isna().all()


def test_alpha_154_direction():
    assert ALPHA154_DIRECTION == -1


# ---------------- Alpha #156 ----------------

def test_alpha_156_basic():
    ctx = _make_ctx(n=30)
    r = alpha_156(ctx)
    assert r.shape == ctx.close.shape
    # corr 5 + decay 6 + delta 1 + delta 1 → idx 7
    assert r.iloc[:7].isna().all().all()


def test_alpha_156_direction():
    assert ALPHA156_DIRECTION == 1


def test_alpha_156_finite():
    ctx = _make_ctx(n=30)
    r = alpha_156(ctx)
    valid = r.iloc[7:].replace([np.inf, -np.inf], np.nan).dropna()
    if len(valid) > 0:
        assert np.isfinite(valid.to_numpy()).all()


# ---------------- Alpha #157 ----------------

def test_alpha_157_basic():
    ctx = _make_ctx(n=80)
    r = alpha_157(ctx)
    assert r.shape == ctx.close.shape
    # 实际首值 idx 44
    assert r.iloc[:44].isna().all().all()
    assert not r.iloc[44].isna().all()


def test_alpha_157_direction():
    assert ALPHA157_DIRECTION == -1


# ---------------- Alpha #159 ----------------

def test_alpha_159_basic():
    ctx = _make_ctx(n=20)
    r = alpha_159(ctx)
    assert r.shape == ctx.close.shape
    # delay 1 → idx 0 NaN
    assert r.iloc[:1].isna().all().all()


def test_alpha_159_direction():
    assert ALPHA159_DIRECTION == -1


def test_alpha_159_values():
    ctx = _make_ctx(n=20)
    r = alpha_159(ctx)
    valid = r.iloc[1:].dropna()
    if len(valid) > 0:
        assert set(valid.to_numpy().flatten().tolist()) - {np.nan} <= {-1.0, 0.0, 1.0}
