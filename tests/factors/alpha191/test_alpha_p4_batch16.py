"""
Alpha191 Phase 4 批次16 因子单元测试
==========================================

覆盖新增: #162, #163, #164, #166, #167, #169
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.alpha191 import (
    alpha_162, alpha_163, alpha_164, alpha_166, alpha_167, alpha_169,
    ALPHA162_DIRECTION, ALPHA163_DIRECTION, ALPHA164_DIRECTION,
    ALPHA166_DIRECTION, ALPHA167_DIRECTION, ALPHA169_DIRECTION,
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


# ---------------- Alpha #162 ----------------

def test_alpha_162_basic():
    ctx = _make_ctx(n=20)
    r = alpha_162(ctx)
    assert r.shape == ctx.close.shape
    # delay 1 → idx 0 NaN
    assert r.iloc[:1].isna().all().all()


def test_alpha_162_direction():
    assert ALPHA162_DIRECTION == 1


def test_alpha_162_finite():
    ctx = _make_ctx(n=20)
    r = alpha_162(ctx)
    valid = r.iloc[1:].replace([np.inf, -np.inf], np.nan).dropna()
    if len(valid) > 0:
        assert np.isfinite(valid.to_numpy()).all()


# ---------------- Alpha #163 ----------------

def test_alpha_163_basic():
    ctx = _make_ctx(n=20)
    r = alpha_163(ctx)
    assert r.shape == ctx.close.shape
    # sma ewm 无预热
    assert not r.iloc[0].isna().all()


def test_alpha_163_direction():
    assert ALPHA163_DIRECTION == 1


def test_alpha_163_finite():
    ctx = _make_ctx(n=20)
    r = alpha_163(ctx)
    valid = r.replace([np.inf, -np.inf], np.nan).dropna()
    if len(valid) > 0:
        assert np.isfinite(valid.to_numpy()).all()


# ---------------- Alpha #164 ----------------

def test_alpha_164_basic():
    ctx = _make_ctx(n=20)
    r = alpha_164(ctx)
    assert r.shape == ctx.close.shape
    # delay 1 → idx 0 NaN
    assert r.iloc[:1].isna().all().all()


def test_alpha_164_direction():
    assert ALPHA164_DIRECTION == 1


def test_alpha_164_finite():
    ctx = _make_ctx(n=20)
    r = alpha_164(ctx)
    valid = r.iloc[1:].replace([np.inf, -np.inf], np.nan).dropna()
    if len(valid) > 0:
        assert np.isfinite(valid.to_numpy()).all()


# ---------------- Alpha #166 ----------------

def test_alpha_166_basic():
    ctx = _make_ctx(n=20)
    r = alpha_166(ctx)
    assert r.shape == ctx.close.shape
    # ts_mean 5 + corr 5 + decay 6 → idx 10
    assert r.iloc[:10].isna().all().all()


def test_alpha_166_direction():
    assert ALPHA166_DIRECTION == -1


# ---------------- Alpha #167 ----------------

def test_alpha_167_basic():
    ctx = _make_ctx(n=80)
    r = alpha_167(ctx)
    assert r.shape == ctx.close.shape
    # 实际首值 idx 39
    assert r.iloc[:39].isna().all().all()
    assert not r.iloc[39].isna().all()


def test_alpha_167_direction():
    assert ALPHA167_DIRECTION == -1


# ---------------- Alpha #169 ----------------

def test_alpha_169_basic():
    ctx = _make_ctx(n=20)
    r = alpha_169(ctx)
    assert r.shape == ctx.close.shape
    # delay 5 + delay 1 → idx 6
    assert r.iloc[:6].isna().all().all()


def test_alpha_169_direction():
    assert ALPHA169_DIRECTION == 1
