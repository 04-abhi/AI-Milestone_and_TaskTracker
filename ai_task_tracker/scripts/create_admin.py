"""
Standalone script to create or reset the admin user.

Usage:
    python scripts/create_admin.py
    python scripts/create_admin.py --email custom@admin.com --password MySecret123
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def create_admin(email: str, username: str, password: str, full_name: str):
    from app.db.session import AsyncSessionLocal, init_db
    from app.services.user_service import UserService
    from app.schemas.user import UserCreate
    from app.core.exceptions import ConflictError

    await init_db()

    async with AsyncSessionLocal() as db:
        existing = await UserService.get_by_email(db, email)
        if existing:
            print(f"⚠️  User '{email}' already exists. Updating admin flag...")
            existing.is_admin = True
            existing.is_verified = True
            existing.is_active = True
            await db.commit()
            print(f"✅  User '{email}' is now an admin.")
            return

        try:
            user = await UserService.create(
                db,
                UserCreate(
                    username=username,
                    email=email,
                    password=password,
                    full_name=full_name,
                ),
            )
            user.is_admin = True
            user.is_verified = True
            await db.commit()
            print(f"✅  Admin user created:")
            print(f"    Email:    {email}")
            print(f"    Username: {username}")
            print(f"    Password: {password}")
        except ConflictError as e:
            print(f"❌  {e.message}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create or promote an admin user")
    parser.add_argument("--email", default="admin@aitasktracker.com")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="Admin@123456")
    parser.add_argument("--full-name", default="System Administrator")
    args = parser.parse_args()

    asyncio.run(create_admin(args.email, args.username, args.password, args.full_name))
