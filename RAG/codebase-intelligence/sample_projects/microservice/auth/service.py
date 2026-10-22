import hashlib
import hmac
import time
from typing import Optional, Dict
from config import config


def hash_password(password: str) -> str:
    """Hash user password with SHA-256 salt."""
    salt = "secure_codebase_salt_987"
    return hashlib.sha256(f"{password}{salt}".encode("utf-8")).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify submitted plain password against stored hash."""
    return hmac.compare_digest(hash_password(plain_password), hashed_password)


def generate_jwt_token(user_id: str, email: str) -> str:
    """Issue a simulated authentication JWT token."""
    payload = f"{user_id}:{email}:{int(time.time()) + 3600}"
    signature = hmac.new(config.SECRET_KEY.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def authenticate_user(email: str, password: str, users_db: Dict[str, dict]) -> Optional[dict]:
    """
    Authenticate user credentials against user repository.
    Returns user record if valid, otherwise None.
    """
    user = users_db.get(email)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user
