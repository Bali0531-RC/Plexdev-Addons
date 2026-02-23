"""Tests for dependency helpers (get_effective_tier)."""
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

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from app.api.deps import get_effective_tier
from app.models import SubscriptionTier


def _make_user(tier=SubscriptionTier.FREE, temp_tier=None, temp_expires=None):
    user = MagicMock()
    user.subscription_tier = tier
    user.temp_tier = temp_tier
    user.temp_tier_expires_at = temp_expires
    return user


class TestGetEffectiveTier:
    def test_free_user(self):
        user = _make_user(SubscriptionTier.FREE)
        assert get_effective_tier(user) == SubscriptionTier.FREE

    def test_pro_user(self):
        user = _make_user(SubscriptionTier.PRO)
        assert get_effective_tier(user) == SubscriptionTier.PRO

    def test_premium_user(self):
        user = _make_user(SubscriptionTier.PREMIUM)
        assert get_effective_tier(user) == SubscriptionTier.PREMIUM

    def test_temp_tier_active(self):
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        user = _make_user(
            SubscriptionTier.FREE,
            temp_tier=SubscriptionTier.PREMIUM,
            temp_expires=future,
        )
        assert get_effective_tier(user) == SubscriptionTier.PREMIUM

    def test_temp_tier_expired(self):
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        user = _make_user(
            SubscriptionTier.FREE,
            temp_tier=SubscriptionTier.PRO,
            temp_expires=past,
        )
        assert get_effective_tier(user) == SubscriptionTier.FREE

    def test_temp_tier_none_expiry(self):
        user = _make_user(
            SubscriptionTier.FREE,
            temp_tier=SubscriptionTier.PRO,
            temp_expires=None,
        )
        assert get_effective_tier(user) == SubscriptionTier.FREE

    def test_no_temp_tier(self):
        user = _make_user(
            SubscriptionTier.PRO,
            temp_tier=None,
            temp_expires=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        assert get_effective_tier(user) == SubscriptionTier.PRO
