"""
V4.4 Experiment Management — Report

报告生成器。
支持 HTML / Markdown 格式。

包含：
  - Parameters
  - Metrics
  - Equity Curve（HTML 内嵌简单 SVG/表格）
  - Drawdown
  - Trade Analysis
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .artifact import ExperimentArtifact


class ReportGenerator:
    """
    报告生成器

    用法：
        gen = ReportGenerator(db=database)
        html = gen.generate_html("exp_001")
        md = gen.generate_markdown("exp_001")
    """

    def __init__(self, db: Any = None) -> None:
        self._db = db

    def generate_html(self, experiment_id: str) -> str:
        """生成 HTML 报告"""
        exp = self._get_experiment(experiment_id)
        if exp is None:
            return f"<html><body><h1>Experiment {experiment_id} not found</h1></body></html>"

        artifact = ExperimentArtifact(experiment_id)
        metrics = exp
        params = exp.get("params", {})
        tags = exp.get("tags", [])

        # 加载权益曲线数据
        equity_data = ""
        eq_df = artifact.load_equity()
        if eq_df is not None and not eq_df.empty:
            equity_data = self._equity_to_html_table(eq_df, max_rows=20)

        # 加载交易数据
        trades_data = ""
        trades_df = artifact.load_trades()
        if trades_df is not None and not trades_df.empty:
            trades_data = self._trades_to_html_table(trades_df, max_rows=20)

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>Experiment Report - {exp.get('name', experiment_id)}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 960px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1 {{ color: #1a1a1a; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #333; margin-top: 30px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin: 20px 0; }}
        .metric-card {{ background: #f8f9fa; padding: 16px; border-radius: 6px; text-align: center; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #1a1a1a; }}
        .metric-label {{ font-size: 12px; color: #666; margin-top: 4px; }}
        .positive {{ color: #4CAF50; }}
        .negative {{ color: #f44336; }}
        table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
        th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #f8f9fa; font-weight: 600; }}
        .tag {{ display: inline-block; background: #e3f2fd; color: #1565c0; padding: 2px 8px; border-radius: 12px; font-size: 12px; margin: 2px; }}
        .params {{ background: #f8f9fa; padding: 16px; border-radius: 6px; }}
        .params dt {{ font-weight: 600; float: left; width: 120px; }}
        .params dd {{ margin-left: 140px; margin-bottom: 4px; }}
    </style>
</head>
<body>
<div class="container">
    <h1>{exp.get('name', experiment_id)}</h1>
    <p><strong>Strategy:</strong> {exp.get('strategy', '')} &nbsp; <strong>Dataset:</strong> {exp.get('dataset_id', '')} &nbsp; <strong>Created:</strong> {exp.get('created_at', '')}</p>
    <p>{' '.join(f'<span class="tag">{t}</span>' for t in tags)}</p>

    <h2>Metrics</h2>
    <div class="metrics">
        <div class="metric-card">
            <div class="metric-value {'positive' if metrics.get('total_return', 0) > 0 else 'negative'}">{metrics.get('total_return', 0):.2f}%</div>
            <div class="metric-label">Total Return</div>
        </div>
        <div class="metric-card">
            <div class="metric-value {'positive' if metrics.get('sharpe', 0) > 0 else 'negative'}">{metrics.get('sharpe', 0):.3f}</div>
            <div class="metric-label">Sharpe Ratio</div>
        </div>
        <div class="metric-card">
            <div class="metric-value negative">{metrics.get('max_drawdown', 0):.2f}%</div>
            <div class="metric-label">Max Drawdown</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{metrics.get('trade_count', 0)}</div>
            <div class="metric-label">Trade Count</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{metrics.get('win_rate', 0):.1f}%</div>
            <div class="metric-label">Win Rate</div>
        </div>
        <div class="metric-card">
            <div class="metric-value">{metrics.get('final_equity', 0):,.0f}</div>
            <div class="metric-label">Final Equity</div>
        </div>
    </div>

    <h2>Parameters</h2>
    <div class="params">
        <dl>
            {''.join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in params.items())}
        </dl>
    </div>

    {f'<h2>Equity Curve</h2>{equity_data}' if equity_data else ''}

    {f'<h2>Recent Trades</h2>{trades_data}' if trades_data else ''}
</div>
</body>
</html>"""
        return html

    def generate_markdown(self, experiment_id: str) -> str:
        """生成 Markdown 报告"""
        exp = self._get_experiment(experiment_id)
        if exp is None:
            return f"# Experiment {experiment_id} not found"

        params = exp.get("params", {})
        tags = exp.get("tags", [])

        lines = [
            f"# {exp.get('name', experiment_id)}",
            "",
            f"- **Strategy:** {exp.get('strategy', '')}",
            f"- **Dataset:** {exp.get('dataset_id', '')} (v{exp.get('dataset_version', '')})",
            f"- **Created:** {exp.get('created_at', '')}",
            f"- **Tags:** {', '.join(tags) if tags else 'None'}",
            "",
            "## Metrics",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Return | {exp.get('total_return', 0):.2f}% |",
            f"| Sharpe Ratio | {exp.get('sharpe', 0):.3f} |",
            f"| Max Drawdown | {exp.get('max_drawdown', 0):.2f}% |",
            f"| Trade Count | {exp.get('trade_count', 0)} |",
            f"| Win Rate | {exp.get('win_rate', 0):.1f}% |",
            f"| Final Equity | {exp.get('final_equity', 0):,.0f} |",
            "",
            "## Parameters",
            "",
        ]

        for k, v in params.items():
            lines.append(f"- **{k}:** {v}")

        return "\n".join(lines)

    # ---------------------------------------------------------
    # 内部方法
    # ---------------------------------------------------------
    def _get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """从 DB 获取实验"""
        if self._db is None:
            return None

        with self._db.get_connection() as conn:
            row = conn.execute(
                """
                SELECT
                    e.id, e.name, e.strategy,
                    e.params_json, e.created_at,
                    e.dataset_id, e.dataset_version,
                    e.tags_json,
                    r.sharpe, r.total_return,
                    r.max_drawdown, r.trade_count,
                    r.win_rate, r.final_equity
                FROM experiments e
                LEFT JOIN results r ON e.id = r.experiment_id
                WHERE e.id = ?
                """,
                (experiment_id,),
            ).fetchone()

        if row is None:
            return None

        d = dict(row)
        try:
            d["params"] = json.loads(d.pop("params_json", "{}"))
        except Exception:
            d["params"] = {}
        try:
            d["tags"] = json.loads(d.pop("tags_json", "[]"))
        except Exception:
            d["tags"] = []
        return d

    @staticmethod
    def _equity_to_html_table(df: Any, max_rows: int = 20) -> str:
        """权益曲线转 HTML 表格"""
        head = df.head(max_rows)
        cols = list(head.columns)
        rows_html = ""
        for idx, row in head.iterrows():
            rows_html += f"<tr><td>{idx}</td>"
            for c in cols:
                rows_html += f"<td>{row[c]:.2f}</td>"
            rows_html += "</tr>"

        header = "<th>Date</th>" + "".join(f"<th>{c}</th>" for c in cols)
        return f"<table><tr>{header}</tr>{rows_html}</table>"

    @staticmethod
    def _trades_to_html_table(df: Any, max_rows: int = 20) -> str:
        """交易明细转 HTML 表格"""
        head = df.head(max_rows)
        cols = list(head.columns)
        rows_html = ""
        for _, row in head.iterrows():
            rows_html += "<tr>"
            for c in cols:
                val = row[c]
                if isinstance(val, float):
                    rows_html += f"<td>{val:.4f}</td>"
                else:
                    rows_html += f"<td>{val}</td>"
            rows_html += "</tr>"

        header = "".join(f"<th>{c}</th>" for c in cols)
        return f"<table><tr>{header}</tr>{rows_html}</table>"
