import datetime as dt

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.config import get_settings

settings = get_settings()
_ph = PasswordHasher()
ALGO = "HS256"


def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except VerifyMismatchError:
        return False


def make_token(account_id: str) -> str:
    now = dt.datetime.now(dt.UTC)
    payload = {
        "sub": str(account_id),
        "iat": now,
        "exp": now + dt.timedelta(seconds=settings.jwt_expiry_seconds),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGO)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[ALGO])
