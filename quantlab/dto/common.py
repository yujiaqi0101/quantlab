"""通用 DTO：分页、错误响应等"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class PageRequest:
    """分页请求"""
    page: int = 1
    size: int = 20

    def offset(self) -> int:
        return max(0, (self.page - 1) * self.size)


@dataclass(slots=True)
class PageResponse:
    """分页响应"""
    total: int
    page: int
    size: int
    items: List[Any] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "page": self.page,
            "size": self.size,
            "items": [
                _to_dict_obj(x) for x in self.items
            ],
        }


@dataclass(slots=True)
class ErrorResponse:
    """统一错误格式"""
    code: str
    message: str
    detail: Optional[Dict[str, Any]] = None


def _to_dict_obj(obj: Any) -> Any:
    """
    将 dataclass / 普通对象转 dict
    - dataclass（含 slots）→ asdict
    - 有 to_dict 方法 → 调它
    - 其它 → 原样
    """
    if obj is None:
        return None
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        return obj.to_dict()
    try:
        return asdict(obj)
    except TypeError:
        return obj
