#!/usr/bin/env python3
"""CLI script to create users for testing.

Usage:
    uv run python scripts/create_user.py user@example.com password123
    uv run python scripts/create_user.py admin@example.com password123 --admin
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add src to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import Settings
from src.infrastructure.database.connection import init_database
from src.modules.auth.repository import UserRepository
from src.modules.auth.schemas import UserCreate
from src.modules.auth.service import AuthService


async def create_user(email: str, password: str, is_admin: bool = False) -> None:
    """Create a user in the database.

    Args:
        email: User's email address.
        password: User's password (will be hashed).
        is_admin: Whether to create an admin user.
    """
    # Load settings
    settings = Settings()

    # Check for JWT secret (required for auth service)
    if settings.jwt_secret_key is None:
        print("✗ Error: JWT_SECRET_KEY not set in .env", file=sys.stderr)
        print("  Please add JWT_SECRET_KEY to your .env file", file=sys.stderr)
        sys.exit(1)

    # Initialize database
    db = await init_database(settings.database_path)

    try:
        # Create repository and service
        repo = UserRepository(db)
        auth_service = AuthService(
            repository=repo,
            jwt_secret=settings.jwt_secret_key.get_secret_value(),
        )

        # Create user
        user_data = UserCreate(
            email=email,
            password=password,
            is_admin=is_admin,
        )

        user = await auth_service.register(user_data)

        # Print success message
        role = "admin" if user.is_admin else "user"
        print(f"✓ Created {role}: {user.email}")
        print(f"  User ID: {user.id}")
        print(f"  Created at: {user.created_at}")

    except ValueError as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await db.disconnect()


def main() -> None:
    """Parse arguments and create user."""
    parser = argparse.ArgumentParser(
        description="Create a user for testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a regular user
  uv run python scripts/create_user.py user@example.com mypassword

  # Create an admin user
  uv run python scripts/create_user.py admin@example.com adminpass --admin

  # Create multiple test users
  uv run python scripts/create_user.py test1@test.com pass123
  uv run python scripts/create_user.py test2@test.com pass123
        """,
    )

    parser.add_argument("email", help="User's email address")
    parser.add_argument("password", help="User's password (min 8 characters)")
    parser.add_argument(
        "--admin",
        action="store_true",
        help="Create user with admin privileges",
    )

    args = parser.parse_args()

    # Validate password length
    if len(args.password) < 8:
        print("✗ Error: Password must be at least 8 characters", file=sys.stderr)
        sys.exit(1)

    # Create user
    asyncio.run(create_user(args.email, args.password, args.admin))


if __name__ == "__main__":
    main()
