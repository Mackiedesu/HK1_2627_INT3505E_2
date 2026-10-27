import os
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    """Application configuration for Social Network API."""
    
    # Flask Secret Key
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev_secret_key_change_in_production_min_32_bytes_long_hash")
    
    # JWT Configuration (Buổi 06 - Slide 15 & 18)
    # Khóa bí mật JWT tối thiểu 256-bit (32 bytes) ngẫu nhiên
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "super_secret_jwt_key_for_social_network_api_at_least_256_bits_length!")
    
    # TTL: Access token sống ngắn (15 phút), Refresh token sống dài (30 ngày)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)     # 900 seconds
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)       # 2,592,000 seconds
    
    # Cố định thuật toán HS256, cấm tuyệt đối alg=none và phòng chống Algorithm Confusion (Slide 18)
    JWT_ALGORITHM = "HS256"
    JWT_DECODE_ALGORITHMS = ["HS256"]
    
    # Bật tính năng kiểm tra token revoked qua loader callback (Slide 15, 17)
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ["access", "refresh"]
    
    # Database Configuration (SQLite)
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", 
        f"sqlite:///{os.path.join(BASE_DIR, 'social_network.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
