"""
Artifact Store — 模型产物存储

ML Lab M6：保存训练过程中产生的所有产物

  artifacts/
  ├── importance.json       特征重要性（gain/permutation/shap）
  ├── walkforward.html     Walk Forward 报告
  ├── shap.parquet          SHAP 值
  ├── learning_curve.json   学习曲线
  ├── confusion_matrix.json 混淆矩阵（分类）
  ├── training.log          训练日志
  └── validation_report.json 验证报告

  以后 Observe Studio 的 Model Detail 页面直接展示。
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger("quantlab.ml.registry.artifacts")


class ArtifactStore:
    """
    产物存储

    用法：
        store = ArtifactStore("/path/to/version_dir/artifacts")
        store.save_importance({"rsi14": 0.3, "momentum20": 0.2})
        store.save_walkforward_report(html_str)
        imp = store.load_importance()
    """

    def __init__(self, artifacts_dir: str) -> None:
        self.artifacts_dir = artifacts_dir
        os.makedirs(self.artifacts_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # 特征重要性
    # ------------------------------------------------------------------

    def save_importance(self, importance: Dict[str, Any]) -> str:
        """
        保存特征重要性

        Args:
            importance: 可以是 {feature: score} 或 {method: {feature: score}}
        """
        path = os.path.join(self.artifacts_dir, "importance.json")
        self._save_json(path, importance)
        return path

    def load_importance(self) -> Dict[str, Any]:
        return self._load_json(os.path.join(self.artifacts_dir, "importance.json"))

    def save_importance_by_method(self, importance_by_method: Dict[str, Dict[str, float]]) -> str:
        """保存按方法分组的特征重要性"""
        return self.save_importance(importance_by_method)

    # ------------------------------------------------------------------
    # Walk Forward 报告
    # ------------------------------------------------------------------

    def save_walkforward_report(self, html: str) -> str:
        """保存 Walk Forward HTML 报告"""
        path = os.path.join(self.artifacts_dir, "walkforward.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return path

    def load_walkforward_report(self) -> Optional[str]:
        path = os.path.join(self.artifacts_dir, "walkforward.html")
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def save_walkforward_result(self, result: Dict[str, Any]) -> str:
        """保存 Walk Forward 结果（JSON）"""
        path = os.path.join(self.artifacts_dir, "walkforward.json")
        self._save_json(path, result)
        return path

    def load_walkforward_result(self) -> Dict[str, Any]:
        return self._load_json(os.path.join(self.artifacts_dir, "walkforward.json"))

    # ------------------------------------------------------------------
    # SHAP 值
    # ------------------------------------------------------------------

    def save_shap(self, df: pd.DataFrame) -> str:
        """保存 SHAP 值（Parquet）"""
        path = os.path.join(self.artifacts_dir, "shap.parquet")
        df.to_parquet(path)
        return path

    def load_shap(self) -> Optional[pd.DataFrame]:
        path = os.path.join(self.artifacts_dir, "shap.parquet")
        if not os.path.exists(path):
            return None
        return pd.read_parquet(path)

    # ------------------------------------------------------------------
    # 学习曲线
    # ------------------------------------------------------------------

    def save_learning_curve(self, curve: Dict[str, Any]) -> str:
        """
        保存学习曲线

        Args:
            curve: {"train_sizes": [...], "train_scores": [...], "val_scores": [...]}
        """
        path = os.path.join(self.artifacts_dir, "learning_curve.json")
        self._save_json(path, curve)
        return path

    def load_learning_curve(self) -> Dict[str, Any]:
        return self._load_json(os.path.join(self.artifacts_dir, "learning_curve.json"))

    # ------------------------------------------------------------------
    # 混淆矩阵（分类）
    # ------------------------------------------------------------------

    def save_confusion_matrix(self, matrix: Dict[str, Any]) -> str:
        """保存混淆矩阵"""
        path = os.path.join(self.artifacts_dir, "confusion_matrix.json")
        self._save_json(path, matrix)
        return path

    def load_confusion_matrix(self) -> Dict[str, Any]:
        return self._load_json(os.path.join(self.artifacts_dir, "confusion_matrix.json"))

    # ------------------------------------------------------------------
    # 训练日志
    # ------------------------------------------------------------------

    def save_training_log(self, log: str) -> str:
        """保存训练日志"""
        path = os.path.join(self.artifacts_dir, "training.log")
        with open(path, "w", encoding="utf-8") as f:
            f.write(log)
        return path

    def load_training_log(self) -> Optional[str]:
        path = os.path.join(self.artifacts_dir, "training.log")
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    # ------------------------------------------------------------------
    # 验证报告
    # ------------------------------------------------------------------

    def save_validation_report(self, report: Dict[str, Any]) -> str:
        """保存验证报告"""
        path = os.path.join(self.artifacts_dir, "validation_report.json")
        self._save_json(path, report)
        return path

    def load_validation_report(self) -> Dict[str, Any]:
        return self._load_json(os.path.join(self.artifacts_dir, "validation_report.json"))

    # ------------------------------------------------------------------
    # 通用：保存任意产物
    # ------------------------------------------------------------------

    def save_json(self, name: str, data: Any) -> str:
        """保存任意 JSON 产物"""
        if not name.endswith(".json"):
            name = name + ".json"
        path = os.path.join(self.artifacts_dir, name)
        self._save_json(path, data)
        return path

    def save_parquet(self, name: str, df: pd.DataFrame) -> str:
        """保存任意 Parquet 产物"""
        if not name.endswith(".parquet"):
            name = name + ".parquet"
        path = os.path.join(self.artifacts_dir, name)
        df.to_parquet(path)
        return path

    def save_file(self, name: str, src_path: str) -> str:
        """复制外部文件到 artifacts"""
        path = os.path.join(self.artifacts_dir, name)
        shutil.copy2(src_path, path)
        return path

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def list_artifacts(self) -> List[Dict[str, Any]]:
        """列出所有产物"""
        result: List[Dict[str, Any]] = []
        if not os.path.exists(self.artifacts_dir):
            return result
        for fn in sorted(os.listdir(self.artifacts_dir)):
            fp = os.path.join(self.artifacts_dir, fn)
            if os.path.isfile(fp):
                result.append({
                    "name": fn,
                    "size_bytes": os.path.getsize(fp),
                    "size_kb": round(os.path.getsize(fp) / 1024, 2),
                    "modified_at": pd.Timestamp(os.path.getmtime(fp), unit="s").isoformat(),
                })
        return result

    def get_artifact_path(self, name: str) -> Optional[str]:
        """获取产物文件路径"""
        path = os.path.join(self.artifacts_dir, name)
        return path if os.path.exists(path) else None

    def delete_artifact(self, name: str) -> bool:
        """删除产物"""
        path = os.path.join(self.artifacts_dir, name)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def get_summary(self) -> Dict[str, Any]:
        """获取产物存储摘要"""
        artifacts = self.list_artifacts()
        total_size = sum(a["size_bytes"] for a in artifacts)
        return {
            "artifacts_dir": self.artifacts_dir,
            "n_artifacts": len(artifacts),
            "total_size_kb": round(total_size / 1024, 2),
            "artifacts": artifacts,
        }

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    @staticmethod
    def _save_json(path: str, data: Any) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    @staticmethod
    def _load_json(path: str) -> Dict[str, Any]:
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
