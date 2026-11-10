"""Module-level Flask extensions waiting for init_app() binding."""

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# Separate extension instances from the Flask app to prevent circular imports
# and allow multiple independent app instances during testing.
db = SQLAlchemy()
migrate = Migrate()
