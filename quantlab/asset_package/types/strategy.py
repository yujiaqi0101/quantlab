"""
Strategy Package — 策略包（.qlstrategy）

P3 实现：定义 .qlstrategy 包格式，全是 ref 引用。

manifest.yaml 示例：
  id: Momentum_LGBM_v2@2.0
  name: Momentum_LGBM_v2
  version: "2.0"
  type: STRATEGY
  family: Momentum
  status: candidate
  validation: PENDING
  model: ref://Momentum_LGBM@1.2.0
  signal: ref://ProbabilitySignal@1.0
  position: ref://VolatilitySizing@2.0
  risk: ref://CryptoBasicRisk@1.1
  execution: ref://PaperExecution@1.0
  observe: ref://StandardObserve@1.0
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..base import AssetPackage, PackageType, Ref, parse_ref

logger = logging.getLogger("quantlab.asset_package.types.strategy")


# ==================================================================
# StrategyStatus
# ==================================================================

class StrategyStatus(str):
    """策略状态"""
    CANDIDATE = "candidate"       # 候选（刚装配）
    VALIDATED = "validated"       # 已验证（通过 smoke test）
    DEPLOYED = "deployed"         # 已部署
    ARCHIVED = "archived"         # 已归档


class ValidationState(str):
    """验证状态"""
    PENDING = "PENDING"
    PASS = "PASS"
    FAIL = "FAIL"


# ==================================================================
# StrategyPackage
# ==================================================================

@dataclass
class StrategyPackage(AssetPackage):
    """
    策略包（.qlstrategy）

    全是 ref 引用，不复制数据：
      model:      ref://Momentum_LGBM@1.2.0
      signal:     ref://ProbabilitySignal@1.0
      position:   ref://VolatilitySizing@2.0
      risk:       ref://CryptoBasicRisk@1.1
      execution:  ref://PaperExecution@1.0
      observe:    ref://StandardObserve@1.0
    """
    package_type: PackageType = PackageType.STRATEGY

    # 策略特有字段
    family: str = ""
    strategy_status: str = StrategyStatus.CANDIDATE
    validation: str = ValidationState.PENDING

    # ref 引用（全是 ref://name@version 格式）
    model_ref: str = ""
    signal_ref: str = ""
    position_ref: str = ""
    risk_ref: str = ""
    execution_ref: str = ""
    observe_ref: str = ""

    # 验证报告（可选）
    validation_report: Optional[Dict[str, Any]] = None

    def to_config(self) -> Dict[str, Any]:
        return {
            "family": self.family,
            "strategy_status": self.strategy_status,
            "validation": self.validation,
            "model": self.model_ref,
            "signal": self.signal_ref,
            "position": self.position_ref,
            "risk": self.risk_ref,
            "execution": self.execution_ref,
            "observe": self.observe_ref,
            "validation_report": self.validation_report,
        }

    def _load_config(self, config: Dict[str, Any]) -> None:
        self.family = config.get("family", "")
        self.strategy_status = config.get("strategy_status", StrategyStatus.CANDIDATE)
        self.validation = config.get("validation", ValidationState.PENDING)
        self.model_ref = config.get("model", "")
        self.signal_ref = config.get("signal", "")
        self.position_ref = config.get("position", "")
        self.risk_ref = config.get("risk", "")
        self.execution_ref = config.get("execution", "")
        self.observe_ref = config.get("observe", "")
        self.validation_report = config.get("validation_report")

    def compute_hash(self) -> str:
        return self._hash_dict({
            "name": self.name,
            "version": self.version,
            "type": self.package_type.value,
            "family": self.family,
            "model": self.model_ref,
            "signal": self.signal_ref,
            "position": self.position_ref,
            "risk": self.risk_ref,
            "execution": self.execution_ref,
            "observe": self.observe_ref,
        })

    # ------------------------------------------------------------------
    # ref 解析工具
    # ------------------------------------------------------------------

    def get_all_refs(self) -> Dict[str, str]:
        """返回所有 ref 引用"""
        return {
            "model": self.model_ref,
            "signal": self.signal_ref,
            "position": self.position_ref,
            "risk": self.risk_ref,
            "execution": self.execution_ref,
            "observe": self.observe_ref,
        }

    def get_ref_objects(self) -> Dict[str, Ref]:
        """返回所有 Ref 对象"""
        return {k: parse_ref(v) for k, v in self.get_all_refs().items() if v}
