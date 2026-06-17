"""
OMS State Machine — 订单状态机

定义合法的状态转换，防止非法状态跳变
"""

from __future__ import annotations

from typing import Dict, List

from .order import OrderState, VALID_TRANSITIONS


class OrderStateMachine:
    """
    订单状态机验证器

    用法：
        sm = OrderStateMachine()
        if sm.can_transition(OrderState.NEW, OrderState.SUBMITTED):
            sm.transition(order, OrderState.SUBMITTED)
    """

    @staticmethod
    def can_transition(
        from_state: OrderState,
        to_state: OrderState,
    ) -> bool:
        return to_state in VALID_TRANSITIONS.get(from_state, [])

    @staticmethod
    def get_valid_next_states(state: OrderState) -> List[OrderState]:
        return VALID_TRANSITIONS.get(state, [])

    @staticmethod
    def is_terminal(state: OrderState) -> bool:
        return len(VALID_TRANSITIONS.get(state, [])) == 0

    @staticmethod
    def is_active(state: OrderState) -> bool:
        return state in (
            OrderState.NEW,
            OrderState.PENDING_SUBMIT,
            OrderState.SUBMITTED,
            OrderState.PARTIAL,
        )

    @staticmethod
    def validate_transition(
        from_state: OrderState,
        to_state: OrderState,
    ) -> bool:
        if not OrderStateMachine.can_transition(from_state, to_state):
            raise ValueError(
                f"Invalid order state transition: "
                f"{from_state.value} → {to_state.value}"
            )
        return True
