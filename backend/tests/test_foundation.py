from fastapi.testclient import TestClient


def test_health_and_versioned_openapi(client: TestClient):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "X-Request-ID" in response.headers

    schema = client.get("/openapi.json").json()
    business_paths = [path for path in schema["paths"] if path != "/openapi.json"]
    assert business_paths
    assert all(path.startswith("/api/v1/") for path in business_paths)


def test_errors_have_stable_envelope_and_request_id(client: TestClient):
    response = client.get("/api/v1/auth/me", headers={"X-Request-ID": "req-test-1"})
    assert response.status_code == 401
    assert response.json() == {
        "code": "AUTH_REQUIRED",
        "message": "Authentication is required",
        "request_id": "req-test-1",
    }
    assert response.headers["X-Request-ID"] == "req-test-1"


def test_roles_and_member_ownership_are_enforced(client: TestClient, member_headers, admin_headers):
    assert client.get("/api/v1/operations/status", headers=member_headers).status_code == 403
    assert client.get("/api/v1/operations/status", headers=admin_headers).status_code == 200

    own = client.get("/api/v1/members/member-demo/profile", headers=member_headers)
    assert own.status_code == 200
    assert own.json()["member_id"] == "member-demo"

    other = client.get("/api/v1/members/member-other/profile", headers=member_headers)
    assert other.status_code == 403
    assert other.json()["code"] == "RESOURCE_FORBIDDEN"


def test_development_login_is_explicitly_unavailable_in_production(client: TestClient):
    from app.core.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()
    settings.app_env = "production"
    settings.dev_auth_enabled = False

    response = client.post("/api/v1/auth/dev", json={"role": "member"})
    assert response.status_code == 403
    assert response.json()["code"] == "DEV_AUTH_DISABLED"
    static_token = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer dev-admin"})
    assert static_token.status_code == 401
