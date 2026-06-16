import asyncio
import getpass
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(ROOT))

from sqlalchemy import or_, select  # noqa: E402

from app.models.database import SessionLocal, init_db  # noqa: E402
from app.models.tables import User  # noqa: E402
from app.services.security import hash_password  # noqa: E402


async def main() -> None:
    await init_db()
    username = input("Username: ").strip()
    email = input("Email: ").strip()
    password = getpass.getpass("Password: ")
    async with SessionLocal() as db:
        user = (
            await db.execute(select(User).where(or_(User.username == username, User.email == email)))
        ).scalar_one_or_none()
        if user is None:
            user = User(
                username=username,
                email=email,
                password_hash=hash_password(password),
                role="admin",
            )
            db.add(user)
        else:
            user.role = "admin"
            if password:
                user.password_hash = hash_password(password)
        await db.commit()
    print("Admin account is ready.")


if __name__ == "__main__":
    asyncio.run(main())

