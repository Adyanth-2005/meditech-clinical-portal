import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

import jwt
import auth


def test_password_roundtrip():
    h = auth.hash_password("S3cret!")
    assert h != "S3cret!"
    assert auth.verify_password("S3cret!", h)
    assert not auth.verify_password("wrong", h)


def test_password_bad_hash_is_false():
    assert auth.verify_password("x", "not-a-hash") is False


def test_token_roundtrip():
    tok = auth.create_token("rajan", "patient", "PT-001")
    claims = auth.decode_token(tok)
    assert claims["sub"] == "rajan"
    assert claims["role"] == "patient"
    assert claims["linked_id"] == "PT-001"


def test_token_expiry():
    # craft an already-expired token
    payload = {"sub": "x", "role": "admin", "linked_id": None,
               "iat": int(time.time()) - 100, "exp": int(time.time()) - 10}
    tok = jwt.encode(payload, auth.JWT_SECRET, algorithm=auth.JWT_ALGO)
    try:
        auth.decode_token(tok)
        assert False, "expected expiry error"
    except jwt.ExpiredSignatureError:
        pass


def test_tampered_token_rejected():
    tok = auth.create_token("a", "doctor", None) + "x"
    try:
        auth.decode_token(tok)
        assert False
    except jwt.PyJWTError:
        pass
