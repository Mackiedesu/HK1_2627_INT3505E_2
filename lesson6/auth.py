from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity
import re

# Password Hashing using Argon2id (Buổi 06 - Slide 27 & 28)
try:
    from argon2 import PasswordHasher, Type
    from argon2.exceptions import VerifyMismatchError, InvalidHash
    ph = PasswordHasher(
        time_cost=3,
        memory_cost=65536,
        parallelism=4,
        type=Type.ID
    )
    _USE_ARGON2 = True
except ImportError:
    _USE_ARGON2 = False
    import bcrypt

# Tạo một dummy hash cố định để xử lý thời gian kiểm tra không đổi (Constant-time timing attack defense)
if _USE_ARGON2:
    DUMMY_HASH = ph.hash("constant_time_dummy_secret_for_enumeration_protection")
else:
    DUMMY_HASH = bcrypt.hashpw(b"constant_dummy_password", bcrypt.gensalt()).decode("utf-8")


def hash_password(plain: str) -> str:
    """
    Hash a password using Argon2id (or bcrypt fallback) with per-user salt and high cost.
    (Buổi 06 - Slide 27 & 28).
    """
    if _USE_ARGON2:
        return ph.hash(plain)
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def verify_password(stored_hash: str, plain: str) -> bool:
    """Verify password against stored Argon2id/bcrypt hash."""
    if not stored_hash or not plain:
        return False
    if _USE_ARGON2:
        try:
            return ph.verify(stored_hash, plain)
        except (VerifyMismatchError, InvalidHash):
            return False
        except Exception:
            return False
    else:
        try:
            return bcrypt.checkpw(plain.encode("utf-8"), stored_hash.encode("utf-8"))
        except Exception:
            return False


def dummy_verify_password(plain: str) -> bool:
    """
    Perform a dummy hash verification when a user does not exist.
    Prevents Timing Attacks that reveal valid usernames/emails (Slide 7, 29).
    """
    verify_password(DUMMY_HASH, plain)
    return False


def is_valid_email(email: str) -> bool:
    """Validate email format."""
    if not email or not isinstance(email, str):
        return False
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return bool(re.match(pattern, email.strip()))


# =============================================================================
# Authorization Decorators (Buổi 06 - Slide 24 & 25)
# =============================================================================

def require_roles(*allowed_roles):
    """
    Decorator 1: Roles (OR) — Coarse-grained check (Slide 24).
    Verifies that the caller has at least one of the specified roles in JWT claims.
    Returns 403 Forbidden if not authorized.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            user_roles = set(claims.get("roles", []))
            if not user_roles & set(allowed_roles):
                return jsonify({
                    "error": "forbidden",
                    "message": f"Requires at least one role: {list(allowed_roles)}",
                    "need_one_of": list(allowed_roles),
                    "status": 403
                }), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def require_scopes(*needed_scopes):
    """
    Decorator 2: Scopes (AND) — Fine-grained check per request (Slide 25).
    Verifies that the JWT contains ALL of the requested scopes.
    Returns 403 Forbidden with `need_all_of` list if insufficient.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            claims = get_jwt()
            granted_scopes = set(claims.get("scopes", []))
            needed = set(needed_scopes)
            if not needed.issubset(granted_scopes):
                return jsonify({
                    "error": "insufficient_scope",
                    "message": f"Access token lacks required scopes: {list(needed_scopes)}",
                    "need_all_of": list(needed_scopes),
                    "status": 403
                }), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def can_access_post(post, current_user_id: int | str | None, user_roles: list[str] | None = None) -> bool:
    """
    Chống BOLA (Broken Object Level Authorization - OWASP API1:2023 / Slide 24, 26).
    - Public posts: Bất kỳ ai có token hợp lệ đều được xem.
    - Private / Draft posts: Chỉ chính tác giả (`author_id == current_user_id`)
      HOẶC người dùng có quyền Quản trị viên (`admin` role) mới được xem.
    """
    if not post:
        return False
    if post.visibility == "public":
        return True
    
    if current_user_id is None:
        return False

    roles = set(user_roles or [])
    is_owner = str(post.author_id) == str(current_user_id)
    is_admin = "admin" in roles

    return is_owner or is_admin
