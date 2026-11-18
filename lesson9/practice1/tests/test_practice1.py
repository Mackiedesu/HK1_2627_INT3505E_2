"""Tests for Practice 1: URI Path Versioning (v1 & v2), POST /users, and Sunset headers."""

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import app  # noqa: E402
from blueprints import users_data  # noqa: E402


@pytest.fixture(autouse=True)
def reset_users():
    """Restore in-memory USERS between tests."""
    snapshot = copy.deepcopy(users_data.USERS)
    yield
    users_data.USERS.clear()
    users_data.USERS.update(snapshot)


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def test_get_user_v1_returns_full_name_and_sunset_headers(client):
    resp = client.get("/api/v1/users/1")
    assert resp.status_code == 200
    assert resp.get_json() == {
        "id": 1,
        "full_name": "Văn Nguyễn",
        "email": "a@vnu.vn",
    }
    assert resp.headers.get("Sunset") == "Thu, 31 Dec 2026 23:59:59 GMT"
    assert resp.headers.get("Deprecation") == "true"
    assert resp.headers.get("Link") == '</api/v2/users>; rel="successor-version"'


def test_get_user_v2_returns_first_and_last_name(client):
    resp = client.get("/api/v2/users/1")
    assert resp.status_code == 200
    assert resp.get_json() == {
        "id": 1,
        "first_name": "Văn",
        "last_name": "Nguyễn",
        "email": "a@vnu.vn",
    }
    assert "Sunset" not in resp.headers


def test_get_user_not_found_both_versions(client):
    assert client.get("/api/v1/users/999").status_code == 404
    assert client.get("/api/v2/users/999").status_code == 404


def test_create_user_v2_and_read_from_both_versions(client):
    create_resp = client.post(
        "/api/v2/users",
        json={"first_name": "Minh", "last_name": "Lê", "email": "c@vnu.vn"},
    )
    assert create_resp.status_code == 201
    created = create_resp.get_json()
    assert created == {
        "id": 3,
        "first_name": "Minh",
        "last_name": "Lê",
        "email": "c@vnu.vn",
    }

    v1_resp = client.get("/api/v1/users/3")
    assert v1_resp.status_code == 200
    assert v1_resp.get_json()["full_name"] == "Minh Lê"

    v2_resp = client.get("/api/v2/users/3")
    assert v2_resp.status_code == 200
    assert v2_resp.get_json()["first_name"] == "Minh"


def test_create_user_v2_validation_error(client):
    resp = client.post("/api/v2/users", json={"first_name": "Minh"})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["error"] == "validation_error"
    assert set(data["missing_fields"]) == {"last_name", "email"}
