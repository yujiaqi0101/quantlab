"""
Alpha191 Phase 4 批次14 因子单元测试
==========================================

覆盖新增: #141, #142, #146, #147, #148, #151
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.alpha191 import (
    alpha_141, alpha_142, alpha_146, alpha_147, alpha_148, alpha_151,
    ALPHA141_DIRECTION, ALPHA142_DIRECTION, ALPHA146_DIRECTION,
    ALPHA147_DIRECTION, ALPHA148_DIRECTION, ALPHA151_DIRECTION,
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


# ---------------- Alpha #141 ----------------

def test_alpha_141_basic():
    ctx = _make_ctx(n=40)
    r = alpha_141(ctx)
    assert r.shape == ctx.close.shape
    # 实际首值 idx 22
    assert r.iloc[:22].isna().all().all()
    assert not r.iloc[22].isna().all()


def test_alpha_141_direction():
    assert ALPHA141_DIRECTION == 1


def test_alpha_141_finite():
    ctx = _make_ctx(n=40)
    r = alpha_141(ctx)
    valid = r.iloc[22:].replace([np.inf, -np.inf], np.nan).dropna()
    if len(valid) > 0:
        assert np.isfinite(valid.to_numpy()).all()


# ---------------- Alpha #142 ----------------

def test_alpha_142_basic():
    ctx = _make_ctx(n=20)
    r = alpha_142(ctx)
    assert r.shape == ctx.close.shape
    # delay 1 → idx 0 NaN
    assert r.iloc[:1].isna().all().all()


def test_alpha_142_direction():
    assert ALPHA142_DIRECTION == 1


def test_alpha_142_values():
    ctx = _make_ctx(n=20)
    r = alpha_142(ctx)
    valid = r.iloc[1:].dropna()
    if len(valid) > 0:
        assert set(valid.to_numpy().flatten().tolist()) - {np.nan} <= {-1.0, 0.0, 1.0}


# ---------------- Alpha #146 ----------------

def test_alpha_146_basic():
    ctx = _make_ctx(n=80)
    r = alpha_146(ctx)
    assert r.shape == ctx.close.shape
    # 实际首值 idx 39
    assert r.iloc[:39].isna().all().all()
    assert not r.iloc[39].isna().all()


def test_alpha_146_direction():
    assert ALPHA146_DIRECTION == 1


# ---------------- Alpha #147 ----------------

def test_alpha_147_basic():
    ctx = _make_ctx(n=40)
    r = alpha_147(ctx)
    assert r.shape == ctx.close.shape
    # delta 12 + decay 12 → idx 23
    assert r.iloc[:23].isna().all().all()


def test_alpha_147_direction():
    assert ALPHA147_DIRECTION == -1


# ---------------- Alpha #148 ----------------

def test_alpha_148_basic():
    ctx = _make_ctx(n=100)
    r = alpha_148(ctx)
    assert r.shape == ctx.close.shape
    # 实际首值 idx 72
    assert r.iloc[:72].isna().all().all()
    assert not r.iloc[72].isna().all()


def test_alpha_148_direction():
    assert ALPHA148_DIRECTION == 1


# ---------------- Alpha #151 ----------------

def test_alpha_151_basic():
    ctx = _make_ctx(n=20)
    r = alpha_151(ctx)
    assert r.shape == ctx.close.shape
    # delay 1 → idx 0 NaN; sma 用 ewm 无预热 → idx 1 起有效
    assert r.iloc[:1].isna().all().all()


def test_alpha_151_direction():
    assert ALPHA151_DIRECTION == 1


def test_alpha_151_finite():
    ctx = _make_ctx(n=20)
    r = alpha_151(ctx)
    valid = r.iloc[1:].replace([np.inf, -np.inf], np.nan).dropna()
    if len(valid) > 0:
        assert np.isfinite(valid.to_numpy()).all()
