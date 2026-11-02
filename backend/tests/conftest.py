from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{tmp_path / 'test.sqlite3'}")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEV_AUTH_ENABLED", "true")
    monkeypatch.setenv("WEB_ORIGIN", "http://localhost:5173")

    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            del sys.modules[module_name]

    main = importlib.import_module("app.main")
    app = main.create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db(client: TestClient):
    from app.core.database import SessionLocal

    with SessionLocal() as session:
        yield session


@pytest.fixture()
def member_headers() -> dict[str, str]:
    return {"Authorization": "Bearer dev-member"}


@pytest.fixture()
def admin_headers() -> dict[str, str]:
    return {"Authorization": "Bearer dev-admin"}


@pytest.fixture()
def frontdesk_headers() -> dict[str, str]:
    return {"Authorization": "Bearer dev-frontdesk"}


@pytest.fixture()
def merchant_headers() -> dict[str, str]:
    return {"Authorization": "Bearer dev-merchant"}


@pytest.fixture()
def finance_headers() -> dict[str, str]:
    return {"Authorization": "Bearer dev-finance"}


@pytest.fixture()
def device_headers() -> dict[str, str]:
    return {"Authorization": "Bearer dev-device-service-change-me"}
