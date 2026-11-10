"""Structured single-line JSON logging and request latency tracking."""

import json
import logging
import sys
import time
from flask import has_request_context, request


class JsonFormatter(logging.Formatter):
    """Format log records as single-line JSON objects for ELK/Loki ingestion."""

    def format(self, rec: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(rec, "%Y-%m-%dT%H:%M:%SZ"),
            "level": rec.levelname,
            "msg": rec.getMessage(),
        }
        if has_request_context():
            payload["rid"] = request.headers.get("X-Request-Id", "-")
        if hasattr(rec, "s"):
            payload["status"] = rec.s
        if hasattr(rec, "ms"):
            payload["ms"] = rec.ms
        return json.dumps(payload, ensure_ascii=False)


def configure(app) -> None:
    """Attach JSON stream handler and request lifecycle timing hooks to the Flask app."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    # Replace default Flask handlers with structured JSON handler
    app.logger.handlers = [handler]
    app.logger.setLevel(app.config.get("LOG_LEVEL", "INFO"))

    @app.before_request
    def _t0() -> None:
        """Record request start timestamp."""
        request._t0 = time.perf_counter()

    @app.after_request
    def _done(resp):
        """Log completed request status code and latency in milliseconds."""
        t0 = getattr(request, "_t0", None)
        ms = int((time.perf_counter() - t0) * 1000) if t0 is not None else 0
        app.logger.info(
            "done",
            extra={"s": resp.status_code, "ms": ms},
        )
        return resp
