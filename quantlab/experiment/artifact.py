"""
V4.4 Experiment Management — Artifact

实验产出物管理。
每个实验的 equity_curve / trades / orders / report 落盘到独立目录。

目录结构：
  experiments/
    exp_001/
      metadata.json
      metrics.json
      equity.parquet
      trades.parquet
      report.html
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass(slots=True)
class ExperimentArtifact:
    """
    实验产出物

    保存：
      equity_curve  权益曲线
      trades        交易明细
      orders        订单明细
      report_html   HTML 报告
    """
    experiment_id: str
    base_dir: str = "experiments"

    @property
    def exp_dir(self) -> str:
        return os.path.join(self.base_dir, self.experiment_id)

    def ensure_dir(self) -> str:
        """确保实验目录存在"""
        os.makedirs(self.exp_dir, exist_ok=True)
        return self.exp_dir

    # ---------------------------------------------------------
    # 保存
    # ---------------------------------------------------------
    def save_equity(self, equity: pd.DataFrame) -> str:
        """保存权益曲线"""
        self.ensure_dir()
        path = os.path.join(self.exp_dir, "equity.parquet")
        equity.to_parquet(path, index=True)
        return path

    def save_trades(self, trades: pd.DataFrame) -> str:
        """保存交易明细"""
        self.ensure_dir()
        path = os.path.join(self.exp_dir, "trades.parquet")
        trades.to_parquet(path, index=False)
        return path

    def save_orders(self, orders: pd.DataFrame) -> str:
        """保存订单明细"""
        self.ensure_dir()
        path = os.path.join(self.exp_dir, "orders.parquet")
        orders.to_parquet(path, index=False)
        return path

    def save_metadata(self, metadata: Dict[str, Any]) -> str:
        """保存实验元信息"""
        self.ensure_dir()
        path = os.path.join(self.exp_dir, "metadata.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2, default=str)
        return path

    def save_metrics(self, metrics: Dict[str, Any]) -> str:
        """保存实验指标"""
        self.ensure_dir()
        path = os.path.join(self.exp_dir, "metrics.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2, default=str)
        return path

    def save_report_html(self, html: str) -> str:
        """保存 HTML 报告"""
        self.ensure_dir()
        path = os.path.join(self.exp_dir, "report.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return path

    def save_report_markdown(self, md: str) -> str:
        """保存 Markdown 报告"""
        self.ensure_dir()
        path = os.path.join(self.exp_dir, "report.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(md)
        return path

    # ---------------------------------------------------------
    # 加载
    # ---------------------------------------------------------
    def load_equity(self) -> Optional[pd.DataFrame]:
        """加载权益曲线"""
        path = os.path.join(self.exp_dir, "equity.parquet")
        if os.path.isfile(path):
            return pd.read_parquet(path)
        return None

    def load_trades(self) -> Optional[pd.DataFrame]:
        """加载交易明细"""
        path = os.path.join(self.exp_dir, "trades.parquet")
        if os.path.isfile(path):
            return pd.read_parquet(path)
        return None

    def load_orders(self) -> Optional[pd.DataFrame]:
        """加载订单明细"""
        path = os.path.join(self.exp_dir, "orders.parquet")
        if os.path.isfile(path):
            return pd.read_parquet(path)
        return None

    def load_metadata(self) -> Optional[Dict[str, Any]]:
        """加载元信息"""
        path = os.path.join(self.exp_dir, "metadata.json")
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def load_metrics(self) -> Optional[Dict[str, Any]]:
        """加载指标"""
        path = os.path.join(self.exp_dir, "metrics.json")
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def load_report_html(self) -> Optional[str]:
        """加载 HTML 报告"""
        path = os.path.join(self.exp_dir, "report.html")
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return None

    # ---------------------------------------------------------
    # 状态
    # ---------------------------------------------------------
    def exists(self) -> bool:
        """实验目录是否存在"""
        return os.path.isdir(self.exp_dir)

    def list_files(self) -> List[str]:
        """列出实验目录下所有文件"""
        if not self.exists():
            return []
        return os.listdir(self.exp_dir)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "base_dir": self.base_dir,
            "exp_dir": self.exp_dir,
            "exists": self.exists(),
            "files": self.list_files(),
        }
