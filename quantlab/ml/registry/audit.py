"""
Model Audit Log — 模型操作审计

ML Lab M4 第八部分：记录所有操作

  记录：
    创建模型
    修改 Champion
    删除模型
    上线模型
    退役模型

  以后出现问题：
    为什么收益下降？
    可以回查：
      2026-07-15 Champion v3 → v4
"""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger("quantlab.ml.registry.audit")


# 审计动作类型
class AuditAction:
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    PROMOTE = "PROMOTE"          # Champion 提升
    DEMOTE = "DEMOTE"            # Champion 降级
    TRANSITION = "TRANSITION"    # 生命周期转换
    RETIRE = "RETIRE"            # 退役
    RESTORE = "RESTORE"          # 恢复
    EXPORT = "EXPORT"            # 导出
    IMPORT = "IMPORT"            # 导入


@dataclass
class AuditEntry:
    """审计日志条目"""
    entry_id: str = ""
    timestamp: str = ""
    action: str = ""               # AuditAction.*
    version_id: str = ""
    version_name: str = ""
    family: str = ""
    operator: str = "system"
    reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp,
            "action": self.action,
            "version_id": self.version_id,
            "version_name": self.version_name,
            "family": self.family,
            "operator": self.operator,
            "reason": self.reason,
            "details": self.details,
        }


class ModelAuditLog:
    """
    模型审计日志

    用法：
        audit = ModelAuditLog()
        audit.log_create(version, operator="alice")
        audit.log_promote(version, old_champion, operator="bob", reason="sharpe 更高")
        entries = audit.query(family="LGBM_Momentum", action=AuditAction.PROMOTE)
    """

    def __init__(self, log_file: Optional[str] = None) -> None:
        """
        Args:
            log_file: 日志文件路径（None 表示仅内存）
        """
        self.log_file = log_file
        self._entries: List[AuditEntry] = []
        self._lock = threading.RLock()
        self._counter = 0

        if log_file and os.path.exists(log_file):
            self._load_from_file()

    # ------------------------------------------------------------------
    # 记录操作
    # ------------------------------------------------------------------

    def log(
        self,
        action: str,
        version_id: str = "",
        version_name: str = "",
        family: str = "",
        operator: str = "system",
        reason: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        """记录一条审计日志"""
        with self._lock:
            self._counter += 1
            entry = AuditEntry(
                entry_id=f"AUDIT-{self._counter:06d}",
                timestamp=datetime.now().isoformat(),
                action=action,
                version_id=version_id,
                version_name=version_name,
                family=family,
                operator=operator,
                reason=reason,
                details=details or {},
            )
            self._entries.append(entry)
            self._save_to_file()
            logger.info(
                f"Audit: {action} {version_name} by {operator} ({reason})"
            )
            return entry

    def log_create(self, version, operator: str = "system") -> AuditEntry:
        """记录创建模型"""
        return self.log(
            action=AuditAction.CREATE,
            version_id=version.version_id,
            version_name=version.name,
            family=version.family,
            operator=operator,
            reason="Model version created",
            details=version.to_dict(),
        )

    def log_delete(self, version, operator: str = "system") -> AuditEntry:
        """记录删除模型"""
        return self.log(
            action=AuditAction.DELETE,
            version_id=version.version_id,
            version_name=version.name,
            family=version.family,
            operator=operator,
            reason="Model version deleted",
        )

    def log_promote(
        self,
        new_champion,
        old_champion=None,
        operator: str = "system",
        reason: str = "",
    ) -> AuditEntry:
        """记录 Champion 提升"""
        details = {
            "new_champion": new_champion.name,
            "new_champion_id": new_champion.version_id,
        }
        if old_champion:
            details["old_champion"] = old_champion.name
            details["old_champion_id"] = old_champion.version_id
        return self.log(
            action=AuditAction.PROMOTE,
            version_id=new_champion.version_id,
            version_name=new_champion.name,
            family=new_champion.family,
            operator=operator,
            reason=reason or "Promoted to champion",
            details=details,
        )

    def log_transition(
        self,
        version,
        from_status: str,
        to_status: str,
        operator: str = "system",
        reason: str = "",
    ) -> AuditEntry:
        """记录生命周期转换"""
        return self.log(
            action=AuditAction.TRANSITION,
            version_id=version.version_id,
            version_name=version.name,
            family=version.family,
            operator=operator,
            reason=reason,
            details={
                "from_status": from_status,
                "to_status": to_status,
            },
        )

    def log_retire(self, version, operator: str = "system", reason: str = "") -> AuditEntry:
        """记录退役"""
        return self.log(
            action=AuditAction.RETIRE,
            version_id=version.version_id,
            version_name=version.name,
            family=version.family,
            operator=operator,
            reason=reason or "Model retired",
        )

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def query(
        self,
        version_id: Optional[str] = None,
        family: Optional[str] = None,
        action: Optional[str] = None,
        operator: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> List[AuditEntry]:
        """
        查询审计日志

        Args:
            version_id: 按版本过滤
            family: 按族过滤
            action: 按动作过滤
            operator: 按操作者过滤
            start_time: 起始时间（ISO 格式）
            end_time: 结束时间（ISO 格式）
        """
        with self._lock:
            result = list(self._entries)

        if version_id:
            result = [e for e in result if e.version_id == version_id]
        if family:
            result = [e for e in result if e.family == family]
        if action:
            result = [e for e in result if e.action == action]
        if operator:
            result = [e for e in result if e.operator == operator]
        if start_time:
            result = [e for e in result if e.timestamp >= start_time]
        if end_time:
            result = [e for e in result if e.timestamp <= end_time]

        return result

    def get_recent(self, n: int = 20) -> List[AuditEntry]:
        """获取最近 N 条"""
        with self._lock:
            return list(self._entries[-n:])

    def get_version_history(self, version_id: str) -> List[AuditEntry]:
        """获取指定版本的所有操作历史"""
        return self.query(version_id=version_id)

    def get_champion_history(self, family: str) -> List[AuditEntry]:
        """获取指定族的 Champion 变更历史"""
        return self.query(family=family, action=AuditAction.PROMOTE)

    # ------------------------------------------------------------------
    # 统计
    # ------------------------------------------------------------------

    def get_summary(self) -> Dict[str, Any]:
        """获取审计日志统计"""
        with self._lock:
            total = len(self._entries)
            by_action: Dict[str, int] = {}
            by_operator: Dict[str, int] = {}
            by_family: Dict[str, int] = {}
            for e in self._entries:
                by_action[e.action] = by_action.get(e.action, 0) + 1
                by_operator[e.operator] = by_operator.get(e.operator, 0) + 1
                by_family[e.family] = by_family.get(e.family, 0) + 1
        return {
            "total": total,
            "by_action": by_action,
            "by_operator": by_operator,
            "by_family": by_family,
        }

    def to_dataframe(self) -> pd.DataFrame:
        """转为 DataFrame"""
        with self._lock:
            data = [e.to_dict() for e in self._entries]
        return pd.DataFrame(data)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": len(self._entries),
            "entries": [e.to_dict() for e in self._entries],
        }

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------

    def _save_to_file(self) -> None:
        """保存到文件"""
        if not self.log_file:
            return
        try:
            os.makedirs(os.path.dirname(self.log_file) or ".", exist_ok=True)
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(
                    [e.to_dict() for e in self._entries],
                    f, indent=2, ensure_ascii=False, default=str,
                )
        except Exception as e:
            logger.error(f"Failed to save audit log: {e}")

    def _load_from_file(self) -> None:
        """从文件加载"""
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._entries = [
                AuditEntry(
                    entry_id=d.get("entry_id", ""),
                    timestamp=d.get("timestamp", ""),
                    action=d.get("action", ""),
                    version_id=d.get("version_id", ""),
                    version_name=d.get("version_name", ""),
                    family=d.get("family", ""),
                    operator=d.get("operator", "system"),
                    reason=d.get("reason", ""),
                    details=d.get("details", {}),
                )
                for d in data
            ]
            # 更新计数器
            if self._entries:
                last_id = self._entries[-1].entry_id
                try:
                    self._counter = int(last_id.split("-")[-1])
                except (ValueError, IndexError):
                    self._counter = len(self._entries)
            logger.info(f"Audit log loaded: {len(self._entries)} entries")
        except Exception as e:
            logger.error(f"Failed to load audit log: {e}")


# ------------------------------------------------------------------
# 模块级单例
# ------------------------------------------------------------------

_audit_log: Optional[ModelAuditLog] = None


def get_audit_log(log_file: Optional[str] = None) -> ModelAuditLog:
    """获取 ModelAuditLog 单例"""
    global _audit_log
    if _audit_log is None:
        if log_file is None:
            log_file = "storage/audit/model_audit.json"
        _audit_log = ModelAuditLog(log_file)
    return _audit_log
