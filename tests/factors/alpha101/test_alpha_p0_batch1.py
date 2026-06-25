"""
Alpha101 P0 因子单元测试 (批次1)
================================

覆盖: #4, #6, #9, #10, #12
"""
import numpy as np
import pandas as pd
import pytest

from quantlab.factors.alpha101.alpha_004 import alpha_004, DIRECTION as D4
from quantlab.factors.alpha101.alpha_006 import alpha_006, DIRECTION as D6
from quantlab.factors.alpha101.alpha_009 import alpha_009, DIRECTION as D9
from quantlab.factors.alpha101.alpha_010 import alpha_010, DIRECTION as D10
from quantlab.factors.alpha101.alpha_012 import alpha_012, DIRECTION as D12
from quantlab.factors.context import FactorContext


def _make_ctx(n=20):
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


# ---------------- Alpha #4 ----------------

def test_alpha_004_basic():
    ctx = _make_ctx(n=20)
    r = alpha_004(ctx, period=9)
    # 首期 NaN (ts_rank 预热)
    assert r.iloc[0].isna().all()
    # 末尾期有值
    assert not r.iloc[-1].isna().all()


def test_alpha_004_direction():
    assert D4 == -1


# ---------------- Alpha #6 ----------------

def test_alpha_006_basic():
    ctx = _make_ctx(n=20)
    r = alpha_006(ctx, period=10)
    # 首期 NaN
    assert r.iloc[0].isna().all()
    # 末尾期有值
    assert not r.iloc[-1].isna().all()


def test_alpha_006_perfect_negative_corr():
    # open 上升, volume 下降 → 负相关 → corr=-1 → -corr=1
    n = 12
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    data = {
        "A": pd.DataFrame(
            {
                "open": np.arange(100, 100+n, dtype=float),
                "high": np.arange(100, 100+n, dtype=float)+1,
                "low": np.arange(100, 100+n, dtype=float)-1,
                "close": np.arange(100, 100+n, dtype=float),
                "volume": np.arange(n, 0, -1, dtype=float)*1000,
            }, index=dates,
        ),
    }
    ctx = FactorContext.from_dict(data)
    r = alpha_006(ctx, period=10)
    # 第 10 期: 完美负相关 → -1 * (-1) = 1
    assert r.iloc[10, 0] == pytest.approx(1.0, abs=1e-6)


def test_alpha_006_direction():
    assert D6 == -1


# ---------------- Alpha #9 ----------------

def test_alpha_009_persistent_up():
    # 持续上涨 → min(d1,5)>0 → 顺势 = d1 > 0
    n = 10
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    closes = np.arange(100, 100+n, dtype=float)
    data = {
        "A": pd.DataFrame(
            {
                "open": closes, "high": closes+1, "low": closes-1,
                "close": closes, "volume": [1000.0]*n,
            }, index=dates,
        ),
    }
    ctx = FactorContext.from_dict(data)
    r = alpha_009(ctx, period=5)
    # 第 6 期 (delta 1 + ts_min 5): 持续上涨 → 取 d1 = +1
    assert r.iloc[6, 0] == pytest.approx(1.0)


def test_alpha_009_persistent_down():
    # 持续下跌 → max(d1,5)<0 → 顺势 = d1 < 0
    n = 10
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    closes = np.arange(100, 100-n, -1, dtype=float)
    data = {
        "A": pd.DataFrame(
            {
                "open": closes, "high": closes+1, "low": closes-1,
                "close": closes, "volume": [1000.0]*n,
            }, index=dates,
        ),
    }
    ctx = FactorContext.from_dict(data)
    r = alpha_009(ctx, period=5)
    # 第 6 期: 持续下跌 → 取 d1 = -1
    assert r.iloc[6, 0] == pytest.approx(-1.0)


def test_alpha_009_oscillation_reverse():
    # 震荡 (有正有负) → 反转 = -d1
    n = 10
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    closes = np.array([100, 101, 99, 102, 98, 103, 97, 104, 96, 105], dtype=float)
    data = {
        "A": pd.DataFrame(
            {
                "open": closes, "high": closes+1, "low": closes-1,
                "close": closes, "volume": [1000.0]*n,
            }, index=dates,
        ),
    }
    ctx = FactorContext.from_dict(data)
    r = alpha_009(ctx, period=5)
    # 第 6 期: d1 = 97-103 = -6, min(d1,5)=97-103=-6<0, max(d1,5)=102-99=3>0 → 震荡 → -d1 = 6
    assert r.iloc[6, 0] == pytest.approx(6.0)


def test_alpha_009_direction():
    assert D9 == 1


# ---------------- Alpha #10 ----------------

def test_alpha_010_basic():
    ctx = _make_ctx(n=10)
    r = alpha_010(ctx, period=4)
    # 首期 NaN (delta 预热)
    assert r.iloc[0].isna().all()
    # 末尾期有值 (且经过 rank, 范围 [0,1])
    assert not r.iloc[-1].isna().all()


def test_alpha_010_direction():
    assert D10 == 1


# ---------------- Alpha #12 ----------------

def test_alpha_012_volume_up_close_up():
    # 放量 + 上涨 → 看空 (因子值 < 0)
    n = 5
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    data = {
        "A": pd.DataFrame(
            {
                "open": [100.0]*n, "high": [101.0]*n, "low": [99.0]*n,
                "close": [100, 101, 102, 103, 104],
                "volume": [1000, 1100, 1200, 1300, 1400],
            }, index=dates,
        ),
    }
    ctx = FactorContext.from_dict(data)
    r = alpha_012(ctx)
    # 第 1 期起: sign(+1)*(-1) = -1
    assert r.iloc[1, 0] < 0


def test_alpha_012_volume_up_close_down():
    # 放量 + 下跌 → 看多 (因子值 > 0)
    n = 5
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    data = {
        "A": pd.DataFrame(
            {
                "open": [100.0]*n, "high": [101.0]*n, "low": [99.0]*n,
                "close": [104, 103, 102, 101, 100],
                "volume": [1000, 1100, 1200, 1300, 1400],
            }, index=dates,
        ),
    }
    ctx = FactorContext.from_dict(data)
    r = alpha_012(ctx)
    # 第 1 期: sign(+1)*(+1) = 1
    assert r.iloc[1, 0] > 0


def test_alpha_012_direction():
    assert D12 == 1


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
        "quantlab.factors.alpha101.alpha_004",
        "quantlab.factors.alpha101.alpha_006",
        "quantlab.factors.alpha101.alpha_009",
        "quantlab.factors.alpha101.alpha_010",
        "quantlab.factors.alpha101.alpha_012",
    ],
)
def test_docstring_has_all_10_required_fields(modname):
    doc = _module_doc(modname)
    missing = [f for f in _REQUIRED_FIELDS if f not in doc]
    assert not missing, f"{modname} 完整备注缺少字段: {missing}"
