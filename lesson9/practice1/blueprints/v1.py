"""User API v1 blueprint (returns full_name, includes Sunset deprecation headers)."""

from datetime import datetime, timezone
from email.utils import format_datetime
from flask import Blueprint
from .users_data import get_user

bp = Blueprint("v1", __name__, url_prefix="/users")

V1_SUNSET = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)


@bp.after_request
def add_sunset_headers(response):
    """Attach RFC 8594 Sunset and Deprecation headers to all v1 responses."""
    response.headers["Sunset"] = format_datetime(V1_SUNSET, usegmt=True)
    response.headers["Deprecation"] = "true"
    response.headers["Link"] = '</api/v2/users>; rel="successor-version"'
    return response


@bp.route("/<int:uid>", methods=["GET"])
def get(uid: int):
    """Get user by ID in v1 schema (full_name)."""
    u = get_user(uid)
    if not u:
        return {"error": "nf"}, 404
    return {
        "id": uid,
        "full_name": f"{u['first_name']} {u['last_name']}",
        "email": u["email"],
    }
