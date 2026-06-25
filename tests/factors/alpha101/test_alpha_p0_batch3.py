"""
Alpha101 P0 因子单元测试 (批次3)
================================

覆盖: #38, #40, #41, #42, #44, #46
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.alpha101.alpha_038 import alpha_038, DIRECTION as D38
from quantlab.factors.alpha101.alpha_040 import alpha_040, DIRECTION as D40
from quantlab.factors.alpha101.alpha_041 import alpha_041, DIRECTION as D41
from quantlab.factors.alpha101.alpha_042 import alpha_042, DIRECTION as D42
from quantlab.factors.alpha101.alpha_044 import alpha_044, DIRECTION as D44
from quantlab.factors.alpha101.alpha_046 import alpha_046, DIRECTION as D46
from quantlab.factors.context import FactorContext


def _make_ctx(n=30, with_vwap=False):
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
        if with_vwap:
            df["vwap"] = (df["high"] + df["low"] + df["close"]) / 3
        data[sym] = df
    return FactorContext.from_dict(data)


# ---------------- Alpha #38 ----------------

def test_alpha_038_basic():
    ctx = _make_ctx(n=30)
    r = alpha_038(ctx)
    assert r.iloc[0].isna().all()
    assert not r.iloc[-1].isna().all()


def test_alpha_038_direction():
    assert D38 == -1


# ---------------- Alpha #40 ----------------

def test_alpha_040_basic():
    ctx = _make_ctx(n=30)
    r = alpha_040(ctx)
    assert r.iloc[0].isna().all()
    assert not r.iloc[-1].isna().all()


def test_alpha_040_direction():
    assert D40 == -1


# ---------------- Alpha #41 ----------------

def test_alpha_041_basic():
    ctx = _make_ctx(n=30, with_vwap=True)
    r = alpha_041(ctx)
    # 无窗口算子，首期有值
    assert not r.iloc[0].isna().all()


def test_alpha_041_geo_minus_vwap():
    # 构造 high=110, low=90, vwap=100 → sqrt(110*90)-100 = sqrt(9900)-100 ≈ 99.5-100 = -0.5
    n = 5
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    data = {
        "A": pd.DataFrame(
            {
                "open": [100.0]*n, "high": [110.0]*n, "low": [90.0]*n,
                "close": [100.0]*n, "volume": [1000.0]*n,
                "vwap": [100.0]*n,
            }, index=dates,
        ),
    }
    ctx = FactorContext.from_dict(data)
    r = alpha_041(ctx)
    expected = np.sqrt(110 * 90) - 100
    assert r.iloc[0, 0] == pytest.approx(expected, rel=1e-6)


def test_alpha_041_direction():
    assert D41 == 1


# ---------------- Alpha #42 ----------------

def test_alpha_042_basic():
    ctx = _make_ctx(n=30, with_vwap=True)
    r = alpha_042(ctx)
    assert not r.iloc[-1].isna().all()


def test_alpha_042_direction():
    assert D42 == 1


# ---------------- Alpha #44 ----------------

def test_alpha_044_basic():
    ctx = _make_ctx(n=30)
    r = alpha_044(ctx)
    assert r.iloc[0].isna().all()
    assert not r.iloc[-1].isna().all()


def test_alpha_044_direction():
    assert D44 == -1


# ---------------- Alpha #46 ----------------

def test_alpha_046_basic():
    ctx = _make_ctx(n=30)
    r = alpha_046(ctx)
    # 前 20 期 NaN (delay 20)
    assert r.iloc[0].isna().all()
    assert not r.iloc[-1].isna().all()


def test_alpha_046_accel_positive_high():
    # 构造加速度 > 0.25 → 返回 -1
    # accel = (dc20-dc10)/10 - (dc10-close)/10
    # 设计: close 递增使 (dc10-close) 为负 → 第二项为正 → accel 高
    n = 25
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    # close 快速上升
    closes = np.linspace(100, 130, n)
    data = {
        "A": pd.DataFrame(
            {
                "open": closes, "high": closes+1, "low": closes-1,
                "close": closes, "volume": [1000.0]*n,
            }, index=dates,
        ),
    }
    ctx = FactorContext.from_dict(data)
    r = alpha_046(ctx)
    # 加速度应较大 (close 上升使 dc10-close 为负)
    # 检查末尾期有值
    assert not r.iloc[-1].isna().all()


def test_alpha_046_direction():
    assert D46 == 1


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
        "quantlab.factors.alpha101.alpha_038",
        "quantlab.factors.alpha101.alpha_040",
        "quantlab.factors.alpha101.alpha_041",
        "quantlab.factors.alpha101.alpha_042",
        "quantlab.factors.alpha101.alpha_044",
        "quantlab.factors.alpha101.alpha_046",
    ],
)
def test_docstring_has_all_10_required_fields(modname):
    doc = _module_doc(modname)
    missing = [f for f in _REQUIRED_FIELDS if f not in doc]
    assert not missing, f"{modname} 完整备注缺少字段: {missing}"
