"""Tests for security utilities (JWT tokens)."""
import os
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("DISCORD_CLIENT_ID", "test")
os.environ.setdefault("DISCORD_CLIENT_SECRET", "test")
os.environ.setdefault("DISCORD_REDIRECT_URI", "http://localhost/callback")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_fake")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test")
os.environ.setdefault("STRIPE_PRO_PRICE_ID", "price_pro")
os.environ.setdefault("STRIPE_PREMIUM_PRICE_ID", "price_premium")
os.environ.setdefault("PAYPAL_CLIENT_ID", "test")
os.environ.setdefault("PAYPAL_CLIENT_SECRET", "test")
os.environ.setdefault("PAYPAL_WEBHOOK_ID", "test")
os.environ.setdefault("PAYPAL_PRO_PLAN_ID", "P-test")
os.environ.setdefault("PAYPAL_PREMIUM_PLAN_ID", "P-test")

from datetime import timedelta
from app.core.security import create_access_token, decode_access_token


class TestJWT:
    def test_create_and_decode(self):
        token = create_access_token({"sub": "42"})
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "42"

    def test_custom_expiry(self):
        token = create_access_token({"sub": "1"}, expires_delta=timedelta(hours=2))
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "1"

    def test_expired_token(self):
        token = create_access_token({"sub": "42"}, expires_delta=timedelta(seconds=-1))
        payload = decode_access_token(token)
        assert payload is None

    def test_invalid_token(self):
        payload = decode_access_token("not.a.valid.token")
        assert payload is None

    def test_empty_token(self):
        payload = decode_access_token("")
        assert payload is None

    def test_payload_has_exp(self):
        token = create_access_token({"sub": "1"})
        payload = decode_access_token(token)
        assert "exp" in payload

    def test_extra_claims(self):
        token = create_access_token({"sub": "1", "role": "admin"})
        payload = decode_access_token(token)
        assert payload["role"] == "admin"
