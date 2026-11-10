"""Application Factory wiring Flask config, extensions, logging, errors, and blueprints."""

import os
from flask import Flask
from .api.health import health_bp
from .api.orders import orders_bp
from .api.products import products_bp
from .config import DefaultConfig
from .errors import register_error_handlers
from .extensions import db, migrate
from .logging_config import configure as configure_logging


def create_app(config=None) -> Flask:
    """Create and configure a Flask application instance."""
    cfg = config or os.environ.get("APP_CONFIG", DefaultConfig)

    app = Flask(__name__)
    app.config.from_object(cfg)
    app.config.from_prefixed_env("APP")

    # Configure single-line JSON structured logging and latency tracking
    configure_logging(app)

    # Initialize database and Alembic migration extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Register global error handlers for 4xx/5xx JSON responses
    register_error_handlers(app)

    # Register modular Blueprints
    app.register_blueprint(health_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(orders_bp)

    # Ensure database tables exist when starting the service
    with app.app_context():
        from . import models  # noqa: F401
        db.create_all()

    return app
