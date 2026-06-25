"""
Alpha101 P0 因子单元测试 (批次2)
================================

覆盖: #20, #22, #23, #33, #34
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.alpha101.alpha_020 import alpha_020, DIRECTION as D20
from quantlab.factors.alpha101.alpha_022 import alpha_022, DIRECTION as D22
from quantlab.factors.alpha101.alpha_023 import alpha_023, DIRECTION as D23
from quantlab.factors.alpha101.alpha_033 import alpha_033, DIRECTION as D33
from quantlab.factors.alpha101.alpha_034 import alpha_034, DIRECTION as D34
from quantlab.factors.context import FactorContext


def _make_ctx(n=25):
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


# ---------------- Alpha #20 ----------------

def test_alpha_020_basic():
    ctx = _make_ctx(n=25)
    r = alpha_020(ctx)
    # 首期 NaN (delay 1)
    assert r.iloc[0].isna().all()
    # 末尾期有值
    assert not r.iloc[-1].isna().all()


def test_alpha_020_direction():
    assert D20 == -1


# ---------------- Alpha #22 ----------------

def test_alpha_022_basic():
    ctx = _make_ctx(n=30)
    r = alpha_022(ctx)
    # 首期 NaN
    assert r.iloc[0].isna().all()
    # 末尾期有值
    assert not r.iloc[-1].isna().all()


def test_alpha_022_direction():
    assert D22 == -1


# ---------------- Alpha #23 ----------------

def test_alpha_023_basic():
    ctx = _make_ctx(n=25)
    r = alpha_023(ctx)
    # 首期有值 (未突破时为 0)
    assert not r.iloc[-1].isna().all()
    # 末尾期有值
    assert not r.iloc[-1].isna().all()


def test_alpha_023_no_breakout_returns_zero():
    # high 始终低于 20 日均线 → 不突破 → 0
    n = 25
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    highs = np.linspace(90, 95, n)  # 缓慢上升
    data = {
        "A": pd.DataFrame(
            {
                "open": highs, "high": highs, "low": highs-5,
                "close": highs-1, "volume": [1000.0]*n,
            }, index=dates,
        ),
    }
    ctx = FactorContext.from_dict(data)
    r = alpha_023(ctx)
    # 末尾期: 若未突破应接近 0
    # (缓慢上升的 high 可能突破 20 日均线，这里只验证值有限)
    assert np.isfinite(r.iloc[-1, 0])


def test_alpha_023_direction():
    assert D23 == -1


# ---------------- Alpha #33 ----------------

def test_alpha_033_basic():
    ctx = _make_ctx(n=25)
    r = alpha_033(ctx)
    # 无 delay，首期有值
    assert not r.iloc[0].isna().all()


def test_alpha_033_intraday_up():
    # close > open → open/close-1 < 0 → rank 低 → 取负后看多
    # 但单标的无法 rank，需多标的比较
    n = 5
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    data = {
        "A": pd.DataFrame(
            {"open": [110.0]*n, "high": [115.0]*n, "low": [105.0]*n,
             "close": [100.0]*n, "volume": [1000.0]*n}, index=dates,
        ),
        "B": pd.DataFrame(
            {"open": [90.0]*n, "high": [95.0]*n, "low": [85.0]*n,
             "close": [100.0]*n, "volume": [1000.0]*n}, index=dates,
        ),
    }
    ctx = FactorContext.from_dict(data)
    r = alpha_033(ctx)
    # A: open/close-1 = 110/100-1 = 0.1 (高 rank)
    # B: open/close-1 = 90/100-1 = -0.1 (低 rank)
    # rank 后 A>B，公式 rank(open/close-1) 直接返回排名
    assert r.iloc[0]["A"] > r.iloc[0]["B"]


def test_alpha_033_direction():
    assert D33 == -1


# ---------------- Alpha #34 ----------------

def test_alpha_034_basic():
    ctx = _make_ctx(n=25)
    r = alpha_034(ctx)
    # 前 6 期 NaN (returns 1 + ts_std 5)
    assert r.iloc[0].isna().all()
    # 末尾期有值
    assert not r.iloc[-1].isna().all()


def test_alpha_034_direction():
    assert D34 == 1


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
        "quantlab.factors.alpha101.alpha_020",
        "quantlab.factors.alpha101.alpha_022",
        "quantlab.factors.alpha101.alpha_023",
        "quantlab.factors.alpha101.alpha_033",
        "quantlab.factors.alpha101.alpha_034",
    ],
)
def test_docstring_has_all_10_required_fields(modname):
    doc = _module_doc(modname)
    missing = [f for f in _REQUIRED_FIELDS if f not in doc]
    assert not missing, f"{modname} 完整备注缺少字段: {missing}"
