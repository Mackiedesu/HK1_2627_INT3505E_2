"""LAB 1 — add your five tests here. Do not delete the smoke tests.

A. GET /books, empty database -> HTTP 200 and []
B. GET /books/9999 -> HTTP 404, JSON code == NOT_FOUND
C. POST /books with only author -> HTTP 400, errors contains title
D. POST valid book, DELETE it, GET same id -> HTTP 404
BONUS. Validate a Book response using JSON Schema; add an unknown
       field to a *copy* of the response and assert ValidationError.

Useful imports:
    from jsonschema import validate, ValidationError
    import pytest
    from tools import get_book_schema

Do not depend on test execution order. Fixtures: client, app, sample_book.
"""

from jsonschema import ValidationError, validate
import pytest
from tools import get_book_schema


def test_list_books_empty_returns_empty_array(client):
    """A. GET /books when database is empty returns HTTP 200 and [] (not null)."""
    response = client.get("/books")
    assert response.status_code == 200
    assert response.content_type.startswith("application/json")
    assert response.get_json() == []


def test_get_book_unknown_id_returns_404_not_found(client):
    """B. GET /books/9999 returns HTTP 404 and JSON containing 'code': 'NOT_FOUND'."""
    response = client.get("/books/9999")
    assert response.status_code == 404
    body = response.get_json()
    assert body["code"] == "NOT_FOUND"


def test_create_book_missing_title_returns_400_with_title_error(client):
    """C. POST /books missing 'title' returns HTTP 400 and 'title' in errors."""
    response = client.post("/books", json={"author": "J.J. Geewax"})
    assert response.status_code == 400
    body = response.get_json()
    assert body["code"] == "VALIDATION_ERROR"
    error_fields = {err["field"] for err in body.get("errors", [])}
    assert "title" in error_fields


def test_delete_book_then_get_same_id_returns_404(client):
    """D. Delete a created book and verify subsequent GET for the same id returns 404."""
    create_resp = client.post(
        "/books",
        json={"title": "Designing Data-Intensive Applications", "author": "Martin Kleppmann", "year": 2017},
    )
    assert create_resp.status_code == 201
    book_id = create_resp.get_json()["id"]

    delete_resp = client.delete(f"/books/{book_id}")
    assert delete_resp.status_code == 204

    get_resp = client.get(f"/books/{book_id}")
    assert get_resp.status_code == 404
    assert get_resp.get_json()["code"] == "NOT_FOUND"


def test_response_extra_field_blocked(client):
    """BONUS. Validate Book response against OpenAPI schema and ensure extra fields like password_hash are rejected."""
    schema = get_book_schema()
    create_resp = client.post(
        "/books",
        json={
            "title": "API Design Patterns",
            "author": "J.J. Geewax",
            "year": 2021,
            "isbn": "9781617295850",
        },
    )
    assert create_resp.status_code == 201
    book_id = create_resp.get_json()["id"]

    response = client.get(f"/books/{book_id}")
    assert response.status_code == 200
    book_data = response.get_json()

    # Valid response from the Flask endpoint conforms to the OpenAPI Book schema
    validate(instance=book_data, schema=schema)

    # Simulate an unexpected leaked field (e.g., password_hash) on a copy of the payload
    tampered = dict(book_data)
    tampered["password_hash"] = "$2b$12$simulatedsecret"
    with pytest.raises(ValidationError):
        validate(instance=tampered, schema=schema)
