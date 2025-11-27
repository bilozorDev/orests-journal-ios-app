from typing import AsyncGenerator, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import get_settings

settings = get_settings()

# Create async engine for Neon PostgreSQL
# Configuration to fix asyncpg + PostgreSQL enum type issues:
# - jit=off: Prevents slow enum type introspection (https://github.com/MagicStack/asyncpg/issues/1078)
# - prepared_statement_cache_size=0: Disables prepared statement caching to avoid InvalidCachedStatementError
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args={
        "server_settings": {
            "jit": "off",
            "plan_cache_mode": "force_custom_plan",
        },
        "prepared_statement_cache_size": 0,
        "statement_cache_size": 0,
    },
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def set_rls_user(session: AsyncSession, user_id: str) -> None:
    """
    Set the current user ID for Row-Level Security (RLS) policies.

    This must be called at the start of each request that requires RLS
    protection. It sets a session-level variable that RLS policies use
    to determine which rows the user can access.

    Args:
        session: The database session
        user_id: The authenticated user's UUID as a string
    """
    # SET commands don't support parameterized queries in PostgreSQL
    # Validate UUID format to prevent SQL injection
    from uuid import UUID as UUID_validator
    try:
        UUID_validator(user_id)  # Validates format
    except ValueError:
        raise ValueError(f"Invalid user_id format: {user_id}")

    # Safe to use string formatting since we validated the UUID format
    await session.execute(text(f"SET LOCAL app.current_user_id = '{user_id}'"))


async def clear_rls_user(session: AsyncSession) -> None:
    """
    Clear the current user ID for Row-Level Security (RLS) policies.

    This should be called at the end of each request or when the user
    context is no longer valid.

    Args:
        session: The database session
    """
    await session.execute(text("RESET app.current_user_id"))
