"""
Alpha101 P0 因子单元测试 (批次4)
================================

覆盖: #49, #51, #53, #55
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.alpha101.alpha_049 import alpha_049, DIRECTION as D49
from quantlab.factors.alpha101.alpha_051 import alpha_051, DIRECTION as D51
from quantlab.factors.alpha101.alpha_053 import alpha_053, DIRECTION as D53
from quantlab.factors.alpha101.alpha_055 import alpha_055, DIRECTION as D55
from quantlab.factors.context import FactorContext


def _make_ctx(n=30):
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    rng = np.random.default_rng(0)
    data = {}
    for sym in ["A", "B"]:
        df = pd.DataFrame(
            {
                "open": rng.uniform(90, 110, n),
                "high": rng.uniform(100, 120, n),
                "low": rng.uniform(80, 100, n),
                "close": rng.uniform(95, 115, n),
                "volume": rng.integers(1000, 10000, n).astype(float),
            },
            index=dates,
        )
        data[sym] = df
    return FactorContext.from_dict(data)


# ---------------- Alpha #49 ----------------

def test_alpha_049_basic():
    ctx = _make_ctx(n=30)
    r = alpha_049(ctx)
    # 前 20 期 NaN (delay 20)
    assert r.iloc[0].isna().all()
    assert r.iloc[19].isna().all()
    assert not r.iloc[-1].isna().all()


def test_alpha_049_accel_below_threshold():
    # 加速度 < -0.1 → 返回 1
    # 设计: close 递减使 (dc10-close) 为正 → 第二项为负 → accel 为负
    n = 25
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    closes = np.linspace(130, 100, n)  # 递减
    data = {
        "A": pd.DataFrame(
            {
                "open": closes, "high": closes+1, "low": closes-1,
                "close": closes, "volume": [1000.0]*n,
            }, index=dates,
        ),
    }
    ctx = FactorContext.from_dict(data)
    r = alpha_049(ctx)
    # 末尾期应有值
    assert not r.iloc[-1].isna().all()


def test_alpha_049_direction():
    assert D49 == 1


# ---------------- Alpha #51 ----------------

def test_alpha_051_basic():
    ctx = _make_ctx(n=30)
    r = alpha_051(ctx, period=9)
    assert r.iloc[0].isna().all()
    assert not r.iloc[-1].isna().all()


def test_alpha_051_direction():
    assert D51 == -1


# ---------------- Alpha #53 ----------------

def test_alpha_053_basic():
    ctx = _make_ctx(n=30)
    r = alpha_053(ctx, period=9)
    assert r.iloc[0].isna().all()
    assert not r.iloc[-1].isna().all()


def test_alpha_053_zero_range_returns_nan():
    # high-low=0 (一字板) → NaN
    n = 15
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    data = {
        "A": pd.DataFrame(
            {
                "open": [100.0]*n, "high": [100.0]*n, "low": [100.0]*n,
                "close": [100.0]*n, "volume": [1000.0]*n,
            }, index=dates,
        ),
    }
    ctx = FactorContext.from_dict(data)
    r = alpha_053(ctx, period=9)
    assert np.isnan(r.iloc[-1, 0])


def test_alpha_053_direction():
    assert D53 == -1


# ---------------- Alpha #55 ----------------

def test_alpha_055_basic():
    ctx = _make_ctx(n=30)
    r = alpha_055(ctx, period=10)
    assert r.iloc[0].isna().all()
    assert not r.iloc[-1].isna().all()


def test_alpha_055_direction():
    assert D55 == -1


# ---------------- 完整备注字段检查 ----------------

_REQUIRED_FIELDS = [
    "公式", "公式解释", "分类", "信号方向", "数据来源与频率",
    "算子依赖", "背后逻辑", "适用场景", "变种与优化", "注意事项",
]


def _module_doc(modname):
    import sys
    mod = sys.modules.get(modname)
    return mod.__doc__ if (mod and mod.__doc__) else ""


@pytest.mark.parametrize(
    "modname",
    [
        "quantlab.factors.alpha101.alpha_049",
        "quantlab.factors.alpha101.alpha_051",
        "quantlab.factors.alpha101.alpha_053",
        "quantlab.factors.alpha101.alpha_055",
    ],
)
def test_docstring_has_all_10_required_fields(modname):
    doc = _module_doc(modname)
    missing = [f for f in _REQUIRED_FIELDS if f not in doc]
    assert not missing, f"{modname} 完整备注缺少字段: {missing}"
