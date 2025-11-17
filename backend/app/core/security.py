from datetime import datetime, timedelta, UTC
from typing import Optional
from jose import JWTError, jwt
import hashlib
import hmac
import bcrypt
from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a stored hash.
    
    Compatibility rules:
    - bcrypt ($2b$/$2a$/$2y$): use bcrypt.checkpw
    - sha256 hex (64 chars): compare with sha256 hexdigest
    - fallback: constant-time plain text compare (legacy dev data)
    """
    if not hashed_password:
        return False
    try:
        # 1) bcrypt
        if hashed_password.startswith("$2"):
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

        # 2) sha256(hex) legacy support
        if len(hashed_password) == 64:
            # all hex chars? keep it lightweight without regex
            lowered = hashed_password.lower()
            if all(c in "0123456789abcdef" for c in lowered):
                expected = hashlib.sha256(plain_password.encode()).hexdigest()
                return hmac.compare_digest(expected, hashed_password)

        # 3) plain text (legacy DEBUG data)
        return hmac.compare_digest(plain_password, hashed_password)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt (60-char hash)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT access token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None
