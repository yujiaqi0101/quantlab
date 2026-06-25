"""
Alpha191 Phase 4 批次4 因子单元测试
==========================================

覆盖: #2, #12, #13, #19, #22, #26
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.alpha191 import (
    alpha_002, alpha_012, alpha_013, alpha_019, alpha_022, alpha_026,
    ALPHA002_DIRECTION, ALPHA012_DIRECTION, ALPHA013_DIRECTION,
    ALPHA019_DIRECTION, ALPHA022_DIRECTION, ALPHA026_DIRECTION,
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


# ---------------- Alpha #2 ----------------

def test_alpha_002_basic():
    ctx = _make_ctx(n=60)
    r = alpha_002(ctx, period=1)
    assert r.shape == ctx.close.shape
    # body_pos 用当日 high/low/close 无预热，delta(1) 需前 1 期 → idx 1 首值
    assert r.iloc[:1].isna().all().all()
    assert not r.iloc[1].isna().all()


def test_alpha_002_direction():
    assert ALPHA002_DIRECTION == -1


def test_alpha_002_zero_range():
    """HIGH=LOW 时分母为 0，应返回 NaN。"""
    dates = pd.date_range("2026-01-05", periods=5, freq="B")
    df = pd.DataFrame(
        {
            "open": 100.0, "high": 100.0, "low": 100.0,
            "close": 100.0, "volume": 1000.0, "amount": 100000.0,
        },
        index=dates,
    )
    ctx = FactorContext.from_dict({"A": df})
    r = alpha_002(ctx)
    assert r.isna().all().all()


# ---------------- Alpha #12 ----------------

def test_alpha_012_basic():
    ctx = _make_ctx(n=60)
    r = alpha_012(ctx, vwap_period=10)
    assert r.shape == ctx.close.shape
    # ts_sum(10) 预热 9 → idx 9 首值
    assert r.iloc[:9].isna().all().all()
    assert not r.iloc[9].isna().all()


def test_alpha_012_direction():
    assert ALPHA012_DIRECTION == -1


# ---------------- Alpha #13 ----------------

def test_alpha_013_basic():
    ctx = _make_ctx(n=60)
    r = alpha_013(ctx)
    assert r.shape == ctx.close.shape
    # 纯当日计算，无预热
    assert not r.iloc[0].isna().all()


def test_alpha_013_direction():
    assert ALPHA013_DIRECTION == 1


# ---------------- Alpha #19 ----------------

def test_alpha_019_basic():
    ctx = _make_ctx(n=60)
    r = alpha_019(ctx, period=5)
    assert r.shape == ctx.close.shape
    # delay(5) 预热 5 → idx 5 首值
    assert r.iloc[:5].isna().all().all()
    assert not r.iloc[5].isna().all()


def test_alpha_019_direction():
    assert ALPHA019_DIRECTION == 1


def test_alpha_019_equal_case():
    """收盘价与前价相等时应返回 0。"""
    dates = pd.date_range("2026-01-05", periods=10, freq="B")
    close = pd.Series([100.0] * 10, index=dates)
    df = pd.DataFrame(
        {
            "open": 100.0, "high": 101.0, "low": 99.0,
            "close": close, "volume": 1000.0, "amount": 100000.0,
        },
        index=dates,
    )
    ctx = FactorContext.from_dict({"A": df})
    r = alpha_019(ctx, period=5)
    assert (r.iloc[5:] == 0.0).all().all()


# ---------------- Alpha #22 ----------------

def test_alpha_022_basic():
    ctx = _make_ctx(n=60)
    r = alpha_022(ctx, mean_period=6, delta_period=3, sma_n=12, sma_m=1)
    assert r.shape == ctx.close.shape
    # ts_mean(6) 预热 5 + delta(3) 预热 3 → idx 8 首个非 NaN
    assert r.iloc[:8].isna().all().all()
    assert not r.iloc[8].isna().all()


def test_alpha_022_direction():
    assert ALPHA022_DIRECTION == -1


# ---------------- Alpha #26 ----------------

def test_alpha_026_basic():
    ctx = _make_ctx(n=260)
    r = alpha_026(ctx, short_period=7, delay_period=5, corr_period=230)
    assert r.shape == ctx.close.shape
    # delay(5) 预热 5 + corr(230) 预热 229 → idx 234 首值
    assert r.iloc[:234].isna().all().all()
    assert not r.iloc[234].isna().all()


def test_alpha_026_direction():
    assert ALPHA026_DIRECTION == 1


# ---------------- 完整备注字段检查 ----------------

_REQUIRED_FIELDS = [
    "公式", "公式解释", "分类", "信号方向", "数据来源与频率",
    "算子依赖", "背后逻辑", "适用场景", "变种与优化", "注意事项",
]


@pytest.mark.parametrize(
    "modname",
    [
        "quantlab.factors.alpha191.alpha_002",
        "quantlab.factors.alpha191.alpha_012",
        "quantlab.factors.alpha191.alpha_013",
        "quantlab.factors.alpha191.alpha_019",
        "quantlab.factors.alpha191.alpha_022",
        "quantlab.factors.alpha191.alpha_026",
    ],
)
def test_docstring_has_all_10_required_fields(modname):
    import importlib

    mod = importlib.import_module(modname)
    doc = mod.__doc__ or ""
    missing = [f for f in _REQUIRED_FIELDS if f not in doc]
    assert not missing, f"{modname} 完整备注缺少字段: {missing}"
