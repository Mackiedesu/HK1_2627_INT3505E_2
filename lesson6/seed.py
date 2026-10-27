from app import create_app
from models import db, User, Post, TokenBlocklist
from auth import hash_password

def seed_database():
    app = create_app()
    with app.app_context():
        # Clean existing tables
        db.drop_all()
        db.create_all()

        print("[Seed] Creating sample users with Argon2id passwords...")
        
        # User 1: Alice (Regular User)
        alice = User(
            id=1,
            username="alice",
            email="alice@social.net",
            name="Alice Johnson",
            password_hash=hash_password("Password123!"),
            roles="user",
            scopes="posts:read,posts:write",
            avatar_url="https://api.social.net/avatars/alice.png"
        )
        
        # User 2: Bob (Regular User)
        bob = User(
            id=2,
            username="bob",
            email="bob@social.net",
            name="Bob Smith",
            password_hash=hash_password("Password123!"),
            roles="user",
            scopes="posts:read,posts:write",
            avatar_url="https://api.social.net/avatars/bob.png"
        )
        
        # User 3: Viewer (Limited User - Has NO posts:read scope to test 403 insufficient_scope)
        viewer = User(
            id=3,
            username="viewer",
            email="viewer@social.net",
            name="Guest Viewer",
            password_hash=hash_password("Password123!"),
            roles="viewer",
            scopes="profile:read", # Lacks posts:read!
            avatar_url=None
        )
        
        # User 4: Admin (Administrator)
        admin = User(
            id=4,
            username="admin",
            email="admin@social.net",
            name="System Administrator",
            password_hash=hash_password("AdminPass123!"),
            roles="admin,user",
            scopes="posts:read,posts:write,admin:all",
            avatar_url="https://api.social.net/avatars/admin.png"
        )

        db.session.add_all([alice, bob, viewer, admin])
        db.session.commit()
        print("[Seed] Created 4 users (Alice, Bob, Viewer, Admin).")

        print("[Seed] Creating sample posts (Public, Private, Draft)...")
        # Post 101: Alice's Public Post
        p101 = Post(
            id=101,
            title="Khai phá kiến trúc phân quyền trong RESTful API",
            content="Trong thiết kế API hiện đại, AuthN xác định bạn là ai, còn AuthZ quyết định bạn được làm gì. Kết hợp RBAC và BOLA checks giúp bảo vệ tài nguyên toàn diện.",
            visibility="public",
            author_id=alice.id
        )

        # Post 102: Alice's Private Post (BOLA test case: Bob cannot view, Admin can view)
        p102 = Post(
            id=102,
            title="Nhật ký bảo mật cá nhân của Alice (Private)",
            content="Đây là ghi chú bí mật chứa các thông tin tài chính cá nhân không được công khai.",
            visibility="private",
            author_id=alice.id
        )

        # Post 103: Bob's Public Post
        p103 = Post(
            id=103,
            title="Hành trình tối ưu hóa JWT và Refresh Token Rotation",
            content="Sử dụng Refresh Token Rotation kết hợp Redis token blocklist giúp khắc phục nhược điểm lớn nhất của stateless JWT là bài toán thu hồi phiên.",
            visibility="public",
            author_id=bob.id
        )

        # Post 104: Bob's Draft Post (BOLA test case: Only Bob and Admin can view)
        p104 = Post(
            id=104,
            title="Bản thảo tính năng tin nhắn tức thời (Draft)",
            content="Kế hoạch phát triển tính năng WebSocket chat cho phiên bản v2 sắp tới.",
            visibility="draft",
            author_id=bob.id
        )

        db.session.add_all([p101, p102, p103, p104])
        db.session.commit()
        print("[Seed] Created 4 sample posts (101, 102, 103, 104).")
        print("[Seed] Database seeding completed successfully!")

if __name__ == "__main__":
    seed_database()
