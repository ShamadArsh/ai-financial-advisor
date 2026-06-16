"""
Integration tests for the FastAPI app endpoints.
Tests the HTTP API layer without requiring ML dependencies.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


class TestHealthEndpoint:
    """Tests for GET /api/health"""

    def test_health_returns_200(self):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_health_returns_status_ok(self):
        data = resp_data(client.get("/api/health"))
        assert data["status"] == "ok"

    def test_health_returns_agents_dict(self):
        data = resp_data(client.get("/api/health"))
        assert "agents" in data
        agents = data["agents"]
        assert "news_agent" in agents
        assert "rag_agent" in agents
        assert "finbert_agent" in agents
        assert "gemini_merge" in agents

    def test_rag_and_finbert_always_available(self):
        """Local models should always report as available."""
        data = resp_data(client.get("/api/health"))
        assert data["agents"]["rag_agent"] is True
        assert data["agents"]["finbert_agent"] is True


class TestAgentsEndpoint:
    """Tests for GET /api/agents"""

    def test_agents_returns_200(self):
        resp = client.get("/api/agents")
        assert resp.status_code == 200

    def test_agents_returns_list(self):
        data = resp_data(client.get("/api/agents"))
        assert "agents" in data
        assert isinstance(data["agents"], list)
        assert len(data["agents"]) == 7

    def test_agents_have_required_fields(self):
        data = resp_data(client.get("/api/agents"))
        for agent in data["agents"]:
            assert "name" in agent
            assert "description" in agent
            assert "configured" in agent


class TestIndexPage:
    """Tests for GET /"""

    def test_index_returns_200(self):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_index_returns_html(self):
        resp = client.get("/")
        assert "text/html" in resp.headers.get("content-type", "")
        assert "Financial AI Advisor" in resp.text


class TestAskEndpoint:
    """Tests for POST /api/ask"""

    def test_ask_empty_question_returns_400(self):
        resp = client.post("/api/ask", json={"question": ""})
        assert resp.status_code == 400

    def test_ask_no_question_returns_400(self):
        resp = client.post("/api/ask", json={})
        assert resp.status_code == 422  # Pydantic validation error

    def test_ask_returns_structured_response(self):
        """Even without ML deps, the endpoint should return a structured response."""
        resp = client.post("/api/ask", json={"question": "Should I invest in steel?"})
        assert resp.status_code == 200
        data = resp.json()
        assert "question" in data
        assert "answer" in data
        assert "error" in data  # Expected: error due to missing langgraph


class TestStockEndpoint:
    """Tests for GET /api/stock/{ticker}"""

    def test_stock_no_key_returns_503(self):
        """Without FMP_API_KEY, should return 503."""
        resp = client.get("/api/stock/AAPL")
        assert resp.status_code == 503


def resp_data(resp):
    """Helper to get JSON data from a response."""
    return resp.json()


if __name__ == "__main__":
    # Simple test runner
    test_classes = [TestHealthEndpoint, TestAgentsEndpoint, TestIndexPage, TestAskEndpoint, TestStockEndpoint]
    passed = 0
    failed = 0
    for cls in test_classes:
        instance = cls()
        test_methods = [m for m in dir(instance) if m.startswith("test_")]
        for method_name in test_methods:
            try:
                getattr(instance, method_name)()
                print(f"  ✅ {cls.__name__}.{method_name}")
                passed += 1
            except Exception as e:
                print(f"  ❌ {cls.__name__}.{method_name}: {e}")
                failed += 1
    print(f"\n{passed}/{passed + failed} tests passed")
    if failed:
        exit(1)
