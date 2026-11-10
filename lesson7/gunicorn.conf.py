"""Gunicorn WSGI server production configuration."""

bind = "0.0.0.0:5000"
workers = 2  # Adjust based on workload and CPU limits
worker_class = "sync"  # Or "gthread"
timeout = 60  # Worker timeout in seconds
graceful_timeout = 30
keepalive = 5
preload_app = False
accesslog = "-"
errorlog = "-"
loglevel = "info"
proc_name = "product-api"
