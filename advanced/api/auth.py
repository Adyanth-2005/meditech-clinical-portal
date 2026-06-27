"""
auth.py — password hashing + JWT, framework-agnostic and unit-testable.

Uses the `bcrypt` package directly (not passlib) to avoid the well-known
passlib/bcrypt>=4.1 version-detection crash on Windows.
"""

import os
import time
import bcrypt
import jwt  # PyJWT

# In a real deployment this comes from a secret manager. For the lab we read an
# env var and fall back to a dev default (fine for localhost-only use).
JWT_SECRET = os.environ.get("MEDITECH_JWT_SECRET", "dev-secret-change-me-in-prod")
JWT_ALGO = "HS256"
TOKEN_TTL_SECONDS = 8 * 60 * 60  # 8 hours


# ── passwords ────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    # bcrypt has a 72-byte limit; encode and truncate defensively.
    pw = plain.encode("utf-8")[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ── tokens ───────────────────────────────────────────────────────────────────

def create_token(username: str, role: str, linked_id) -> str:
    now = int(time.time())
    payload = {
        "sub": username,
        "role": role,
        "linked_id": linked_id,   # patient_id for patients, None otherwise
        "iat": now,
        "exp": now + TOKEN_TTL_SECONDS,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def decode_token(token: str) -> dict:
    """Raises jwt.PyJWTError (incl. ExpiredSignatureError) on failure."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
