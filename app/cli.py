"""Super Admin provisioning. CLI-only, no UI path ever (spec 2).

    uv run python -m app.cli create-super-admin --username root
    uv run python -m app.cli create-super-admin --username root --password s3cr3t
"""

import argparse
import asyncio
import getpass

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Account
from app.security import hash_password


async def _create(username: str, password: str) -> None:
    async with SessionLocal() as db:
        if await db.scalar(select(Account).where(Account.username == username)):
            raise SystemExit(f"username '{username}' already exists")
        db.add(
            Account(
                username=username,
                password_hash=hash_password(password),
                is_super_admin=True,
                org_unit_id=None,
            )
        )
        await db.commit()
    print(f"created super admin '{username}'")


def main() -> None:
    p = argparse.ArgumentParser(prog="app.cli")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create-super-admin")
    c.add_argument("--username", required=True)
    c.add_argument("--password", default=None)
    args = p.parse_args()

    if args.cmd == "create-super-admin":
        pw = args.password or getpass.getpass("password: ")
        if not pw:
            raise SystemExit("empty password")
        asyncio.run(_create(args.username, pw))


if __name__ == "__main__":
    main()
