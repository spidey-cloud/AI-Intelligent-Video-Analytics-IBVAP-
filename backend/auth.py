"""Authentication & authorization: PBKDF2 password hashing, HS256 JWT, RBAC.

Production hardening (see docs/ARCHITECTURE.md §11): MFA, SSO/LDAP,
short-lived tokens with refresh, per-BOP data scoping.
"""
import hashlib
import time

import jwt
from fastapi import Depends, HTTPException, Request

from .config import settings

ALGO = "HS256"
_PEPPER = b"ibvap-v1"


def hash_password(pw: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), _PEPPER, 120_000).hex()


def verify_password(pw: str, hashed: str) -> bool:
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), _PEPPER, 120_000).hex() == hashed


def create_token(user: dict) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "sub": user["username"],
            "uid": user["id"],
            "role": user["role"],
            "iat": now,
            "exp": now + settings.token_ttl_hours * 3600,
        },
        settings.secret,
        algorithm=ALGO,
    )


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret, algorithms=[ALGO])
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")


def get_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    q = request.query_params.get("token")
    if q:
        return q
    raise HTTPException(401, "Missing token")


def get_user(token: str = Depends(get_token)) -> dict:
    """Current-user dependency (validates JWT from header or ?token= query)."""
    return decode_token(token)


def require_role(*roles):
    def dep(user: dict = Depends(get_user)):
        if user.get("role") not in roles:
            raise HTTPException(403, "Insufficient role")
        return user

    return dep
