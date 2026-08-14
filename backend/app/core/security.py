import datetime
import hashlib
import secrets
from typing import Optional, Union, Any
import bcrypt
import jwt
from app.core.config import settings

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        password_bytes = plain_password.encode("utf-8")[:72]
        hashed_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        # Fallback to sha256 check
        sha256_hash = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
        return secrets.compare_digest(sha256_hash, hashed_password)

def get_password_hash(password: str) -> str:
    password_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")

def create_access_token(subject: Union[str, Any], expires_delta: Optional[datetime.timedelta] = None, role: str = "developer") -> str:
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "role": role,
        "type": "access_token"
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception:
        return None

def generate_api_token(user_id: int) -> tuple[str, str, str]:
    """
    Generates (raw_token, token_prefix, token_hash)
    Raw token format: z9r_xxxx...
    """
    random_part = secrets.token_urlsafe(32)
    raw_token = f"z9r_{random_part}"
    prefix = raw_token[:8]
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    return raw_token, prefix, token_hash

def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
