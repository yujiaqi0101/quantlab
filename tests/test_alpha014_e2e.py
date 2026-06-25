"""
Alpha014 端到端回测验收测试
==========================

完整链路: FactorContext → Alpha014Strategy → TopN → BarEngine → Report

验证:
    - 整条流水线跑通不报错
    - 动量信号能正确选出上涨股票
    - 报告指标合理
    - 持仓历史与信号一致
"""
import numpy as np
import pandas as pd

from quantlab.engine import BarEngine
from quantlab.factors.context import FactorContext
from quantlab.portfolio_construction import TopN
from quantlab.research import Experiment, Report
from quantlab.signals.alpha_014 import Alpha014Strategy


def _make_trending_ctx(n=40):
    """构造有明确趋势的干净数据: A 持续上涨, B 持续下跌, C 震荡。"""
    dates = pd.date_range("2026-01-05", periods=n, freq="B")
    t = np.arange(n)
    # A: 线性上涨 100→140
    a_close = 100 + t * 1.0
    # B: 线性下跌 100→60
    b_close = 100 - t * 1.0
    # C: 震荡 100±5
    c_close = 100 + 5 * np.sin(t / 3)

    data = {}
    for sym, closes in [("A", a_close), ("B", b_close), ("C", c_close)]:
        closes = closes.astype(float)
        data[sym] = pd.DataFrame(
            {
                "open": closes,
                "high": closes + 1,
                "low": closes - 1,
                "close": closes,
                "volume": np.full(n, 10000.0),
            },
            index=dates,
        )
    return FactorContext.from_dict(data)


def test_alpha014_e2e_full_pipeline():
    """端到端: Alpha014 + TopN(1) 在趋势数据上跑通。"""
    ctx = _make_trending_ctx(n=40)

    strategy = Alpha014Strategy(period=5)
    ctor = TopN(n=1)
    engine = BarEngine(
        strategy=strategy,
        portfolio_constructor=ctor,
        initial_cash=100000.0,
    )
    result = engine.run(ctx)

    # 1. 净值曲线长度正确
    assert len(result.equity_curve) == 40
    assert (result.equity_curve > 0).all()

    # 2. 信号在预热期后应选出 A (持续上涨)
    # A 的 5 日动量始终为正且最大
    sig = strategy.signal(ctx)
    a_signal = sig["A"].iloc[10:]
    assert (a_signal > 0).all()
    # A 信号应大于 B (B 下跌, 动量为负)
    assert (sig["A"].iloc[10:] > sig["B"].iloc[10:]).all()

    # 3. B 持续下跌 → 动量恒为负 → TopN(1) 永不选 B
    #    (A 动量恒为 +5; C 震荡上行段动量可能 >5, 故 C 有时会被选中, 属正常)
    pos_b = result.positions_history["B"].iloc[8:]
    assert (pos_b == 0).all(), "B 下跌, 动量为负, 永不应被 TopN 选中"
    # A 与 C 持仓互斥 (TopN=1 每次至多持一个)
    pos_a = result.positions_history["A"].iloc[8:]
    pos_c = result.positions_history["C"].iloc[8:]
    overlap = (pos_a > 0) & (pos_c > 0)
    assert not overlap.any(), "TopN(1) 不应同时持有两只"

    # 4. 报告指标齐全且合理
    report = Report(result)
    metrics = report.metrics()
    assert metrics["n_days"] == 40
    assert metrics["n_trades"] > 0
    # A 长期上涨, 满仓 A/A&C 轮动 应有正收益
    assert metrics["total_return"] > 0, "趋势行情下应有正收益"
    assert metrics["max_drawdown"] <= 0, "最大回撤应 <= 0"


def test_alpha014_e2e_experiment_report():
    """Experiment 封装 + 报告生成。"""
    ctx = _make_trending_ctx(n=30)
    exp = Experiment(name="alpha014_e2e")
    res = exp.run(
        strategy=Alpha014Strategy(period=5),
        ctx=ctx,
        portfolio_constructor=TopN(n=1),
        params={"factor": "alpha014", "period": 5},
    )
    assert res.name == "alpha014_e2e"
    assert res.params["factor"] == "alpha014"
    assert "sharpe" in res.metrics
    # 报告文本可生成
    txt = Report(res.result).generate()
    assert "夏普比率" in txt
