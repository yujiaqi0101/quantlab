"""
Signal Engine API 冒烟测试
==========================

用 FastAPI TestClient 验证 9 个端点的基本可用性：
  - GET  /templates
  - GET  /templates/{name}
  - POST /generate
  - GET  /signals
  - GET  /signals/{signal_id}  (404 用例)
  - GET  /registry/versions
  - GET  /explain/{signal_id}  (404 用例)
  - POST /adapt
  - POST /validate             (400 用例：缺 returns)

注：本测试不写入正式市场数据库；仅用内存 predictions 触发 pipeline。
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from quantlab.api.app import app


@pytest.fixture(scope="module")
def client():
    """复用 TestClient"""
    with TestClient(app) as c:
        yield c


# ---------- /templates ----------

def test_templates_returns_200_and_8_templates(client: TestClient):
    r = client.get("/api/v1/signal-engine/templates")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 8
    names = {t["name"] for t in data["templates"]}
    assert "topk" in names
    assert "long_short" in names


def test_template_detail_returns_200(client: TestClient):
    r = client.get("/api/v1/signal-engine/templates/topk")
    assert r.status_code == 200
    assert r.json()["name"] == "topk"


def test_template_detail_returns_404_for_unknown(client: TestClient):
    r = client.get("/api/v1/signal-engine/templates/__not_exist__")
    assert r.status_code == 404


# ---------- /generate ----------

def _minimal_payload():
    return {
        "predictions": [
            {"symbol": "BTC", "datetime": "2024-01-01", "value": 0.05, "model_type": "lightgbm"},
            {"symbol": "ETH", "datetime": "2024-01-01", "value": 0.03, "model_type": "lightgbm"},
            {"symbol": "SOL", "datetime": "2024-01-01", "value": -0.02, "model_type": "lightgbm"},
        ],
        "config": {
            "generator_type": "threshold",
            "generator_params": {
                "long_threshold": 0.025,
                "short_threshold": -0.015,
                "use_short": True,
            },
            "ranker_type": "topk",
            "ranker_params": {"k": 2},
            "allocator_type": "equal_weight",
        },
    }


def test_generate_returns_signals_with_explain_trace(client: TestClient):
    r = client.post("/api/v1/signal-engine/generate", json=_minimal_payload())
    assert r.status_code == 200
    data = r.json()
    # 顶层结构
    assert "set_id" in data
    assert "signals" in data
    assert "summary" in data
    assert "metadata" in data
    # signals 非空
    assert len(data["signals"]) == 3
    # 每条 signal 有完整字段
    s = data["signals"][0]
    for key in ("signal_id", "symbol", "direction", "score", "suggested_weight", "metadata"):
        assert key in s, f"missing key: {key}"
    # explain_trace 完整：generator → filter → ranker → scorer → allocator
    trace = s["metadata"].get("explain_trace", [])
    steps = [t["step"] for t in trace]
    assert steps == ["generator", "filter", "ranker", "scorer", "allocator"]


def test_generate_with_empty_predictions_returns_empty_signals(client: TestClient):
    r = client.post(
        "/api/v1/signal-engine/generate",
        json={"predictions": []},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["signals"] == []


# ---------- /signals ----------

def test_signals_list_returns_200(client: TestClient):
    r = client.get("/api/v1/signal-engine/signals?limit=10")
    assert r.status_code == 200
    data = r.json()
    assert "signals" in data
    assert "total" in data
    assert isinstance(data["signals"], list)


def test_signal_detail_returns_404_for_unknown(client: TestClient):
    r = client.get("/api/v1/signal-engine/signals/__not_exist__")
    assert r.status_code == 404


# ---------- /registry/versions ----------

def test_registry_versions_returns_200(client: TestClient):
    r = client.get("/api/v1/signal-engine/registry/versions")
    assert r.status_code == 200
    data = r.json()
    assert "versions" in data
    assert "total" in data


def test_registry_version_detail_returns_404_for_unknown(client: TestClient):
    r = client.get("/api/v1/signal-engine/registry/versions/__not_exist__")
    assert r.status_code == 404


# ---------- /explain ----------

def test_explain_returns_404_for_unknown(client: TestClient):
    r = client.get("/api/v1/signal-engine/explain/__not_exist__")
    assert r.status_code == 404


# ---------- /adapt ----------

def test_adapt_returns_predictions(client: TestClient):
    r = client.post(
        "/api/v1/signal-engine/adapt",
        json={
            "model_type": "lightgbm",
            "outputs": [0.05, -0.02],
            "symbols": ["BTC", "ETH"],
            "datetime": "2024-01-01",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    assert data["predictions"][0]["symbol"] == "BTC"


# ---------- /validate ----------

def test_validate_returns_400_when_no_returns(client: TestClient):
    r = client.post(
        "/api/v1/signal-engine/validate",
        json={"signal_ids": ["__not_exist__"], "returns_data": {}, "returns_index": []},
    )
    assert r.status_code == 404  # 没找到任何 signal


# ---------- 端到端：generate → signals → explain ----------

def test_e2e_generate_then_query(client: TestClient):
    """先生成信号并持久化，再查询单个 signal + explain，确认端到端链路通畅"""
    payload = _minimal_payload()
    payload["save_to_registry"] = True
    payload["model_version"] = "test-v1"
    # 1. 生成并保存
    r1 = client.post("/api/v1/signal-engine/generate", json=payload)
    assert r1.status_code == 200
    sig_id = r1.json()["signals"][0]["signal_id"]

    # 2. 查询单个 signal
    r2 = client.get(f"/api/v1/signal-engine/signals/{sig_id}")
    assert r2.status_code == 200
    assert r2.json()["signal_id"] == sig_id

    # 3. 查询 explain
    r3 = client.get(f"/api/v1/signal-engine/explain/{sig_id}")
    assert r3.status_code == 200
    explain = r3.json()
    # ExplainTrace.to_dict() 字段：prediction / after_generator / after_allocator / final_signal 等
    assert "after_generator" in explain
    assert "final_signal" in explain
