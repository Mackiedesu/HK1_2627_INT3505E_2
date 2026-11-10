"""Kubernetes-ready liveness (/healthz) and readiness (/ready) probes."""

from flask import Blueprint, jsonify
from sqlalchemy import text
from ..extensions import db

health_bp = Blueprint("health", __name__, url_prefix="")


@health_bp.get("/healthz")
def liveness():
    """
    GET /healthz - Liveness probe.
    Lightweight check independent of external dependencies; returns 200 if process is alive.
    """
    return jsonify({"status": "ok"}), 200


@health_bp.get("/ready")
def readiness():
    """
    GET /ready - Readiness probe.
    Verifies database connectivity via SELECT 1; returns 200 when ready or 503 when degraded.
    """
    checks = {}
    try:
        db.session.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception:
        checks["db"] = "err"

    ok = all(v == "ok" for v in checks.values())
    return (
        jsonify(
            {
                "status": "ok" if ok else "degraded",
                "checks": checks,
            }
        ),
        200 if ok else 503,
    )
