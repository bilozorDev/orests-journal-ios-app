#!/usr/bin/env python3
"""
Reset the local development database by truncating all tables.
Also clears the Redis cache.

Usage:
    python scripts/reset_db.py

Or via Makefile:
    make reset-db
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
import redis
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_db_connection():
    """Get a sync psycopg2 connection from DATABASE_URL."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL not set in environment")

    # Convert asyncpg URL to psycopg2 format
    # postgresql+asyncpg://user:pass@host:port/db -> postgresql://user:pass@host:port/db
    db_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    # Remove ssl=require for local dev (psycopg2 uses sslmode=require)
    if "localhost" in db_url or "127.0.0.1" in db_url:
        db_url = db_url.replace("?ssl=require", "")

    return psycopg2.connect(db_url)


def reset_database():
    """Truncate all application tables."""
    # All tables in the application (CASCADE handles FK order)
    tables = [
        "notification_logs",
        "user_device_tokens",
        "medication_schedules",
        "pet_medication_doses",
        "pet_medications",
        "pet_feedings",
        "pet_calorie_goals",
        "pet_health_events",
        "pet_health_categories",
        "health_records",
        "pet_foods",
        "pets",
        "invite_attempt_logs",
        "family_members",
        "families",
        "users",
    ]

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Truncate all tables with CASCADE to handle foreign keys
        tables_str = ", ".join(tables)
        cursor.execute(f"TRUNCATE TABLE {tables_str} RESTART IDENTITY CASCADE")
        conn.commit()
        print(f"Truncated {len(tables)} tables:")
        for table in tables:
            print(f"  - {table}")
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Database error: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def clear_redis():
    """Clear the Redis cache."""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    try:
        r = redis.from_url(redis_url)
        r.flushall()
        print("Cleared Redis cache")
    except redis.ConnectionError as e:
        print(f"Redis not available (skipping): {e}")


def main():
    print("Resetting local development database...")
    print("-" * 40)

    reset_database()
    print()
    clear_redis()

    print("-" * 40)
    print("Database reset complete!")


if __name__ == "__main__":
    main()
