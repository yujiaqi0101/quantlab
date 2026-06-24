"""
Validation Artifacts — 验证产物持久化

保存验证过程中产生的所有产物：
  validation/
  ├── summary.json        验证摘要
  ├── walkforward.json    Walk Forward 结果
  ├── benchmark.json      基准对比结果
  ├── robustness.json     鲁棒性结果
  ├── report.html         HTML 报告
  └── plots/              图表

复用：ml/registry/artifacts.py 的 ArtifactStore
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger("quantlab.ml.validation.pipeline.artifacts")


class ValidationArtifactStore:
    """
    验证产物存储

    用法：
        store = ValidationArtifactStore("/path/to/validation_dir")
        store.save_result(pipeline_result)
        store.save_report_html(html_str)
    """

    def __init__(self, base_dir: str) -> None:
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)
        self.plots_dir = os.path.join(self.base_dir, "plots")
        os.makedirs(self.plots_dir, exist_ok=True)

    def save_summary(self, result: Any) -> str:
        """保存验证摘要"""
        path = os.path.join(self.base_dir, "summary.json")
        data = result.to_dict() if hasattr(result, "to_dict") else result
        self._save_json(path, data)
        return path

    def save_gate_result(self, gate_name: str, gate_result: Any) -> str:
        """保存单个 Gate 结果"""
        path = os.path.join(self.base_dir, f"{gate_name}.json")
        data = gate_result.to_dict() if hasattr(gate_result, "to_dict") else gate_result
        self._save_json(path, data)
        return path

    def save_all_gates(self, pipeline_result: Any) -> list[str]:
        """保存所有 Gate 结果"""
        paths = []
        for gr in pipeline_result.gate_results:
            path = self.save_gate_result(gr.gate_name, gr)
            paths.append(path)
        return paths

    def save_report_html(self, html: str) -> str:
        """保存 HTML 报告"""
        path = os.path.join(self.base_dir, "report.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        return path

    def save_plot(self, name: str, data: bytes) -> str:
        """保存图表"""
        path = os.path.join(self.plots_dir, name)
        with open(path, "wb") as f:
            f.write(data)
        return path

    def load_summary(self) -> Optional[Dict[str, Any]]:
        """加载验证摘要"""
        path = os.path.join(self.base_dir, "summary.json")
        return self._load_json(path)

    def load_gate_result(self, gate_name: str) -> Optional[Dict[str, Any]]:
        """加载单个 Gate 结果"""
        path = os.path.join(self.base_dir, f"{gate_name}.json")
        return self._load_json(path)

    def list_artifacts(self) -> list[str]:
        """列出所有产物文件"""
        artifacts = []
        for root, dirs, files in os.walk(self.base_dir):
            for f in files:
                rel = os.path.relpath(os.path.join(root, f), self.base_dir)
                artifacts.append(rel)
        return artifacts

    def _save_json(self, path: str, data: Any) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    def _load_json(self, path: str) -> Optional[Dict[str, Any]]:
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)


def generate_html_report(pipeline_result: Any) -> str:
    """
    生成 HTML 验证报告

    生成一个包含所有 Gate 结果的 HTML Dashboard。
    """
    result_dict = pipeline_result.to_dict() if hasattr(pipeline_result, "to_dict") else pipeline_result

    # 构建 HTML
    html_parts = []
    html_parts.append("<!DOCTYPE html>")
    html_parts.append('<html lang="zh-CN">')
    html_parts.append("<head>")
    html_parts.append('<meta charset="UTF-8">')
    html_parts.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    html_parts.append(f"<title>Validation Report - {result_dict.get('validation_id', '')}</title>")
    html_parts.append("<style>")
    html_parts.append("""
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 20px; background: #f5f7fa; }
        .header { background: #fff; padding: 20px; border-radius: 8px; margin-bottom: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .score-display { font-size: 48px; font-weight: bold; }
        .grade-A { color: #67c23a; }
        .grade-B { color: #409eff; }
        .grade-C { color: #e6a23c; }
        .grade-D { color: #f56c6c; }
        .grade-F { color: #f56c6c; }
        .gate-card { background: #fff; padding: 16px; border-radius: 8px; margin-bottom: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .gate-header { display: flex; justify-content: space-between; align-items: center; }
        .gate-name { font-weight: bold; font-size: 16px; }
        .gate-status { padding: 4px 12px; border-radius: 4px; font-size: 12px; font-weight: bold; }
        .status-PASS { background: #f0f9eb; color: #67c23a; }
        .status-WARNING { background: #fdf6ec; color: #e6a23c; }
        .status-FAIL { background: #fef0f0; color: #f56c6c; }
        .status-SKIP { background: #f4f4f5; color: #909399; }
        .status-ERROR { background: #fef0f0; color: #f56c6c; }
        .gate-score { font-size: 24px; font-weight: bold; margin: 8px 0; }
        .gate-summary { color: #606266; font-size: 14px; }
        .gate-details { background: #f5f7fa; padding: 12px; border-radius: 4px; margin-top: 8px; font-size: 12px; font-family: monospace; white-space: pre-wrap; max-height: 300px; overflow: auto; }
        .passed { color: #67c23a; }
        .failed { color: #f56c6c; }
    """)
    html_parts.append("</style>")
    html_parts.append("</head>")
    html_parts.append("<body>")

    # Header
    html_parts.append('<div class="header">')
    html_parts.append(f"<h1>Validation Report</h1>")
    html_parts.append(f"<p>Validation ID: {result_dict.get('validation_id', '')}</p>")
    html_parts.append(f'<p>Overall Score: <span class="score-display grade-{result_dict.get("overall_grade", "F")}">{result_dict.get("overall_score", 0):.1f} ({result_dict.get("overall_grade", "F")})</span></p>')
    html_parts.append(f'<p>Status: <span class="{"passed" if result_dict.get("passed") else "failed"}">{result_dict.get("overall_status", "UNKNOWN")}</span></p>')
    if result_dict.get("stopped_at"):
        html_parts.append(f'<p style="color: #f56c6c;">Stopped at: {result_dict["stopped_at"]}</p>')
    html_parts.append(f"<p>Execution Time: {result_dict.get('total_execution_time', 0):.2f}s</p>")
    html_parts.append("</div>")

    # Gate Results
    for gr in result_dict.get("gate_results", []):
        status = gr.get("status", "SKIP")
        grade = gr.get("grade", "F")
        html_parts.append('<div class="gate-card">')
        html_parts.append('<div class="gate-header">')
        html_parts.append(f'<span class="gate-name">[{gr.get("level", "")}] {gr.get("gate_name", "")}</span>')
        html_parts.append(f'<span class="gate-status status-{status}">{status}</span>')
        html_parts.append("</div>")
        html_parts.append(f'<div class="gate-score grade-{grade}">{gr.get("score", 0):.1f} ({grade})</div>')
        html_parts.append(f'<div class="gate-summary">{gr.get("summary", "")}</div>')
        if gr.get("details"):
            details_json = json.dumps(gr["details"], indent=2, ensure_ascii=False, default=str)
            html_parts.append(f'<div class="gate-details">{details_json}</div>')
        if gr.get("error"):
            html_parts.append(f'<div class="gate-details" style="color: #f56c6c;">Error: {gr["error"]}</div>')
        html_parts.append("</div>")

    html_parts.append("</body>")
    html_parts.append("</html>")

    return "\n".join(html_parts)
