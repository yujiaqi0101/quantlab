"""
Port — 节点输入输出端口声明

ResearchNode 通过 Port 声明其输入输出，Graph 编译期据此做类型校验与连线匹配。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict


class PortType(str, Enum):
    """端口数据类型"""
    SERIES = "series"          # 单标的时序 (pd.Series, datetime index)
    FRAME = "frame"            # 面板 (ResearchFrame / pd.DataFrame, MultiIndex)
    PANEL = "panel"            # 横截面 (pd.DataFrame, symbol index)
    SCALAR = "scalar"          # 标量 (int/float/str)
    REFERENCE = "reference"   # 引用类型 (Dataset/Universe/Graph id)


@dataclass
class Port:
    """节点输入/输出端口声明"""
    name: str                              # 端口名 (如 "close", "rsi")
    type: PortType = PortType.FRAME        # 数据类型
    required: bool = True                  # 是否必须连接
    description: str = ""                  # 人可读说明
    default: Any = None                    # 默认值 (required=False 时生效)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type.value,
            "required": self.required,
            "description": self.description,
            "default": self.default,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Port":
        return cls(
            name=d["name"],
            type=PortType(d.get("type", "frame")),
            required=d.get("required", True),
            description=d.get("description", ""),
            default=d.get("default"),
        )
