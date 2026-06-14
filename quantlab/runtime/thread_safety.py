"""
ThreadSafety：线程安全包装（V3.3 第八件事）

V3.3 实盘多线程场景：
    - 主线程：信号 / 决策
    - 行情线程：推送 tick
    - 成交线程：broker 回调
    - 风控线程：定时检查

共享资源（必须加锁）：
    - portfolio.positions
    - broker.cash / positions
    - open_orders 队列
    - metrics 指标

API:
    with TradeLock.section("broker"):
        broker.submit_order(o)
"""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Dict


class TradeLock:
    """
    V3.3 全局锁（细粒度）

    用法：
        TradeLock.section("portfolio")  →  portfolio 区域锁
        TradeLock.section("broker")      →  broker 区域锁
    """

    _locks: Dict[str, threading.RLock] = {}
    _meta_lock = threading.Lock()

    @classmethod
    def get(cls, name: str) -> threading.RLock:
        if name not in cls._locks:
            with cls._meta_lock:
                if name not in cls._locks:
                    cls._locks[name] = threading.RLock()
        return cls._locks[name]

    @classmethod
    @contextmanager
    def section(cls, name: str):
        """
        临界区
        """
        lock = cls.get(name)
        acquired = lock.acquire(timeout=5.0)
        if not acquired:
            raise TimeoutError(
                f"failed to acquire lock '{name}' in 5s"
            )
        try:
            yield
        finally:
            lock.release()


def critical(name: str = "default"):
    """
    装饰器用法
    """
    def deco(fn):
        def wrapper(*args, **kwargs):
            with TradeLock.section(name):
                return fn(*args, **kwargs)
        return wrapper
    return deco
