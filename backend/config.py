# backend/config.py
import os
import secrets

SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
