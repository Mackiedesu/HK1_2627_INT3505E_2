from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from models import db, Post, User
from auth import require_scopes, can_access_post

posts_bp = Blueprint("posts", __name__, url_prefix="/api/v1/posts")


# =============================================================================
# 3. GET /posts/{id} (Buổi 06 - Slide 24, 25, 26)
# =============================================================================
@posts_bp.get("/<id>")
@jwt_required()
@require_scopes("posts:read")
def get_post(id):
    """
    Retrieve details of a post by ID.
    
    Multi-layer Security Stack (Slide 24 & 25):
    1. Layer 1 (AuthN): @jwt_required() validates Bearer JWT token, expiration, signature, and blocklist.
    2. Layer 2 (AuthZ Scope): @require_scopes("posts:read") ensures token has read scope.
    3. Layer 3 (Ownership & BOLA Defense):
       - If post is public: any authorized user can read.
       - If post is private or draft: only the author or an admin can read.
       - Unauthorized requests return 404 Not Found to prevent Resource Enumeration.
    
    DTO Serialization (Slide 29 - Anti-Mass Exposure):
    - Uses post.to_dto() which strips internal sensitive database fields.
    """
    # 1. Validate ID parameter (Slide 29 - Input Validation)
    if not id.isdigit() or int(id) <= 0:
        return jsonify({
            "error": "bad_request",
            "message": "Post ID must be a positive integer",
            "status": 400
        }), 400

    post_id = int(id)
    post = db.session.get(Post, post_id)

    # 2. Check existence
    if not post:
        return jsonify({
            "error": "not_found",
            "message": "Post not found",
            "status": 404
        }), 404

    # 3. Layer 3: Ownership & BOLA check (OWASP API1:2023 / Slide 24, 26)
    uid_str = get_jwt_identity()
    claims = get_jwt()
    current_user_roles = claims.get("roles", [])

    if not can_access_post(post, uid_str, current_user_roles):
        # Resource Masking: Trả về 404 thay vì 403 để tránh lộ ID bài viết riêng tư
        return jsonify({
            "error": "not_found",
            "message": "Post not found",
            "status": 404
        }), 404

    # 4. Return safe DTO (OWASP API3:2023)
    return jsonify(post.to_dto()), 200


# =============================================================================
# Bonus Companion Endpoints for Social Network Functionality
# =============================================================================

@posts_bp.get("")
@jwt_required()
@require_scopes("posts:read")
def list_posts():
    """List all public posts accessible to users with `posts:read` scope."""
    posts = Post.query.filter_by(visibility="public").order_by(Post.created_at.desc()).all()
    return jsonify({
        "data": [p.to_dto() for p in posts],
        "count": len(posts)
    }), 200


@posts_bp.post("")
@jwt_required()
@require_scopes("posts:write")
def create_post():
    """Create a new post. Requires `posts:write` scope."""
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({
            "error": "bad_request",
            "message": "Request body must be valid JSON",
            "status": 400
        }), 400

    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    visibility = data.get("visibility", "public").strip().lower()

    if not title or not content:
        return jsonify({
            "error": "bad_request",
            "message": "Both 'title' and 'content' are required",
            "status": 400
        }), 400

    if visibility not in ("public", "private", "draft"):
        return jsonify({
            "error": "validation_error",
            "message": "Field 'visibility' must be one of: 'public', 'private', 'draft'",
            "status": 422
        }), 422

    uid_str = get_jwt_identity()
    author_id = int(uid_str)

    new_post = Post(
        title=title,
        content=content,
        visibility=visibility,
        author_id=author_id
    )
    db.session.add(new_post)
    db.session.commit()

    return jsonify(new_post.to_dto()), 201
