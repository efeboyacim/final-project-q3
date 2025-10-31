from app.core.security import create_access_token, decode_token, hash_password, verify_password


def test_password_hash_cycle():
    h = hash_password("secret123")
    assert verify_password("secret123", h)
    assert not verify_password("wrong", h)

def test_jwt_cycle():
    t = create_access_token("user-1", expires_minutes=5)
    p = decode_token(t)
    assert p and p.get("sub") == "user-1"
