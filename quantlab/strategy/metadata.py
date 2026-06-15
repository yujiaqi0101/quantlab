"""
V4.1 Strategy Registry — Metadata

策略"自描述"模型。
前端拿到 StrategyMetadata + parameters 列表
→ 自动生成表单（不需要为每个策略手写 .vue 页面）。

为什么 dataclass + slots=True：
  - slots 节省内存（策略平台可能上千个策略）
  - dataclass 自动 __init__ / __repr__ / __eq__
  - 不依赖 pydantic（保持轻量，DTO/API 层再用 pydantic）
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


# -------------------------------------------------------------
# 参数类型
# -------------------------------------------------------------
# 前端表单控件的映射规则：
#   int / float  → <InputNumber>
#   bool         → <Switch>
#   str          → <Input>
#   choice       → <Select>
#   any          → <Input>  (兜底)
PARAM_TYPES = (
    "int",
    "float",
    "bool",
    "str",
    "choice",
    "any",
)


@dataclass(slots=True)
class StrategyParameter:
    """
    单个参数的 schema（前端表单生成用）

    字段：
      name          参数名
      type          "int" / "float" / "bool" / "str" / "choice" / "any"
      default       默认值
      min_value     数值下限（int/float 用）
      max_value     数值上限（int/float 用）
      step          数值步长（前端 InputNumber 用）
      choices       候选值列表（type="choice" 用）
      description   描述
      required      是否必填（默认 False：有 default 即非必填）
    """
    name: str
    type: str = "any"
    default: Any = None
    min_value: Any = None
    max_value: Any = None
    step: Any = None
    choices: List[Any] = field(default_factory=list)
    description: str = ""
    required: bool = False

    def __post_init__(self) -> None:
        # 兜底：非法 type → "any"
        if self.type not in PARAM_TYPES:
            self.type = "any"
        # 没有 default 时强制 required=True
        if self.default is None and not self.required:
            self.required = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class StrategyMetadata:
    """
    策略的"对外定义"

    字段：
      id            短 ID（前端/URL 用："ma_cross"）
      name          显示名
      description   描述
      author        作者
      version       semver 字符串（"1.0.0"）
      tags          标签
      parameters    List[StrategyParameter]
      default_parameters  Dict（前端"恢复默认"按钮用）
      param_space   网格/优化空间（Optimizer 用）
      class_path    "quantlab.signals.MACrossStrategy"（可执行路径）
      source_path   源文件绝对路径（溯源/复现用）
      extra         其它元数据
    """
    id: str
    name: str = ""
    description: str = ""
    author: str = ""
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    parameters: List[StrategyParameter] = field(
        default_factory=list
    )
    default_parameters: Dict[str, Any] = field(
        default_factory=dict
    )
    param_space: Dict[str, Any] = field(
        default_factory=dict
    )
    class_path: str = ""
    source_path: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    # ---------------------------------------------------------
    # 派生属性
    # ---------------------------------------------------------
    @property
    def parameter_names(self) -> List[str]:
        return [p.name for p in self.parameters]

    def get_parameter(
        self, name: str
    ) -> Optional[StrategyParameter]:
        for p in self.parameters:
            if p.name == name:
                return p
        return None

    def schema_dict(self) -> Dict[str, Dict[str, Any]]:
        """
        { name: {type, default, min, max, ...} }
        兼容 domain.StrategyDefinition.schema_dict() 格式
        """
        return {
            p.name: {
                "type": p.type,
                "default": p.default,
                "min": p.min_value,
                "max": p.max_value,
                "step": p.step,
                "choices": list(p.choices),
                "description": p.description,
                "required": p.required,
            }
            for p in self.parameters
        }

    # ---------------------------------------------------------
    # 序列化
    # ---------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "version": self.version,
            "tags": list(self.tags),
            "parameters": [p.to_dict() for p in self.parameters],
            "default_parameters": dict(
                self.default_parameters
            ),
            "param_space": dict(self.param_space),
            "class_path": self.class_path,
            "source_path": self.source_path,
            "extra": dict(self.extra),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StrategyMetadata":
        params = [
            StrategyParameter(**p)
            for p in d.get("parameters", [])
            if isinstance(p, dict)
        ]
        return cls(
            id=d.get("id", ""),
            name=d.get("name", ""),
            description=d.get("description", ""),
            author=d.get("author", ""),
            version=d.get("version", "1.0.0"),
            tags=list(d.get("tags", [])),
            parameters=params,
            default_parameters=dict(
                d.get("default_parameters", {})
            ),
            param_space=dict(d.get("param_space", {})),
            class_path=d.get("class_path", ""),
            source_path=d.get("source_path", ""),
            extra=dict(d.get("extra", {})),
        )

    # ---------------------------------------------------------
    # 合并 / 校验
    # ---------------------------------------------------------
    def validate_params(
        self, params: Dict[str, Any]
    ) -> List[str]:
        """
        校验一组参数值是否合法
        返回错误信息列表（空列表表示全部合法）
        """
        errors: List[str] = []
        for p in self.parameters:
            if p.name not in params:
                if p.required:
                    errors.append(
                        f"missing required param: {p.name}"
                    )
                continue
            v = params[p.name]
            if p.type == "int" and not isinstance(
                v, (int, bool)
            ):
                # bool 是 int 子集，但通常不想让 bool 进 int 参数
                if not isinstance(v, int):
                    errors.append(
                        f"{p.name}: expect int, got "
                        f"{type(v).__name__}"
                    )
                    continue
            if p.type == "float":
                try:
                    v = float(v)
                except (TypeError, ValueError):
                    errors.append(
                        f"{p.name}: expect float, got "
                        f"{type(v).__name__}"
                    )
                    continue
            if p.type == "bool" and not isinstance(
                v, (bool, int)
            ):
                errors.append(
                    f"{p.name}: expect bool, got "
                    f"{type(v).__name__}"
                )
                continue
            if p.type == "choice" and p.choices:
                if v not in p.choices:
                    errors.append(
                        f"{p.name}: {v!r} not in choices "
                        f"{p.choices}"
                    )
            # 数值范围
            if p.type in ("int", "float"):
                try:
                    v_num = float(v)
                    if (
                        p.min_value is not None
                        and v_num < float(p.min_value)
                    ):
                        errors.append(
                            f"{p.name}: {v_num} < min "
                            f"{p.min_value}"
                        )
                    if (
                        p.max_value is not None
                        and v_num > float(p.max_value)
                    ):
                        errors.append(
                            f"{p.name}: {v_num} > max "
                            f"{p.max_value}"
                        )
                except (TypeError, ValueError):
                    pass
        return errors
