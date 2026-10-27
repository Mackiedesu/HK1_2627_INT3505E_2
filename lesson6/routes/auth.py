from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from datetime import datetime, timezone
from models import db, User, TokenBlocklist
from auth import (
    verify_password,
    dummy_verify_password,
    is_valid_email
)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


# =============================================================================
# 1. POST /auth/login (Buổi 06 - Slide 16)
# =============================================================================
@auth_bp.post("/login")
def login():
    """
    Authenticate user via email and password, return JWT Access & Refresh tokens.
    
    Security considerations:
    - Scope required: None (Public endpoint).
    - Prevents User Enumeration & Timing Attacks: returns generic 401 error.
    - Rate limit recommended on this endpoint.
    - Never returns password_hash or internal secrets.
    """
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({
            "error": "bad_request",
            "message": "Request body must be valid JSON",
            "status": 400
        }), 400

    email = data.get("email")
    password = data.get("password")

    # Kiểm tra trường bắt buộc
    if not email or not password:
        return jsonify({
            "error": "bad_request",
            "message": "Both 'email' and 'password' fields are required",
            "status": 400
        }), 400

    # Validation email format (Slide 29 - Lỗi 422)
    if not is_valid_email(email):
        return jsonify({
            "error": "validation_error",
            "message": "Invalid email address format",
            "status": 422,
            "details": {"field": "email", "rule": "format_email"}
        }), 422

    # Tìm kiếm user trong DB
    user = User.query.filter_by(email=email.strip().lower()).first()

    # Kiểm tra mật khẩu (chống timing attack bằng dummy verification nếu user không tồn tại)
    if not user:
        dummy_verify_password(password)
        return jsonify({
            "error": "invalid_credentials",
            "message": "Invalid email or password",
            "status": 401
        }), 401

    if not verify_password(user.password_hash, password):
        return jsonify({
            "error": "invalid_credentials",
            "message": "Invalid email or password",
            "status": 401
        }), 401

    if not user.is_active:
        return jsonify({
            "error": "forbidden",
            "message": "Account has been deactivated or locked",
            "status": 403
        }), 403

    # Nạp claims (roles, scopes) đưa vào JWT payload (Slide 16)
    uid_str = str(user.id)
    claims = {
        "roles": user.get_roles_list(),
        "scopes": user.get_scopes_list(),
        "username": user.username
    }

    access_token = create_access_token(
        identity=uid_str,
        additional_claims=claims
    )
    refresh_token = create_refresh_token(
        identity=uid_str,
        additional_claims={
            "type": "refresh",
            "roles": user.get_roles_list(),
            "scopes": user.get_scopes_list()
        }
    )

    return jsonify({
        "token_type": "Bearer",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": 900,            # 15 phút
        "refresh_expires_in": 2592000 # 30 ngày
    }), 200


# =============================================================================
# 2. POST /auth/refresh (Buổi 06 - Slide 17)
# =============================================================================
@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    """
    Exchange a valid Refresh Token for a new Access Token.
    
    Security considerations:
    - Scope required: Token must be a valid Refresh Token (`type: refresh`).
    - Implements Refresh Token Rotation (RTR): Revokes the old refresh token
      and issues a fresh rotated refresh token.
    - Re-fetches fresh user roles/scopes from DB (Slide 17).
    """
    uid_str = get_jwt_identity()
    old_jwt = get_jwt()
    old_jti = old_jwt.get("jti")
    
    # 1. Kiểm tra tài khoản người dùng còn tồn tại và còn active không
    user = db.session.get(User, int(uid_str))
    if not user or not user.is_active:
        return jsonify({
            "error": "forbidden",
            "message": "User account is inactive or has been deleted",
            "status": 403
        }), 403

    # 2. Refresh Token Rotation (RTR): Thu hồi refresh token cũ (Slide 15 & 20)
    if old_jti:
        exp_timestamp = old_jwt.get("exp")
        expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc) if exp_timestamp else None
        revoked_token = TokenBlocklist(
            jti=old_jti,
            token_type="refresh",
            user_id=user.id,
            expires_at=expires_at
        )
        db.session.add(revoked_token)
        db.session.commit()

    # 3. Nạp quyền hiện tại của user từ Database (tránh quyền cũ bị lưu vĩnh viễn trong token)
    fresh_claims = {
        "roles": user.get_roles_list(),
        "scopes": user.get_scopes_list(),
        "username": user.username
    }

    new_access_token = create_access_token(
        identity=uid_str,
        additional_claims=fresh_claims
    )
    new_refresh_token = create_refresh_token(
        identity=uid_str,
        additional_claims={
            "type": "refresh",
            "roles": user.get_roles_list(),
            "scopes": user.get_scopes_list()
        }
    )

    return jsonify({
        "token_type": "Bearer",
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "expires_in": 900,
        "refresh_expires_in": 2592000
    }), 200


# =============================================================================
# Helper: POST /auth/logout (Buổi 06 - Slide 15)
# =============================================================================
@auth_bp.post("/logout")
@jwt_required(verify_type=False)
def logout():
    """
    Revoke current token (Access Token or Refresh Token) by adding its `jti` to blocklist.
    """
    jwt_data = get_jwt()
    jti = jwt_data.get("jti")
    token_type = jwt_data.get("type", "access")
    uid_str = get_jwt_identity()
    user_id = int(uid_str) if uid_str and uid_str.isdigit() else 0
    exp_timestamp = jwt_data.get("exp")
    expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc) if exp_timestamp else None

    if jti:
        revoked_token = TokenBlocklist(
            jti=jti,
            token_type=token_type,
            user_id=user_id,
            expires_at=expires_at
        )
        db.session.add(revoked_token)
        db.session.commit()

    return jsonify({
        "message": f"Successfully revoked {token_type} token. Logged out.",
        "status": 200
    }), 200
