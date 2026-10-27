from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def utcnow():
    return datetime.now(timezone.utc)

class User(db.Model):
    """User entity in the Social Network."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(128), unique=True, nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    # RBAC: Coarse-grained roles (e.g. 'user', 'admin', 'moderator')
    roles = db.Column(db.String(128), default="user", nullable=False)
    
    # Scopes: Fine-grained permissions (e.g. 'posts:read,posts:write')
    scopes = db.Column(db.String(255), default="posts:read,posts:write", nullable=False)
    
    avatar_url = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    # Relationships
    posts = db.relationship("Post", back_populates="author", cascade="all, delete-orphan")

    def get_roles_list(self) -> list[str]:
        return [r.strip() for r in self.roles.split(",") if r.strip()]

    def get_scopes_list(self) -> list[str]:
        return [s.strip() for s in self.scopes.split(",") if s.strip()]

    def has_role(self, role_name: str) -> bool:
        return role_name in self.get_roles_list()

    def to_dto(self) -> dict:
        """
        Safe DTO serialization for public consumption (OWASP API3 Defense).
        Never exposes password_hash, salt, or sensitive internal properties.
        """
        return {
            "id": self.id,
            "username": self.username,
            "name": self.name,
            "avatar_url": self.avatar_url,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Post(db.Model):
    """Social Network Post entity."""
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    
    # Visibility: 'public', 'private', 'draft' (Chống BOLA - Slide 26)
    visibility = db.Column(db.String(32), default="public", nullable=False)
    
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    author = db.relationship("User", back_populates="posts")

    def to_dto(self) -> dict:
        """
        DTO representation of a Post.
        Encapsulates safe author DTO without exposing author's private details.
        """
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "visibility": self.visibility,
            "author": self.author.to_dto() if self.author else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class TokenBlocklist(db.Model):
    """
    Token Revocation Blocklist (Slide 15, 17).
    Stores revoked JWT IDs (`jti`) for both Access Tokens and Refresh Tokens.
    """
    __tablename__ = "token_blocklist"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    jti = db.Column(db.String(36), nullable=False, unique=True, index=True)
    token_type = db.Column(db.String(16), nullable=False) # 'access' or 'refresh'
    user_id = db.Column(db.Integer, nullable=False, index=True)
    revoked_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<TokenBlocklist jti={self.jti} type={self.token_type} user_id={self.user_id}>"
