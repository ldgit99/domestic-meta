from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root_returns_service_index() -> None:
    response = client.get("/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["api_base"] == "/api"
    assert payload["dashboard_url"] == "/dashboard"
    assert "/api/search-requests" in payload["key_endpoints"]


def test_dashboard_serves_frontend_html() -> None:
    response = client.get("/dashboard")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "교육학 메타분석 AI 워크스페이스" in response.text


def test_api_root_returns_message_and_key_endpoints() -> None:
    response = client.get("/api")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["dashboard_url"] == "/dashboard"
    assert payload["message"].startswith("Use /docs")
    assert "/api/candidates/{id}/extract" in payload["key_endpoints"]


def test_health_endpoints_return_ok() -> None:
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/api/health").json() == {"status": "ok"}
