"""Tests for Pydantic schema validation."""
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

import pytest
from pydantic import ValidationError
from app.schemas import (
    AddonCreate,
    AddonUpdate,
    UserProfileUpdate,
    UserUpdate,
)
from app.models import AddonTag


class TestAddonCreate:
    def test_valid_minimal(self):
        addon = AddonCreate(name="My Addon")
        assert addon.name == "My Addon"
        assert addon.description is None
        assert addon.tags == []

    def test_valid_full(self):
        addon = AddonCreate(
            name="Cool Addon",
            description="A cool addon",
            homepage="https://example.com",
            external=True,
            tags=[AddonTag.UTILITY, AddonTag.MEDIA],
        )
        assert addon.external is True
        assert len(addon.tags) == 2

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            AddonCreate(name="")

    def test_name_too_long(self):
        with pytest.raises(ValidationError):
            AddonCreate(name="x" * 101)


class TestAddonUpdate:
    def test_all_optional(self):
        update = AddonUpdate()
        assert update.name is None
        assert update.is_active is None

    def test_valid_partial(self):
        update = AddonUpdate(name="New Name", is_public=True)
        assert update.name == "New Name"
        assert update.is_public is True
        assert update.description is None

    def test_accent_color_valid(self):
        update = AddonUpdate(theme_accent_color="#FF5500")
        assert update.theme_accent_color == "#FF5500"

    def test_accent_color_invalid(self):
        with pytest.raises(ValidationError):
            AddonUpdate(theme_accent_color="red")

    def test_accent_color_invalid_short(self):
        with pytest.raises(ValidationError):
            AddonUpdate(theme_accent_color="#FFF")

    def test_screenshots_max(self):
        update = AddonUpdate(screenshots=["a.png"] * 6)
        assert len(update.screenshots) == 6

    def test_screenshots_too_many(self):
        with pytest.raises(ValidationError):
            AddonUpdate(screenshots=["a.png"] * 7)


class TestUserProfileUpdate:
    def test_valid_slug(self):
        profile = UserProfileUpdate(profile_slug="my-profile_1")
        assert profile.profile_slug == "my-profile_1"

    def test_slug_too_short(self):
        with pytest.raises(ValidationError):
            UserProfileUpdate(profile_slug="ab")

    def test_slug_invalid_chars(self):
        with pytest.raises(ValidationError):
            UserProfileUpdate(profile_slug="bad slug!")

    def test_accent_color_valid(self):
        profile = UserProfileUpdate(accent_color="#AABBCC")
        assert profile.accent_color == "#AABBCC"

    def test_accent_color_invalid(self):
        with pytest.raises(ValidationError):
            UserProfileUpdate(accent_color="notahex")

    def test_bio_max_length(self):
        profile = UserProfileUpdate(bio="x" * 500)
        assert len(profile.bio) == 500

    def test_bio_too_long(self):
        with pytest.raises(ValidationError):
            UserProfileUpdate(bio="x" * 501)


class TestUserUpdate:
    def test_valid_email(self):
        update = UserUpdate(email="user@example.com")
        assert update.email == "user@example.com"

    def test_invalid_email(self):
        with pytest.raises(ValidationError):
            UserUpdate(email="not-an-email")

    def test_none_email(self):
        update = UserUpdate(email=None)
        assert update.email is None
