"""Pytest fixtures for testing the Product & Order Backend Service."""

from contextlib import contextmanager
import pytest
from sqlalchemy import event
from product_api.config import TestConfig
from product_api.extensions import db
from product_api.factory import create_app


@pytest.fixture()
def app():
    """Create an isolated Flask application instance backed by in-memory SQLite."""
    application = create_app(TestConfig)
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    """Provide a Flask test client for issuing HTTP requests."""
    return app.test_client()


@pytest.fixture()
def count_queries(app):
    """
    Context manager fixture that counts the exact number of SQL statements executed
    against the database engine to detect N+1 query issues.
    """

    @contextmanager
    def _counter():
        statements: list[str] = []

        def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            statements.append(statement)

        with app.app_context():
            engine = db.engine
            event.listen(engine, "before_cursor_execute", _before_cursor_execute)
            try:
                yield statements
            finally:
                event.remove(engine, "before_cursor_execute", _before_cursor_execute)

    return _counter
