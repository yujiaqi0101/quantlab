"""
FactorStrategy — V4.6 因子策略

核心架构：Factor -> Signal -> Target Position

与旧 SignalStrategy 的区别：
  - SignalStrategy: signal(ctx) 直接返回 DataFrame（因子+信号+策略混在一起）
  - FactorStrategy: 明确三级分离
      1. FactorEngine 计算因子值
      2. SignalEngine 生成信号
      3. FactorStrategy 组合成策略

用法：
    from quantlab.factor import FactorRegistry, FactorEngine, RSIFactor
    from quantlab.signal import ThresholdSignal, SignalEngine

    # 定义因子
    registry = FactorRegistry()
    registry.register(lambda: RSIFactor(14))

    # 定义信号
    sig_engine = SignalEngine()
    sig_engine.register(ThresholdSignal("RSI14", 30, 70))

    # 组合成策略
    strategy = FactorStrategy(
        name="rsi_threshold",
        factor_registry=registry,
        signal_engine=sig_engine,
        factor_names=["RSI14"],
        signal_name="THRESH_RSI14_30_70",
    )

    # 跑回测
    result = engine.run(strategy=strategy, data=data)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from ..signals.base import SignalStrategy
from ..factor.registry import FactorRegistry
from ..factor.factor_engine import FactorEngine
from ..signal.signal_engine import SignalEngine
from ..signal.filters import HoldFilter, CooldownFilter, StatefulSignal

logger = logging.getLogger("quantlab.strategy.factor_strategy")


class FactorStrategy(SignalStrategy):
    """
    因子策略：Factor -> Signal -> Target Position

    继承 SignalStrategy（兼容 BarEngine），内部用 Factor + Signal 三级模型

    流程：
      1. FactorEngine.compute_batch() 计算所有因子
      2. SignalEngine.transform_single() 生成信号
      3. 可选 Filter 后处理
      4. 输出 signal DataFrame（兼容旧引擎）
    """

    def __init__(
        self,
        name: str = "factor_strategy",
        factor_registry: Optional[FactorRegistry] = None,
        signal_engine: Optional[SignalEngine] = None,
        factor_names: Optional[List[str]] = None,
        signal_name: str = "",
        min_hold: int = 0,          # HoldFilter 参数
        cooldown: int = 0,          # CooldownFilter 参数
        stateful: bool = False,     # 是否将脉冲信号转为状态信号
    ) -> None:
        self._name = name
        self.factor_registry = factor_registry or FactorRegistry()
        self.signal_engine = signal_engine or SignalEngine()
        self.factor_names = factor_names or []
        self.signal_name = signal_name
        self.min_hold = min_hold
        self.cooldown = cooldown
        self.stateful = stateful

    def signal(self, ctx) -> pd.DataFrame:
        """
        生成信号 DataFrame（兼容 BarEngine）

        流程：
          1. 计算因子
          2. 生成信号
          3. Filter 后处理
          4. 返回 DataFrame(index=时间, columns=symbols, values∈{-1,0,1})
        """
        factor_engine = FactorEngine(self.factor_registry)

        # 1) 逐 symbol 计算因子 + 信号
        result: Dict[str, pd.Series] = {}
        for sym in ctx.symbols:
            df = ctx.data[sym]

            # 计算因子
            factor_values = factor_engine.compute_batch(
                self.factor_names, df
            )

            # 生成信号
            sig = self.signal_engine.transform_single(
                factor_values, self.signal_name
            )

            # Filter 后处理
            if self.stateful:
                sig = StatefulSignal().apply(sig)
            if self.min_hold > 0:
                sig = HoldFilter(min_hold=self.min_hold).apply(sig)
            if self.cooldown > 0:
                sig = CooldownFilter(cooldown_bars=self.cooldown).apply(sig)

            result[sym] = sig

        return pd.DataFrame(result)


class MultiFactorStrategy(SignalStrategy):
    """
    多因子策略：多个因子 → 横截面 rank → 加权组合 → 信号

    流程：
      1. 计算多个因子（所有 symbol）
      2. 横截面 rank
      3. 加权求和
      4. TopN 选股 → 信号

    用法：
        strategy = MultiFactorStrategy(
            factor_registry=registry,
            factor_weights={"RSI14": -0.5, "MOM20": 0.5},  # RSI 越小越好
            top_n=2,
        )
    """

    def __init__(
        self,
        factor_registry: Optional[FactorRegistry] = None,
        factor_weights: Optional[Dict[str, float]] = None,
        top_n: int = 2,
        name: str = "multi_factor",
    ) -> None:
        self.factor_registry = factor_registry or FactorRegistry()
        self.factor_weights = factor_weights or {}
        self.top_n = top_n
        self._name = name

    def signal(self, ctx) -> pd.DataFrame:
        from ..factor.operators import rank as cs_rank

        factor_engine = FactorEngine(self.factor_registry)
        factor_names = list(self.factor_weights.keys())

        # 1) 计算所有因子（所有 symbol）
        all_factors = factor_engine.compute_all_batch(factor_names, ctx.data)

        # 2) 横截面 rank + 加权组合
        alpha = pd.DataFrame(0, index=ctx.data[ctx.symbols[0]].index,
                             columns=ctx.symbols, dtype=float)
        for fname, weight in self.factor_weights.items():
            if fname in all_factors:
                ranked = cs_rank(all_factors[fname])
                alpha = alpha.add(ranked.mul(weight), fill_value=0)

        # 3) TopN 选股
        signal_df = pd.DataFrame(0, index=alpha.index, columns=alpha.columns,
                                 dtype=float)
        for i in alpha.index:
            row = alpha.loc[i]
            valid = row.dropna()
            if len(valid) == 0:
                continue
            top_symbols = valid.nlargest(min(self.top_n, len(valid))).index
            signal_df.loc[i, top_symbols] = 1

        return signal_df
