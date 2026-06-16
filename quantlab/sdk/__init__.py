"""
QuantLab V2.0 — SDK

统一客户端接口。未来 CLI / Jupyter / Web 全部通过 SDK 访问。

用法：
    from quantlab.sdk import QuantLabClient

    client = QuantLabClient(base_url="http://localhost:8000")

    # Factors
    factors = client.factors.list()
    factor = client.factors.get("RSI14")

    # Signals
    signals = client.signals.list()
    signal = client.signals.build_threshold("RSI14", "<", 30)

    # Strategies
    strategies = client.strategies.list()
    spec = client.strategies.create_spec("MyStrategy", signals=[...])

    # Experiments
    experiments = client.experiments.list()
    sweep = client.experiments.run_sweep("ma_cross", {"fast": [10,20], "slow": [40,60]})

    # Workflow
    suggestions = client.workflow.suggestions()
    next_step = client.workflow.next_step()
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import HTTPError

logger = logging.getLogger("quantlab.sdk")


# ============================================================
# HTTP Transport
# ============================================================

class HttpTransport:
    """简单 HTTP 客户端（不依赖 requests）"""

    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        self.base_url = base_url.rstrip("/")

    def get(self, path: str, params: Optional[Dict] = None) -> Any:
        url = f"{self.base_url}{path}"
        if params:
            query = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
            if query:
                url += f"?{query}"
        req = Request(url, method="GET")
        req.add_header("Accept", "application/json")
        with urlopen(req) as resp:
            return json.loads(resp.read().decode())

    def post(self, path: str, data: Optional[Dict] = None) -> Any:
        url = f"{self.base_url}{path}"
        body = json.dumps(data or {}).encode()
        req = Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json")
        try:
            with urlopen(req) as resp:
                return json.loads(resp.read().decode())
        except HTTPError as e:
            error_body = e.read().decode()
            raise SDKError(f"HTTP {e.code}: {error_body}") from e

    def delete(self, path: str) -> Any:
        url = f"{self.base_url}{path}"
        req = Request(url, method="DELETE")
        req.add_header("Accept", "application/json")
        with urlopen(req) as resp:
            return json.loads(resp.read().decode())


class SDKError(Exception):
    """SDK 错误"""
    pass


# ============================================================
# Resource Clients
# ============================================================

class FactorClient:
    """因子资源客户端"""

    def __init__(self, transport: HttpTransport) -> None:
        self._t = transport

    def list(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        return self._t.get("/api/v1/factors", {"category": category})

    def get(self, name: str) -> Dict[str, Any]:
        return self._t.get(f"/api/v1/factors/{name}")

    def compute(self, name: str, **kwargs) -> Any:
        return self._t.post(f"/api/v1/factors/{name}/compute", kwargs)


class SignalClient:
    """信号资源客户端"""

    def __init__(self, transport: HttpTransport) -> None:
        self._t = transport

    def list(self) -> List[Dict[str, Any]]:
        return self._t.get("/api/v1/signals")

    def get(self, name: str) -> Dict[str, Any]:
        return self._t.get(f"/api/v1/signals/{name}")

    def build_threshold(self, factor_name: str, operator: str, value: float, **kwargs) -> Dict[str, Any]:
        return self._t.post("/api/v1/signals/build/threshold", {
            "factor_name": factor_name, "operator": operator, "value": value, **kwargs,
        })

    def build_crossover(self, fast_factor: str, slow_factor: str, **kwargs) -> Dict[str, Any]:
        return self._t.post("/api/v1/signals/build/crossover", {
            "fast_factor": fast_factor, "slow_factor": slow_factor, **kwargs,
        })

    def preview(self, name: str, **kwargs) -> Dict[str, Any]:
        return self._t.post(f"/api/v1/signals/{name}/preview", kwargs)


class StrategyClient:
    """策略资源客户端"""

    def __init__(self, transport: HttpTransport) -> None:
        self._t = transport

    def list(self, q: str = "", tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        return self._t.get("/api/v1/strategies", {"q": q, "tags": ",".join(tags or [])})

    def get(self, strategy_id: str) -> Dict[str, Any]:
        return self._t.get(f"/api/v1/strategies/{strategy_id}")

    def create_spec(self, name: str, signals: List[Dict], signal_logic: str = "AND",
                    position: Optional[Dict] = None, risk: Optional[Dict] = None,
                    description: str = "", tags: Optional[List[str]] = None) -> Dict[str, Any]:
        return self._t.post("/api/v1/strategy-builder/create", {
            "name": name, "signals": signals, "signal_logic": signal_logic,
            "position": position, "risk": risk, "description": description, "tags": tags,
        })

    def compile(self, spec_id: str) -> Dict[str, Any]:
        return self._t.post("/api/v1/strategy-builder/compile", {"spec_id": spec_id})

    def list_specs(self) -> List[Dict[str, Any]]:
        return self._t.get("/api/v1/strategy-builder/specs")

    def templates(self) -> List[Dict[str, Any]]:
        return self._t.get("/api/v1/strategy-builder/templates")


class ExperimentClient:
    """实验资源客户端"""

    def __init__(self, transport: HttpTransport) -> None:
        self._t = transport

    def list(self, strategy: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        return self._t.get("/api/v1/experiments", {"strategy": strategy, "limit": limit})

    def get(self, experiment_id: str) -> Dict[str, Any]:
        return self._t.get(f"/api/v1/experiments/{experiment_id}")

    def run_sweep(self, strategy_id: str, param_space: Dict[str, List],
                  dataset_id: str = "default") -> Dict[str, Any]:
        return self._t.post("/api/v1/research/sweep", {
            "strategy_id": strategy_id, "param_space": param_space, "dataset_id": dataset_id,
        })

    def get_sweep(self, sweep_id: str) -> Dict[str, Any]:
        return self._t.get(f"/api/v1/research/sweeps/{sweep_id}")

    def list_sweeps(self) -> List[Dict[str, Any]]:
        return self._t.get("/api/v1/research/sweeps")

    def heatmap(self, sweep_id: str, x_param: str, y_param: str, metric: str = "sharpe") -> Dict[str, Any]:
        return self._t.post("/api/v1/research/heatmap", {
            "sweep_id": sweep_id, "x_param": x_param, "y_param": y_param, "metric": metric,
        })

    def robustness(self, sweep_id: str, params: List[str], metric: str = "sharpe") -> Dict[str, Any]:
        return self._t.post("/api/v1/research/robustness", {
            "sweep_id": sweep_id, "params": params, "metric": metric,
        })

    def candidates(self, sweep_id: str, min_sharpe: float = 1.5) -> Dict[str, Any]:
        return self._t.post("/api/v1/research/candidates", {
            "sweep_id": sweep_id, "min_sharpe": min_sharpe,
        })


class DatasetClient:
    """数据集资源客户端"""

    def __init__(self, transport: HttpTransport) -> None:
        self._t = transport

    def list(self) -> List[Dict[str, Any]]:
        return self._t.get("/api/v1/datasets")

    def get(self, dataset_id: str) -> Dict[str, Any]:
        return self._t.get(f"/api/v1/datasets/{dataset_id}")


class WorkflowClient:
    """研究流程客户端"""

    def __init__(self, transport: HttpTransport) -> None:
        self._t = transport

    def suggestions(self, include_dismissed: bool = False) -> Dict[str, Any]:
        return self._t.get("/api/v1/research/workflow/suggestions", {
            "include_dismissed": str(include_dismissed).lower(),
        })

    def next_step(self) -> Dict[str, Any]:
        return self._t.get("/api/v1/research/workflow/next-step")

    def dismiss(self, index: int) -> Dict[str, Any]:
        return self._t.post(f"/api/v1/research/workflow/dismiss/{index}")

    def clear(self) -> Dict[str, Any]:
        return self._t.post("/api/v1/research/workflow/clear")

    def history(self, limit: int = 50) -> Dict[str, Any]:
        return self._t.get("/api/v1/research/workflow/history", {"limit": limit})

    def publish_event(self, event_type: str, payload: Optional[Dict] = None) -> Dict[str, Any]:
        return self._t.post("/api/v1/research/workflow/event", {
            "event_type": event_type, "payload": payload or {},
        })


# ============================================================
# QuantLabClient — 主入口
# ============================================================

class QuantLabClient:
    """
    QuantLab SDK 主入口

    用法：
        client = QuantLabClient()
        factors = client.factors.list()
        suggestions = client.workflow.suggestions()
    """

    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        self._transport = HttpTransport(base_url)
        self.factors = FactorClient(self._transport)
        self.signals = SignalClient(self._transport)
        self.strategies = StrategyClient(self._transport)
        self.experiments = ExperimentClient(self._transport)
        self.datasets = DatasetClient(self._transport)
        self.workflow = WorkflowClient(self._transport)

    @property
    def base_url(self) -> str:
        return self._transport.base_url

    def health(self) -> Dict[str, Any]:
        """健康检查"""
        return self._transport.get("/health")
