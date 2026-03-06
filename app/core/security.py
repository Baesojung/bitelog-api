from datetime import datetime, timedelta
import hashlib
from typing import Any, Union
import bcrypt
from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "supersecretkey"  # Can also be from settings.secret_key
ALGORITHM = "HS256"

def _is_passlib_bcrypt_usable() -> bool:
    bcrypt_version = str(getattr(bcrypt, "__version__", "0"))
    try:
        bcrypt_major = int(bcrypt_version.split(".", 1)[0])
    except ValueError:
        bcrypt_major = 0

    # passlib==1.7.4 is incompatible with bcrypt 5.x in this environment.
    if bcrypt_major >= 5:
        return False

    try:
        pwd_context.hash("bitelog-passlib-selftest")
        return True
    except Exception:
        return False

PASSLIB_BCRYPT_USABLE = _is_passlib_bcrypt_usable()

def _prehash_password(password: str) -> str:
    # Avoid bcrypt's 72-byte input limit while preserving deterministic verification.
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Backward compatibility:
    # 1) legacy hashes created from raw password
    # 2) newer hashes created from pre-hashed password
    prehashed_password = _prehash_password(plain_password)
    if PASSLIB_BCRYPT_USABLE:
        try:
            if pwd_context.verify(plain_password, hashed_password):
                return True
        except Exception:
            pass
        try:
            if pwd_context.verify(prehashed_password, hashed_password):
                return True
        except Exception:
            pass

    # Fallback for passlib<->bcrypt backend incompatibility (e.g., bcrypt 5.x)
    try:
        hashed_bytes = hashed_password.encode("utf-8")
    except Exception:
        return False

    try:
        if bcrypt.checkpw(plain_password.encode("utf-8"), hashed_bytes):
            return True
    except Exception:
        pass

    try:
        return bcrypt.checkpw(prehashed_password.encode("utf-8"), hashed_bytes)
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    prehashed_password = _prehash_password(password)
    if PASSLIB_BCRYPT_USABLE:
        try:
            return pwd_context.hash(prehashed_password)
        except Exception:
            pass
    # Fallback for passlib<->bcrypt backend incompatibility.
    return bcrypt.hashpw(
        prehashed_password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")

def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=60 * 24 * 7) # 1 week
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
