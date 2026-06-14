"""
AllocationEngine：策略 × 账户分配（V3.4）

V3.4 核心：策略输出 target weights
                       ↓
       AllocationEngine 按 account 拆
                       ↓
       OrderRouter 把 Order 投到对应 account/broker

Allocation Map 结构：
    { strategy_id: [(account_id, weight), ...] }
    weight ∈ [0, 1], sum(to weights) == 1.0

默认：
    { strategy_id: [(account_id, 1.0)] }   一对一

示例：
    "A → acc1 60% + acc2 40%"
    "B → acc3 100%"

用 AllocationRule 表达：
    1) FixedAllocation        静态
    2) DynamicAllocation      动态（按 pnl / 风险调权重）
    3) PriorityAllocation     顺序填账户
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple

from .account_manager import AccountManager


class AllocationRule(ABC):
    """分配规则基类"""

    @abstractmethod
    def allocate(
        self,
        strategy_id: str,
        amount: float,                       # 目标资金量
        account_manager: AccountManager,
    ) -> List[Tuple[str, float]]:
        """
        返回 [(account_id, allocated_amount), ...]
        """
        ...


class FixedAllocation(AllocationRule):
    """
    固定权重分配

    用法：
        rule = FixedAllocation({
            "strategy_A": [("acc1", 0.6), ("acc2", 0.4)],
            "strategy_B": [("acc3", 1.0)],
        })
    """

    def __init__(
        self,
        allocation_map: Dict[str, List[Tuple[str, float]]],
    ):
        self.allocation_map = allocation_map
        # 校验
        for sid, lst in allocation_map.items():
            total = sum(w for _, w in lst)
            if abs(total - 1.0) > 0.01:
                raise ValueError(
                    f"strategy {sid!r} weights sum={total}, "
                    f"must be 1.0"
                )

    def allocate(
        self,
        strategy_id: str,
        amount: float,
        account_manager: AccountManager,
    ) -> List[Tuple[str, float]]:
        if strategy_id not in self.allocation_map:
            return []
        return [
            (acc_id, w * amount)
            for acc_id, w in self.allocation_map[strategy_id]
        ]


class DynamicAllocation(AllocationRule):
    """
    动态权重分配：按当前账户 pnl 反比调整
    pnl 越差 → 权重越低（输的账户少投）

    用法：
        rule = DynamicAllocation(default_weight=0.5)
    """

    def __init__(
        self,
        default_weight: float = 0.5,
        decay: float = 0.1,
    ):
        self.default_weight = default_weight
        self.decay = decay

    def allocate(
        self,
        strategy_id: str,
        amount: float,
        account_manager: AccountManager,
    ) -> List[Tuple[str, float]]:
        # 简化：均匀分布到所有 account
        accounts = account_manager.list_accounts()
        n = len(accounts)
        if n == 0:
            return []
        each = amount / n
        return [
            (a.account_id, each) for a in accounts
        ]


class AllocationEngine:
    """
    V3.4 AllocationEngine

    用法：
        ae = AllocationEngine(FixedAllocation({
            "strategy_A": [("acc1", 0.6), ("acc2", 0.4)],
        }))

        # 策略A 当前要买 1000 股 AAPL
        splits = ae.split("strategy_A", shares=1000)
        → [("acc1", 600), ("acc2", 400)]
    """

    def __init__(self, rule: AllocationRule):
        self.rule = rule

    def split(
        self,
        strategy_id: str,
        shares: int,
        account_manager: AccountManager,
    ) -> List[Tuple[str, int]]:
        """
        V3.4 整数拆单

        简化：按权重分配，剩余归到第一个账户
        """
        raw = self.rule.allocate(
            strategy_id, float(shares), account_manager
        )
        if not raw:
            return []

        # 整数化
        int_shares: List[Tuple[str, int]] = []
        remaining = shares
        for acc_id, amt in raw:
            n = int(round(amt))
            n = max(0, min(n, remaining))
            if n > 0:
                int_shares.append((acc_id, n))
            remaining -= n

        # 余量归到第一个
        if remaining > 0 and int_shares:
            acc_id, n = int_shares[0]
            int_shares[0] = (acc_id, n + remaining)
            remaining = 0

        return int_shares
