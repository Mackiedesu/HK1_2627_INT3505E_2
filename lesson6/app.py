from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from config import Config
from models import db, TokenBlocklist
from routes import auth_bp, posts_bp


def create_app(config_class=Config):
    """Application factory for Social Network API."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Khởi tạo CSDL
    db.init_app(app)

    # Khởi tạo JWT Manager (Buổi 06 - Slide 15)
    jwt = JWTManager(app)

    # -------------------------------------------------------------------------
    # Revocation: Kiểm tra token jti trong Blocklist (Slide 15 & 17)
    # -------------------------------------------------------------------------
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload.get("jti")
        if not jti:
            return False
        token = db.session.query(TokenBlocklist.id).filter_by(jti=jti).scalar()
        return token is not None

    # -------------------------------------------------------------------------
    # JWT Error Callbacks (Chuẩn hóa phản hồi JSON theo RFC 7807)
    # -------------------------------------------------------------------------
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        token_type = jwt_payload.get("type", "token")
        return jsonify({
            "error": "token_expired",
            "message": f"The {token_type} has expired. Please authenticate again.",
            "status": 401
        }), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error_string):
        return jsonify({
            "error": "invalid_token",
            "message": f"Signature verification failed: {error_string}",
            "status": 401
        }), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error_string):
        return jsonify({
            "error": "missing_token",
            "message": f"Authorization header is missing or malformed: {error_string}",
            "status": 401
        }), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        token_type = jwt_payload.get("type", "token")
        return jsonify({
            "error": "token_revoked",
            "message": f"The {token_type} has been revoked and is no longer valid.",
            "status": 401
        }), 401

    # -------------------------------------------------------------------------
    # Global HTTP Error Handlers
    # -------------------------------------------------------------------------
    @app.errorhandler(400)
    def bad_request_error(e):
        return jsonify({
            "error": "bad_request",
            "message": getattr(e, "description", "Bad Request"),
            "status": 400
        }), 400

    @app.errorhandler(404)
    def not_found_error(e):
        return jsonify({
            "error": "not_found",
            "message": "Resource not found",
            "status": 404
        }), 404

    @app.errorhandler(405)
    def method_not_allowed_error(e):
        return jsonify({
            "error": "method_not_allowed",
            "message": "HTTP method not allowed for this route",
            "status": 405
        }), 405

    @app.errorhandler(500)
    def internal_server_error(e):
        return jsonify({
            "error": "internal_server_error",
            "message": "An unexpected server error occurred",
            "status": 500
        }), 500

    # Đăng ký Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(posts_bp)

    # Tạo bảng CSDL
    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
