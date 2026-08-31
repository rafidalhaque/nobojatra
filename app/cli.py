"""Super Admin provisioning + password reset. CLI-only, no UI path ever (spec 2).

    uv run python -m app.cli create-super-admin --username root
    uv run python -m app.cli create-super-admin --username root --password s3cr3t
    uv run python -m app.cli set-password --username root            # reset any account
"""

import argparse
import asyncio
import getpass
import re

from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import Account
from app.security import hash_password, verify_password


def _db_target() -> str:
    # host/name only, no credentials — so you can see which DB you're writing to
    url = get_settings().database_url
    m = re.search(r"@([^/]+)/(\S+)", url)
    return f"{m.group(1)}/{m.group(2)}" if m else "?"


def _prompt_password() -> str:
    pw = getpass.getpass("password: ")
    if pw != getpass.getpass("confirm : "):
        raise SystemExit("passwords did not match")
    if not pw:
        raise SystemExit("empty password")
    return pw


async def _create(username: str, password: str) -> None:
    async with SessionLocal() as db:
        if await db.scalar(select(Account).where(Account.username == username)):
            raise SystemExit(f"username '{username}' already exists on {_db_target()}")
        db.add(
            Account(
                username=username,
                password_hash=hash_password(password),
                is_super_admin=True,
                org_unit_id=None,
            )
        )
        await db.commit()
    print(f"created super admin '{username}' on {_db_target()}")


async def _set_password(username: str, password: str) -> None:
    async with SessionLocal() as db:
        account = await db.scalar(select(Account).where(Account.username == username))
        if account is None:
            raise SystemExit(f"no account '{username}' on {_db_target()}")
        account.password_hash = hash_password(password)
        await db.commit()
        ok = verify_password(password, account.password_hash)
    print(f"password updated for '{username}' on {_db_target()} (self-check: {'ok' if ok else 'FAILED'})")


def main() -> None:
    p = argparse.ArgumentParser(prog="app.cli")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("create-super-admin", "set-password"):
        s = sub.add_parser(name)
        s.add_argument("--username", required=True)
        s.add_argument("--password", default=None, help="skip the interactive prompt")
    args = p.parse_args()

    pw = args.password if args.password is not None else _prompt_password()
    if not pw:
        raise SystemExit("empty password")

    if args.cmd == "create-super-admin":
        asyncio.run(_create(args.username, pw))
    elif args.cmd == "set-password":
        asyncio.run(_set_password(args.username, pw))


if __name__ == "__main__":
    main()
