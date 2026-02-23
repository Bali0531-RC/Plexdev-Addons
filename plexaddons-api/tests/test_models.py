"""Tests for model enums and basic model construction."""
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

from app.models import (
    SubscriptionTier,
    SubscriptionStatus,
    PaymentProvider,
    AddonTag,
    ReleaseChannel,
    OrganizationRole,
    CollaboratorRole,
    ApiKeyScope,
)


class TestSubscriptionTier:
    def test_values(self):
        assert SubscriptionTier.FREE.value == "free"
        assert SubscriptionTier.PRO.value == "pro"
        assert SubscriptionTier.PREMIUM.value == "premium"

    def test_count(self):
        assert len(SubscriptionTier) == 3

    def test_is_str(self):
        assert isinstance(SubscriptionTier.FREE, str)


class TestSubscriptionStatus:
    def test_active(self):
        assert SubscriptionStatus.ACTIVE.value == "active"

    def test_all_statuses(self):
        expected = {
            "active", "past_due", "canceled", "unpaid",
            "trialing", "paused", "incomplete", "incomplete_expired",
        }
        assert {s.value for s in SubscriptionStatus} == expected


class TestPaymentProvider:
    def test_providers(self):
        assert PaymentProvider.STRIPE.value == "stripe"
        assert PaymentProvider.PAYPAL.value == "paypal"


class TestAddonTag:
    def test_has_utility(self):
        assert AddonTag.UTILITY.value == "utility"

    def test_count(self):
        assert len(AddonTag) == 11

    def test_all_are_strings(self):
        for tag in AddonTag:
            assert isinstance(tag, str)


class TestReleaseChannel:
    def test_channels(self):
        assert ReleaseChannel.STABLE.value == "stable"
        assert ReleaseChannel.BETA.value == "beta"
        assert ReleaseChannel.ALPHA.value == "alpha"


class TestOrganizationRole:
    def test_roles(self):
        assert OrganizationRole.OWNER.value == "owner"
        assert OrganizationRole.ADMIN.value == "admin"
        assert OrganizationRole.MEMBER.value == "member"


class TestCollaboratorRole:
    def test_roles(self):
        assert CollaboratorRole.ADMIN.value == "admin"
        assert CollaboratorRole.EDITOR.value == "editor"
        assert CollaboratorRole.VIEWER.value == "viewer"


class TestApiKeyScope:
    def test_read_scopes(self):
        assert "read" in ApiKeyScope.ADDONS_READ.value
        assert "read" in ApiKeyScope.VERSIONS_READ.value
        assert "read" in ApiKeyScope.ANALYTICS_READ.value

    def test_write_scopes(self):
        assert "write" in ApiKeyScope.VERSIONS_WRITE.value
        assert "write" in ApiKeyScope.ADDONS_WRITE.value

    def test_full_access(self):
        assert ApiKeyScope.FULL_ACCESS.value == "full:access"
