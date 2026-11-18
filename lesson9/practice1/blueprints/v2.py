"""User API v2 blueprint (breaking schema: first_name + last_name, plus POST /users)."""

from flask import Blueprint, request
from .users_data import create_user, get_user

bp = Blueprint("v2", __name__, url_prefix="/users")


@bp.route("/<int:uid>", methods=["GET"])
def get(uid: int):
    """Get user by ID in v2 schema (first_name, last_name)."""
    u = get_user(uid)
    if not u:
        return {"error": "nf"}, 404
    return {
        "id": uid,
        "first_name": u["first_name"],
        "last_name": u["last_name"],
        "email": u["email"],
    }


@bp.route("", methods=["POST"])
def create():
    """Create a new user in v2."""
    data = request.get_json(silent=True) or {}
    required = ("first_name", "last_name", "email")
    missing = [field for field in required if not isinstance(data.get(field), str) or not data[field].strip()]
    if missing:
        return {"error": "validation_error", "missing_fields": missing}, 400

    uid, user = create_user(
        data["first_name"].strip(),
        data["last_name"].strip(),
        data["email"].strip(),
    )
    return {
        "id": uid,
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "email": user["email"],
    }, 201
