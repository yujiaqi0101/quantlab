"""
Alpha 数据模型

Alpha = Factor + Signal 规则

例如：
  RSI14 < 30 → 做多    (ThresholdAlpha)
  Momentum20 > 0 → 做多 (ThresholdAlpha)
  MA5 上穿 MA20 → 做多  (CrossoverAlpha)

AlphaMetrics: 评估指标
AlphaRecord:  持久化记录
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional

import pandas as pd


class AlphaType(str, Enum):
    """Alpha 类型"""
    THRESHOLD = "threshold"       # 因子阈值：RSI < 30
    CROSSOVER = "crossover"       # 因子交叉：MA5 上穿 MA20
    ZERO_CROSS = "zero_cross"     # 零轴穿越：Momentum > 0
    COMPOSITE = "composite"       # 组合 Alpha：0.5*RSI + 0.5*MOM
    CUSTOM = "custom"             # 自定义


class AlphaStatus(str, Enum):
    """Alpha 状态"""
    DRAFT = "draft"               # 草稿
    EVALUATED = "evaluated"       # 已评估
    CANDIDATE = "candidate"       # 候选（通过筛选）
    PRODUCTION = "production"     # 生产
    ARCHIVED = "archived"         # 归档


class ResearchMode(str, Enum):
    """研究模式

    TIME_SERIES   单品种时间序列（RSI<30, MACD金叉）
    CROSS_SECTION 截面排序（MomentumRank Top50, PE Rank）
    HYBRID        混合（先截面选股 → 再时序择时）
    """
    TIME_SERIES = "time_series"
    CROSS_SECTION = "cross_section"
    HYBRID = "hybrid"


@dataclass
class AlphaMetrics:
    """
    Alpha 评估指标

    核心指标：
      ic          平均 IC (Pearson)
      rank_ic     平均 Rank IC (Spearman)
      ir          IC 信息比率 (mean_ic / std_ic)
      coverage    信号覆盖率（非零比例）
      turnover    信号换手率
      forward_ret 前瞻收益（1D）
      win_rate    胜率
      score       综合评分
    """
    ic: float = 0.0
    rank_ic: float = 0.0
    ir: float = 0.0
    coverage: float = 0.0
    turnover: float = 0.0
    forward_ret_1d: float = 0.0
    forward_ret_5d: float = 0.0
    forward_ret_10d: float = 0.0
    forward_ret_20d: float = 0.0
    win_rate: float = 0.0
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    trade_count: int = 0
    score: float = 0.0

    # IC 统计
    ic_std: float = 0.0
    ic_positive_ratio: float = 0.0
    ic_t_stat: float = 0.0

    # 截面指标（Cross Section）
    quantile_return_top: float = 0.0    # Top 分组收益
    quantile_return_bottom: float = 0.0 # Bottom 分组收益
    quantile_spread: float = 0.0        # Top - Bottom 收益差
    long_short_sharpe: float = 0.0      # 多空 Sharpe

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "AlphaMetrics":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class Alpha:
    """
    Alpha 对象

    Alpha = Factor + Signal 规则

    例如：
      factor_name="RSI14", signal_expr="LT_30", alpha_type=THRESHOLD
      含义：RSI14 < 30 → 做多信号
    """
    alpha_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    alpha_type: AlphaType = AlphaType.THRESHOLD
    status: AlphaStatus = AlphaStatus.DRAFT
    research_mode: ResearchMode = ResearchMode.TIME_SERIES  # 研究模式

    # 因子 + 信号规则
    factor_name: str = ""
    signal_expr: str = ""          # 例如 "LT_30" 或 "GT_0" 或 "CROSS_MA20"

    # 阈值参数（ThresholdAlpha）
    lower: Optional[float] = None  # factor < lower → 做多
    upper: Optional[float] = None  # factor > upper → 做空

    # 交叉参数（CrossoverAlpha）
    factor_name_2: Optional[str] = None  # 第二个因子

    # 组合参数（CompositeAlpha）
    components: Optional[List[Dict[str, Any]]] = None  # [{"alpha_id": "xxx", "weight": 0.5}]
    combine_method: Optional[str] = None  # "and" / "or" / "weighted"

    # 评估指标
    metrics: AlphaMetrics = field(default_factory=AlphaMetrics)

    # 元数据
    tags: List[str] = field(default_factory=list)
    note: str = ""
    dataset_id: str = ""
    created_at: str = ""
    evaluated_at: str = ""

    def __post_init__(self):
        if not self.name:
            self.name = self._auto_name()
        if not self.created_at:
            from datetime import datetime
            self.created_at = datetime.now().isoformat()

    def _auto_name(self) -> str:
        """自动生成 Alpha 名称"""
        if self.alpha_type == AlphaType.THRESHOLD:
            if self.lower is not None and self.upper is not None:
                return f"{self.factor_name}_{self.lower}_{self.upper}"
            elif self.lower is not None:
                return f"{self.factor_name}_LT_{self.lower}"
            elif self.upper is not None:
                return f"{self.factor_name}_GT_{self.upper}"
        elif self.alpha_type == AlphaType.CROSSOVER:
            return f"{self.factor_name}_CROSS_{self.factor_name_2 or '?'}"
        elif self.alpha_type == AlphaType.ZERO_CROSS:
            return f"{self.factor_name}_ZERO_CROSS"
        elif self.alpha_type == AlphaType.COMPOSITE:
            return f"Composite_{self.combine_method or 'weighted'}"
        return f"Alpha_{self.alpha_id}"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["alpha_type"] = self.alpha_type.value
        d["status"] = self.status.value
        d["research_mode"] = self.research_mode.value
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Alpha":
        if isinstance(d.get("alpha_type"), str):
            d["alpha_type"] = AlphaType(d["alpha_type"])
        if isinstance(d.get("status"), str):
            d["status"] = AlphaStatus(d["status"])
        if isinstance(d.get("research_mode"), str):
            d["research_mode"] = ResearchMode(d["research_mode"])
        if isinstance(d.get("metrics"), dict):
            d["metrics"] = AlphaMetrics.from_dict(d["metrics"])
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class AlphaRecord:
    """
    Alpha 持久化记录（对应 SQLite 一行）

    与 Alpha 的区别：AlphaRecord 是扁平化的数据库行
    """
    alpha_id: str
    name: str
    alpha_type: str
    status: str
    factor_name: str
    signal_expr: str
    lower: Optional[float] = None
    upper: Optional[float] = None
    factor_name_2: Optional[str] = None
    components_json: str = "[]"
    combine_method: Optional[str] = None
    # 指标
    ic: float = 0.0
    rank_ic: float = 0.0
    ir: float = 0.0
    coverage: float = 0.0
    turnover: float = 0.0
    forward_ret_1d: float = 0.0
    win_rate: float = 0.0
    sharpe: float = 0.0
    score: float = 0.0
    # 元数据
    tags_json: str = "[]"
    note: str = ""
    dataset_id: str = ""
    created_at: str = ""
    evaluated_at: str = ""

    @classmethod
    def from_alpha(cls, alpha: Alpha) -> "AlphaRecord":
        return cls(
            alpha_id=alpha.alpha_id,
            name=alpha.name,
            alpha_type=alpha.alpha_type.value,
            status=alpha.status.value,
            factor_name=alpha.factor_name,
            signal_expr=alpha.signal_expr,
            lower=alpha.lower,
            upper=alpha.upper,
            factor_name_2=alpha.factor_name_2,
            components_json=json.dumps(alpha.components or []),
            combine_method=alpha.combine_method,
            ic=alpha.metrics.ic,
            rank_ic=alpha.metrics.rank_ic,
            ir=alpha.metrics.ir,
            coverage=alpha.metrics.coverage,
            turnover=alpha.metrics.turnover,
            forward_ret_1d=alpha.metrics.forward_ret_1d,
            win_rate=alpha.metrics.win_rate,
            sharpe=alpha.metrics.sharpe,
            score=alpha.metrics.score,
            tags_json=json.dumps(alpha.tags),
            note=alpha.note,
            dataset_id=alpha.dataset_id,
            created_at=alpha.created_at,
            evaluated_at=alpha.evaluated_at,
        )

    def to_alpha(self) -> Alpha:
        return Alpha(
            alpha_id=self.alpha_id,
            name=self.name,
            alpha_type=AlphaType(self.alpha_type),
            status=AlphaStatus(self.status),
            factor_name=self.factor_name,
            signal_expr=self.signal_expr,
            lower=self.lower,
            upper=self.upper,
            factor_name_2=self.factor_name_2,
            components=json.loads(self.components_json) if self.components_json else None,
            combine_method=self.combine_method,
            metrics=AlphaMetrics(
                ic=self.ic, rank_ic=self.rank_ic, ir=self.ir,
                coverage=self.coverage, turnover=self.turnover,
                forward_ret_1d=self.forward_ret_1d,
                win_rate=self.win_rate, sharpe=self.sharpe, score=self.score,
            ),
            tags=json.loads(self.tags_json) if self.tags_json else [],
            note=self.note,
            dataset_id=self.dataset_id,
            created_at=self.created_at,
            evaluated_at=self.evaluated_at,
        )

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["tags"] = json.loads(d.pop("tags_json", "[]"))
        d["components"] = json.loads(d.pop("components_json", "[]"))
        return d
