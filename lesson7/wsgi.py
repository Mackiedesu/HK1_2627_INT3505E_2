"""WSGI entry point for Gunicorn production server."""

from product_api.factory import create_app

app = create_app()
