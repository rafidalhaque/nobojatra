from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Account
from app.permissions import has_permission
from app.security import decode_token

DbDep = Annotated[AsyncSession, Depends(get_db)]

_UNAUTH = HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")


def _extract_token(request: Request) -> str:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:]
    if not token:
        raise _UNAUTH
    return token


async def get_current_account(request: Request, db: DbDep) -> Account:
    try:
        payload = decode_token(_extract_token(request))
    except jwt.PyJWTError:
        raise _UNAUTH
    account = await db.get(Account, payload.get("sub"))
    if account is None:
        raise _UNAUTH

    # Scope every RLS-guarded query in this request's transaction. is_local=true
    # so it resets on the get_db commit/rollback.
    await db.execute(
        text(
            "SELECT set_config('app.current_org_unit', :ou, true), "
            "set_config('app.is_super_admin', :sa, true)"
        ),
        {
            "ou": str(account.org_unit_id) if account.org_unit_id else "",
            "sa": "on" if account.is_super_admin else "off",
        },
    )
    return account


AccountDep = Annotated[Account, Depends(get_current_account)]


def require_super_admin(account: AccountDep) -> Account:
    if not account.is_super_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Super Admin only")
    return account


SuperAdminDep = Annotated[Account, Depends(require_super_admin)]


def require_permission(key: str):
    async def _dep(account: AccountDep, db: DbDep) -> Account:
        if not await has_permission(db, account, key):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Missing permission: {key}")
        return account

    return _dep
