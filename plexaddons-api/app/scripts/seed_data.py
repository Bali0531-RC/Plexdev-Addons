"""
Seed data script for PlexAddons development database.

Usage:
    cd plexaddons-api
    python -m app.scripts.seed_data

Populates the database with sample users, addons, and versions
for local development and testing.
"""
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta, date

# Ensure env vars are set for local dev
os.environ.setdefault("SECRET_KEY", "dev-secret-key-change-in-production")
os.environ.setdefault("DATABASE_URL", "postgresql://plexaddons:plexaddons@localhost:5432/plexaddons")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("DISCORD_CLIENT_ID", "dev")
os.environ.setdefault("DISCORD_CLIENT_SECRET", "dev")
os.environ.setdefault("DISCORD_REDIRECT_URI", "http://localhost:3000/auth/callback")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_dev")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_dev")
os.environ.setdefault("STRIPE_PRO_PRICE_ID", "price_dev_pro")
os.environ.setdefault("STRIPE_PREMIUM_PRICE_ID", "price_dev_premium")
os.environ.setdefault("PAYPAL_CLIENT_ID", "dev")
os.environ.setdefault("PAYPAL_CLIENT_SECRET", "dev")
os.environ.setdefault("PAYPAL_WEBHOOK_ID", "dev")
os.environ.setdefault("PAYPAL_PRO_PLAN_ID", "P-dev")
os.environ.setdefault("PAYPAL_PREMIUM_PLAN_ID", "P-dev")
os.environ.setdefault("EMAIL_ENABLED", "false")

from app.database import AsyncSessionLocal, engine, Base
from app.models import (
    User, Addon, Version, SubscriptionTier, AddonTag,
)
from app.utils import slugify


SAMPLE_USERS = [
    {
        "discord_id": "100000000000000001",
        "discord_username": "devadmin",
        "email": "admin@plexdev.local",
        "subscription_tier": SubscriptionTier.PREMIUM,
        "is_admin": True,
        "bio": "PlexAddons platform administrator.",
        "is_verified_developer": True,
    },
    {
        "discord_id": "100000000000000002",
        "discord_username": "prouser",
        "email": "pro@plexdev.local",
        "subscription_tier": SubscriptionTier.PRO,
        "is_admin": False,
        "bio": "Pro tier developer building cool addons.",
    },
    {
        "discord_id": "100000000000000003",
        "discord_username": "freeuser",
        "email": "free@plexdev.local",
        "subscription_tier": SubscriptionTier.FREE,
        "is_admin": False,
    },
]

SAMPLE_ADDONS = [
    {
        "owner_idx": 0,  # devadmin
        "name": "Auto Moderator",
        "description": "Automatically moderate your server with AI-powered content filtering.",
        "tags": [AddonTag.MODERATION.value, AddonTag.AUTOMATION.value],
        "is_public": True,
        "verified": True,
        "versions": [
            {"version": "1.0.0", "description": "Initial release", "days_ago": 30},
            {"version": "1.1.0", "description": "Added word filters", "days_ago": 20},
            {"version": "1.2.0", "description": "AI content analysis", "days_ago": 5},
        ],
    },
    {
        "owner_idx": 0,  # devadmin
        "name": "Music Bot Pro",
        "description": "High quality music streaming from YouTube, Spotify and SoundCloud.",
        "tags": [AddonTag.MUSIC.value, AddonTag.MEDIA.value],
        "is_public": True,
        "verified": True,
        "versions": [
            {"version": "2.0.0", "description": "Major rewrite with queue system", "days_ago": 60},
            {"version": "2.1.0", "description": "Spotify integration", "days_ago": 15},
        ],
    },
    {
        "owner_idx": 1,  # prouser
        "name": "Level System",
        "description": "XP and leveling with role rewards and leaderboards.",
        "tags": [AddonTag.LEVELING.value, AddonTag.FUN.value],
        "is_public": True,
        "verified": False,
        "versions": [
            {"version": "1.0.0", "description": "Basic XP and levels", "days_ago": 45},
            {"version": "1.0.1", "description": "Bug fixes", "days_ago": 40},
            {"version": "1.1.0", "description": "Leaderboard API", "days_ago": 10},
        ],
    },
    {
        "owner_idx": 1,  # prouser
        "name": "Economy Plus",
        "description": "Virtual currency system with shops, trading, and gambling.",
        "tags": [AddonTag.ECONOMY.value, AddonTag.FUN.value],
        "is_public": True,
        "verified": False,
        "versions": [
            {"version": "0.9.0", "description": "Beta release", "days_ago": 25},
            {"version": "1.0.0", "description": "Stable release with shops", "days_ago": 7},
        ],
    },
    {
        "owner_idx": 2,  # freeuser
        "name": "Simple Logger",
        "description": "Log server events to a channel with customizable formats.",
        "tags": [AddonTag.LOGGING.value, AddonTag.UTILITY.value],
        "is_public": True,
        "verified": False,
        "versions": [
            {"version": "1.0.0", "description": "Initial release", "days_ago": 14},
        ],
    },
    {
        "owner_idx": 2,  # freeuser
        "name": "Private Addon",
        "description": "A private addon for testing.",
        "tags": [AddonTag.OTHER.value],
        "is_public": False,
        "verified": False,
        "versions": [
            {"version": "0.1.0", "description": "Draft", "days_ago": 3},
        ],
    },
]


async def seed():
    print("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Check if data already exists
        from sqlalchemy import select, func as sa_func
        result = await db.execute(select(sa_func.count()).select_from(User))
        count = result.scalar()
        if count > 0:
            print(f"Database already has {count} user(s). Skipping seed.")
            print("To re-seed, truncate the tables first.")
            return

        print("Seeding users...")
        users = []
        for data in SAMPLE_USERS:
            user = User(
                discord_id=data["discord_id"],
                discord_username=data["discord_username"],
                email=data.get("email"),
                subscription_tier=data["subscription_tier"],
                is_admin=data.get("is_admin", False),
                bio=data.get("bio"),
                is_verified_developer=data.get("is_verified_developer", False),
            )
            db.add(user)
            users.append(user)
        await db.flush()

        print("Seeding addons and versions...")
        now = datetime.now(timezone.utc)
        for addon_data in SAMPLE_ADDONS:
            owner = users[addon_data["owner_idx"]]
            addon = Addon(
                owner_id=owner.id,
                name=addon_data["name"],
                slug=slugify(addon_data["name"]),
                description=addon_data["description"],
                tags=addon_data["tags"],
                is_public=addon_data["is_public"],
                verified=addon_data["verified"],
                is_active=True,
            )
            db.add(addon)
            await db.flush()

            for ver_data in addon_data["versions"]:
                release = date.today() - timedelta(days=ver_data["days_ago"])
                version = Version(
                    addon_id=addon.id,
                    version=ver_data["version"],
                    release_date=release,
                    download_url=f"https://example.com/downloads/{addon.slug}/{ver_data['version']}.zip",
                    description=ver_data["description"],
                )
                db.add(version)

            print(f"  + {addon.name} ({len(addon_data['versions'])} versions)")

        await db.commit()

    print(f"\nSeed complete!")
    print(f"  Users: {len(SAMPLE_USERS)}")
    print(f"  Addons: {len(SAMPLE_ADDONS)}")
    print(f"  Versions: {sum(len(a['versions']) for a in SAMPLE_ADDONS)}")
    print(f"\nAdmin login: discord_id={SAMPLE_USERS[0]['discord_id']}")


if __name__ == "__main__":
    asyncio.run(seed())
