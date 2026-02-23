"""Shared test fixtures for PlexAddons API tests."""
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Set test environment variables before importing app modules
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("DISCORD_CLIENT_ID", "test-client-id")
os.environ.setdefault("DISCORD_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("DISCORD_REDIRECT_URI", "http://localhost:3000/auth/callback")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_fake")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test_fake")
os.environ.setdefault("STRIPE_PRO_PRICE_ID", "price_test_pro")
os.environ.setdefault("STRIPE_PREMIUM_PRICE_ID", "price_test_premium")
os.environ.setdefault("PAYPAL_CLIENT_ID", "test-paypal-id")
os.environ.setdefault("PAYPAL_CLIENT_SECRET", "test-paypal-secret")
os.environ.setdefault("PAYPAL_WEBHOOK_ID", "test-webhook-id")
os.environ.setdefault("PAYPAL_PRO_PLAN_ID", "P-test-pro")
os.environ.setdefault("PAYPAL_PREMIUM_PLAN_ID", "P-test-premium")
os.environ.setdefault("ENVIRONMENT", "testing")
os.environ.setdefault("EMAIL_ENABLED", "false")

from app.database import Base
from app.core.security import create_access_token
from app.models import User, SubscriptionTier


# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def db_engine():
    """Create a test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Create a test database session."""
    session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession):
    """Create a test user."""
    user = User(
        discord_id="123456789",
        discord_username="testuser",
        discord_avatar=None,
        email="test@example.com",
        subscription_tier=SubscriptionTier.FREE,
        is_admin=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession):
    """Create an admin test user."""
    user = User(
        discord_id="987654321",
        discord_username="adminuser",
        discord_avatar=None,
        email="admin@example.com",
        subscription_tier=SubscriptionTier.PREMIUM,
        is_admin=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User):
    """Generate auth headers for the test user."""
    token = create_access_token({"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(admin_user: User):
    """Generate auth headers for the admin user."""
    token = create_access_token({"sub": str(admin_user.id)})
    return {"Authorization": f"Bearer {token}"}
